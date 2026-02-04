import os
import logging
import traceback
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Calendar API settings
SCOPES = ['https://www.googleapis.com/auth/calendar']
# Get calendar ID from environment
CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID', 'primary')

def get_service_account_info():
    """Get service account from environment variable"""
    service_account_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    if not service_account_json:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON not found in environment")
    return json.loads(service_account_json)

def get_calendar_service():
    """Initialize and return Google Calendar service"""
    logger.info("📡 Initializing Google Calendar service...")
    
    try:
        service_account_info = get_service_account_info()
        
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )
        
        service = build('calendar', 'v3', credentials=credentials)
        logger.info("✅ Calendar service initialized successfully")
        return service
        
    except Exception as e:
        logger.error(f"❌ Error initializing calendar service: {e}")
        logger.error(f"❌ TRACEBACK: {traceback.format_exc()}")
        raise

def get_calendar_events(start_date, end_date):
    """Get calendar events between two dates"""
    logger.info(f"📅 GET_EVENTS CALLED")
    logger.info(f"  Start: {start_date}")
    logger.info(f"  End: {end_date}")
    
    try:
        service = get_calendar_service()
        
        logger.info(f"🔍 Fetching events from calendar...")
        
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start_date,
            timeMax=end_date,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        logger.info(f"✅ Found {len(events)} events")
        
        if not events:
            return "No hay eventos en ese rango de fechas."
        
        event_list = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'Sin título')
            location = event.get('location', '')
            
            event_str = f"- {summary} ({start})"
            if location:
                event_str += f" en {location}"
            
            event_list.append(event_str)
        
        result = f"Eventos encontrados ({len(events)}):\n" + "\n".join(event_list)
        logger.info(f"📤 EVENTS RESULT: {result}")
        
        return result
        
    except Exception as e:
        error_msg = f"❌ Error getting events: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return error_msg

def create_calendar_event(summary, start_time, end_time, location=None, reminder_minutes=None):
    """Create a calendar event"""
    logger.info(f"📅 CREATE_EVENT CALLED")
    logger.info(f"  Summary: {summary}")
    logger.info(f"  Start: {start_time}")
    logger.info(f"  End: {end_time}")
    logger.info(f"  Location: {location}")
    logger.info(f"  Reminder: {reminder_minutes} minutes")
    
    try:
        service = get_calendar_service()
        logger.info(f"✅ Calendar service obtained")
        
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time,
                'timeZone': 'America/Costa_Rica',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'America/Costa_Rica',
            },
        }
        
        # Add reminders if specified
        if reminder_minutes is not None and reminder_minutes > 0:
            event['reminders'] = {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': reminder_minutes},
                    {'method': 'popup', 'minutes': reminder_minutes},
                ],
            }
            logger.info(f"⏰ Adding reminder: {reminder_minutes} minutes before")
        else:
            # No reminders
            event['reminders'] = {
                'useDefault': False,
                'overrides': [],
            }
            logger.info(f"🔕 No reminders set")
        
        if location:
            event['location'] = location
        
        logger.info(f"📝 Event object created: {event}")
        
        logger.info(f"🚀 Calling Google Calendar API to insert event...")
        
        created_event = service.events().insert(
            calendarId=CALENDAR_ID,
            body=event
        ).execute()
        
        event_link = created_event.get('htmlLink', 'No link')
        event_id = created_event.get('id', 'No ID')
        
        logger.info(f"🎉 EVENT CREATED SUCCESSFULLY!")
        logger.info(f"  ID: {event_id}")
        logger.info(f"  Link: {event_link}")
        
        return f"✅ Evento creado: {event_link}\nEvent ID: {event_id}"
        
    except Exception as e:
        error_msg = f"❌ CALENDAR ERROR: {str(e)}"
        logger.error(error_msg)
        logger.error(f"❌ FULL TRACEBACK:\n{traceback.format_exc()}")
        return error_msg

def update_event_reminder(event_id, reminder_minutes):
    """Update reminder for an existing event"""
    logger.info(f"⏰ UPDATE_REMINDER CALLED")
    logger.info(f"  Event ID: {event_id}")
    logger.info(f"  Reminder: {reminder_minutes} minutes")
    
    try:
        service = get_calendar_service()
        
        # Get the existing event
        event = service.events().get(
            calendarId=CALENDAR_ID,
            eventId=event_id
        ).execute()
        
        logger.info(f"📖 Retrieved event: {event.get('summary')}")
        
        # Update reminders
        if reminder_minutes > 0:
            event['reminders'] = {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': reminder_minutes},
                    {'method': 'popup', 'minutes': reminder_minutes},
                ],
            }
            logger.info(f"✅ Setting reminder: {reminder_minutes} minutes before")
        else:
            # No reminder
            event['reminders'] = {
                'useDefault': False,
                'overrides': [],
            }
            logger.info(f"🔕 Removing reminders")
        
        # Update the event
        updated_event = service.events().update(
            calendarId=CALENDAR_ID,
            eventId=event_id,
            body=event
        ).execute()
        
        logger.info(f"🎉 REMINDER UPDATED SUCCESSFULLY!")
        
        if reminder_minutes > 0:
            return f"✅ Recordatorio configurado: {reminder_minutes} minutos antes"
        else:
            return f"✅ Sin recordatorio"
        
    except Exception as e:
        error_msg = f"❌ ERROR UPDATING REMINDER: {str(e)}"
        logger.error(error_msg)
        logger.error(f"❌ TRACEBACK:\n{traceback.format_exc()}")
        return error_msg

if __name__ == "__main__":
    # Test
    from datetime import datetime, timedelta
    
    logger.info("🧪 Testing calendar functions...")
    
    # Test get events
    start = datetime.now().isoformat() + "-06:00"
    end = (datetime.now() + timedelta(days=7)).isoformat() + "-06:00"
    
    logger.info(f"Testing get_calendar_events...")
    print(get_calendar_events(start, end))
    
    # Test create event
    logger.info(f"Testing create_calendar_event...")
    test_start = (datetime.now() + timedelta(days=1)).replace(hour=14, minute=0).isoformat() + "-06:00"
    test_end = (datetime.now() + timedelta(days=1)).replace(hour=15, minute=0).isoformat() + "-06:00"
    
    print(create_calendar_event(
        "Test Event from Script",
        test_start,
        test_end,
        "Test Location"
    ))
