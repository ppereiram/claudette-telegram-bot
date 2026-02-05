"""
Gmail Service para Claudette Bot.
Funciones para leer, buscar y enviar emails.
"""

import os
import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# Gmail API scopes
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose'
]

def get_gmail_credentials():
    """Get OAuth credentials from environment variables."""
    client_id = os.environ.get('GOOGLE_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
    refresh_token = os.environ.get('GOOGLE_REFRESH_TOKEN')
    
    if not all([client_id, client_secret, refresh_token]):
        logger.error("Missing Gmail OAuth credentials in environment")
        return None
    
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=client_id,
        client_secret=client_secret,
        scopes=GMAIL_SCOPES
    )
    
    # Refresh the token
    try:
        creds.refresh(Request())
        return creds
    except Exception as e:
        logger.error(f"Error refreshing Gmail credentials: {e}")
        return None

def get_gmail_service():
    """Build and return Gmail API service."""
    creds = get_gmail_credentials()
    if not creds:
        return None
    
    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Error building Gmail service: {e}")
        return None

def search_emails(query: str, max_results: int = 10) -> dict:
    """
    Search emails using Gmail query syntax.
    
    Args:
        query: Gmail search query (e.g., "from:example@gmail.com", "subject:meeting", "is:unread")
        max_results: Maximum number of emails to return (default 10)
    
    Returns:
        dict with 'success', 'emails' list, and 'error' if any
    """
    service = get_gmail_service()
    if not service:
        return {"success": False, "error": "No se pudo conectar a Gmail. Verifica las credenciales OAuth."}
    
    try:
        # Search for messages
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return {"success": True, "emails": [], "message": "No se encontraron emails con esa búsqueda."}
        
        emails = []
        for msg in messages:
            # Get message details
            message = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['From', 'To', 'Subject', 'Date']
            ).execute()
            
            headers = {h['name']: h['value'] for h in message['payload']['headers']}
            
            emails.append({
                "id": msg['id'],
                "thread_id": message.get('threadId'),
                "from": headers.get('From', 'Desconocido'),
                "to": headers.get('To', ''),
                "subject": headers.get('Subject', '(Sin asunto)'),
                "date": headers.get('Date', ''),
                "snippet": message.get('snippet', '')[:150]  # Preview del contenido
            })
        
        return {"success": True, "emails": emails, "count": len(emails)}
    
    except Exception as e:
        logger.error(f"Error searching emails: {e}")
        return {"success": False, "error": f"Error buscando emails: {str(e)}"}

def get_email(email_id: str) -> dict:
    """
    Get full content of a specific email.
    
    Args:
        email_id: The Gmail message ID
    
    Returns:
        dict with email details and body
    """
    service = get_gmail_service()
    if not service:
        return {"success": False, "error": "No se pudo conectar a Gmail."}
    
    try:
        message = service.users().messages().get(
            userId='me',
            id=email_id,
            format='full'
        ).execute()
        
        headers = {h['name']: h['value'] for h in message['payload']['headers']}
        
        # Extract body
        body = ""
        payload = message['payload']
        
        if 'body' in payload and payload['body'].get('data'):
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        elif 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain' and part['body'].get('data'):
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
                elif part['mimeType'] == 'text/html' and part['body'].get('data') and not body:
                    # Fallback to HTML if no plain text
                    html_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    # Simple HTML stripping (basic)
                    import re
                    body = re.sub('<[^<]+?>', '', html_body)
        
        # Truncate very long bodies
        if len(body) > 3000:
            body = body[:3000] + "\n\n... [Contenido truncado - email muy largo]"
        
        return {
            "success": True,
            "id": email_id,
            "from": headers.get('From', 'Desconocido'),
            "to": headers.get('To', ''),
            "subject": headers.get('Subject', '(Sin asunto)'),
            "date": headers.get('Date', ''),
            "body": body
        }
    
    except Exception as e:
        logger.error(f"Error getting email: {e}")
        return {"success": False, "error": f"Error obteniendo email: {str(e)}"}

def send_email(to: str, subject: str, body: str, reply_to_id: str = None) -> dict:
    """
    Send an email.
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body (plain text)
        reply_to_id: Optional message ID to reply to
    
    Returns:
        dict with success status and message ID
    """
    service = get_gmail_service()
    if not service:
        return {"success": False, "error": "No se pudo conectar a Gmail."}
    
    try:
        # Get sender email
        profile = service.users().getProfile(userId='me').execute()
        sender_email = profile['emailAddress']
        
        # Create message
        message = MIMEMultipart()
        message['to'] = to
        message['from'] = sender_email
        message['subject'] = subject
        
        # If replying, add headers
        thread_id = None
        if reply_to_id:
            original = service.users().messages().get(
                userId='me',
                id=reply_to_id,
                format='metadata',
                metadataHeaders=['Message-ID', 'Subject']
            ).execute()
            
            orig_headers = {h['name']: h['value'] for h in original['payload']['headers']}
            if 'Message-ID' in orig_headers:
                message['In-Reply-To'] = orig_headers['Message-ID']
                message['References'] = orig_headers['Message-ID']
            thread_id = original.get('threadId')
        
        message.attach(MIMEText(body, 'plain'))
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Send
        send_body = {'raw': raw_message}
        if thread_id:
            send_body['threadId'] = thread_id
        
        sent = service.users().messages().send(
            userId='me',
            body=send_body
        ).execute()
        
        return {
            "success": True,
            "message_id": sent['id'],
            "thread_id": sent.get('threadId'),
            "message": f"Email enviado exitosamente a {to}"
        }
    
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return {"success": False, "error": f"Error enviando email: {str(e)}"}

def get_unread_count() -> dict:
    """Get count of unread emails in inbox."""
    service = get_gmail_service()
    if not service:
        return {"success": False, "error": "No se pudo conectar a Gmail."}
    
    try:
        results = service.users().messages().list(
            userId='me',
            q='is:unread in:inbox',
            maxResults=1
        ).execute()
        
        # Get total from resultSizeEstimate
        count = results.get('resultSizeEstimate', 0)
        
        return {"success": True, "unread_count": count}
    
    except Exception as e:
        logger.error(f"Error getting unread count: {e}")
        return {"success": False, "error": str(e)}
