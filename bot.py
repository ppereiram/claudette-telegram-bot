import os
import logging
import json
import pytz
import re
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic
import google_calendar
import gmail_service
import google_tasks
import google_drive
import google_places
from memory_manager import setup_database, save_fact, get_fact, get_all_facts
from openai import OpenAI
from elevenlabs.client import ElevenLabs
from duckduckgo_search import DDGS
import tempfile

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================
# ENVIRONMENT VARIABLES
# ============================================
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
ELEVENLABS_VOICE_ID = os.environ.get('ELEVENLABS_VOICE_ID', 'JBFqnCBsd6RMkjVDRZzb') 

if not TELEGRAM_BOT_TOKEN or not ANTHROPIC_API_KEY:
    raise ValueError("Missing required environment variables")

# Initialize clients
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY) if ELEVENLABS_API_KEY else None

# Conversation state
conversation_history = {}
user_modes = {}
user_locations = {}
MAX_HISTORY_LENGTH = 10

# Default location: San José, Costa Rica
DEFAULT_LOCATION = {"lat": 9.9281, "lng": -84.0907, "name": "San José, Costa Rica"}
DEFAULT_MODEL = "claude-sonnet-4-20250514"

# ============================================
# LOAD FILES
# ============================================

def load_file_content(filename, default_text=""):
    try:
        path = f'prompts/{filename}'
        if not os.path.exists(path): path = filename
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                logger.info(f"📚 Loaded {filename}")
                return f.read()
    except Exception as e:
        logger.error(f"⚠️ Error loading {filename}: {e}")
    return default_text

CLAUDETTE_CORE = load_file_content('CLAUDETTE_CORE.md', "Eres Claudette, asistente de Pablo.")
USER_PROFILE = load_file_content('user_profile.md', "") 

# ============================================
# HELPERS (Dates & Search)
# ============================================

def clean_date_iso(date_str, is_end=False):
    """Google Calendar exige formato ISO con zona horaria (RFC3339)."""
    if 'T' not in date_str:
        # Si es solo fecha YYYY-MM-DD, agregar hora y zona horaria CR (-06:00)
        time_part = "T23:59:59" if is_end else "T00:00:00"
        return f"{date_str}{time_part}-06:00"
    return date_str

def search_web_ddg(query: str, max_results=5):
    """Búsqueda en web con manejo de errores."""
    try:
        # Forzar búsqueda de "hoy" si la query tiene fecha futura (evitar error 2026)
        if "2026" in query:
            query = query.replace("2026", "").strip()
            query += " actual hoy"
            
        results = []
        with DDGS() as ddgs:
            search_gen = ddgs.text(query, region='wt-wt', safesearch='off', timelimit='d', max_results=max_results)
            for r in search_gen:
                results.append(f"📰 {r['title']}\n🔗 {r['href']}\n📝 {r['body']}\n")
        
        if not results: return "No encontré noticias recientes."
        return "\n".join(results)
    except Exception as e:
        logger.error(f"Search Error: {e}")
        return f"Error buscando: {str(e)}"

# ============================================
# TOOLS
# ============================================

TOOLS = [
    {
        "name": "search_web",
        "description": "Buscar noticias y actualidad. Si preguntan por 'noticias de hoy', usa esto. Ignora el año 2026 del sistema, busca información del 'mundo real' actual.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Término de búsqueda (ej: 'Noticias Costa Rica hoy', 'Precio Bitcoin hoy')"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_calendar_events",
        "description": "Ver eventos del calendario.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Fecha YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "Fecha YYYY-MM-DD"}
            },
            "required": ["start_date", "end_date"]
        }
    },
    {
        "name": "create_calendar_event",
        "description": "Crear evento.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "start_time": {"type": "string"},
                "end_time": {"type": "string"},
                "location": {"type": "string"}
            },
            "required": ["summary", "start_time", "end_time"]
        }
    },
    {
        "name": "list_tasks",
        "description": "Listar tareas.",
        "input_schema": {
            "type": "object",
            "properties": {"show_completed": {"type": "boolean"}},
            "required": []
        }
    },
    {
        "name": "create_task",
        "description": "Crear tarea.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "notes": {"type": "string"},
                "due_date": {"type": "string"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "complete_task",
        "description": "Completar tarea.",
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"]
        }
    },
    {
        "name": "delete_task",
        "description": "Borrar tarea.",
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"]
        }
    },
    {
        "name": "search_emails",
        "description": "Buscar emails.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"]
        }
    },
    {
        "name": "read_email",
        "description": "Leer email.",
        "input_schema": {
            "type": "object",
            "properties": {"email_id": {"type": "string"}},
            "required": ["email_id"]
        }
    },
    {
        "name": "send_email",
        "description": "Enviar email.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"}
            },
            "required": ["to", "subject", "body"]
        }
    },
    {
        "name": "search_drive",
        "description": "Buscar archivos.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"]
        }
    },
    {
        "name": "list_recent_files",
        "description": "Archivos recientes.",
        "input_schema": {
            "type": "object",
            "properties": {"max_results": {"type": "integer"}},
            "required": []
        }
    },
    {
        "name": "search_nearby_places",
        "description": "Buscar lugares.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"]
        }
    },
    {
        "name": "save_user_fact",
        "description": "Aprender dato del usuario.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "key": {"type": "string"},
                "value": {"type": "string"}
            },
            "required": ["category", "key", "value"]
        }
    },
    {
        "name": "read_knowledge_file",
        "description": "Leer modelos mentales (Jarvis).",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "enum": ["MODELS_DEEP.md", "FRAMEWORK.md", "ANTIPATTERNS.md", "TEMPLATES.md"]}
            },
            "required": ["filename"]
        }
    }
]

