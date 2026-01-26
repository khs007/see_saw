from llm.run_agent import run_agent
from agent.finance_agent import finance_transaction_handler, handle_budget_setup
from typing import Dict, Any, Literal
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate


# ========================================
# QUERY CLASSIFICATION SCHEMA
# ========================================

class QueryClassification(BaseModel):
    """Classification of user query intent"""
    category: Literal[
        "government_schemes",
        "transaction_logging", 
        "spending_query",
        "budget_setup",
        "scam_detection",
        "general_conversation"
    ] = Field(
        ..., 
        description="Primary category of the user's query"
    )
    
    sub_category: str = Field(
        default="",
        description="Optional sub-category for more specific routing"
    )
    
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0 to 1.0) for this classification"
    )
    
    reasoning: str = Field(
        ...,
        description="Brief explanation of why this category was chosen"
    )


# ========================================
# LLM-BASED QUERY CLASSIFIER
# ========================================

classification_llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0
)

classification_prompt = ChatPromptTemplate.from_messages([
    ("system", """
You are a query intent classifier for FinGuard, an AI assistant that helps with:
1. Indian government schemes (eligibility, benefits, application process)
2. Personal finance tracking (transactions, budgets, spending analysis)
3. Scam detection and fraud awareness

Classify the user's query into ONE of these categories:

**government_schemes**: Questions about government schemes, benefits, eligibility, subsidies, yojanas, loans (MUDRA, PMEGP, etc.), rural/urban schemes, women/farmer/MSME schemes, application process, required documents.

**transaction_logging**: User is RECORDING a financial transaction they made.
Clear indicators:
- States a specific amount with action: "I spent 50", "paid 200", "bought for 100"
- Past tense spending with amount: "spent 50 on tea", "paid 200 for auto"
- Recording expenses: "₹100 for lunch", "coffee cost 20"

**spending_query**: User is ASKING about their past spending/expenses.
Clear indicators:
- Questions about spending: "how much did I spend?", "what did I spend on?"
- Requests for reports: "show my spending", "monthly expenses"
- Balance checks: "how much left?", "budget status"
- Pattern: "spent" WITHOUT a specific amount = query, not logging

**budget_setup**: Setting or modifying budget limits.
Indicators: "set budget", "my budget is", "limit for", "change budget"

**scam_detection**: Asking about fraud, scams, phishing, suspicious links, OTP requests.

**general_conversation**: Greetings, thanks, unclear queries, chit-chat.

CRITICAL RULES:
1. "spent for this month" = spending_query (asking about history)
2. "spent 50 on tea" = transaction_logging (recording new transaction)
3. "woman 22 years old scheme" = government_schemes (NOT finance)
4. "years" in query does NOT mean "rupees"
5. If query mentions schemes/yojanas/eligibility → ALWAYS government_schemes
6. Confidence should be HIGH (>0.8) when intent is clear

Return classification with reasoning.
"""),
    ("human", "Query: {query}")
])

classifier_chain = classification_prompt | classification_llm.with_structured_output(
    QueryClassification
)


def classify_query(query: str) -> QueryClassification:
    """
    Use LLM to intelligently classify the query intent.
    
    Args:
        query: User's query text
        
    Returns:
        QueryClassification with category, confidence, and reasoning
    """
    try:
        classification = classifier_chain.invoke({"query": query})
        
        print(f"[QueryClassifier] Category: {classification.category}")
        print(f"[QueryClassifier] Confidence: {classification.confidence:.2f}")
        print(f"[QueryClassifier] Reasoning: {classification.reasoning}")
        
        return classification
        
    except Exception as e:
        print(f"[QueryClassifier] ❌ Error: {e}")
        # Fallback to safe default
        return QueryClassification(
            category="general_conversation",
            confidence=0.5,
            reasoning=f"Classification failed: {str(e)}"
        )


# ========================================
# MAIN ROUTER
# ========================================

