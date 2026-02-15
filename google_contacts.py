"""
Google Contacts Service para Claudette Bot.
Usa autenticación OAuth unificada (google_auth.py).
"""

import logging
from googleapiclient.discovery import build
from google_auth import get_credentials

logger = logging.getLogger("claudette")


def get_contacts_service():
    creds = get_credentials()
    if not creds:
        return None
    try:
        return build('people', 'v1', credentials=creds, cache_discovery=False)
    except Exception as e:
        logger.error(f"Error building Contacts service: {e}")
        return None


def search_contact(name_query):
    """Busca un contacto en Google Contacts por nombre."""
    try:
        service = get_contacts_service()
        if not service:
            return None

        results = service.people().connections().list(
            resourceName='people/me',
            pageSize=100,
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
                if query_lower in display_name.lower():
                    found_contacts.append({
                        "name": display_name,
                        "phone": phones[0].get('value')
                    })

        return found_contacts

    except Exception as e:
        logger.error(f"Error buscando contacto: {e}")
        return None
