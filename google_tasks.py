"""
Google Tasks Service para Claudette Bot.
Funciones para listar, crear, completar y eliminar tareas.
"""

import os
import logging
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# Tasks API scopes
TASKS_SCOPES = ['https://www.googleapis.com/auth/tasks']

def get_tasks_credentials():
    """Get OAuth credentials from environment variables."""
    client_id = os.environ.get('GOOGLE_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
    refresh_token = os.environ.get('GOOGLE_REFRESH_TOKEN')
    
    if not all([client_id, client_secret, refresh_token]):
        logger.error("Missing Google OAuth credentials in environment")
        return None
    
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=client_id,
        client_secret=client_secret,
        scopes=TASKS_SCOPES
    )
    
    try:
        creds.refresh(Request())
        return creds
    except Exception as e:
        logger.error(f"Error refreshing Tasks credentials: {e}")
        return None

def get_tasks_service():
    """Build and return Tasks API service."""
    creds = get_tasks_credentials()
    if not creds:
        return None
    
    try:
        service = build('tasks', 'v1', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Error building Tasks service: {e}")
        return None

def get_task_lists() -> dict:
    """
    Get all task lists.
    
    Returns:
        dict with 'success', 'lists' array, and 'error' if any
    """
    service = get_tasks_service()
    if not service:
        return {"success": False, "error": "No se pudo conectar a Google Tasks."}
    
    try:
        results = service.tasklists().list(maxResults=10).execute()
        task_lists = results.get('items', [])
        
        lists = []
        for tl in task_lists:
            lists.append({
                "id": tl['id'],
                "title": tl['title']
            })
        
        return {"success": True, "lists": lists}
    
    except Exception as e:
        logger.error(f"Error getting task lists: {e}")
        return {"success": False, "error": f"Error obteniendo listas: {str(e)}"}

def list_tasks(tasklist_id: str = "@default", show_completed: bool = False, max_results: int = 20) -> dict:
    """
    List tasks from a task list.
    
    Args:
        tasklist_id: The task list ID (use "@default" for primary list)
        show_completed: Whether to include completed tasks
        max_results: Maximum number of tasks to return
    
    Returns:
        dict with 'success', 'tasks' array, and 'error' if any
    """
    service = get_tasks_service()
    if not service:
        return {"success": False, "error": "No se pudo conectar a Google Tasks."}
    
    try:
        results = service.tasks().list(
            tasklist=tasklist_id,
            maxResults=max_results,
            showCompleted=show_completed,
            showHidden=show_completed
        ).execute()
        
        tasks = results.get('items', [])
        
        if not tasks:
            return {"success": True, "tasks": [], "message": "No hay tareas pendientes."}
        
        task_list = []
        for task in tasks:
            task_info = {
                "id": task['id'],
                "title": task.get('title', '(Sin título)'),
                "status": task.get('status', 'needsAction'),
                "due": task.get('due', None),
                "notes": task.get('notes', '')
            }
            
            # Format due date if exists
            if task_info['due']:
                # Due date comes as '2026-02-10T00:00:00.000Z'
                task_info['due_formatted'] = task_info['due'][:10]
            
            task_list.append(task_info)
        
        return {"success": True, "tasks": task_list, "count": len(task_list)}
    
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return {"success": False, "error": f"Error listando tareas: {str(e)}"}

def create_task(title: str, notes: str = None, due_date: str = None, tasklist_id: str = "@default") -> dict:
    """
    Create a new task.
    
    Args:
        title: Task title
        notes: Optional task notes/description
        due_date: Optional due date in ISO format (e.g., '2026-02-10')
        tasklist_id: The task list ID (use "@default" for primary list)
    
    Returns:
        dict with 'success', task details, and 'error' if any
    """
    service = get_tasks_service()
    if not service:
        return {"success": False, "error": "No se pudo conectar a Google Tasks."}
    
    try:
        task_body = {
            'title': title,
            'status': 'needsAction'
        }
        
        if notes:
            task_body['notes'] = notes
        
        if due_date:
            # Ensure proper format for due date (RFC 3339)
            if 'T' not in due_date:
                due_date = f"{due_date}T00:00:00.000Z"
            elif not due_date.endswith('Z'):
                due_date = f"{due_date}Z"
            task_body['due'] = due_date
        
        result = service.tasks().insert(
            tasklist=tasklist_id,
            body=task_body
        ).execute()
        
        return {
            "success": True,
            "task_id": result['id'],
            "title": result['title'],
            "message": f"Tarea '{title}' creada exitosamente."
        }
    
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return {"success": False, "error": f"Error creando tarea: {str(e)}"}

def complete_task(task_id: str, tasklist_id: str = "@default") -> dict:
    """
    Mark a task as completed.
    
    Args:
        task_id: The task ID to complete
        tasklist_id: The task list ID
    
    Returns:
        dict with 'success' and 'message' or 'error'
    """
    service = get_tasks_service()
    if not service:
        return {"success": False, "error": "No se pudo conectar a Google Tasks."}
    
    try:
        # First get the task to preserve its data
        task = service.tasks().get(
            tasklist=tasklist_id,
            task=task_id
        ).execute()
        
        # Update status to completed
        task['status'] = 'completed'
        
        result = service.tasks().update(
            tasklist=tasklist_id,
            task=task_id,
            body=task
        ).execute()
        
        return {
            "success": True,
            "message": f"Tarea '{result.get('title', '')}' marcada como completada."
        }
    
    except Exception as e:
        logger.error(f"Error completing task: {e}")
        return {"success": False, "error": f"Error completando tarea: {str(e)}"}

def delete_task(task_id: str, tasklist_id: str = "@default") -> dict:
    """
    Delete a task.
    
    Args:
        task_id: The task ID to delete
        tasklist_id: The task list ID
    
    Returns:
        dict with 'success' and 'message' or 'error'
    """
    service = get_tasks_service()
    if not service:
        return {"success": False, "error": "No se pudo conectar a Google Tasks."}
    
    try:
        service.tasks().delete(
            tasklist=tasklist_id,
            task=task_id
        ).execute()
        
        return {
            "success": True,
            "message": "Tarea eliminada exitosamente."
        }
    
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        return {"success": False, "error": f"Error eliminando tarea: {str(e)}"}

def update_task(task_id: str, title: str = None, notes: str = None, due_date: str = None, tasklist_id: str = "@default") -> dict:
    """
    Update an existing task.
    
    Args:
        task_id: The task ID to update
        title: New title (optional)
        notes: New notes (optional)
        due_date: New due date (optional)
        tasklist_id: The task list ID
    
    Returns:
        dict with 'success' and updated task info or 'error'
    """
    service = get_tasks_service()
    if not service:
        return {"success": False, "error": "No se pudo conectar a Google Tasks."}
    
    try:
        # Get current task
        task = service.tasks().get(
            tasklist=tasklist_id,
            task=task_id
        ).execute()
        
        # Update fields if provided
        if title:
            task['title'] = title
        if notes is not None:
            task['notes'] = notes
        if due_date:
            if 'T' not in due_date:
                due_date = f"{due_date}T00:00:00.000Z"
            task['due'] = due_date
        
        result = service.tasks().update(
            tasklist=tasklist_id,
            task=task_id,
            body=task
        ).execute()
        
        return {
            "success": True,
            "task_id": result['id'],
            "title": result['title'],
            "message": f"Tarea actualizada exitosamente."
        }
    
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        return {"success": False, "error": f"Error actualizando tarea: {str(e)}"}