# ============================================
# EXECUTION LOGIC
# ============================================

def execute_tool(tool_name: str, tool_input: dict, chat_id: int):
    # 🌍 WEB SEARCH
    if tool_name == "search_web":
        return search_web_ddg(tool_input['query'])
    
    # 📅 CALENDAR (FIXED DATES)
    elif tool_name == "get_calendar_events":
        return google_calendar.get_calendar_events(
            start_date=clean_date_iso(tool_input['start_date']),
            end_date=clean_date_iso(tool_input['end_date'], is_end=True)
        )
    elif tool_name == "create_calendar_event":
        return google_calendar.create_calendar_event(
            summary=tool_input.get('summary'),
            start_time=tool_input.get('start_time'),
            end_time=tool_input.get('end_time'),
            location=tool_input.get('location')
        )
    
    # ✅ TASKS
    elif tool_name == "list_tasks":
        return google_tasks.list_tasks(show_completed=tool_input.get('show_completed', False))
    elif tool_name == "create_task":
        return google_tasks.create_task(
            title=tool_input['title'],
            notes=tool_input.get('notes'),
            due_date=tool_input.get('due_date')
        )
    elif tool_name == "complete_task":
        return google_tasks.complete_task(tool_input['task_id'])
    
    # 📧 EMAIL
    elif tool_name == "search_emails":
        return gmail_service.search_emails(query=tool_input['query'])
    elif tool_name == "read_email":
        return gmail_service.read_email(tool_input['email_id'])
    elif tool_name == "send_email":
        return gmail_service.send_email(
            to=tool_input['to'], 
            subject=tool_input['subject'], 
            body=tool_input['body']
        )
    
    # 📁 DRIVE
    elif tool_name == "search_drive":
        return google_drive.search_files(query=tool_input['query'])
    elif tool_name == "list_recent_files":
        return google_drive.list_recent_files()
    
    # 📍 PLACES
    elif tool_name == "search_nearby_places":
        loc = get_user_location(chat_id)
        result = google_places.search_nearby_places(
            query=tool_input['query'],
            latitude=loc['lat'],
            longitude=loc['lng']
        )
        if result.get('success') and result.get('places'):
            return google_places.format_places_response(result['places'])
        return "No encontré lugares."
    
    # 🧠 MEMORY & JARVIS
    elif tool_name == "save_user_fact":
        save_fact(chat_id, tool_input['category'], tool_input['key'], tool_input['value'])
        return f"✅ Aprendido: {tool_input['key']}"
    elif tool_name == "read_knowledge_file":
        return load_file_content(tool_input['filename'], "No encontrado.")
    
    return "Tool desconocido."

# ============================================
# BOT HANDLERS
# ============================================

def get_history(chat_id):
    if chat_id not in conversation_history: conversation_history[chat_id] = []
    return conversation_history[chat_id]

def add_to_history(chat_id, role, content):
    hist = get_history(chat_id)
    hist.append({"role": role, "content": content})
    if len(hist) > MAX_HISTORY_LENGTH * 2: conversation_history[chat_id] = hist[-(MAX_HISTORY_LENGTH * 2):]

