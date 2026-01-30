"""
Email Scam Detection API Endpoints
Add to backend/app/main.py
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

# Create router
email_router = APIRouter(prefix="/email", tags=["Email Scam Detection"])


class EmailScanRequest(BaseModel):
    """Request model for email scanning"""
    user_id: str = "default_user"
    hours_ago: int = 24
    max_emails: int = 10


class SingleEmailCheckRequest(BaseModel):
    """Request model for single email check"""
    email_text: str
    sender: Optional[str] = None
    subject: Optional[str] = None


@email_router.post("/scan")
def scan_emails(request: EmailScanRequest):
    """
    Scan recent emails for scams
    
    **First time usage**: Will trigger OAuth flow
    
    Args:
        request: EmailScanRequest with scan parameters
        
    Returns:
        Analysis results with scam detection
        
    Example:
        POST /email/scan
        {
            "user_id": "user123",
            "hours_ago": 24,
            "max_emails": 10
        }
    """
    try:
        from email_scam_handler import handle_email_scam_check
        
        result = handle_email_scam_check(
            user_id=request.user_id,
            hours_ago=request.hours_ago,
            max_emails=request.max_emails
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("message", "Email scan failed")
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Email scan failed: {str(e)}"
        )


@email_router.post("/check-single")
def check_single_email(request: SingleEmailCheckRequest):
    """
    Check a single email for scam indicators
    
    Use this when user pastes an email they received
    
    Args:
        request: SingleEmailCheckRequest with email details
        
    Returns:
        Scam analysis result
        
    Example:
        POST /email/check-single
        {
            "email_text": "Dear user, your account will be suspended...",
            "sender": "no-reply@suspicious.com",
            "subject": "Urgent: Verify your account"
        }
    """
    try:
        from email_scam_handler import handle_single_email_analysis
        
        result = handle_single_email_analysis(
            email_text=request.email_text,
            sender=request.sender,
            subject=request.subject
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Analysis failed")
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Email analysis failed: {str(e)}"
        )


@email_router.get("/status")
def get_email_service_status():
    """
    Check if Gmail API is configured and working
    
    Returns:
        Status information
    """
    try:
        from email_service import get_email_service, GMAIL_AVAILABLE
        
        if not GMAIL_AVAILABLE:
            return {
                "configured": False,
                "authenticated": False,
                "message": "Gmail API libraries not installed",
                "help": "Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
            }
        
        service = get_email_service()
        authenticated = service.authenticate()
        
        return {
            "configured": True,
            "authenticated": authenticated,
            "user_email": service.user_email if authenticated else None,
            "message": "Ready" if authenticated else "Authentication required"
        }
        
    except Exception as e:
        return {
            "configured": False,
            "authenticated": False,
            "error": str(e)
        }


# ============================================
# Integration Instructions
# ============================================

"""
TO INTEGRATE: Add to backend/app/main.py

1. Import the router:
   from app.email_api import email_router

2. Include the router in your app:
   app.include_router(email_router)

3. The endpoints will be available at:
   - POST /email/scan - Scan recent Gmail inbox
   - POST /email/check-single - Check a single email
   - GET /email/status - Check Gmail API status

4. Example usage from frontend:

   // Scan inbox
   const response = await fetch('http://localhost:8000/email/scan', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({
       user_id: 'user123',
       hours_ago: 24,
       max_emails: 10
     })
   });
   const data = await response.json();

   // Check single email
   const response = await fetch('http://localhost:8000/email/check-single', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({
       email_text: 'Suspicious email text...',
       sender: 'scammer@evil.com',
       subject: 'You won a prize!'
     })
   });
"""