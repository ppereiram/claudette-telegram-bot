"""
Utilidades de seguridad y YouTube para Claudette Bot.
"""

from functools import wraps
from telegram import Update
from config import OWNER_CHAT_ID, logger
import re

# --- 1. IMPORTACIÓN BLINDADA (compatible con v0.x y v1.x) ---
YTApi = None
YT_VERSION = None

try:
    # Intentar v1.x+ primero (nueva API)
    from youtube_transcript_api import YouTubeTranscriptApi
    # En v1.x, se instancia el objeto
    _yt_instance = YouTubeTranscriptApi()
    if hasattr(_yt_instance, 'fetch'):
        YTApi = _yt_instance
        YT_VERSION = "v1"
        logger.info("✅ youtube_transcript_api v1.x cargada")
    else:
        raise AttributeError("No tiene .fetch()")
except Exception:
    try:
        # Fallback v0.x (API estática)
        from youtube_transcript_api import YouTubeTranscriptApi
        if hasattr(YouTubeTranscriptApi, 'get_transcript'):
            YTApi = YouTubeTranscriptApi
            YT_VERSION = "v0"
            logger.info("✅ youtube_transcript_api v0.x cargada")
        else:
            YTApi = None
    except ImportError:
        YTApi = None
        logger.error("⚠️ youtube_transcript_api no está instalada.")


# --- 2. DECORADOR DE SEGURIDAD ---
def restricted(func):
    """Solo permite al OWNER_CHAT_ID usar el bot."""
    @wraps(func)
    async def wrapped(update: Update, context, *args, **kwargs):
        if not update.effective_user:
            return
        user_id = str(update.effective_user.id)
        if user_id != str(OWNER_CHAT_ID):
            logger.warning(f"⛔ Acceso denegado a: {user_id}")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped


# --- 3. FUNCIÓN YOUTUBE (Compatible v0.x y v1.x) ---
def get_youtube_transcript(text):
    """
    Extrae transcripción de un video de YouTube si el texto contiene un link.
    Retorna None si no hay link de YouTube en el texto.
    """
    if not YTApi:
        return None  # Sin librería = silencioso (no romper mensajes normales)

    # Extraer video ID con regex
    video_id = None
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:shorts\/)([0-9A-Za-z_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            video_id = match.group(1)
            break

    if not video_id:
        return None  # No es un video, no hacer nada

    # Intentar obtener transcripción
    try:
        if YT_VERSION == "v1":
            # API v1.x: instancia con .fetch()
            transcript_data = YTApi.fetch(video_id, languages=['es', 'en'])
            # v1.x retorna un objeto FetchedTranscript
            if hasattr(transcript_data, 'text'):
                full_text = transcript_data.text
            else:
                # Iterar sobre los snippets
                full_text = " ".join([
                    snippet.text if hasattr(snippet, 'text') else str(snippet)
                    for snippet in transcript_data
                ])
        else:
            # API v0.x: método estático
            transcript_list = YTApi.get_transcript(video_id, languages=['es', 'en'])
            full_text = " ".join([t['text'] for t in transcript_list])

        if not full_text.strip():
            return "[Sistema]: Video detectado pero la transcripción está vacía."

        # Limitar caracteres
        return f"📺 TRANSCRIPCIÓN VIDEO (ID: {video_id}):\n{full_text[:12000]}\n(Fin de transcripción)"

    except Exception as e:
        logger.error(f"YouTube Transcript Error: {e}")
        return f"[Sistema]: Detecté un video de YouTube (ID: {video_id}), pero no tiene subtítulos disponibles o es privado."
