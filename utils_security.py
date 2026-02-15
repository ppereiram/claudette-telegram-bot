from functools import wraps
from telegram import Update
from config import OWNER_CHAT_ID, logger
from youtube_transcript_api import YouTubeTranscriptApi

# --- SEGURIDAD ---
def restricted(func):
    @wraps(func)
    async def wrapped(update: Update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if str(user_id) != str(OWNER_CHAT_ID):
            logger.warning(f"⛔ Acceso denegado a: {user_id}")
            return # Ignora al intruso
        return await func(update, context, *args, **kwargs)
    return wrapped

# --- YOUTUBE ---
def get_youtube_transcript(url):
    """Extrae texto de videos de YouTube"""
    try:
        video_id = None
        if "v=" in url: video_id = url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in url: video_id = url.split("youtu.be/")[1].split("?")[0]
        
        if not video_id: return None
        
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['es', 'en'])
        text = " ".join([t['text'] for t in transcript])
        return f"📺 TRANSCRIPCIÓN VIDEO ({url}):\n{text[:15000]}..." # Limite tokens
    except Exception as e:
        logger.error(f"YouTube Error: {e}")
        return None
