import os
import os.path
import json
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# SCOPES necesarios para Tasks
SCOPES = ['https://www.googleapis.com/auth/tasks']

def get_tasks_service():
    creds = None
    
    # 1. Intentar cargar desde archivo token.json (Prioridad 1)
    # Buscamos en varias rutas posibles por si Render lo movió
    possible_paths = [
        'token.json',
        '/etc/secrets/token.json', 
        '/opt/render/project/src/token.json'
    ]
    
    token_path = None
    for path in possible_paths:
        if os.path.exists(path):
            token_path = path
            logger.info(f"✅ Token encontrado en: {path}")
            break

    if token_path:
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception as e:
            logger.error(f"Error leyendo token.json: {e}")

    # 2. Si no hay archivo, intentar desde Variables de Entorno (Legacy)
    if not creds and os.environ.get('GOOGLE_REFRESH_TOKEN'):
        try:
            creds_info = {
                "token": "DUMMY_ACCESS_TOKEN",
                "refresh_token": os.environ.get('GOOGLE_REFRESH_TOKEN'),
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": os.environ.get('GOOGLE_CLIENT_ID'),
                "client_secret": os.environ.get('GOOGLE_CLIENT_SECRET'),
                "scopes": SCOPES
            }
            creds = Credentials.from_authorized_user_info(creds_info, SCOPES)
        except Exception as e:
            logger.error(f"Error creando credenciales desde ENV: {e}")

    # 3. Refrescar token si es necesario
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            logger.error(f"Error refrescando token: {e}")
            return None

    if not creds or not creds.valid:
        logger.error("❌ No se encontraron credenciales válidas para Tasks.")
        return None

    try:
        service = build('tasks', 'v1', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Error construyendo servicio Tasks: {e}")
        return None

# --- FUNCIONES DE TAREAS ---

def list_tasks(show_completed=False):
    service = get_tasks_service()
    if not service: return "Error de conexión con Google Tasks."
    
    try:
        # Obtener lista por defecto
        lists = service.tasklists().list(maxResults=1).execute()
        if not lists.get('items'): return "No tienes listas de tareas."
        tasklist_id = lists['items'][0]['id']
        
        results = service.tasks().list(tasklist=tasklist_id, showCompleted=show_completed, maxResults=10).execute()
        items = results.get('items', [])
        
        if not items: return "No hay tareas pendientes."
        
        msg = "📝 **Tus Tareas:**\n"
        for task in items:
            status = "✅" if task['status'] == 'completed' else "⬜"
            msg += f"{status} {task['title']}\n"
        return msg
    except Exception as e:
        return f"Error listando tareas: {e}"

def create_task(title, notes=None, due_date=None):
    service = get_tasks_service()
    if not service: return "Error de conexión con Google Tasks."
    
    try:
        lists = service.tasklists().list(maxResults=1).execute()
        if not lists.get('items'): return "No hay listas de tareas."
        tasklist_id = lists['items'][0]['id']
        
        task_body = {'title': title}
        if notes: task_body['notes'] = notes
        # Fecha formato RFC 3339 (YYYY-MM-DDTHH:MM:SSZ) si hiciera falta
        
        result = service.tasks().insert(tasklist=tasklist_id, body=task_body).execute()
        return f"✅ Tarea creada: {result['title']}"
    except Exception as e:
        return f"Error creando tarea: {e}"

def complete_task(task_query):
    # Simplificado para el ejemplo
    return "Función completar pendiente de implementar búsqueda exacta."
