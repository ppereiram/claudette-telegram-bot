from functools import wraps
from telegram import Update
from config import OWNER_CHAT_ID, logger
import re

# --- 1. IMPORTACIÓN SEGURA DE YOUTUBE ---
try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None
    logger.error("⚠️ La librería youtube_transcript_api no está instalada.")

# --- 2. DECORADOR DE SEGURIDAD (¡AQUÍ ESTÁ LO QUE FALTABA!) ---
def restricted(func):
    """Decorador para restringir el acceso solo al dueño del bot."""
    @wraps(func)
    async def wrapped(update: Update, context, *args, **kwargs):
        # Verificar que update.effective_user existe (a veces es None en ciertos updates)
        if not update.effective_user:
            return
            
        user_id = str(update.effective_user.id)
        owner_id = str(OWNER_CHAT_ID)
        
        if user_id != owner_id:
            logger.warning(f"⛔ Acceso denegado a usuario: {user_id}")
            return  # Ignoramos al intruso silenciosamente
            
        return await func(update, context, *args, **kwargs)
    return wrapped

# --- 3. FUNCIÓN DE YOUTUBE ---
def get_youtube_transcript(url):
    """Extrae texto de videos de YouTube de forma segura."""
    if not YouTubeTranscriptApi:
        return "[Sistema]: No puedo leer el video porque falta la librería 'youtube_transcript_api'."

    try:
        # Regex para sacar el ID del video
        video_id = None
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
            r'(?:embed\/)([0-9A-Za-z_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                break
        
        if not video_id: 
            return None
        
        # Intentar obtener transcripción
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['es', 'en'])
            full_text = " ".join([t['text'] for t in transcript_list])
            return f"📺 TRANSCRIPCIÓN VIDEO ({url}):\n{full_text[:15000]}..."
        except Exception as e:
            logger.error(f"Error obteniendo transcripción de {video_id}: {e}")
            return f"[Sistema]: No pude obtener la transcripción del video (quizás no tiene subtítulos). Error: {e}"
            
    except Exception as e:
        logger.error(f"YouTube Error General: {e}")
        return None
