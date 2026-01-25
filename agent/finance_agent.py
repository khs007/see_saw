from agent.class_agent import AgentState
from smart_budget_manager.transaction_parser import parse_transaction
from smart_budget_manager.spending_analyser import SpendingAnalyzer
from smart_budget_manager.alert_generator import AlertGenerator
from smart_budget_manager.report_generator import generate_monthly_report
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from typing import Optional


class BudgetIntent(BaseModel):
    """Parsed budget setup intent"""
    category: str = Field(..., description="Budget category (food, transport, shopping, etc.)")
    limit: float = Field(..., description="Monthly budget limit in INR")


def finance_transaction_handler(state: AgentState, kg_conn, user_id: str) -> AgentState:
    """Handle finance-related queries and transactions"""
    
    messages = state.get("messages", [])
    last_message = messages[-1].content if messages else ""
    
    # Initialize services (using singleton to avoid recreating indexes)
    from db_.neo4j_finance import get_finance_db
    finance_db = get_finance_db(kg_conn)
    analyzer = SpendingAnalyzer(kg_conn)
    alert_gen = AlertGenerator()
    
    # Detect query type
    query_lower = last_message.lower()
    
    # Check if it's a spending report query
    if any(kw in query_lower for kw in [
        "total spent", "how much spent", "spending", "expenses",
        "remaining", "left", "balance", "budget status",
        "monthly report", "spending report"
    ]):
        print(f"[FinanceHandler] → Spending report/analysis")
        
        # Check if asking about specific category
        category = None
        for cat in ["food", "transport", "shopping", "entertainment", "bills", "health", "education"]:
            if cat in query_lower:
                category = cat
                break
        
        # Get spending data
        spending_data = analyzer.get_monthly_spending(user_id, category)
        budget_status = analyzer.check_budget_status(user_id)
        
        if not spending_data:
            response = "You haven't logged any transactions yet this month."
        else:
            # Generate response
            total = sum(item['total_spent'] for item in spending_data)
            response = f"📊 **Spending Summary**\n\n"
            response += f"**Total spent this month:** ₹{total:,.2f}\n\n"
            
            if spending_data:
                response += "**By category:**\n"
                for item in spending_data:
                    response += f"• {item['category'].capitalize()}: ₹{item['total_spent']:,.2f} ({item['transaction_count']} transactions)\n"
            
            # Add budget status if available
            if budget_status:
                response += "\n**Budget Status:**\n"
                for item in budget_status:
                    cat = item['category'].capitalize()
                    used = item['usage_percent']
                    spent = item['spent']
                    budget = item['budget']
                    remaining = budget - spent
                    
                    if used >= 100:
                        emoji = "🚨"
                    elif used >= 75:
                        emoji = "⚠️"
                    else:
                        emoji = "✅"
                    
                    response += f"{emoji} {cat}: ₹{spent:,.2f} / ₹{budget:,.2f} ({used:.1f}% used, ₹{remaining:,.2f} remaining)\n"
        
        state["messages"].append(AIMessage(content=response))
        return state
    
    # Otherwise, try to parse as transaction
    transaction = parse_transaction(last_message)
    
    if transaction:
        # Store transaction
        success = finance_db.add_transaction(user_id, transaction.model_dump())
        
        if success:
            # Check budget after transaction
            budget_status = analyzer.check_budget_status(user_id)
            alert = alert_gen.generate_alert(budget_status)
            
            response = f"✅ Transaction logged: ₹{transaction.amount} for {transaction.description}"
            
            if transaction.category:
                response += f" ({transaction.category})"
            
            if alert:
                response += f"\n\n{alert}"
            
            state["messages"].append(AIMessage(content=response))
            state["transaction_data"] = transaction.model_dump()
            state["alert_message"] = alert
        else:
            state["messages"].append(
                AIMessage(content="❌ Failed to log transaction. Please try again.")
            )
    else:
        state["messages"].append(
            AIMessage(content="I couldn't parse that as a transaction. Please try: 'Spent 50 on tea' or 'Paid 200 for auto'")
        )
    
    return state


def handle_budget_setup(state: AgentState, kg_conn, user_id: str) -> AgentState:
    """Handle budget creation/update via natural language"""
    
    last_message = state.get("messages", [])[-1].content
    
    # Use LLM to parse budget intent
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
    
    budget_prompt = ChatPromptTemplate.from_messages([
        ("system", """
Extract budget settings from user message.

RULES:
- Category must be one of: food, transport, shopping, entertainment, bills, health, education, other
- Limit must be a positive number in INR

Examples:
- "Set food budget to 5000" → category: food, limit: 5000
- "My transport budget is 2000 monthly" → category: transport, limit: 2000
- "I want to spend max 10000 on shopping" → category: shopping, limit: 10000
- "budget for this month 500 on food" → category: food, limit: 500
"""),
        ("human", "{message}")
    ])
    
    chain = budget_prompt | llm.with_structured_output(BudgetIntent)
    
    try:
        budget_intent = chain.invoke({"message": last_message})
        
        # Set budget in database (using singleton)
        from db_.neo4j_finance import get_finance_db
        finance_db = get_finance_db(kg_conn)
        success = finance_db.set_budget(
            user_id=user_id,
            category=budget_intent.category,
            monthly_limit=budget_intent.limit
        )
        
        if success:
            response = (
                f"✅ Budget set successfully!\n"
                f"   Category: {budget_intent.category.capitalize()}\n"
                f"   Monthly Limit: ₹{budget_intent.limit:,.2f}"
            )
        else:
            response = "❌ Failed to set budget. Please try again."
            
    except Exception as e:
        print(f"[BudgetSetup] Error: {e}")
        response = "I couldn't understand that budget request. Please try: 'Set food budget to 5000'"
    
    state["messages"].append(AIMessage(content=response))
    return state