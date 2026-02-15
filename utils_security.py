# utils_security.py
from functools import wraps
from telegram import Update
from config import OWNER_CHAT_ID, logger
import re

# IMPORTACIÓN CORRECTA
try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    logger.error("Falta instalar youtube_transcript_api")
    YouTubeTranscriptApi = None

# ... (resto de tu código: decorador @restricted) ...

def get_youtube_transcript(url):
    # Verificación segura
    if YouTubeTranscriptApi is None:
        return "[Error: Librería de YouTube no disponible]"
        
    try:
        # ... (Tu código de regex para sacar el ID sigue igual) ...
        # ... (patrones regex ...)
        
        # AQUÍ ESTÁ EL CAMBIO CLAVE:
        # Usamos la clase importada directamente
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['es', 'en'])
        
        full_text = " ".join([t['text'] for t in transcript_list])
        return f"📺 TRANSCRIPCIÓN VIDEO ({url}):\n{full_text[:15000]}..." 
        
    except Exception as e:
        logger.error(f"YouTube Error: {e}")
        return None
