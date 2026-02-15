"""
Google Calendar Service para Claudette Bot.
Usa autenticación OAuth unificada (google_auth.py).
"""

import os
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth import get_credentials

logger = logging.getLogger("claudette")

CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID', 'primary')


def get_calendar_service():
    """Initialize and return Google Calendar service."""
    creds = get_credentials()
    if not creds:
        raise Exception("No hay credenciales Google válidas para Calendar")
    return build('calendar', 'v3', credentials=creds, cache_discovery=False)


def get_calendar_events(start_date, end_date):
    """Get calendar events between two dates."""
    try:
        service = get_calendar_service()
        logger.info(f"📅 FETCHING EVENTS: {start_date} to {end_date}")

        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start_date,
            timeMax=end_date,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            return "No hay eventos en ese rango de fechas."

        result = "📅 Eventos encontrados:\n\n"
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'Sin título')
            result += f"• {summary}\n  📆 {start}\n\n"

        logger.info(f"✅ FOUND {len(events)} EVENTS")
        return result

    except HttpError as error:
        logger.error(f"❌ GOOGLE API ERROR: {error}")
        return f"Error al obtener eventos: {error}"
    except Exception as e:
        logger.error(f"❌ ERROR: {e}")
        return f"Error: {str(e)}"


def create_calendar_event(summary, start_time, end_time, location=None):
    """Create a new calendar event."""
    try:
        service = get_calendar_service()
        logger.info(f"🎉 CREATING EVENT: {summary} | {start_time} → {end_time}")

        event = {
            'summary': summary,
            'start': {'dateTime': start_time, 'timeZone': 'America/Costa_Rica'},
            'end': {'dateTime': end_time, 'timeZone': 'America/Costa_Rica'},
        }

        if location:
            event['location'] = location

        created_event = service.events().insert(
            calendarId=CALENDAR_ID, body=event
        ).execute()

        event_link = created_event.get('htmlLink')
        logger.info(f"🎉 EVENT CREATED: {event_link}")
        return f"✅ Evento creado: {event_link}"

    except HttpError as error:
        logger.error(f"❌ GOOGLE API ERROR: {error}")
        return f"Error al crear evento: {error}"
    except Exception as e:
        logger.error(f"❌ ERROR: {e}", exc_info=True)
        return f"Error: {str(e)}"
