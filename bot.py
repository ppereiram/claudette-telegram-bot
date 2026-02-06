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
from duckduckgo_search import DDGS  # <--- NUEVA LIBRERÍA DE BÚSQUEDA
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
# LOAD CORE & MEMORY
# ============================================

def load_file_content(filename, default_text=""):
    try:
        path = f'prompts/{filename}'
        if not os.path.exists(path):
            path = filename
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
# SEARCH HELPER (DuckDuckGo)
# ============================================

def search_web_ddg(query: str, max_results=5):
    """Realiza búsquedas en internet usando DuckDuckGo."""
    try:
        results = []
        with DDGS() as ddgs:
            # Usamos 'text' para búsqueda general/noticias recientes
            search_gen = ddgs.text(query, region='wt-wt', safesearch='off', timelimit='d', max_results=max_results)
            for r in search_gen:
                results.append(f"Titulo: {r['title']}\nLink: {r['href']}\nResumen: {r['body']}\n")
        
        if not results:
            return "No se encontraron resultados recientes."
        return "\n---\n".join(results)
    except Exception as e:
        logger.error(f"Error en DuckDuckGo: {e}")
        return f"Error buscando en la web: {str(e)}"

# ============================================
# TOOLS DEFINITION
# ============================================

TOOLS = [
    # === CAPA 0: WEB & NOTICIAS (NUEVO) ===
    {
        "name": "search_web",
        "description": "Buscar noticias actuales, hechos recientes o información en internet. Úsalo cuando te pregunten 'qué pasó hoy', 'noticias', 'precio de X', o información que no está en tu base de datos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Término de búsqueda (ej: 'Noticias internacionales hoy', 'Precio Bitcoin hoy')"}
            },
            "required": ["query"]
        }
    },

    # === CAPA 1: Asistente Diario ===
    {
        "name": "get_calendar_events",
        "description": "Ver eventos del calendario.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string"},
                "end_date": {"type": "string"}
            },
            "required": ["start_date", "end_date"]
        }
    },
    {
        "name": "create_calendar_event",
        "description": "Crear evento en calendario.",
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
        "description": "Listar tareas pendientes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "show_completed": {"type": "boolean"},
                "max_results": {"type": "integer"}
            },
            "required": []
        }
    },
    {
        "name": "create_task",
        "description": "Crear nueva tarea.",
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
        "description": "Completar tarea por ID.",
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"]
        }
    },
    {
        "name": "delete_task",
        "description": "Eliminar tarea.",
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
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "read_email",
        "description": "Leer email completo por ID.",
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
                "body": {"type": "string"},
                "reply_to_id": {"type": "string"}
            },
            "required": ["to", "subject", "body"]
        }
    },
    {
        "name": "search_drive",
        "description": "Buscar archivos en Drive.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "list_recent_files",
        "description": "Archivos recientes en Drive.",
        "input_schema": {
            "type": "object",
            "properties": {"max_results": {"type": "integer"}},
            "required": []
        }
    },
    {
        "name": "search_nearby_places",
        "description": "Buscar lugares cercanos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "radius": {"type": "integer"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "make_phone_call",
        "description": "Generar link de llamada.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone_number": {"type": "string"},
                "contact_name": {"type": "string"}
            },
            "required": ["phone_number"]
        }
    },
    {
        "name": "save_user_fact",
        "description": "Aprender/Guardar dato nuevo sobre el usuario.",
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
        "name": "get_user_fact",
        "description": "Recuperar dato guardado.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "key": {"type": "string"}
            },
            "required": ["category", "key"]
        }
    },
    {
        "name": "read_knowledge_file",
        "description": "Leer modelos mentales (MODELS_DEEP.md, etc).",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "enum": ["MODELS_DEEP.md", "FRAMEWORK.md", "ANTIPATTERNS.md", "TEMPLATES.md"]
                }
            },
            "required": ["filename"]
        }
    }
]

# ============================================
# TOOL EXECUTION
# ============================================

