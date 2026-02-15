from functools import wraps
from telegram import Update
from config import OWNER_CHAT_ID, logger
import re

# Intentamos importar YouTube de forma segura
try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None

# --- SEGURIDAD ---
def restricted(func):
    @wraps(func)
    async def wrapped(update: Update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if str(user_id) != str(OWNER_CHAT_ID):
            logger.warning(f"⛔ Acceso denegado a: {user_id}")
            return 
        return await func(update, context, *args, **kwargs)
    return wrapped

# --- YOUTUBE (Fixed) ---
def get_youtube_transcript(url):
    """Extrae texto de videos de YouTube"""
    if not YouTubeTranscriptApi:
        return "[Error: Librería youtube_transcript_api no instalada]"

    try:
        # Extraer ID con Regex (más robusto)
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
        
        # Llamada directa a la API
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['es', 'en'])
        
        # Formatear texto
        full_text = " ".join([t['text'] for t in transcript_list])
        return f"📺 TRANSCRIPCIÓN VIDEO ({url}):\n{full_text[:15000]}..." 
        
    except Exception as e:
        # Logueamos el error pero no rompemos el bot, devolvemos None
        logger.error(f"YouTube Error: {e}")
        return None
