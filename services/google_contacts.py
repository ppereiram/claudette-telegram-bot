import os.path
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# Scopes necesarios
SCOPES = ['https://www.googleapis.com/auth/contacts.readonly']

def get_contacts_service():
    creds = None
    
    # Buscar token en varias rutas posibles
    possible_paths = [
        'token.json',
        '/etc/secrets/token.json', 
        '/opt/render/project/src/token.json'
    ]
    
    token_path = None
    for path in possible_paths:
        if os.path.exists(path):
            token_path = path
            break

    if token_path:
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception as e:
            logger.error(f"Error leyendo token para contactos: {e}")

    # Fallback a variables de entorno (si usaras eso en vez de archivo)
    if not creds and os.environ.get('GOOGLE_REFRESH_TOKEN'):
        try:
            info = {
                "refresh_token": os.environ.get('GOOGLE_REFRESH_TOKEN'),
                "client_id": os.environ.get('GOOGLE_CLIENT_ID'),
                "client_secret": os.environ.get('GOOGLE_CLIENT_SECRET'),
                "token_uri": "https://oauth2.googleapis.com/token",
            }
            creds = Credentials.from_authorized_user_info(info, SCOPES)
        except: pass

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except: return None

    if not creds or not creds.valid:
        return None

    return build('people', 'v1', credentials=creds)

def search_contact(name_query):
    """Busca un contacto en Google Contacts por nombre."""
    try:
        service = get_contacts_service()
        if not service: return None

        # Buscamos en las conexiones
        results = service.people().connections().list(
            resourceName='people/me',
            pageSize=100, # Buscamos más para filtrar mejor
            personFields='names,phoneNumbers',
            sortOrder='FIRST_NAME_ASCENDING'
        ).execute()
        
        connections = results.get('connections', [])
        found_contacts = []
        query_lower = name_query.lower()

        for person in connections:
            names = person.get('names', [])
            phones = person.get('phoneNumbers', [])
            
            if names and phones:
                display_name = names[0].get('displayName', '')
                # Búsqueda simple (contiene)
                if query_lower in display_name.lower():
                    found_contacts.append({
                        "name": display_name,
                        "phone": phones[0].get('value')
                    })
        
        return found_contacts

    except Exception as e:
        logger.error(f"Error buscando contacto: {e}")
        return None