def execute_tool(tool_name: str, tool_input: dict, chat_id: int):
    """Execute tool and return result."""
    
    # === NUEVA HERRAMIENTA DE BÚSQUEDA ===
    if tool_name == "search_web":
        return search_web_ddg(tool_input['query'])
    
    # Calendar
    elif tool_name == "get_calendar_events":
        return google_calendar.get_calendar_events(
            start_date=tool_input['start_date'],
            end_date=tool_input['end_date']
        )
    elif tool_name == "create_calendar_event":
        return google_calendar.create_calendar_event(
            summary=tool_input.get('summary'),
            start_time=tool_input.get('start_time'),
            end_time=tool_input.get('end_time'),
            location=tool_input.get('location')
        )
    
    # Tasks
    elif tool_name == "list_tasks":
        return google_tasks.list_tasks(
            show_completed=tool_input.get('show_completed', False),
            max_results=tool_input.get('max_results', 10)
        )
    elif tool_name == "create_task":
        return google_tasks.create_task(
            title=tool_input['title'],
            notes=tool_input.get('notes'),
            due_date=tool_input.get('due_date')
        )
    elif tool_name == "complete_task":
        return google_tasks.complete_task(tool_input['task_id'])
    elif tool_name == "delete_task":
        return google_tasks.delete_task(tool_input['task_id'])
    
    # Email
    elif tool_name == "search_emails":
        return gmail_service.search_emails(
            query=tool_input['query'],
            max_results=tool_input.get('max_results', 10)
        )
    elif tool_name == "read_email":
        return gmail_service.read_email(tool_input['email_id'])
    elif tool_name == "send_email":
        return gmail_service.send_email(
            to=tool_input['to'],
            subject=tool_input['subject'],
            body=tool_input['body'],
            reply_to_id=tool_input.get('reply_to_id')
        )
    
    # Drive
    elif tool_name == "search_drive":
        return google_drive.search_files(
            query=tool_input['query'],
            max_results=tool_input.get('max_results', 10)
        )
    elif tool_name == "list_recent_files":
        return google_drive.list_recent_files(
            max_results=tool_input.get('max_results', 10)
        )
    
    # Places
    elif tool_name == "search_nearby_places":
        loc = get_user_location(chat_id)
        result = google_places.search_nearby_places(
            query=tool_input['query'],
            latitude=loc['lat'],
            longitude=loc['lng'],
            radius=tool_input.get('radius', 2000)
        )
        if result.get('success') and result.get('places'):
            return google_places.format_places_response(result['places'])
        elif result.get('success'):
            return result.get('message', 'No encontré lugares.')
        else:
            return f"Error: {result.get('error')}"
    
    # Phone
    elif tool_name == "make_phone_call":
        phone = tool_input['phone_number']
        return f"📞 Link: [Llamar]({f'tel:{phone}'})"
    
    # Memory
    elif tool_name == "save_user_fact":
        save_fact(chat_id, tool_input['category'], tool_input['key'], tool_input['value'])
        return f"✅ Guardado: {tool_input['key']}"
    elif tool_name == "get_user_fact":
        return get_fact(chat_id, tool_input['category'], tool_input['key']) or "No encontrado."
    
    # Jarvis
    elif tool_name == "read_knowledge_file":
        return load_file_content(tool_input['filename'], "No encontrado.")
    
    else:
        return f"Tool '{tool_name}' no existe."

# ============================================
# LOGIC
# ============================================

def get_history(chat_id):
    if chat_id not in conversation_history: conversation_history[chat_id] = []
    return conversation_history[chat_id]

def add_to_history(chat_id, role, content):
    hist = get_history(chat_id)
    hist.append({"role": role, "content": content})
    if len(hist) > MAX_HISTORY_LENGTH * 2: conversation_history[chat_id] = hist[-(MAX_HISTORY_LENGTH * 2):]

def clear_history(chat_id): conversation_history[chat_id] = []
def get_mode(chat_id): return user_modes.get(chat_id, "normal")
def set_mode(chat_id, mode): user_modes[chat_id] = mode
def get_user_location(chat_id): return user_locations.get(chat_id, DEFAULT_LOCATION.copy())
def set_user_location(chat_id, lat, lng, name): user_locations[chat_id] = {"lat": lat, "lng": lng, "name": name}

async def transcribe_voice(audio_path):
    if not openai_client: return ""
    try:
        with open(audio_path, 'rb') as audio:
            return openai_client.audio.transcriptions.create(model="whisper-1", file=audio, language="es").text
    except Exception: return ""

def has_many_numbers(text): return len(re.findall(r'\d+', text)) > 5

