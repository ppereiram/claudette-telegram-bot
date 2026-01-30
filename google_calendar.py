import os
import json
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
import logging

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """Initialize Google Calendar service"""
    try:
        # Load service account from environment
        if os.getenv('GOOGLE_SERVICE_ACCOUNT'):
            creds_data = json.loads(os.getenv('GOOGLE_SERVICE_ACCOUNT'))
            credentials = service_account.Credentials.from_service_account_info(
                creds_data, scopes=SCOPES)
        else:
            credentials = service_account.Credentials.from_service_account_file(
                'service-account.json', scopes=SCOPES)
        
        service = build('calendar', 'v3', credentials=credentials)
        return service
    except Exception as e:
        logging.error(f"Error initializing Calendar service: {e}")
        return None

def list_upcoming_events(max_results=10):
    """List upcoming calendar events"""
    service = get_calendar_service()
    if not service:
        return None
    
    try:
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        return events
    except Exception as e:
        logging.error(f"Error listing events: {e}")
        return None

def get_today_events():
    """Get today's calendar events"""
    service = get_calendar_service()
    if not service:
        return None
    
    try:
        # Start and end of today
        now = datetime.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_of_day.isoformat() + 'Z',
            timeMax=end_of_day.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        return events
    except Exception as e:
        logging.error(f"Error getting today's events: {e}")
        return None

def create_event(summary, start_time, end_time, description=None, location=None):
    """Create a new calendar event"""
    service = get_calendar_service()
    if not service:
        return None
    
    try:
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/Costa_Rica',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/Costa_Rica',
            },
        }
        
        if description:
            event['description'] = description
        if location:
            event['location'] = location
        
        event = service.events().insert(calendarId='primary', body=event).execute()
        return event
    except Exception as e:
        logging.error(f"Error creating event: {e}")
        return None

def search_events(query, max_results=10):
    """Search events by keyword"""
    service = get_calendar_service()
    if not service:
        return None
    
    try:
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            q=query,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        return events
    except Exception as e:
        logging.error(f"Error searching events: {e}")
        return None

def format_events_for_context(events):
    """Format events for Claude's context"""
    if not events:
        return "No hay eventos próximos en el calendario."
    
    formatted = "📅 EVENTOS EN CALENDARIO:\n\n"
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        summary = event.get('summary', 'Sin título')
        location = event.get('location', '')
        
        # Parse datetime
        try:
            dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            time_str = dt.strftime('%I:%M %p')
            date_str = dt.strftime('%d %b')
        except:
            time_str = start
            date_str = ''
        
        formatted += f"• {summary}\n"
        formatted += f"  📅 {date_str} a las {time_str}\n"
        if location:
            formatted += f"  📍 {location}\n"
        formatted += "\n"
    
    return formatted
