from llm.run_agent import run_agent
from agent.finance_agent import finance_transaction_handler, handle_budget_setup
from typing import Dict, Any, Literal
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from email_scam_handler import handle_email_scam_check, format_email_scam_response
from email_payment_handler_integrated import (
    handle_email_payment_extraction, 
    format_email_payment_response
)

def _is_greeting(query: str) -> bool:
    """
    Detect if query is a greeting/casual conversation starter
    Args:
        query: User's query
    Returns:
        True if it's a greeting
    """
    query_lower = query.lower().strip()
 
    greetings = [
        'hi', 'hello', 'hey', 'namaste', 'namaskar',
        'good morning', 'good afternoon', 'good evening',
        'hii', 'hiii', 'heyyy', 'helo', 'hlo',
        'hola', 'sup', 'wassup', "what's up",
        'kaise ho', 'kya haal hai', 'how are you',
        'start', 'begin', 'help'
    ]
    
    if query_lower in greetings:
        return True
    
    if any(query_lower.startswith(g) for g in greetings):
        return True

    if len(query_lower) <= 10 and '?' not in query_lower:
        return True
    
    return False

def handle_greeting(query: str, user_id: str) -> Dict[str, Any]:
    """
    Handle greetings with personalized, friendly response in user's language
    
    Args:
        query: User's query
        user_id: User identifier
        
    Returns:
        Greeting response
    """
    from financial_explainer.language_handler import get_language_handler
    

    language_handler = get_language_handler()
    lang_detection = language_handler.detect_language(query)
    
    print(f"[GreetingHandler] Language: {lang_detection.should_respond_in}")
 
    try:
        from smart_budget_manager.spending_analyser import SpendingAnalyzer
        from db_.neo4j_finance import get_finance_db
        
        finance_db = get_finance_db()
        analyzer = SpendingAnalyzer(finance_db.kg)
        spending_summary = analyzer.get_monthly_spending(user_id)
        
        has_transactions = len(spending_summary) > 0 if spending_summary else False
    except:
        has_transactions = False
    
    # Generate greeting based on language
    if lang_detection.should_respond_in == "hinglish":
        greeting = _get_hinglish_greeting(has_transactions)
    elif lang_detection.should_respond_in == "hindi":
        greeting = _get_hindi_greeting(has_transactions)
    else:
        greeting = _get_english_greeting(has_transactions)
    
    return {
        "answer": greeting,
        "type": "greeting"
    }

def _get_english_greeting(has_transactions: bool) -> str:
    """Get English greeting"""
    greeting = "👋 **Hello! I'm FinGuard** - Your Personal Finance Assistant\n\n"
    
    if has_transactions:
        greeting += "**Welcome back!** I can help you with:\n\n"
    else:
        greeting += "**Nice to meet you!** I'm here to help with:\n\n"
    
    greeting += """🏛️ **Government Schemes**
   • Check eligibility for schemes
   • Learn about benefits & subsidies
   • Get application guidance

💰 **Finance Tracking**
   • Log your expenses (e.g., "spent 50 on tea")
   • Check spending reports ("how much spent this month?")
   • Set budgets for different categories

🛡️ **Scam Detection**
   • Analyze suspicious messages
   • Learn about common scams
   • Stay safe from fraud

💡 **Financial Education**
   • Understand FD, PPF, mutual funds
   • Get personalized advice
   • Learn about investments

**How can I help you today?**

*Try asking:*
• "What is FD?"
• "Show my spending"
• "Am I eligible for MUDRA loan?"
• "Check if this message is a scam"
"""
    
    return greeting


