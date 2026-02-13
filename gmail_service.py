"""
Gmail Service para Claudette Bot.
Usa token.json (igual que Calendar y Tasks) con auto-refresh robusto.
"""

import os
import base64
import re
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

TOKEN_FILE = 'token.json'

def get_gmail_credentials():
    """
    Get OAuth credentials from token.json (mismo método que Calendar/Tasks).
    Auto-refresh si el token expiró.
    """
    if not os.path.exists(TOKEN_FILE):
        logger.error(f"❌ No se encontró {TOKEN_FILE}")
        return None
    
    try:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE)
        
        # Auto-refresh si expiró
        if creds and creds.expired and creds.refresh_token:
            logger.info("🔄 Gmail token expirado, renovando automáticamente...")
            creds.refresh(Request())
            
            # Guardar el token renovado
            with open(TOKEN_FILE, 'w') as f:
                f.write(creds.to_json())
            logger.info("✅ Gmail token renovado y guardado")
        
        if not creds or not creds.valid:
            if creds and creds.refresh_token:
                creds.refresh(Request())
                with open(TOKEN_FILE, 'w') as f:
                    f.write(creds.to_json())
            else:
                logger.error("❌ Gmail token inválido y sin refresh_token")
                return None
        
        return creds
        
    except Exception as e:
        logger.error(f"❌ Error con credenciales Gmail: {e}")
        return None

def get_gmail_service():
    """Build and return Gmail API service."""
    creds = get_gmail_credentials()
    if not creds:
        return None
    
    try:
        service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
        return service
    except Exception as e:
        logger.error(f"❌ Error building Gmail service: {e}")
        return None

def search_emails(query: str, max_results: int = 10) -> dict:
    """
    Search emails using Gmail query syntax.
    
    Args:
        query: Gmail search query (e.g., "from:example@gmail.com", "subject:meeting", "is:unread")
        max_results: Maximum number of emails to return
    """
    service = get_gmail_service()
    if not service:
        return {"success": False, "error": "No se pudo conectar a Gmail. Verificar token.json"}
    
    try:
        results = service.users().messages().list(
            userId='me', q=query, maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            return {"success": True, "emails": [], "message": "No se encontraron emails con esa búsqueda."}
        
        emails = []
        for msg in messages:
            message = service.users().messages().get(
                userId='me', id=msg['id'], format='metadata',
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
                "snippet": message.get('snippet', '')[:150]
            })
        
        return {"success": True, "emails": emails, "count": len(emails)}
    except Exception as e:
        logger.error(f"❌ Error searching emails: {e}")
        return {"success": False, "error": f"Error buscando emails: {str(e)}"}

def get_email(email_id: str) -> dict:
    """Get full content of a specific email."""
    service = get_gmail_service()
    if not service:
        return {"success": False, "error": "No se pudo conectar a Gmail."}
    
    try:
        message = service.users().messages().get(
            userId='me', id=email_id, format='full'
        ).execute()
        
        headers = {h['name']: h['value'] for h in message['payload']['headers']}
        
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
                    html_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    body = re.sub('<[^<]+?>', '', html_body)
        
        if len(body) > 3000:
            body = body[:3000] + "\n\n... [Contenido truncado]"
        
        return {
            "success": True, "id": email_id,
            "from": headers.get('From', 'Desconocido'),
            "to": headers.get('To', ''),
            "subject": headers.get('Subject', '(Sin asunto)'),
            "date": headers.get('Date', ''),
            "body": body
        }
    except Exception as e:
        logger.error(f"❌ Error getting email: {e}")
        return {"success": False, "error": f"Error obteniendo email: {str(e)}"}

def send_email(to: str, subject: str, body: str, reply_to_id: str = None) -> dict:
    """Send an email."""
    service = get_gmail_service()
    if not service:
        return {"success": False, "error": "No se pudo conectar a Gmail."}
    
    try:
        profile = service.users().getProfile(userId='me').execute()
        sender_email = profile['emailAddress']
        
        message = MIMEMultipart()
        message['to'] = to
        message['from'] = sender_email
        message['subject'] = subject
        
        thread_id = None
        if reply_to_id:
            original = service.users().messages().get(
                userId='me', id=reply_to_id, format='metadata',
                metadataHeaders=['Message-ID', 'Subject']
            ).execute()
            orig_headers = {h['name']: h['value'] for h in original['payload']['headers']}
            if 'Message-ID' in orig_headers:
                message['In-Reply-To'] = orig_headers['Message-ID']
                message['References'] = orig_headers['Message-ID']
            thread_id = original.get('threadId')
        
        message.attach(MIMEText(body, 'plain'))
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        send_body = {'raw': raw_message}
        if thread_id:
            send_body['threadId'] = thread_id
        
        sent = service.users().messages().send(userId='me', body=send_body).execute()
        
        return {
            "success": True,
            "message_id": sent['id'],
            "thread_id": sent.get('threadId'),
            "message": f"✅ Email enviado exitosamente a {to}"
        }
    except Exception as e:
        logger.error(f"❌ Error sending email: {e}")
        return {"success": False, "error": f"Error enviando email: {str(e)}"}

def get_unread_count() -> dict:
    """Get count of unread emails in inbox."""
    service = get_gmail_service()
    if not service:
        return {"success": False, "error": "No se pudo conectar a Gmail."}
    
    try:
        results = service.users().messages().list(
            userId='me', q='is:unread in:inbox', maxResults=1
        ).execute()
        count = results.get('resultSizeEstimate', 0)
        return {"success": True, "unread_count": count}
    except Exception as e:
        logger.error(f"❌ Error getting unread count: {e}")
        return {"success": False, "error": str(e)}
