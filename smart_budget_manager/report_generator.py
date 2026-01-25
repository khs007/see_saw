
from smart_budget_manager.spending_analyser import SpendingAnalyzer


def generate_monthly_report(user_id: str, kg_conn) -> str:
    """Generate comprehensive spending report"""
    
    analyzer = SpendingAnalyzer(kg_conn)
    spending = analyzer.get_monthly_spending(user_id)
    budget_status = analyzer.check_budget_status(user_id)
    
    report = "📊 **Monthly Spending Report**\n\n"
    
    for item in spending:
        report += f"**{item['category'].capitalize()}**: ₹{item['total_spent']:.2f} ({item['transaction_count']} transactions)\n"
    
    # Add budget comparison
    # ... format nicely
    
    return report