def _get_hinglish_greeting(has_transactions: bool) -> str:
    """Get Hinglish greeting"""
    greeting = "👋 **Namaste! Main FinGuard hoon** - Aapka Personal Finance Assistant\n\n"
    
    if has_transactions:
        greeting += "**Welcome back!** Main aapki help kar sakta hoon:\n\n"
    else:
        greeting += "**Aapse mil ke achha laga!** Main yeh sab kar sakta hoon:\n\n"
    
    greeting += """🏛️ **Government Schemes**
   • Schemes ke liye eligibility check karo
   • Benefits aur subsidies ke baare mein jaano
   • Application guidance lo

💰 **Finance Tracking**
   • Expenses log karo (jaise "spent 50 on tea")
   • Spending reports dekho ("kitna spend kiya is mahine?")
   • Alag categories ke liye budget set karo

🛡️ **Scam Detection**
   • Suspicious messages analyze karo
   • Common scams ke baare mein jaano
   • Fraud se bach ke raho

💡 **Financial Education**
   • FD, PPF, mutual funds samjho
   • Personalized advice lo
   • Investments ke baare mein seekho

**Aaj main aapki kaise madad kar sakta hoon?**

*Try karo ye questions:*
• "FD kya hai?"
• "Mera spending dikha"
• "Kya main MUDRA loan ke liye eligible hoon?"
• "Check karo kya ye message scam hai"
"""
    
    return greeting


def _get_hindi_greeting(has_transactions: bool) -> str:
    """Get Hindi greeting (for now, returns Hinglish)"""
    # TODO: Implement proper Devanagari Hindi
    return _get_hinglish_greeting(has_transactions)


class QueryClassification(BaseModel):
    category: Literal[
        "government_schemes",
        "transaction_logging", 
        "spending_query",
        "budget_setup",
        "scam_detection",
        "scam_analysis",
        "concept_explanation",
        "email_scam_check",  # ← ADD THIS
        "email_payment_extraction",
        "general_conversation"
    ]  = Field(
        ..., 
        description="Primary category of the user's query"
    )
    
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str = Field(...)


classification_llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)

classification_prompt = ChatPromptTemplate.from_messages([
    ("system", """
You are a query intent classifier for FinGuard, an AI assistant that helps with:
1. Indian government schemes (eligibility, benefits, application process)
2. Personal finance tracking (transactions, budgets, spending analysis)
3. Scam detection and fraud awareness
4. Financial concept education and explanations

Classify the user's query into ONE of these categories:

**general_conversation**: Greetings, casual chat, unclear intent.
CRITICAL INDICATORS (highest priority):
- Single word greetings: "hi", "hello", "hey", "namaste"
- Short greetings: "hi there", "hello ji", "kaise ho"
- Very vague: "help", "start", "what can you do"
- Empty or very short queries (< 10 chars)
Examples:
✅ general_conversation: "hi"
✅ general_conversation: "hello"
✅ general_conversation: "hey there"
✅ general_conversation: "namaste"
✅ general_conversation: "help me"
❌ government_schemes: "help with MUDRA loan" (specific intent)

**government_schemes**: Questions about government schemes, benefits, eligibility, subsidies, yojanas, loans (MUDRA, PMEGP, etc.), rural/urban schemes, women/farmer/MSME schemes, application process, required documents.

**transaction_logging**: User is RECORDING a financial transaction they made.
Clear indicators:
- States a specific amount with action: "I spent 50", "paid 200", "bought for 100"
- Past tense spending with amount: "spent 50 on tea", "paid 200 for auto"
- Recording expenses: "₹100 for lunch", "coffee cost 20"

**spending_query**: User is ASKING about their past spending/expenses.
CRITICAL INDICATORS (high priority):
- Questions about spending: "how much did I spend?", "what did I spend on?"
- Time-specific queries: "today", "yesterday", "this week", "last 7 days", "this month"
- Requests for reports: "show my spending", "monthly expenses", "daily report"
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
- Contains actual suspicious content: links, phone numbers, offers

**concept_explanation**: User wants to UNDERSTAND a financial concept/product.
CRITICAL INDICATORS (high priority):
- "What is [financial term]": FD, mutual fund, SIP, PPF, ELSS, NPS, insurance
- "Explain [concept]": any financial product or investment term
- "Tell me about": financial products, investment options
- "How does [product] work"
- "Should I invest in": seeking advice on financial products
- "Is [product] good": asking for evaluation of financial instruments
- "Difference between": comparing financial products
- "What does [term] mean": financial jargon
Examples:
✅ concept_explanation: "What is FD?"
✅ concept_explanation: "Explain mutual funds to me"
✅ concept_explanation: "Should I invest in PPF or NPS?"
✅ concept_explanation: "Tell me about SIP"
✅ concept_explanation: "How does ELSS work?"
✅ concept_explanation: "Is term insurance good for me?"
❌ government_schemes: "Am I eligible for MUDRA loan?" (scheme eligibility)
❌ transaction_logging: "I invested 5000 in FD" (recording transaction)
    
**email_scam_check**: User wants to check emails for scams.
CRITICAL INDICATORS:
- "check my emails"
- "scan my inbox"
- "analyze my emails"
- "are my emails safe"
- "email scam check"
- "check for phishing emails"
Examples:
✅ email_scam_check: "Check my emails for scams"
✅ email_scam_check: "Scan my inbox"
✅ email_scam_check: "Are my recent emails safe?"

**email_payment_extraction**: User wants to extract payment transactions from emails.
CRITICAL INDICATORS:
- "extract payments from emails"
- "scan my emails for transactions"
- "check my email for payments"
- "import transactions from gmail"
- "auto-log email payments"
- "find payments in my inbox"
Examples:
✅ email_payment_extraction: "Extract payments from my emails"
✅ email_payment_extraction: "Scan my inbox for transactions"
✅ email_payment_extraction: "Import UPI transactions from Gmail"
✅ email_payment_extraction: "Check my emails and add payments to database"

CRITICAL RULES:
1. "spent for this month" = spending_query (asking about history)
2. "spent 50 on tea" = transaction_logging (recording new transaction)
3. If query contains ACTUAL suspicious content to analyze → scam_analysis
4. If query asks ABOUT scams in general → scam_detection
5. If query asks to EXPLAIN/UNDERSTAND financial concept → concept_explanation
6. "what is [financial term]" = concept_explanation (NOT general_conversation)
7. If query mentions schemes/yojanas/eligibility → ALWAYS government_schemes
8. Confidence should be HIGH (>0.8) when intent is clear

Return classification with reasoning.
"""),
    ("human", "Query: {query}")
])

