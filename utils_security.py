"""
Utilidades de seguridad y YouTube para Claudette Bot.
YouTube: Intenta transcript directo -> si IP bloqueada -> oEmbed titulo + busqueda web.
"""

from functools import wraps
from telegram import Update
from config import OWNER_CHAT_ID, logger
import re
import requests as http_requests

# --- 1. IMPORTACION BLINDADA ---
YTApi = None
YT_VERSION = None

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    _yt_instance = YouTubeTranscriptApi()
    if hasattr(_yt_instance, 'fetch'):
        YTApi = _yt_instance
        YT_VERSION = "v1"
        logger.info("youtube_transcript_api v1.x cargada")
    else:
        raise AttributeError("No tiene .fetch()")
except Exception:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        if hasattr(YouTubeTranscriptApi, 'get_transcript'):
            YTApi = YouTubeTranscriptApi
            YT_VERSION = "v0"
            logger.info("youtube_transcript_api v0.x cargada")
        else:
            YTApi = None
    except ImportError:
        YTApi = None
        logger.warning("youtube_transcript_api no instalada. Solo fallback disponible.")


# --- 2. DECORADOR DE SEGURIDAD ---
def restricted(func):
    """Solo permite al OWNER_CHAT_ID usar el bot."""
    @wraps(func)
    async def wrapped(update: Update, context, *args, **kwargs):
        if not update.effective_user:
            return
        user_id = str(update.effective_user.id)
        if user_id != str(OWNER_CHAT_ID):
            logger.warning(f"Acceso denegado a: {user_id}")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped


# --- 3. EXTRAER VIDEO ID ---
def _extract_video_id(text):
    """Extrae video ID de cualquier formato de URL YouTube."""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})(?:[&?]|$)',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:shorts\/)([0-9A-Za-z_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


# --- 4. FALLBACK: oEmbed + Web Search ---
def _get_video_metadata(video_id):
    """Obtiene titulo y autor del video via oEmbed (no bloqueado por YouTube)."""
    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        resp = http_requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "title": data.get("title", ""),
                "author": data.get("author_name", ""),
            }
    except Exception as e:
        logger.warning(f"oEmbed fallo: {e}")
    return None


def _web_search_video_summary(video_id, title=""):
    """Busca resumen del video en la web como fallback."""
    try:
        from duckduckgo_search import DDGS
        ddgs = DDGS()

        query = f'"{title}" youtube resumen' if title else f"youtube {video_id} summary"
        results = ddgs.text(query, max_results=3, region="es-es")

        summaries = []
        for r in results:
            summaries.append(f"- {r['title']}: {r['body'][:200]}")

        if summaries:
            return "\n".join(summaries)
    except Exception as e:
        logger.warning(f"Web search fallback fallo: {e}")
    return None


# --- 5. FUNCION PRINCIPAL YOUTUBE ---
def get_youtube_transcript(text):
    """
    Extrae contenido de un video de YouTube.
    Estrategia:
    1. Intentar transcripcion directa (puede fallar desde cloud IPs)
    2. Si falla -> obtener titulo via oEmbed + buscar resumen en web
    3. Si todo falla -> dar contexto minimo a Claude para que ayude
    """
    video_id = _extract_video_id(text)
    if not video_id:
        return None  # No es un link de YouTube

    logger.info(f"YouTube detectado: {video_id}")

    # --- INTENTO 1: Transcripcion directa ---
    if YTApi:
        try:
            if YT_VERSION == "v1":
                transcript_data = YTApi.fetch(video_id, languages=['es', 'en'])
                if hasattr(transcript_data, 'text'):
                    full_text = transcript_data.text
                else:
                    full_text = " ".join([
                        snippet.text if hasattr(snippet, 'text') else str(snippet)
                        for snippet in transcript_data
                    ])
            else:
                transcript_list = YTApi.get_transcript(video_id, languages=['es', 'en'])
                full_text = " ".join([t['text'] for t in transcript_list])

            if full_text.strip():
                logger.info(f"Transcripcion directa obtenida ({len(full_text)} chars)")
                return f"TRANSCRIPCION VIDEO (https://youtube.com/watch?v={video_id}):\n{full_text[:12000]}\n(Fin de transcripcion)"

        except Exception as e:
            error_str = str(e)
            if "blocking" in error_str.lower() or "ip" in error_str.lower() or "banned" in error_str.lower():
                logger.warning(f"YouTube bloqueo IP de Render. Usando fallback...")
            else:
                logger.error(f"YouTube Transcript Error: {e}")

    # --- INTENTO 2: oEmbed (titulo) + Web Search (resumen) ---
    logger.info("Intentando fallback: oEmbed + web search...")

    metadata = _get_video_metadata(video_id)
    title = metadata["title"] if metadata else ""
    author = metadata["author"] if metadata else ""

    web_summary = _web_search_video_summary(video_id, title)

    # Construir contexto para Claude
    parts = [f"VIDEO DE YOUTUBE: https://youtube.com/watch?v={video_id}"]

    if title:
        parts.append(f'Titulo: "{title}"')
    if author:
        parts.append(f"Canal: {author}")

    if web_summary:
        parts.append(f"\nInformacion encontrada en la web sobre este video:\n{web_summary}")
        parts.append("\n[NOTA SISTEMA: No pude obtener la transcripcion completa porque YouTube bloquea servidores cloud. La informacion anterior viene de busquedas web. Ofrece analisis basado en lo disponible y sugiere al usuario que comparta puntos especificos del video si quiere profundizar.]")
    else:
        parts.append("\n[NOTA SISTEMA: No pude obtener ni la transcripcion ni un resumen web de este video. YouTube bloquea servidores cloud. Pide al usuario que te cuente de que trata el video o que copie y pegue las partes relevantes para poder analizarlo juntos.]")

    result = "\n".join(parts)
    logger.info(f"Fallback completado: titulo={'OK' if title else 'NO'}, web={'OK' if web_summary else 'NO'}")
    return result
