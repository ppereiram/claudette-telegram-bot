"""
Google Tasks Service para Claudette Bot.
Usa autenticación OAuth unificada (google_auth.py).
"""

import logging
from googleapiclient.discovery import build
from google_auth import get_credentials

logger = logging.getLogger("claudette")


def get_tasks_service():
    creds = get_credentials()
    if not creds:
        return None
    try:
        return build('tasks', 'v1', credentials=creds, cache_discovery=False)
    except Exception as e:
        logger.error(f"Error construyendo servicio Tasks: {e}")
        return None


def list_tasks(show_completed=False):
    service = get_tasks_service()
    if not service:
        return "Error de conexión con Google Tasks."

    try:
        lists = service.tasklists().list(maxResults=1).execute()
        if not lists.get('items'):
            return "No tienes listas de tareas."
        tasklist_id = lists['items'][0]['id']

        results = service.tasks().list(
            tasklist=tasklist_id, showCompleted=show_completed, maxResults=10
        ).execute()
        items = results.get('items', [])

        if not items:
            return "No hay tareas pendientes."

        msg = "📝 **Tus Tareas:**\n"
        for task in items:
            status = "✅" if task['status'] == 'completed' else "⬜"
            msg += f"{status} {task['title']}\n"
        return msg
    except Exception as e:
        return f"Error listando tareas: {e}"


def create_task(title, notes=None, due_date=None):
    service = get_tasks_service()
    if not service:
        return "Error de conexión con Google Tasks."

    try:
        lists = service.tasklists().list(maxResults=1).execute()
        if not lists.get('items'):
            return "No hay listas de tareas."
        tasklist_id = lists['items'][0]['id']

        task_body = {'title': title}
        if notes:
            task_body['notes'] = notes

        result = service.tasks().insert(tasklist=tasklist_id, body=task_body).execute()
        return f"✅ Tarea creada: {result['title']}"
    except Exception as e:
        return f"Error creando tarea: {e}"
