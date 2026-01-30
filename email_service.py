"""
Email Service for Gmail Integration
Fetches recent emails and analyzes them for scams
"""

import os
import base64
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from email.mime.text import MIMEText
import re

# Gmail API imports (install: google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client)
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    print("[EmailService] ⚠️ Gmail API libraries not installed")


# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class EmailMessage:
    """Represents an email message"""
    def __init__(
        self,
        id: str,
        subject: str,
        sender: str,
        body: str,
        received_date: datetime,
        snippet: str = "",
        has_links: bool = False,
        links: List[str] = None
    ):
        self.id = id
        self.subject = subject
        self.sender = sender
        self.body = body
        self.received_date = received_date
        self.snippet = snippet
        self.has_links = has_links
        self.links = links or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "subject": self.subject,
            "sender": self.sender,
            "body": self.body[:500],  # Truncate for API
            "received_date": self.received_date.isoformat(),
            "snippet": self.snippet,
            "has_links": self.has_links,
            "links": self.links[:5]  # Limit to 5 links
        }


class EmailService:
    """Service for fetching and analyzing emails"""
    
    def __init__(self, credentials_path: str = None, token_path: str = None):
        """
        Initialize email service
        
        Args:
            credentials_path: Path to OAuth credentials.json file
            token_path: Path to store/load token.json file
        """
        if not GMAIL_AVAILABLE:
            raise ImportError("Gmail API libraries not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        
        self.credentials_path = credentials_path or os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
        self.token_path = token_path or os.getenv("GMAIL_TOKEN_PATH", "token.json")
        self.service = None
        self.user_email = None
    
    def authenticate(self) -> bool:
        """
        Authenticate with Gmail API using OAuth 2.0
        
        Returns:
            True if authentication successful
        """
        creds = None
        
        # Load token if exists
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except Exception as e:
                print(f"[EmailService] ⚠️ Failed to load token: {e}")
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"[EmailService] ⚠️ Token refresh failed: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_path):
                    print(f"[EmailService] ❌ Credentials file not found: {self.credentials_path}")
                    return False
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    print(f"[EmailService] ❌ OAuth flow failed: {e}")
                    return False
            
            # Save credentials
            try:
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                print(f"[EmailService] ⚠️ Failed to save token: {e}")
        
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            
            # Get user email
            profile = self.service.users().getProfile(userId='me').execute()
            self.user_email = profile.get('emailAddress')
            
            print(f"[EmailService] ✅ Authenticated as {self.user_email}")
            return True
            
        except HttpError as e:
            print(f"[EmailService] ❌ API error: {e}")
            return False
    
    def fetch_recent_emails(
        self,
        max_results: int = 10,
        hours_ago: int = 24,
        query: str = None
    ) -> List[EmailMessage]:
        """
        Fetch recent emails
        
        Args:
            max_results: Maximum number of emails to fetch
            hours_ago: Fetch emails from last N hours
            query: Additional Gmail search query
            
        Returns:
            List of EmailMessage objects
        """
        if not self.service:
            if not self.authenticate():
                return []
        
        try:
            # Build query
            after_date = datetime.now() - timedelta(hours=hours_ago)
            after_str = after_date.strftime('%Y/%m/%d')
            
            search_query = f'after:{after_str}'
            if query:
                search_query += f' {query}'
            
            # Fetch message IDs
            results = self.service.users().messages().list(
                userId='me',
                q=search_query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                print("[EmailService] No recent emails found")
                return []
            
            # Fetch full messages
            email_objects = []
            for msg in messages:
                try:
                    email_obj = self._parse_message(msg['id'])
                    if email_obj:
                        email_objects.append(email_obj)
                except Exception as e:
                    print(f"[EmailService] ⚠️ Failed to parse message {msg['id']}: {e}")
            
            print(f"[EmailService] ✅ Fetched {len(email_objects)} emails")
            return email_objects
            
        except HttpError as e:
            print(f"[EmailService] ❌ Fetch error: {e}")
            return []
    
    def _parse_message(self, msg_id: str) -> Optional[EmailMessage]:
        """Parse a single email message"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()
            
            headers = message['payload'].get('headers', [])
            
            # Extract headers
            subject = self._get_header(headers, 'Subject') or '(No Subject)'
            sender = self._get_header(headers, 'From') or 'Unknown'
            date_str = self._get_header(headers, 'Date') or ''
            
            # Parse date
            received_date = self._parse_date(date_str)
            
            # Extract body
            body = self._get_body(message['payload'])
            snippet = message.get('snippet', '')
            
            # Extract links
            links = self._extract_links(body)
            
            return EmailMessage(
                id=msg_id,
                subject=subject,
                sender=sender,
                body=body,
                received_date=received_date,
                snippet=snippet,
                has_links=len(links) > 0,
                links=links
            )
            
        except Exception as e:
            print(f"[EmailService] ⚠️ Parse error: {e}")
            return None
    
    def _get_header(self, headers: List[Dict], name: str) -> Optional[str]:
        """Get header value by name"""
        for header in headers:
            if header['name'].lower() == name.lower():
                return header['value']
        return None
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse email date string"""
        try:
            # Try common formats
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except:
            return datetime.now()
    
    def _get_body(self, payload: Dict) -> str:
        """Extract email body from payload"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        break
                elif part['mimeType'] == 'text/html' and not body:
                    data = part['body'].get('data', '')
                    if data:
                        html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        body = self._strip_html(html)
        else:
            data = payload['body'].get('data', '')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        return body
    
    def _strip_html(self, html: str) -> str:
        """Strip HTML tags"""
        import re
        clean = re.compile('<.*?>')
        return re.sub(clean, '', html)
    
    def _extract_links(self, text: str) -> List[str]:
        """Extract URLs from text"""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return re.findall(url_pattern, text)


# Singleton
_email_service = None


def get_email_service() -> EmailService:
    """Get or create email service singleton"""
    global _email_service
    
    if not GMAIL_AVAILABLE:
        raise ImportError("Gmail API not available")
    
    if _email_service is None:
        _email_service = EmailService()
        print("[EmailService] ✅ Singleton initialized")
    
    return _email_service