def router_feature(req: Dict[str, Any]) -> Dict[str, Any]:
    """
    Intelligent feature router using LLM-based query classification.
    
    Args:
        req: Dictionary with 'query' and optionally 'user_id'
        
    Returns:
        Dictionary with response
    """
    query = req.get("query", "")
    user_id = req.get("user_id", "default_user")
    
    print(f"\n[FeatureRouter] Query: '{query}'")
    print(f"[FeatureRouter] User ID: '{user_id}'")
    
    # Classify the query using LLM
    classification = classify_query(query)
    
    # Route based on classification
    if classification.category == "government_schemes":
        print(f"[FeatureRouter] → GOVERNMENT SCHEMES")
        return run_agent(query, user_id)
    
    elif classification.category == "transaction_logging":
        print(f"[FeatureRouter] → TRANSACTION LOGGING")
        return handle_transaction_request(query, user_id)
    
    elif classification.category == "spending_query":
        print(f"[FeatureRouter] → SPENDING QUERY")
        return handle_spending_query(query, user_id)
    
    elif classification.category == "budget_setup":
        print(f"[FeatureRouter] → BUDGET SETUP")
        return handle_budget_request(query, user_id)
    
    elif classification.category == "scam_detection":
        print(f"[FeatureRouter] → SCAM DETECTION")
        return {
            "answer": "⚠️ **Scam Alert**\n\nPlease be cautious! Common scam tactics include:\n• Requests for OTP/PIN/passwords\n• Suspicious links or fake websites\n• Too-good-to-be-true offers\n• Urgent requests for money/info\n\nNever share sensitive information. Verify before you trust!",
            "type": "scam_warning"
        }
    
    else:  # general_conversation or low confidence
        if classification.confidence < 0.6:
            # Low confidence - try government schemes as safe default
            print(f"[FeatureRouter] → SCHEMES (low confidence fallback)")
            return run_agent(query, user_id)
        else:
            print(f"[FeatureRouter] → GENERAL CONVERSATION")
            return {
                "answer": "Hello! I'm FinGuard, your assistant for:\n\n• 🏛️ Government schemes (eligibility, benefits, applications)\n• 💰 Finance tracking (log expenses, check spending, set budgets)\n• 🛡️ Scam awareness\n\nHow can I help you today?",
                "type": "greeting"
            }


# ========================================
# SPECIALIZED HANDLERS
# ========================================

def handle_transaction_request(query: str, user_id: str) -> Dict[str, Any]:
    """Handle transaction logging requests"""
    from agent.class_agent import AgentState
    from langchain_core.messages import HumanMessage
    
    print(f"[TransactionHandler] Processing: '{query}'")
    
    state: AgentState = {
        "messages": [HumanMessage(content=query)],
        "chat_memory": "",
        "unstructured_context": "",
        "structured_context": "",
        "question": query,
        "rewrite_count": 0,
        "user_profile": {},
        "target_profile": {},
        "target_scope": "generic",
        "transaction_data": None,
        "budget_status": None,
        "alert_message": None,
        "finance_mode": True
    }
    
    updated_state = finance_transaction_handler(state, None, user_id)
    last_message = updated_state["messages"][-1]
    
    return {
        "answer": last_message.content,
        "type": "finance",
        "transaction": updated_state.get("transaction_data"),
        "alert": updated_state.get("alert_message")
    }


def handle_spending_query(query: str, user_id: str) -> Dict[str, Any]:
    """Handle spending analysis/report requests"""
    from agent.class_agent import AgentState
    from langchain_core.messages import HumanMessage
    
    print(f"[SpendingQueryHandler] Processing: '{query}'")
    
    state: AgentState = {
        "messages": [HumanMessage(content=query)],
        "chat_memory": "",
        "unstructured_context": "",
        "structured_context": "",
        "question": query,
        "rewrite_count": 0,
        "user_profile": {},
        "target_profile": {},
        "target_scope": "generic",
        "transaction_data": None,
        "budget_status": None,
        "alert_message": None,
        "finance_mode": True
    }
    
    # Use same handler but it will detect spending query internally
    updated_state = finance_transaction_handler(state, None, user_id)
    last_message = updated_state["messages"][-1]
    
    return {
        "answer": last_message.content,
        "type": "spending_report"
    }


def handle_budget_request(query: str, user_id: str) -> Dict[str, Any]:
    """Handle budget setup requests"""
    from agent.class_agent import AgentState
    from langchain_core.messages import HumanMessage
    
    print(f"[BudgetHandler] Processing: '{query}'")
    
    state: AgentState = {
        "messages": [HumanMessage(content=query)],
        "chat_memory": "",
        "unstructured_context": "",
        "structured_context": "",
        "question": query,
        "rewrite_count": 0,
        "user_profile": {},
        "target_profile": {},
        "target_scope": "generic",
        "transaction_data": None,
        "budget_status": None,
        "alert_message": None,
        "finance_mode": True
    }
    
    updated_state = handle_budget_setup(state, None, user_id)
    last_message = updated_state["messages"][-1]
    
    return {
        "answer": last_message.content,
        "type": "budget_setup"
    }