# ============================================
# HANDLERS
# ============================================

async def start(update, context):
    await update.message.reply_text('👋 Soy Claudette. Comandos: /profundo, /normal, /clear, /ubicacion.')

async def clear_cmd(update, context):
    clear_history(update.message.chat_id)
    await update.message.reply_text('✅ Memoria borrada.')

async def profundo_cmd(update, context):
    set_mode(update.message.chat_id, "profundo")
    await update.message.reply_text('🧠 Modo Profundo (Jarvis) activado.')

async def normal_cmd(update, context):
    set_mode(update.message.chat_id, "normal")
    await update.message.reply_text('⚡ Modo Normal activado.')

async def ubicacion_cmd(update, context):
    loc = get_user_location(update.message.chat_id)
    await update.message.reply_text(f'📍 Ubicación: {loc.get("name")}')

async def handle_location(update, context):
    loc = update.message.location
    set_user_location(update.message.chat_id, loc.latitude, loc.longitude, "Ubicación actual")
    await update.message.reply_text('✅ Ubicación actualizada.')

async def handle_voice(update, context):
    if not openai_client: return await update.message.reply_text("Voz no disponible.")
    try:
        voice = await update.message.voice.get_file()
        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.ogg')
        await voice.download_to_drive(temp.name)
        transcript = await transcribe_voice(temp.name)
        os.unlink(temp.name)
        if not transcript: return await update.message.reply_text("No escuché nada.")
        logger.info(f"🎤 Voice: {transcript}")
        await process_message(update, context, transcript, is_voice=True)
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error de voz.")

async def process_message(update, context, text, is_voice=False):
    chat_id = update.message.chat_id
    mode = get_mode(chat_id)
    logger.info(f"💬 {text}")
    add_to_history(chat_id, "user", text)

    try:
        # Memoria Dinámica
        try:
            db_facts = get_all_facts()
            dynamic_mem = "\n".join([f"- {k}: {v}" for k, v in db_facts.items()]) if db_facts else "Sin datos."
        except: dynamic_mem = "Error memoria."

        # Contexto
        tz = pytz.timezone('America/Costa_Rica')
        now = datetime.now(tz)
        loc = get_user_location(chat_id)
        
        system_prompt = f"""{CLAUDETTE_CORE}
=== MEMORIA ===
PERFIL: {USER_PROFILE}
APRENDIDO: {dynamic_mem}

=== CONTEXTO ===
FECHA: {now.strftime("%A %d-%m-%Y %H:%M")}
UBICACIÓN: {loc['name']} ({loc['lat']}, {loc['lng']})
MODO: {mode.upper()}

INSTRUCCIONES ADICIONALES:
1. Si te piden NOTICIAS o ACTUALIDAD, usa la herramienta 'search_web'.
2. Si te piden RESUMEN, lee los resultados de la búsqueda y sintetiza.
3. Si te piden ANÁLISIS PROFUNDO de una noticia, usa 'search_web' + tus modelos mentales.
4. Para agenda, revisa SIEMPRE 'get_calendar_events' Y 'list_tasks'.
"""
        messages = get_history(chat_id).copy()
        final_response = ""

        # Thinking Loop
        for i in range(5):
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

        # Respuesta (Voz/Texto)
        if is_voice and elevenlabs_client:
            if has_many_numbers(final_response):
                await update.message.reply_text("📝 *Texto (datos complejos):*\n\n" + final_response, parse_mode='Markdown')
            else:
                try:
                    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="record_voice")
                    audio = elevenlabs_client.text_to_speech.convert(
                        text=final_response, voice_id=ELEVENLABS_VOICE_ID, model_id="eleven_multilingual_v2", output_format="mp3_44100_128"
                    )
                    await update.message.reply_voice(voice=b"".join(audio))
                except: await update.message.reply_text(final_response, parse_mode='Markdown')
        else:
            await update.message.reply_text(final_response, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("Ocurrió un error procesando tu mensaje.")

async def handle_text(update, context):
    await process_message(update, context, update.message.text, is_voice=False)

def main():
    setup_database()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(CommandHandler("profundo", profundo_cmd))
    app.add_handler(CommandHandler("normal", normal_cmd))
    app.add_handler(CommandHandler("ubicacion", ubicacion_cmd))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("✅ Claudette lista.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
