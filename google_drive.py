"""
Google Drive Service para Claudette Bot.
Funciones para buscar y listar archivos en Google Drive.
"""

import os
import logging
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# Drive API scopes
DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_drive_credentials():
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
        scopes=DRIVE_SCOPES
    )
    
    try:
        creds.refresh(Request())
        return creds
    except Exception as e:
        logger.error(f"Error refreshing Drive credentials: {e}")
        return None

def get_drive_service():
    """Build and return Drive API service."""
    creds = get_drive_credentials()
    if not creds:
        return None
    
    try:
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Error building Drive service: {e}")
        return None

def search_files(query: str, max_results: int = 10) -> dict:
    """
    Search files in Google Drive.
    
    Args:
        query: Search query (file name or content keywords)
        max_results: Maximum number of files to return (default 10)
    
    Returns:
        dict with 'success', 'files' array, and 'error' if any
    """
    service = get_drive_service()
    if not service:
        return {"success": False, "error": "No se pudo conectar a Google Drive."}
    
    try:
        # Build search query for Drive API
        # Search in file name and full text
        search_query = f"name contains '{query}' or fullText contains '{query}'"
        
        # Exclude trashed files
        search_query += " and trashed = false"
        
        results = service.files().list(
            q=search_query,
            pageSize=max_results,
            fields="files(id, name, mimeType, modifiedTime, webViewLink, size, owners)",
            orderBy="modifiedTime desc"
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            return {"success": True, "files": [], "message": f"No se encontraron archivos con '{query}'."}
        
        file_list = []
        for f in files:
            # Get file type in readable format
            mime_type = f.get('mimeType', '')
            file_type = get_readable_file_type(mime_type)
            
            # Format size
            size = f.get('size')
            size_formatted = format_file_size(int(size)) if size else "N/A"
            
            # Get owner
            owners = f.get('owners', [])
            owner = owners[0].get('displayName', 'Desconocido') if owners else 'Desconocido'
            
            file_list.append({
                "id": f['id'],
                "name": f['name'],
                "type": file_type,
                "mime_type": mime_type,
                "modified": f.get('modifiedTime', '')[:10],  # Just date
                "link": f.get('webViewLink', ''),
                "size": size_formatted,
                "owner": owner
            })
        
        return {"success": True, "files": file_list, "count": len(file_list)}
    
    except Exception as e:
        logger.error(f"Error searching files: {e}")
        return {"success": False, "error": f"Error buscando archivos: {str(e)}"}

def list_recent_files(max_results: int = 10) -> dict:
    """
    List recently modified files in Google Drive.
    
    Args:
        max_results: Maximum number of files to return
    
    Returns:
        dict with 'success', 'files' array, and 'error' if any
    """
    service = get_drive_service()
    if not service:
        return {"success": False, "error": "No se pudo conectar a Google Drive."}
    
    try:
        results = service.files().list(
            q="trashed = false",
            pageSize=max_results,
            fields="files(id, name, mimeType, modifiedTime, webViewLink, size)",
            orderBy="modifiedTime desc"
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            return {"success": True, "files": [], "message": "No hay archivos recientes."}
        
        file_list = []
        for f in files:
            mime_type = f.get('mimeType', '')
            file_type = get_readable_file_type(mime_type)
            
            size = f.get('size')
            size_formatted = format_file_size(int(size)) if size else "N/A"
            
            file_list.append({
                "id": f['id'],
                "name": f['name'],
                "type": file_type,
                "modified": f.get('modifiedTime', '')[:10],
                "link": f.get('webViewLink', ''),
                "size": size_formatted
            })
        
        return {"success": True, "files": file_list, "count": len(file_list)}
    
    except Exception as e:
        logger.error(f"Error listing recent files: {e}")
        return {"success": False, "error": f"Error listando archivos: {str(e)}"}

def get_file_info(file_id: str) -> dict:
    """
    Get detailed information about a specific file.
    
    Args:
        file_id: The Google Drive file ID
    
    Returns:
        dict with file details
    """
    service = get_drive_service()
    if not service:
        return {"success": False, "error": "No se pudo conectar a Google Drive."}
    
    try:
        file = service.files().get(
            fileId=file_id,
            fields="id, name, mimeType, modifiedTime, createdTime, webViewLink, size, owners, shared, description"
        ).execute()
        
        mime_type = file.get('mimeType', '')
        size = file.get('size')
        owners = file.get('owners', [])
        
        return {
            "success": True,
            "id": file['id'],
            "name": file['name'],
            "type": get_readable_file_type(mime_type),
            "mime_type": mime_type,
            "created": file.get('createdTime', '')[:10],
            "modified": file.get('modifiedTime', '')[:10],
            "link": file.get('webViewLink', ''),
            "size": format_file_size(int(size)) if size else "N/A",
            "owner": owners[0].get('displayName', 'Desconocido') if owners else 'Desconocido',
            "shared": file.get('shared', False),
            "description": file.get('description', '')
        }
    
    except Exception as e:
        logger.error(f"Error getting file info: {e}")
        return {"success": False, "error": f"Error obteniendo información: {str(e)}"}

def list_files_in_folder(folder_name: str, max_results: int = 20) -> dict:
    """
    List files inside a specific folder.
    
    Args:
        folder_name: Name of the folder to search
        max_results: Maximum number of files to return
    
    Returns:
        dict with 'success', 'files' array, and 'error' if any
    """
    service = get_drive_service()
    if not service:
        return {"success": False, "error": "No se pudo conectar a Google Drive."}
    
    try:
        # First, find the folder
        folder_query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        folder_results = service.files().list(
            q=folder_query,
            fields="files(id, name)"
        ).execute()
        
        folders = folder_results.get('files', [])
        
        if not folders:
            return {"success": False, "error": f"No se encontró la carpeta '{folder_name}'."}
        
        folder_id = folders[0]['id']
        
        # Now list files in that folder
        files_query = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(
            q=files_query,
            pageSize=max_results,
            fields="files(id, name, mimeType, modifiedTime, webViewLink, size)",
            orderBy="name"
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            return {"success": True, "files": [], "message": f"La carpeta '{folder_name}' está vacía."}
        
        file_list = []
        for f in files:
            mime_type = f.get('mimeType', '')
            file_type = get_readable_file_type(mime_type)
            
            size = f.get('size')
            size_formatted = format_file_size(int(size)) if size else "N/A"
            
            file_list.append({
                "id": f['id'],
                "name": f['name'],
                "type": file_type,
                "modified": f.get('modifiedTime', '')[:10],
                "link": f.get('webViewLink', ''),
                "size": size_formatted
            })
        
        return {
            "success": True,
            "folder": folder_name,
            "files": file_list,
            "count": len(file_list)
        }
    
    except Exception as e:
        logger.error(f"Error listing folder contents: {e}")
        return {"success": False, "error": f"Error listando carpeta: {str(e)}"}

def get_readable_file_type(mime_type: str) -> str:
    """Convert MIME type to readable format."""
    type_map = {
        'application/vnd.google-apps.document': '📄 Google Doc',
        'application/vnd.google-apps.spreadsheet': '📊 Google Sheet',
        'application/vnd.google-apps.presentation': '📽️ Google Slides',
        'application/vnd.google-apps.folder': '📁 Carpeta',
        'application/vnd.google-apps.form': '📝 Google Form',
        'application/pdf': '📕 PDF',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '📄 Word',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '📊 Excel',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': '📽️ PowerPoint',
        'application/zip': '🗜️ ZIP',
        'image/jpeg': '🖼️ Imagen JPEG',
        'image/png': '🖼️ Imagen PNG',
        'image/gif': '🖼️ GIF',
        'video/mp4': '🎬 Video MP4',
        'audio/mpeg': '🎵 Audio MP3',
        'text/plain': '📝 Texto',
        'text/csv': '📊 CSV',
    }
    
    return type_map.get(mime_type, '📎 Archivo')

def format_file_size(size_bytes: int) -> str:
    """Convert bytes to human readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
