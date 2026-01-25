from agent.class_agent import AgentState
from smart_budget_manager.transaction_parser import parse_transaction
from db_.neo4j_finance import FinanceDB
from smart_budget_manager.spending_analyser import SpendingAnalyzer
from smart_budget_manager.alert_generator import AlertGenerator
from langchain_core.messages import AIMessage
from langchain_core.prompts import  ChatPromptTemplate

def finance_transaction_handler(state: AgentState, kg_conn, user_id: str) -> AgentState:
    """Handle finance-related queries and transactions"""
    
    messages = state.get("messages", [])
    last_message = messages[-1].content if messages else ""
    
    # Initialize services
    finance_db = FinanceDB(kg_conn)
    analyzer = SpendingAnalyzer(kg_conn)
    alert_gen = AlertGenerator()
    
    # Check if user is logging a transaction
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
    
    return state



#set budget
def handle_budget_setup(state: AgentState, kg_conn, user_id: str) -> AgentState:
    """Handle budget creation/update via natural language"""
    
    last_message = state.get("messages", [])[-1].content
    
    # Use LLM to parse budget intent
    budget_prompt = ChatPromptTemplate.from_messages([
        ("system", """
Extract budget settings from user message.
Examples:
- "Set food budget to 5000" → category: food, limit: 5000
- "My transport budget is 2000 monthly" → category: transport, limit: 2000
- "I want to spend max 10000 on shopping" → category: shopping, limit: 10000
"""),
        ("human", "{message}")
    ])
    
