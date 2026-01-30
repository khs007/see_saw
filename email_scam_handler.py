"""
Email Scam Handler
Handles email-based scam detection requests
"""

from typing import Dict, Any


def handle_email_scam_check(user_id: str, hours_ago: int = 24, max_emails: int = 10) -> Dict[str, Any]:
    """
    Fetch and analyze recent emails for scams
    
    Args:
        user_id: User identifier
        hours_ago: Fetch emails from last N hours
        max_emails: Maximum emails to analyze
        
    Returns:
        Dictionary with analysis results
    """
    try:
        from email_service import get_email_service
        from email_scam_analyzer import get_email_analyzer
        
        # Get services
        email_service = get_email_service()
        analyzer = get_email_analyzer()
        
        # Authenticate (first time will require OAuth)
        if not email_service.authenticate():
            return {
                "success": False,
                "error": "authentication_failed",
                "message": "Failed to authenticate with Gmail. Please check your credentials.",
                "help": "Make sure credentials.json is in the root directory and has correct permissions."
            }
        
        # Fetch recent emails
        print(f"[EmailScamHandler] Fetching last {max_emails} emails from past {hours_ago} hours")
        emails = email_service.fetch_recent_emails(
            max_results=max_emails,
            hours_ago=hours_ago
        )
        
        if not emails:
            return {
                "success": True,
                "total_analyzed": 0,
                "scams_detected": 0,
                "message": f"No emails found in the last {hours_ago} hours.",
                "results": []
            }
        
        # Analyze emails
        print(f"[EmailScamHandler] Analyzing {len(emails)} emails")
        analysis = analyzer.analyze_bulk(emails, hours_ago)
        
        # Format response
        return {
            "success": True,
            "total_analyzed": analysis.total_analyzed,
            "scams_detected": analysis.scams_detected,
            "safe_emails": analysis.safe_emails,
            "summary": analysis.summary,
            "results": [result.model_dump() for result in analysis.results]
        }
        
    except ImportError as e:
        return {
            "success": False,
            "error": "dependencies_missing",
            "message": str(e),
            "help": "Install required packages: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
        }
    except Exception as e:
        print(f"[EmailScamHandler] ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "error": "analysis_failed",
            "message": f"Email analysis failed: {str(e)}"
        }


def format_email_scam_response(analysis_result: Dict[str, Any]) -> str:
    """
    Format email scam analysis into user-friendly response
    
    Args:
        analysis_result: Result from handle_email_scam_check
        
    Returns:
        Formatted response string
    """
    if not analysis_result.get("success"):
        error_msg = analysis_result.get("message", "Unknown error")
        help_msg = analysis_result.get("help", "")
        
        response = f"❌ **Email Analysis Failed**\n\n"
        response += f"{error_msg}\n"
        if help_msg:
            response += f"\n💡 {help_msg}\n"
        
        return response
    
    total = analysis_result.get("total_analyzed", 0)
    scams = analysis_result.get("scams_detected", 0)
    safe = analysis_result.get("safe_emails", 0)
    summary = analysis_result.get("summary", {})
    results = analysis_result.get("results", [])
    
    if total == 0:
        return analysis_result.get("message", "No emails to analyze")
    
    # Header
    response = f"📧 **Email Scam Analysis Report**\n\n"
    response += f"**Summary:**\n"
    response += f"• Total Emails Analyzed: {total}\n"
    response += f"• 🚨 Scams Detected: {scams}\n"
    response += f"• ✅ Safe Emails: {safe}\n\n"
    
    # Risk breakdown
    if summary.get("risk_breakdown"):
        response += "**Risk Breakdown:**\n"
        risk_breakdown = summary["risk_breakdown"]
        if risk_breakdown.get("CRITICAL", 0) > 0:
            response += f"🚨 Critical: {risk_breakdown['CRITICAL']}\n"
        if risk_breakdown.get("HIGH", 0) > 0:
            response += f"⛔ High: {risk_breakdown['HIGH']}\n"
        if risk_breakdown.get("MEDIUM", 0) > 0:
            response += f"⚠️ Medium: {risk_breakdown['MEDIUM']}\n"
        if risk_breakdown.get("LOW", 0) > 0:
            response += f"✅ Low: {risk_breakdown['LOW']}\n"
        response += "\n"
    
    # Top scams (show only MEDIUM+ risk)
    if scams > 0:
        response += "**⚠️ Suspicious Emails Detected:**\n\n"
        
        count = 0
        for result in results:
            # Only show MEDIUM or higher risk
            if result["risk_level"] in ["CRITICAL", "HIGH", "MEDIUM"]:
                count += 1
                if count > 5:  # Limit to top 5
                    break
                
                # Risk emoji
                if result["risk_level"] == "CRITICAL":
                    emoji = "🚨"
                elif result["risk_level"] == "HIGH":
                    emoji = "⛔"
                else:
                    emoji = "⚠️"
                
                response += f"{emoji} **{result['subject'][:50]}**\n"
                response += f"   From: {result['sender'][:40]}\n"
                response += f"   Risk: {result['risk_level']} ({result['confidence']*100:.0f}% confidence)\n"
                
                if result.get("scam_type"):
                    response += f"   Type: {result['scam_type']}\n"
                
                # Top red flags
                if result.get("red_flags") and len(result["red_flags"]) > 0:
                    response += f"   Red Flags: {result['red_flags'][0]}\n"
                
                response += "\n"
    
    # Recommendations
    response += "**🛡️ Recommendations:**\n"
    if scams > 0:
        response += "• Delete suspicious emails immediately\n"
        response += "• Do NOT click any links in flagged emails\n"
        response += "• Report phishing emails to your email provider\n"
        response += "• Enable spam filtering and two-factor authentication\n"
    else:
        response += "• Your recent emails appear safe\n"
        response += "• Continue to be cautious with unexpected emails\n"
        response += "• Never share OTP, passwords, or financial info via email\n"
    
    return response


def handle_single_email_analysis(email_text: str, sender: str = None, subject: str = None) -> Dict[str, Any]:
    """
    Analyze a single email that user pastes/forwards
    
    Args:
        email_text: Email body text
        sender: Sender email (optional)
        subject: Email subject (optional)
        
    Returns:
        Analysis result
    """
    try:
        from scam_detector.scam_detector import get_scam_detector
        from email_scam_analyzer import get_email_analyzer, EmailScamResult
        from datetime import datetime
        
        # Build analysis text
        analysis_text = ""
        if subject:
            analysis_text += f"Subject: {subject}\n"
        if sender:
            analysis_text += f"From: {sender}\n"
        analysis_text += f"Body: {email_text}"
        
        # Use scam detector
        detector = get_scam_detector()
        scam_analysis = detector.detect_scam(analysis_text)
        
        # Build result
        result = EmailScamResult(
            email_id="manual_analysis",
            subject=subject or "(No subject)",
            sender=sender or "(Unknown sender)",
            received_date=datetime.now().isoformat(),
            is_scam=scam_analysis.is_scam,
            risk_level=scam_analysis.risk_level,
            confidence=scam_analysis.confidence,
            scam_type=scam_analysis.scam_type,
            red_flags=scam_analysis.red_flags,
            recommendation=scam_analysis.recommendation
        )
        
        return {
            "success": True,
            "result": result.model_dump()
        }
        
    except Exception as e:
        print(f"[SingleEmailAnalysis] ❌ Error: {e}")
        return {
            "success": False,
            "error": str(e)
        }