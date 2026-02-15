"""
Google Auth Unificado para Claudette Bot.
Todos los servicios (Calendar, Gmail, Drive, Tasks, Contacts) usan este módulo.
Un solo token, un solo refresh, un solo punto de fallo.
"""

import os
import json
import logging
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

logger = logging.getLogger("claudette")

TOKEN_FILE = 'token.json'

# Todos los scopes del bot unificados
ALL_SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/contacts.readonly',
]

# Cache en memoria para no leer archivo en cada request
_cached_creds = None


def get_credentials():
    """
    Obtiene credenciales OAuth válidas.
    Prioridad: 1) Cache en memoria  2) token.json  3) Env vars
    Auto-refresh si expiró.
    """
    global _cached_creds

    # 1. Cache en memoria (más rápido)
    if _cached_creds and _cached_creds.valid:
        return _cached_creds

    creds = None

    # 2. Buscar token.json en varias rutas posibles
    possible_paths = [
        TOKEN_FILE,
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
            creds = Credentials.from_authorized_user_file(token_path, ALL_SCOPES)
        except Exception as e:
            logger.error(f"Error leyendo {token_path}: {e}")

    # 3. Fallback: Variables de entorno (para Render si no hay archivo)
    if not creds and os.environ.get('GOOGLE_REFRESH_TOKEN'):
        try:
            info = {
                "refresh_token": os.environ['GOOGLE_REFRESH_TOKEN'],
                "client_id": os.environ['GOOGLE_CLIENT_ID'],
                "client_secret": os.environ['GOOGLE_CLIENT_SECRET'],
                "token_uri": "https://oauth2.googleapis.com/token",
            }
            creds = Credentials.from_authorized_user_info(info, ALL_SCOPES)
            logger.info("✅ Credenciales cargadas desde env vars")
        except Exception as e:
            logger.error(f"Error con env vars: {e}")

    # 4. Auto-refresh si expiró
    if creds and creds.expired and creds.refresh_token:
        try:
            logger.info("🔄 Token expirado, renovando...")
            creds.refresh(Request())
            # Guardar token renovado
            _save_token(creds, token_path or TOKEN_FILE)
            logger.info("✅ Token renovado y guardado")
        except Exception as e:
            logger.error(f"❌ Error renovando token: {e}")
            return None

    if not creds or not creds.valid:
        logger.error("❌ No hay credenciales Google válidas")
        return None

    _cached_creds = creds
    return creds


def _save_token(creds, path):
    """Guarda el token renovado al archivo."""
    try:
        with open(path, 'w') as f:
            f.write(creds.to_json())
    except Exception as e:
        logger.warning(f"No se pudo guardar token en {path}: {e}")


def invalidate_cache():
    """Fuerza re-lectura del token (útil si se actualizó externamente)."""
    global _cached_creds
    _cached_creds = None
