"""
Email Scam Analyzer
Analyzes emails for scam indicators and provides detailed reports
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class EmailScamResult(BaseModel):
    """Result of email scam analysis"""
    email_id: str
    subject: str
    sender: str
    received_date: str
    is_scam: bool
    risk_level: str  
    confidence: float
    scam_type: Optional[str] = None
    red_flags: List[str] = Field(default_factory=list)
    recommendation: str
    safe_sender: bool = False  
    
    # Email-specific indicators
    sender_domain: str = ""
    has_suspicious_links: bool = False
    suspicious_links: List[str] = Field(default_factory=list)
    spoofed_sender: bool = False
    urgency_detected: bool = False


class BulkEmailAnalysisResult(BaseModel):
    """Result of bulk email analysis"""
    total_analyzed: int
    scams_detected: int
    safe_emails: int
    results: List[EmailScamResult]
    summary: Dict[str, Any]


class EmailScamAnalyzer:
    """Analyzes emails for scam indicators"""
    
    def __init__(self):
        """Initialize analyzer"""
        from scam_detector.scam_detector import get_scam_detector
        self.scam_detector = get_scam_detector()
        

        self.safe_domains = {
            'gmail.com', 'google.com', 'apple.com', 'microsoft.com',
            'amazon.com', 'paypal.com', 'facebook.com', 'twitter.com',
            'linkedin.com', 'github.com', 'stackoverflow.com'
        }
        

        self.financial_domains = {
            'sbi.co.in', 'hdfcbank.com', 'icicibank.com', 'axisbank.com',
            'kotak.com', 'pnbindia.in', 'bankofbaroda.in', 'canarabank.com'
        }
    
    def analyze_email(self, email_message) -> EmailScamResult:
        """
        Analyze a single email for scam indicators
        
        Args:
            email_message: EmailMessage object from email_service
            
        Returns:
            EmailScamResult with analysis
        """
        # Extract sender domain
        sender_domain = self._extract_domain(email_message.sender)
        
        # Check if sender is known safe
        safe_sender = sender_domain in self.safe_domains
        
        # Build analysis text
        analysis_text = self._build_analysis_text(email_message)
        
        # Email-specific checks
        suspicious_links = self._check_suspicious_links(email_message.links)
        spoofed = self._check_sender_spoofing(email_message.sender, email_message.body)
        urgency = self._check_urgency(email_message.subject, email_message.body)
        
        # Use scam detector
        scam_analysis = self.scam_detector.detect_scam(
            message=analysis_text,
            context={
                "sender": email_message.sender,
                "subject": email_message.subject,
                "has_links": email_message.has_links,
                "link_count": len(email_message.links)
            }
        )
        
        # Build result
        result = EmailScamResult(
            email_id=email_message.id,
            subject=email_message.subject,
            sender=email_message.sender,
            received_date=email_message.received_date.isoformat(),
            is_scam=scam_analysis.is_scam,
            risk_level=scam_analysis.risk_level,
            confidence=scam_analysis.confidence,
            scam_type=scam_analysis.scam_type,
            red_flags=scam_analysis.red_flags,
            recommendation=scam_analysis.recommendation,
            safe_sender=safe_sender,
            sender_domain=sender_domain,
            has_suspicious_links=len(suspicious_links) > 0,
            suspicious_links=suspicious_links,
            spoofed_sender=spoofed,
            urgency_detected=urgency
        )
        
        # Adjust confidence if known safe sender
        if safe_sender and not result.is_scam:
            result.confidence = max(result.confidence, 0.9)
            result.risk_level = "LOW"
        
        return result
    
    def analyze_bulk(
        self,
        email_messages: List,
        hours_ago: int = 24
    ) -> BulkEmailAnalysisResult:
        """
        Analyze multiple emails at once
        
        Args:
            email_messages: List of EmailMessage objects
            hours_ago: Time window for analysis
            
        Returns:
            BulkEmailAnalysisResult with summary
        """
        results = []
        scams_detected = 0
        
        for email in email_messages:
            result = self.analyze_email(email)
            results.append(result)
            
            if result.is_scam:
                scams_detected += 1
        
        # Sort by risk level
        risk_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        results.sort(key=lambda x: risk_order.get(x.risk_level, 4))
        
        # Generate summary
        summary = self._generate_summary(results, hours_ago)
        
        return BulkEmailAnalysisResult(
            total_analyzed=len(results),
            scams_detected=scams_detected,
            safe_emails=len(results) - scams_detected,
            results=results,
            summary=summary
        )
    
    def _build_analysis_text(self, email) -> str:
        """Build text for scam analysis"""
        text = f"Subject: {email.subject}\n"
        text += f"From: {email.sender}\n"
        text += f"Body: {email.body[:1000]}\n"  # Limit body
        
        if email.has_links:
            text += f"Contains {len(email.links)} links\n"
        
        return text
    
    def _extract_domain(self, email_address: str) -> str:
        """Extract domain from email address"""
        try:
            # Extract domain from email
            if '<' in email_address:
                email_address = email_address.split('<')[1].split('>')[0]
            
            domain = email_address.split('@')[-1].lower()
            return domain
        except:
            return ""
    
    def _check_suspicious_links(self, links: List[str]) -> List[str]:
        """Check for suspicious links"""
        suspicious = []
        
        suspicious_patterns = [
            'bit.ly', 'tinyurl', 'goo.gl', 't.co', 
            'verify', 'update', 'secure', 'account-',
            'login-', 'signin-', 'confirm-'
        ]
        
        for link in links:
            link_lower = link.lower()
            if any(pattern in link_lower for pattern in suspicious_patterns):
                suspicious.append(link)
        
        return suspicious[:5] 
    
    def _check_sender_spoofing(self, sender: str, body: str) -> bool:
        """Check if sender might be spoofed"""
        sender_lower = sender.lower()
        body_lower = body.lower()
        
        bank_keywords = ['bank', 'sbi', 'hdfc', 'icici', 'axis', 'kotak']
        
        for keyword in bank_keywords:
            if keyword in body_lower and keyword not in sender_lower:
                return True
        
        return False
    
    def _check_urgency(self, subject: str, body: str) -> bool:
        """Check for urgency tactics"""
        text = (subject + " " + body).lower()
        
        urgency_keywords = [
            'urgent', 'immediately', 'expire', 'within 24 hours',
            'act now', 'limited time', 'expire today', 'last chance',
            'verify now', 'update immediately', 'suspended'
        ]
        
        return any(keyword in text for keyword in urgency_keywords)
    
    def _generate_summary(self, results: List[EmailScamResult], hours_ago: int) -> Dict[str, Any]:
        """Generate analysis summary"""

        risk_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for result in results:
            risk_counts[result.risk_level] = risk_counts.get(result.risk_level, 0) + 1

        scam_types = {}
        for result in results:
            if result.scam_type:
                scam_types[result.scam_type] = scam_types.get(result.scam_type, 0) + 1
        
        return {
            "time_window_hours": hours_ago,
            "risk_breakdown": risk_counts,
            "top_scam_types": dict(sorted(scam_types.items(), key=lambda x: x[1], reverse=True)[:5]),
            "emails_with_links": sum(1 for r in results if r.has_suspicious_links),
            "spoofed_senders": sum(1 for r in results if r.spoofed_sender),
            "urgent_emails": sum(1 for r in results if r.urgency_detected)
        }


_email_analyzer = None


def get_email_analyzer() -> EmailScamAnalyzer:
    """Get or create email analyzer singleton"""
    global _email_analyzer
    
    if _email_analyzer is None:
        _email_analyzer = EmailScamAnalyzer()
        print("[EmailAnalyzer] ✅ Singleton initialized")
    
    return _email_analyzer