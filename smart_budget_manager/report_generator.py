# smart_budget_manager/report_generator.py

from smart_budget_manager.spending_analyser import SpendingAnalyzer


def generate_monthly_report(user_id: str) -> str:
    """
    Generate comprehensive spending report
    
    ✅ FIXED: Creates own finance DB connection
    
    Args:
        user_id: User identifier
        
    Returns:
        Formatted report string
    """
    # ✅ CRITICAL FIX: Get finance database connection
    from db_.neo4j_finance import get_finance_db
    finance_db = get_finance_db()
    
    # ✅ Pass finance connection to analyzer
    analyzer = SpendingAnalyzer(finance_db.kg)
    
    spending = analyzer.get_monthly_spending(user_id)
    budget_status = analyzer.check_budget_status(user_id)
    
    report = "📊 **Monthly Spending Report**\n\n"
    
    if not spending:
        report += "No transactions recorded this month.\n"
        return report
    
    # Total spending
    total = sum(item['total_spent'] for item in spending)
    report += f"**Total Spent:** ₹{total:,.2f}\n\n"
    
    # Category breakdown
    report += "**Category Breakdown:**\n"
    for item in spending:
        report += f"• {item['category'].capitalize()}: ₹{item['total_spent']:,.2f} "
        report += f"({item['transaction_count']} transactions)\n"
    
    # Budget comparison
    if budget_status:
        report += "\n**Budget Status:**\n"
        for item in budget_status:
            cat = item['category'].capitalize()
            usage = item['usage_percent']
            spent = item['spent']
            budget = item['budget']
            remaining = budget - spent
            
            # Emoji based on usage
            if usage >= 100:
                emoji = "🚨"
            elif usage >= 75:
                emoji = "⚠️"
            else:
                emoji = "✅"
            
            report += f"{emoji} {cat}: {usage:.1f}% used "
            report += f"(₹{spent:,.2f} / ₹{budget:,.2f}, ₹{remaining:,.2f} left)\n"
    
    return report