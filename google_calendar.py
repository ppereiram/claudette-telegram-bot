import os
import json
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

logger = logging.getLogger(__name__)

# Get calendar ID from environment (defaults to 'primary' if not set)
CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID', 'primary')

def get_calendar_service():
    """Initialize and return Google Calendar service."""
    try:
        # Get service account JSON from environment variable
        service_account_info = json.loads(os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON'))
        
        # Create credentials
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        
        # Delegate to user's email if needed (for domain-wide delegation)
        # credentials = credentials.with_subject('user@domain.com')
        
        # Build the service
        service = build('calendar', 'v3', credentials=credentials)
        return service
    except Exception as e:
        logger.error(f"❌ ERROR creating calendar service: {e}")
        raise

def get_calendar_events(start_date, end_date):
    """
    Get calendar events between two dates.
    
    Args:
        start_date: ISO format datetime string (e.g., '2024-01-01T00:00:00-06:00')
        end_date: ISO format datetime string
    
    Returns:
        String with formatted events or error message
    """
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

def create_calendar_event(summary, start_time, end_time, location=None, reminder_minutes=None):
    """
    Create a new calendar event.
    
    Args:
        summary: Event title
        start_time: ISO format datetime with timezone (e.g., '2024-01-15T14:00:00-06:00')
        end_time: ISO format datetime with timezone
        location: Optional location string
        reminder_minutes: Optional minutes before event to send reminder (e.g., 60 for 1 hour)
    
    Returns:
        String with event link or error message
    """
    try:
        service = get_calendar_service()
        
        logger.info(f"🎉 CREATING EVENT: {summary}")
        logger.info(f"⏰ START: {start_time}")
        logger.info(f"⏰ END: {end_time}")
        logger.info(f"📍 LOCATION: {location}")
        logger.info(f"⏰ REMINDER: {reminder_minutes} minutes" if reminder_minutes else "⏰ REMINDER: None")
        
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time,
            },
            'end': {
                'dateTime': end_time,
            },
        }
        
        if location:
            event['location'] = location
        
        # Add reminders if specified
        if reminder_minutes is not None and reminder_minutes > 0:
            event['reminders'] = {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': reminder_minutes},
                    {'method': 'popup', 'minutes': reminder_minutes},
                ],
            }
        else:
            # No reminders
            event['reminders'] = {
                'useDefault': False,
                'overrides': []
            }
        
        # Create the event
        created_event = service.events().insert(
            calendarId=CALENDAR_ID,
            body=event
        ).execute()
        
        event_link = created_event.get('htmlLink')
        event_id = created_event.get('id')
        
        logger.info(f"🎉 EVENT CREATED SUCCESSFULLY!")
        logger.info(f"🔗 LINK: {event_link}")
        logger.info(f"🆔 EVENT ID: {event_id}")
        
        return f"✅ Evento creado: {event_link}\nEvent ID: {event_id}"
        
    except HttpError as error:
        logger.error(f"❌ GOOGLE API ERROR: {error}")
        return f"Error al crear evento: {error}"
    except Exception as e:
        logger.error(f"❌ ERROR: {e}", exc_info=True)
        return f"Error: {str(e)}"

def update_event_reminder(event_id, reminder_minutes):
    """
    Update or add reminder to an existing calendar event.
    
    Args:
        event_id: The ID of the event to update
        reminder_minutes: Minutes before event to remind (use 0 for no reminder)
    
    Returns:
        String with confirmation or error message
    """
    try:
        service = get_calendar_service()
        
        logger.info(f"🔄 UPDATING REMINDER FOR EVENT: {event_id}")
        logger.info(f"⏰ NEW REMINDER: {reminder_minutes} minutes")
        
        # First, get the existing event
        event = service.events().get(
            calendarId=CALENDAR_ID,
            eventId=event_id
        ).execute()
        
        # Update reminders
        if reminder_minutes > 0:
            event['reminders'] = {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': reminder_minutes},
                    {'method': 'popup', 'minutes': reminder_minutes},
                ],
            }
        else:
            # Remove reminders
            event['reminders'] = {
                'useDefault': False,
                'overrides': []
            }
        
        # Update the event
        updated_event = service.events().update(
            calendarId=CALENDAR_ID,
            eventId=event_id,
            body=event
        ).execute()
        
        logger.info(f"✅ REMINDER UPDATED SUCCESSFULLY")
        
        if reminder_minutes > 0:
            return f"✅ Recordatorio actualizado: {reminder_minutes} minutos antes del evento"
        else:
            return "✅ Recordatorio eliminado del evento"
        
    except HttpError as error:
        logger.error(f"❌ GOOGLE API ERROR: {error}")
        return f"Error al actualizar recordatorio: {error}"
    except Exception as e:
        logger.error(f"❌ ERROR: {e}", exc_info=True)
        return f"Error: {str(e)}"
