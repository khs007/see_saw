from llm.run_agent import run_agent
from agent.finance_agent import finance_transaction_handler, handle_budget_setup
from retrieval.kg_retrieval import kg_conn
from typing import Dict, Any

# Keywords for different features
FINANCE_KEYWORDS = [
    "spent", "paid", "bought", "expense", "budget",
    "rupees", "₹", "rs", "transaction", "balance",
    "income", "salary", "received", "set budget",
    "spend", "paying", "buy"  # Added variations
]

SCAM_KEYWORDS = ["scam", "fraud", "otp", "phishing", "check", "link"]


def router_feature(req: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main feature router for FinGuard.
    Routes requests to appropriate handlers.
    
    Args:
        req: Dictionary with 'query' and optionally 'user_id'
        
    Returns:
        Dictionary with response
    """
    query = req.get("query", "").lower()
    user_id = req.get("user_id", "default_user")
    
    # Debug logging
    print(f"[FeatureRouter] Query: '{query}'")
    print(f"[FeatureRouter] User ID: '{user_id}'")
    
    # Route to finance handler
    matched_keyword = None
    for keyword in FINANCE_KEYWORDS:
        if keyword in query:
            matched_keyword = keyword
            break
    
    if matched_keyword:
        print(f"[FeatureRouter] → FINANCE (matched: '{matched_keyword}')")
        return handle_finance_request(query, user_id)
    
    # Route to scam detection (placeholder)
    if any(keyword in query for keyword in SCAM_KEYWORDS):
        print(f"[FeatureRouter] → SCAM WARNING")
        return {
            "answer": "⚠️ This appears to be a scam-related query. Please be cautious with any suspicious links or requests for OTP/personal information.",
            "type": "scam_warning"
        }
    
    # Default: Government schemes RAG agent
    print(f"[FeatureRouter] → SCHEMES (RAG agent)")
    return run_agent(query, user_id)


def handle_finance_request(query: str, user_id: str) -> Dict[str, Any]:
    """
    Handle finance-related requests (transactions, budgets).
    
    Args:
        query: User's query
        user_id: User identifier
        
    Returns:
        Response dictionary
    """
    from agent.class_agent import AgentState
    from langchain_core.messages import HumanMessage
    
    print(f"[FinanceHandler] Processing finance query: '{query}'")
    
    # Initialize state
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
    
    # Check if it's a budget setup request
    if any(kw in query for kw in ["set budget", "budget for", "limit for"]):
        print(f"[FinanceHandler] → Budget setup")
        updated_state = handle_budget_setup(state, kg_conn, user_id)
    else:
        # Handle transaction logging
        print(f"[FinanceHandler] → Transaction logging")
        updated_state = finance_transaction_handler(state, kg_conn, user_id)
    
    # Extract response
    last_message = updated_state["messages"][-1]
    
    return {
        "answer": last_message.content,
        "type": "finance",
        "transaction": updated_state.get("transaction_data"),
        "alert": updated_state.get("alert_message")
    }