def clear_history(chat_id): conversation_history[chat_id] = []
def get_user_location(chat_id): return user_locations.get(chat_id, DEFAULT_LOCATION.copy())
def set_user_location(chat_id, lat, lng, name): user_locations[chat_id] = {"lat": lat, "lng": lng, "name": name}

async def transcribe_voice(audio_path):
    if not openai_client: return ""
    try:
        with open(audio_path, 'rb') as audio:
            return openai_client.audio.transcriptions.create(model="whisper-1", file=audio, language="es").text
    except Exception: return ""

async def start(update, context): await update.message.reply_text('👋 Soy Claudette. Lista para ayudar.')
async def clear_cmd(update, context): 
    clear_history(update.message.chat_id)
    await update.message.reply_text('✅ Memoria limpia.')

async def handle_voice(update, context):
    if not openai_client: return await update.message.reply_text("Voz no configurada.")
    try:
        voice = await update.message.voice.get_file()
        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.ogg')
        await voice.download_to_drive(temp.name)
        transcript = await transcribe_voice(temp.name)
        os.unlink(temp.name)
        if not transcript: return await update.message.reply_text("No entendí el audio.")
        await process_message(update, context, transcript, is_voice=True)
    except Exception as e:
        logger.error(f"Voice error: {e}")
        await update.message.reply_text("Error de audio.")

async def process_message(update, context, text, is_voice=False):
    chat_id = update.message.chat_id
    add_to_history(chat_id, "user", text)
    
    try:
        # Contexto Dinámico
        try:
            db_facts = get_all_facts()
            mem_str = "\n".join([f"- {k}: {v}" for k, v in db_facts.items()]) if db_facts else "Vacío"
        except: mem_str = "Error BD"

        tz = pytz.timezone('America/Costa_Rica')
        now = datetime.now(tz)
        loc = get_user_location(chat_id)

        system_prompt = f"""{CLAUDETTE_CORE}
=== MEMORIA ===
PERFIL ESTÁTICO: {USER_PROFILE}
MEMORIA APRENDIDA: {mem_str}

=== CONTEXTO ===
FECHA SISTEMA: {now.strftime("%A %d-%m-%Y %H:%M")} (Año simulado: 2026)
UBICACIÓN: {loc['name']}

=== REGLAS NOTICIAS Y ACTUALIDAD ===
1. Si el usuario pide NOTICIAS, PRECIOS o ACTUALIDAD, usa la herramienta 'search_web'.
2. IMPORTANTE: Al usar 'search_web', ignora que es el año 2026. Busca términos como "Noticias hoy" o "Precio actual" para obtener datos reales de internet.
3. Para la agenda personal, revisa SIEMPRE 'get_calendar_events' Y 'list_tasks'.
"""
        messages = get_history(chat_id).copy()
        final_response = ""

        # Thinking Loop (Max 5 pasos)
        for _ in range(5):
            response = client.messages.create(
                model=DEFAULT_MODEL, max_tokens=4096, system=system_prompt, tools=TOOLS, messages=messages
            )
            messages.append({"role": "assistant", "content": response.content})
            
            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        logger.info(f"🔧 Tool: {block.name}")
                        res = execute_tool(block.name, block.input, chat_id)
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(res)})
                messages.append({"role": "user", "content": tool_results})
            else:
                final_response = "\n".join([b.text for b in response.content if hasattr(b, "text")])
                break

        if not final_response: final_response = "✅ Listo."
        add_to_history(chat_id, "assistant", final_response)

        # Output Handler
        if is_voice and elevenlabs_client:
            # Si tiene muchos números o tablas, enviar texto
            if len(re.findall(r'\d+', final_response)) > 6:
                await update.message.reply_text("📝 *Respuesta detallada:*\n\n" + final_response, parse_mode='Markdown')
            else:
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="record_voice")
                try:
                    audio = elevenlabs_client.text_to_speech.convert(
                        text=final_response, voice_id=ELEVENLABS_VOICE_ID, model_id="eleven_multilingual_v2", output_format="mp3_44100_128"
                    )
                    await update.message.reply_voice(voice=b"".join(audio))
                except Exception:
                    await update.message.reply_text(final_response, parse_mode='Markdown')
        else:
            await update.message.reply_text(final_response, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("Ocurrió un error inesperado.")

async def handle_text(update, context):
    await process_message(update, context, update.message.text, is_voice=False)

def main():
    setup_database()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("✅ Claudette Online")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
