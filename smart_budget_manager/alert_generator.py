# finance/alert_generator.py

from typing import Optional

class AlertGenerator:
    
    @staticmethod
    def generate_alert(budget_status: list) -> Optional[str]:
        """Generate intelligent alerts based on spending"""
        alerts = []
        
        for item in budget_status:
            category = item['category']
            usage = item['usage_percent']
            spent = item['spent']
            budget = item['budget']
            
            if usage >= 100:
                alerts.append(
                    f"🚨 **BUDGET EXCEEDED**: {category.upper()}\n"
                    f"   Spent: ₹{spent:.2f} / ₹{budget:.2f} ({usage:.1f}%)\n"
                    f"   You've overspent by ₹{spent - budget:.2f}!"
                )
            elif usage >= 90:
                alerts.append(
                    f"⚠️  **WARNING**: {category.upper()} budget at {usage:.1f}%\n"
                    f"   Spent: ₹{spent:.2f} / ₹{budget:.2f}\n"
                    f"   Only ₹{budget - spent:.2f} remaining!"
                )
            elif usage >= 75:
                alerts.append(
                    f"ℹ️  {category.capitalize()}: {usage:.1f}% used (₹{spent:.2f} / ₹{budget:.2f})"
                )
        
        return "\n\n".join(alerts) if alerts else None