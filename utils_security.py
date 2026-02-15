from functools import wraps
from telegram import Update
from config import OWNER_CHAT_ID, logger
import re

# --- 1. IMPORTACIÓN BLINDADA ---
# Usamos un alias (YTApi) para que Python no confunda el módulo con la clase
try:
    import youtube_transcript_api
    from youtube_transcript_api import YouTubeTranscriptApi as YTApi
except ImportError:
    YTApi = None
    logger.error("⚠️ La librería youtube_transcript_api no está instalada.")

# --- 2. DECORADOR DE SEGURIDAD ---
def restricted(func):
    @wraps(func)
    async def wrapped(update: Update, context, *args, **kwargs):
        if not update.effective_user: return
        
        user_id = str(update.effective_user.id)
        if user_id != str(OWNER_CHAT_ID):
            logger.warning(f"⛔ Acceso denegado a: {user_id}")
            return
            
        return await func(update, context, *args, **kwargs)
    return wrapped

# --- 3. FUNCIÓN YOUTUBE (Robustecida) ---
def get_youtube_transcript(url):
    """Extrae texto de videos de YouTube."""
    if not YTApi:
        return "[Sistema]: Error interno. La librería de YouTube no cargó correctamente."

    try:
        # Extraer ID con Regex
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
            return None # No es un video, no hacemos nada
        
        # Intentar obtener transcripción
        try:
            # Llamamos al alias YTApi que definimos arriba
            transcript_list = YTApi.get_transcript(video_id, languages=['es', 'en'])
            
            # Unir texto
            full_text = " ".join([t['text'] for t in transcript_list])
            
            # Limitar caracteres para no saturar a Claude
            return f"📺 TRANSCRIPCIÓN VIDEO ({url}):\n{full_text[:12000]}...\n(Fin de transcripción)"
            
        except Exception as e:
            # Si falla (ej: el video no tiene subtítulos), devolvemos el error limpio
            logger.error(f"YouTube Transcript Error: {e}")
            return f"[Sistema]: Detecté un video de YouTube, pero no tiene subtítulos disponibles o es privado."

    except Exception as e:
        logger.error(f"YouTube General Error: {e}")
        return None
