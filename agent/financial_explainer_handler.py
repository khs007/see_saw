# agent/financial_explainer_handler.py
"""
Handler for financial concept explanation queries
Integrates with existing finance tracking system
"""

from agent.class_agent import AgentState
from langchain_core.messages import AIMessage
from typing import Dict, Any


def handle_concept_explanation(state: AgentState, user_id: str) -> AgentState:
    """
    Handle financial concept explanation queries WITH LANGUAGE DETECTION
    
    Args:
        state: Current agent state
        user_id: User identifier
        
    Returns:
        Updated agent state with explanation in user's language
    """
    from financial_explainer.concept_explainer import get_concept_explainer
    from financial_explainer.language_handler import get_language_handler
    from smart_budget_manager.spending_analyser import SpendingAnalyzer
    from db_.neo4j_finance import get_finance_db
    
    messages = state.get("messages", [])
    query = messages[-1].content if messages else ""
    
    print(f"[ConceptExplainer] Processing query: {query}")
    
    # Detect language preference
    language_handler = get_language_handler()
    lang_detection = language_handler.detect_language(query)
    
    print(f"[ConceptExplainer] Language: {lang_detection.primary_language} ({lang_detection.script})")
    print(f"[ConceptExplainer] Will respond in: {lang_detection.should_respond_in}")
    
    # Get user's spending data
    try:
        finance_db = get_finance_db()
        analyzer = SpendingAnalyzer(finance_db.kg)
        
        # Get spending summary
        spending_summary = analyzer.get_monthly_spending(user_id)
        budget_status = analyzer.check_budget_status(user_id)
        
        # Format spending data for explainer
        total_spent = sum(item['total_spent'] for item in spending_summary) if spending_summary else 0
        by_category = {item['category']: item['total_spent'] for item in spending_summary} if spending_summary else {}
        
        # Estimate income (you might want to store this in user profile)
        # For now, we'll estimate based on budget limits
        estimated_income = sum(item['budget'] for item in budget_status) if budget_status else total_spent * 1.5
        
        spending_data = {
            'total_spent': total_spent,
            'by_category': by_category,
            'income': estimated_income
        }
        
    except Exception as e:
        print(f"[ConceptExplainer] ⚠️ Could not fetch spending data: {e}")
        # Fallback to generic data
        spending_data = {
            'total_spent': 15000,
            'by_category': {'food': 5000, 'transport': 3000, 'shopping': 4000},
            'income': 30000
        }
    
    # Get explanation
    explainer = get_concept_explainer()
    
    try:
        explanation = explainer.explain_concept(
            concept_query=query,
            user_spending_data=spending_data
        )
        
        # Format response in user's preferred language
        print(f"[ConceptHandler] Formatting response in: {lang_detection.should_respond_in}")
        
        response = language_handler.format_vernacular_response(
            explanation=explanation.model_dump(),
            language_pref=lang_detection.should_respond_in,
            spending_data=spending_data
        )
        
        print(f"[ConceptHandler] Response formatted, length: {len(response)} chars")
        print(f"[ConceptHandler] First 200 chars: {response[:200]}")
        
        state["messages"].append(AIMessage(content=response))
        
    except Exception as e:
        print(f"[ConceptExplainer] ❌ Error: {e}")
        state["messages"].append(
            AIMessage(content="I'm having trouble explaining that concept right now. Could you rephrase your question?")
        )
    
    return state


def format_explanation_response(explanation, spending_data: Dict[str, Any]) -> str:
    """
    Format the explanation into a user-friendly response
    
    Args:
        explanation: ConceptExplanation object
        spending_data: User's spending data
        
    Returns:
        Formatted response string
    """
    response = f"💡 **Understanding {explanation.concept}**\n\n"
    
    # Simple explanation
    response += f"**What it means:**\n{explanation.simple_explanation}\n\n"
    
    # Personalized context
    response += f"**For your situation:**\n{explanation.personalized_context}\n\n"
    
    # Practical example
    if explanation.practical_example:
        response += f"**Practical Example:**\n{explanation.practical_example}\n\n"
    
    # Key points
    if explanation.key_points:
        response += "**Key Points to Remember:**\n"
        for i, point in enumerate(explanation.key_points, 1):
            response += f"{i}. {point}\n"
        response += "\n"
    
    # Personalized recommendation
    response += f"**My Suggestion:**\n{explanation.recommendation}\n"
    
    # Risk note if applicable
    if explanation.risk_note:
        response += f"\n {explanation.risk_note}\n"
    
    # Add spending summary
    total = spending_data.get('total_spent', 0)
    income = spending_data.get('income', 0)
    if total > 0:
        savings = income - total
        savings_rate = (savings / income * 100) if income > 0 else 0
        response += f"\n📊 **Your Current Finances:**\n"
        response += f"• Monthly Spending: ₹{total:,.0f}\n"
        response += f"• Estimated Savings: ₹{savings:,.0f} ({savings_rate:.1f}%)\n"
    
    return response


def should_explain_concept(query: str) -> bool:
    """
    Determine if query is asking for concept explanation
    
    Args:
        query: User's query
        
    Returns:
        True if query is asking about a financial concept
    """
    query_lower = query.lower()
    
    # Concept keywords
    concept_keywords = [
        'what is', 'what are', 'explain', 'tell me about',
        'how does', 'what does', 'meaning of',
        'fd', 'fixed deposit', 'mutual fund', 'sip', 'ppf',
        'elss', 'nps', 'insurance', 'term insurance',
        'should i invest', 'is it good'
    ]
    
    return any(keyword in query_lower for keyword in concept_keywords)