"""
Google Drive Service para Claudette Bot.
Usa autenticación OAuth unificada (google_auth.py).
"""

import os
import logging
from googleapiclient.discovery import build
from google_auth import get_credentials

logger = logging.getLogger("claudette")


def get_drive_service():
    """Build and return Drive API service."""
    creds = get_credentials()
    if not creds:
        return None
    try:
        return build('drive', 'v3', credentials=creds, cache_discovery=False)
    except Exception as e:
        logger.error(f"❌ Error building Drive service: {e}")
        return None


def search_files(query: str, max_results: int = 10) -> dict:
    """Search files in Google Drive."""
    service = get_drive_service()
    if not service:
        return {"success": False, "error": "No se pudo conectar a Google Drive. Verificar credenciales."}

    try:
        search_query = f"name contains '{query}' or fullText contains '{query}'"
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
            mime_type = f.get('mimeType', '')
            size = f.get('size')
            owners = f.get('owners', [])
            file_list.append({
                "id": f['id'],
                "name": f['name'],
                "type": get_readable_file_type(mime_type),
                "mime_type": mime_type,
                "modified": f.get('modifiedTime', '')[:10],
                "link": f.get('webViewLink', ''),
                "size": format_file_size(int(size)) if size else "N/A",
                "owner": owners[0].get('displayName', 'Desconocido') if owners else 'Desconocido'
            })

        return {"success": True, "files": file_list, "count": len(file_list)}
    except Exception as e:
        logger.error(f"❌ Error searching files: {e}")
        return {"success": False, "error": f"Error buscando archivos: {str(e)}"}


def list_recent_files(max_results: int = 10) -> dict:
    """List recently modified files in Google Drive."""
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
            size = f.get('size')
            file_list.append({
                "id": f['id'],
                "name": f['name'],
                "type": get_readable_file_type(f.get('mimeType', '')),
                "modified": f.get('modifiedTime', '')[:10],
                "link": f.get('webViewLink', ''),
                "size": format_file_size(int(size)) if size else "N/A"
            })

        return {"success": True, "files": file_list, "count": len(file_list)}
    except Exception as e:
        logger.error(f"❌ Error listing recent files: {e}")
        return {"success": False, "error": f"Error listando archivos: {str(e)}"}


def get_readable_file_type(mime_type: str) -> str:
    """Convert MIME type to readable format."""
    type_map = {
        'application/vnd.google-apps.document': '📄 Google Doc',
        'application/vnd.google-apps.spreadsheet': '📊 Google Sheet',
        'application/vnd.google-apps.presentation': '📽️ Google Slides',
        'application/vnd.google-apps.folder': '📁 Carpeta',
        'application/pdf': '📕 PDF',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '📄 Word',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '📊 Excel',
        'application/epub+zip': '📚 EPUB',
        'image/jpeg': '🖼️ JPEG',
        'image/png': '🖼️ PNG',
        'text/plain': '📝 Texto',
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