classifier_chain = classification_prompt | classification_llm.with_structured_output(QueryClassification)


def classify_query(query: str) -> QueryClassification:
    """Use LLM to intelligently classify the query intent."""
    try:
        classification = classifier_chain.invoke({"query": query})
        
        print(f"[QueryClassifier] Category: {classification.category}")
        print(f"[QueryClassifier] Confidence: {classification.confidence:.2f}")
        print(f"[QueryClassifier] Reasoning: {classification.reasoning}")
        
        return classification
        
    except Exception as e:
        print(f"[QueryClassifier] ❌ Error: {e}")
        return QueryClassification(
            category="general_conversation",
            confidence=0.5,
            reasoning=f"Classification failed: {str(e)}"
        )


def router_feature(req: Dict[str, Any]) -> Dict[str, Any]:
    """
    Intelligent feature router using LLM-based query classification.
    NOW INCLUDES FINANCIAL CONCEPT EXPLANATION.
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
    
    elif classification.category == "concept_explanation":
        print(f"[FeatureRouter] → CONCEPT EXPLANATION")
        return handle_concept_explanation_request(query, user_id)
    
    elif classification.category == "email_scam_check":
        print(f"[FeatureRouter] → EMAIL SCAM CHECK")
        return handle_email_scam_request(query, user_id)
    
    elif classification.category == "email_payment_extraction":
        print(f"[FeatureRouter] → EMAIL PAYMENT EXTRACTION")
        return handle_email_payment_request(query, user_id)
    
    else:  # general_conversation or low confidence
        # Check if it's actually a greeting
        if _is_greeting(query):
            print(f"[FeatureRouter] → GREETING")
            return handle_greeting(query, user_id)
        
        # Low confidence - but NOT a greeting
        if classification.confidence < 0.6:
            print(f"[FeatureRouter] → SCHEMES (low confidence fallback)")
            return run_agent(query, user_id)
        
        # General conversation
        print(f"[FeatureRouter] → GENERAL CONVERSATION")
        return handle_greeting(query, user_id)


def handle_transaction_request(query: str, user_id: str) -> Dict[str, Any]:
    """Handle transaction logging requests"""
    from agent.class_agent import AgentState
    from langchain_core.messages import HumanMessage
    
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
        "type": "spending_report"
    }


def handle_budget_request(query: str, user_id: str) -> Dict[str, Any]:
    """Handle budget setup requests"""
    from agent.class_agent import AgentState
    from langchain_core.messages import HumanMessage
    
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


def handle_concept_explanation_request(query: str, user_id: str) -> Dict[str, Any]:
    """
    Handle financial concept explanation requests
    NEW HANDLER FOR CONCEPT EDUCATION
    """
    from agent.financial_explainer_handler import handle_concept_explanation
    from agent.class_agent import AgentState
    from langchain_core.messages import HumanMessage
    
    print(f"[ConceptHandler] Processing concept explanation for user {user_id}")
    
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
        "finance_mode": False
    }
    
    try:
        updated_state = handle_concept_explanation(state, user_id)
        last_message = updated_state["messages"][-1]
        
        return {
            "answer": last_message.content,
            "type": "concept_explanation",
            "user_profile": updated_state.get("user_profile", {})
        }
        
    except Exception as e:
        print(f"[ConceptHandler] ❌ Error: {e}")
        return {
            "answer": "I'm having trouble explaining that concept right now. Could you rephrase your question?",
            "type": "concept_explanation_error"
        }


def handle_scam_analysis(query: str, user_id: str) -> Dict[str, Any]:
    """Handle scam analysis requests"""
    from scam_detector.scam_detector import get_scam_detector
    
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
        
        response = f"{emoji} **Scam Analysis Report**\n\n"
        response += f"**Verdict:** {verdict}\n"
        response += f"**Risk Level:** {result.risk_level}\n"
        response += f"**Confidence:** {result.confidence:.0%}\n\n"
        
        if result.scam_type:
            response += f"**Scam Type:** {result.scam_type}\n\n"
        
        if result.red_flags:
            response += "**⚠️ Red Flags Detected:**\n"
            for flag in result.red_flags[:5]:
                response += f"  • {flag}\n"
            response += "\n"
        
        response += f"**💡 Recommendation:**\n{result.recommendation}\n\n"
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
    """Handle general scam education/awareness queries"""
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

def handle_email_scam_request(query: str, user_id: str) -> Dict[str, Any]:
    """Handle email scam check requests"""
    
    # Extract time parameters
    hours_ago = 24  # default
    max_emails = 10
    
    query_lower = query.lower()
    if "today" in query_lower:
        hours_ago = 12
    elif "yesterday" in query_lower:
        hours_ago = 48
    elif "week" in query_lower or "last 7 days" in query_lower:
        hours_ago = 168
    
    print(f"[EmailScamHandler] Checking last {hours_ago} hours, max {max_emails} emails")
    
    # Process request
    result = handle_email_scam_check(user_id, hours_ago, max_emails)
    formatted_response = format_email_scam_response(result)
    
    return {
        "answer": formatted_response,
        "type": "email_scam_check",
        "analysis_data": result
    }

def handle_email_payment_request(query: str, user_id: str) -> Dict[str, Any]:
    """Handle email payment extraction requests"""
    
    # Extract time parameters from query
    hours_ago = 24  # default
    max_emails = 10
    
    query_lower = query.lower()
    if "today" in query_lower:
        hours_ago = 12
    elif "yesterday" in query_lower:
        hours_ago = 48
    elif "week" in query_lower or "last 7 days" in query_lower:
        hours_ago = 168
    elif "month" in query_lower:
        hours_ago = 720  # 30 days
    
    print(f"[EmailPaymentHandler] Extracting from last {hours_ago} hours, max {max_emails} emails")
    
    # Process request
    result = handle_email_payment_extraction(user_id, hours_ago, max_emails)
    formatted_response = format_email_payment_response(result)
    
    return {
        "answer": formatted_response,
        "type": "email_payment_extraction",
        "extraction_data": result
    }



