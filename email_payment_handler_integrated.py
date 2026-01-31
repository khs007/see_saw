"""
Email Payment Extraction Handler
Integrates UPI transaction scanning with finance database
"""

from typing import Dict, Any


def handle_email_payment_extraction(user_id: str, hours_ago: int = 24, max_emails: int = 10) -> Dict[str, Any]:
    """
    Extract payment transactions from emails and auto-log to finance DB
    
    Args:
        user_id: User identifier
        hours_ago: Fetch emails from last N hours (default: 24)
        max_emails: Maximum emails to analyze (default: 10)
        
    Returns:
        Dictionary with extraction results
    """
    try:
        # Import UPI scanner (already exists in codebase)
        from Project_jan.upi_transaction_scanner import get_upi_scanner
        
        # Get scanner instance
        scanner = get_upi_scanner()
        
        # Scan and import transactions
        print(f"[EmailPaymentHandler] Scanning emails for user {user_id}")
        result = scanner.scan_and_import(
            user_id=user_id,
            hours_ago=hours_ago,
            max_emails=max_emails
        )
        
        return result
        
    except ImportError as e:
        return {
            "success": False,
            "error": "dependencies_missing",
            "message": str(e),
            "help": "Install required packages: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
        }
    except Exception as e:
        print(f"[EmailPaymentHandler] ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "error": "extraction_failed",
            "message": f"Email payment extraction failed: {str(e)}"
        }


def format_email_payment_response(extraction_result: Dict[str, Any]) -> str:
    """
    Format email payment extraction results into user-friendly response
    
    Args:
        extraction_result: Result from handle_email_payment_extraction
        
    Returns:
        Formatted response string
    """
    if not extraction_result.get("success"):
        error_msg = extraction_result.get("message", "Unknown error")
        help_msg = extraction_result.get("help", "")
        
        response = f"❌ **Email Payment Extraction Failed**\n\n"
        response += f"{error_msg}\n"
        if help_msg:
            response += f"\n💡 {help_msg}\n"
        
        return response
    
    total_emails = extraction_result.get("total_emails", 0)
    transactions_found = extraction_result.get("transactions_found", 0)
    transactions_imported = extraction_result.get("transactions_imported", 0)
    transactions = extraction_result.get("transactions", [])
    
    if total_emails == 0:
        return extraction_result.get("message", "No emails found")
    
    # Header
    response = f"💰 **Email Payment Extraction Report**\n\n"
    response += f"**Summary:**\n"
    response += f"• Total Emails Scanned: {total_emails}\n"
    response += f"• 💳 Payment Transactions Found: {transactions_found}\n"
    response += f"• ✅ Imported to Database: {transactions_imported}\n\n"
    
    # Show sample transactions
    if transactions:
        response += "**Recent Transactions Imported:**\n\n"
        
        for i, txn in enumerate(transactions[:5], 1):  # Show first 5
            amount = txn.get("amount", 0)
            txn_type = txn.get("transaction_type", "DEBIT")
            merchant = txn.get("merchant", "Unknown")
            category = txn.get("category", "other")
            date = txn.get("date", "")
            
            # Emoji based on transaction type
            emoji = "💸" if txn_type == "DEBIT" else "💰"
            
            response += f"{emoji} **₹{amount:.2f}** - {merchant}\n"
            response += f"   Category: {category.capitalize()} | Date: {date}\n"
            if i < len(transactions[:5]):
                response += "\n"
    
    # Total amount
    if transactions:
        total_amount = sum(t.get("amount", 0) for t in transactions)
        response += f"\n**Total Amount Extracted:** ₹{total_amount:,.2f}\n"
    
    # Recommendations
    response += "\n**💡 What's Next:**\n"
    response += "• Check your spending with: 'Show my spending this month'\n"
    response += "• View budget status: 'What's my budget status?'\n"
    response += "• Run this again anytime: 'Extract payments from my emails'\n"
    
    return response