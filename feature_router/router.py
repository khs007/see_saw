# feature_router/router.py - UPDATED WITH SCAM DETECTION
"""
Enhanced Feature Router with Scam Detection
Routes queries to appropriate handlers including scam detection
"""

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
        "scam_analysis",  # NEW: For analyzing suspicious messages
        "general_conversation"
    ] = Field(
        ..., 
        description="Primary category of the user's query"
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

**budget_setup**: Setting or modifying budget limits.
Indicators: "set budget", "my budget is", "limit for", "change budget"

**scam_detection**: General questions about fraud, scams, phishing safety.
Indicators: "what is phishing", "how to spot scams", "is this safe", "scam awareness"

**scam_analysis**: User wants to CHECK if a specific message/link/offer is a scam.
CRITICAL INDICATORS (high priority):
- "Is this a scam": user forwarding suspicious message
- "Check this message": providing actual suspicious content
- "I received": followed by suspicious message/SMS/call description
- "Someone asked for": OTP, PIN, bank details, money transfer
- "Should I": trust/click/pay/share followed by suspicious request
- Includes actual suspicious content: links, phone numbers, offers
- "Verify this": followed by message content
- Contains forwarded message text or screenshots

Examples:
✅ scam_analysis: "I got this SMS: 'Your account will be blocked. Click here to verify KYC' - is it real?"
✅ scam_analysis: "Someone called asking for my OTP. Should I give it?"
✅ scam_analysis: "Check if this is scam: You won 10 lakh lottery, send 5000 processing fee"
❌ scam_detection: "How can I protect myself from scams?"
❌ scam_detection: "What is phishing?"

CRITICAL RULES:
1. "spent for this month" = spending_query (asking about history)
2. "spent 50 on tea" = transaction_logging (recording new transaction)
3. If query contains ACTUAL suspicious content to analyze → scam_analysis
4. If query asks ABOUT scams in general → scam_detection
5. "years" in query does NOT mean "rupees"
6. If query mentions schemes/yojanas/eligibility → ALWAYS government_schemes
7. Confidence should be HIGH (>0.8) when intent is clear

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
    
    elif classification.category == "scam_analysis":
        print(f"[FeatureRouter] → SCAM ANALYSIS")
        return handle_scam_analysis(query, user_id)
    
    elif classification.category == "scam_detection":
        print(f"[FeatureRouter] → SCAM EDUCATION")
        return handle_scam_education(query)
    
    else:  # general_conversation or low confidence
        if classification.confidence < 0.6:
            # Low confidence - try government schemes as safe default
            print(f"[FeatureRouter] → SCHEMES (low confidence fallback)")
            return run_agent(query, user_id)
        else:
            print(f"[FeatureRouter] → GENERAL CONVERSATION")
            return {
                "answer": "Hello! I'm FinGuard, your assistant for:\n\n• 🏛️ Government schemes (eligibility, benefits, applications)\n• 💰 Finance tracking (log expenses, check spending, set budgets)\n• 🛡️ Scam detection (analyze suspicious messages, learn about fraud)\n\nHow can I help you today?",
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


def handle_scam_analysis(query: str, user_id: str) -> Dict[str, Any]:
    """
    Handle scam analysis requests - analyze specific suspicious content
    """
    from scam_detector.scam_detector import get_scam_detector
    
    print(f"[ScamAnalysisHandler] Analyzing suspicious content for user {user_id}")
    
    try:
        detector = get_scam_detector()
        result = detector.detect_scam(query)
        
        # Format response based on risk level
        if result.risk_level == "CRITICAL":
            emoji = "🚨"
            verdict = "**HIGHLY LIKELY A SCAM**"
        elif result.risk_level == "HIGH":
            emoji = "⛔"
            verdict = "**LIKELY A SCAM**"
        elif result.risk_level == "MEDIUM":
            emoji = "⚠️"
            verdict = "**SUSPICIOUS - EXERCISE CAUTION**"
        else:
            emoji = "✅"
            verdict = "**APPEARS SAFE** (but stay vigilant)"
        
        # Build response
        response = f"{emoji} **Scam Analysis Report**\n\n"
        response += f"**Verdict:** {verdict}\n"
        response += f"**Risk Level:** {result.risk_level}\n"
        response += f"**Confidence:** {result.confidence:.0%}\n\n"
        
        if result.scam_type:
            response += f"**Scam Type:** {result.scam_type}\n\n"
        
        if result.red_flags:
            response += "**⚠️ Red Flags Detected:**\n"
            for flag in result.red_flags[:5]:  # Limit to top 5
                response += f"  • {flag}\n"
            response += "\n"
        
        response += f"**💡 Recommendation:**\n{result.recommendation}\n\n"
        
        # Add general safety tips
        response += "**🛡️ General Safety Tips:**\n"
        response += "• Never share OTP, PIN, CVV, or passwords\n"
        response += "• Banks never ask for sensitive info via SMS/call\n"
        response += "• Verify with official sources before acting\n"
        response += "• Be cautious of urgent/threatening messages\n"
        
        return {
            "answer": response,
            "type": "scam_analysis",
            "scam_result": result.model_dump()
        }
        
    except Exception as e:
        print(f"[ScamAnalysisHandler] ❌ Error: {e}")
        return {
            "answer": "⚠️ I encountered an error while analyzing this message. Please verify any suspicious content with official sources before taking action.",
            "type": "scam_analysis_error"
        }


def handle_scam_education(query: str) -> Dict[str, Any]:
    """
    Handle general scam education/awareness queries
    """
    response = """🛡️ **Scam Awareness & Protection**

**Common Scam Types in India:**

1. **📱 OTP/Banking Scams**
   • Never share OTP, PIN, CVV with anyone
   • Banks NEVER ask for these via call/SMS
   
2. **🎁 Fake Prize/Lottery Scams**
   • "You won a lottery" - you didn't enter
   • Asking for "processing fee" to claim prize
   
3. **🏦 Phishing (Fake Banks/Govt)**
   • Emails/SMS from fake bank websites
   • "KYC update required" with suspicious links
   
4. **📦 Fake Delivery Scams**
   • "Courier stuck, pay customs fee"
   • Fake tracking links
   
5. **💰 Investment Frauds**
   • "Guaranteed returns" schemes
   • Ponzi/pyramid schemes
   
6. **❤️ Romance Scams**
   • Online relationships leading to money requests

**🚨 Red Flags to Watch For:**
• Urgent/threatening language
• Too-good-to-be-true offers
• Requests for sensitive information
• Suspicious links (verify domain)
• Poor grammar in "official" messages
• Pressure to act immediately

**✅ How to Protect Yourself:**
1. Verify sender through official channels
2. Never click unknown links
3. Use two-factor authentication
4. Keep software updated
5. Report suspicious activity to Cyber Cell (1930)

**Need me to analyze a specific message?**
Just send it to me and I'll check if it's a scam!
"""
    
    return {
        "answer": response,
        "type": "scam_education"
    }