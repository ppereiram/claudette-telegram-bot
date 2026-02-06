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
user_modes = {}  # chat_id -> "normal" or "profundo"
user_locations = {}  # chat_id -> {"lat": x, "lng": y}
MAX_HISTORY_LENGTH = 10

# Default location: San José, Costa Rica
DEFAULT_LOCATION = {"lat": 9.9281, "lng": -84.0907, "name": "San José, Costa Rica"}

# Model
DEFAULT_MODEL = "claude-sonnet-4-20250514"

# ============================================
# LOAD CORE & MEMORY
# ============================================

def load_file_content(filename, default_text=""):
    """Helper to load markdown files safely."""
    try:
        # Intentar ruta prompts/ primero
        path = f'prompts/{filename}'
        if not os.path.exists(path):
            path = filename # Intentar ruta raíz
            
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                logger.info(f"📚 Loaded {filename}")
                return f.read()
    except Exception as e:
        logger.error(f"⚠️ Error loading {filename}: {e}")
    
    return default_text

# Cargar Core y Perfil al inicio
CLAUDETTE_CORE = load_file_content('CLAUDETTE_CORE.md', "Eres Claudette, asistente de Pablo.")
USER_PROFILE = load_file_content('user_profile.md', "") 

# ============================================
# TOOLS DEFINITION
# ============================================

TOOLS = [
    # === CAPA 1: Asistente Diario ===
    
    # Calendar
    {
        "name": "get_calendar_events",
        "description": "Ver eventos del calendario.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Fecha inicio ISO"},
                "end_date": {"type": "string", "description": "Fecha fin ISO"}
            },
            "required": ["start_date", "end_date"]
        }
    },
    {
        "name": "create_calendar_event",
        "description": "Crear evento en calendario. Usar año 2026.",
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
    
    # Tasks
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
    
    # Email
    {
        "name": "search_emails",
        "description": "Buscar emails. Sintaxis: 'is:unread', 'from:x', 'subject:x'.",
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
    
    # Drive
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
    
    # Places
    {
        "name": "search_nearby_places",
        "description": "Buscar lugares cercanos: restaurantes, ferreterías, farmacias, gasolineras, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Qué buscar"},
                "radius": {"type": "integer", "description": "Radio en metros (default 2000)"}
            },
            "required": ["query"]
        }
    },
    
    # Phone
    {
        "name": "make_phone_call",
        "description": "Generar link para hacer llamada telefónica.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone_number": {"type": "string"},
                "contact_name": {"type": "string"}
            },
            "required": ["phone_number"]
        }
    },
    
    # Memory
    {
        "name": "save_user_fact",
        "description": "Guardar información nueva sobre el usuario en la base de datos (aprender).",
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
        "description": "Recuperar dato guardado específicamente.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "key": {"type": "string"}
            },
            "required": ["category", "key"]
        }
    },
    
    # === JARVIS SYSTEM ===
    
    {
        "name": "read_knowledge_file",
        "description": "Leer archivos del sistema Jarvis. NO usar para user_profile (ya está cargado). Usar para modelos mentales.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "enum": ["MODELS_DEEP.md", "FRAMEWORK.md", "ANTIPATTERNS.md", "TEMPLATES.md"],
                    "description": "Archivo a leer"
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
    
    # Calendar
    if tool_name == "get_calendar_events":
        # === FIX: Nombre correcto de la función ===
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
            formatted = google_places.format_places_response(result['places'])
            return formatted
        elif result.get('success'):
            return result.get('message', 'No encontré lugares.')
        else:
            return f"Error: {result.get('error')}"
    
    # Phone
    elif tool_name == "make_phone_call":
        phone = tool_input['phone_number']
        name = tool_input.get('contact_name', 'el número')
        # Generate tel: link
        tel_link = f"tel:{phone}"
        return f"📞 Para llamar a {name}: [Click aquí]({tel_link}) o marca {phone}"
    
    # Memory
    elif tool_name == "save_user_fact":
        save_fact(
            chat_id=chat_id,
            category=tool_input['category'],
            key=tool_input['key'],
            value=tool_input['value']
        )
        return f"✅ Dato aprendido y guardado: {tool_input['category']}/{tool_input['key']}"
    
    elif tool_name == "get_user_fact":
        fact = get_fact(
            chat_id=chat_id,
            category=tool_input['category'],
            key=tool_input['key']
        )
        return fact if fact else "No encontré ese dato específico."
    
    # === JARVIS SYSTEM ===
    elif tool_name == "read_knowledge_file":
        filename = tool_input['filename']
        return load_file_content(filename, f"Error: {filename} no encontrado.")
    
    else:
        return f"Tool '{tool_name}' no implementado."

# ============================================
# CONVERSATION MANAGEMENT
# ============================================

def get_history(chat_id: int):
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []
    return conversation_history[chat_id]

def add_to_history(chat_id: int, role: str, content: str):
    hist = get_history(chat_id)
    hist.append({"role": role, "content": content})
    
    # Keep only last N messages
    if len(hist) > MAX_HISTORY_LENGTH * 2:
        conversation_history[chat_id] = hist[-(MAX_HISTORY_LENGTH * 2):]

def clear_history(chat_id: int):
    conversation_history[chat_id] = []

def get_mode(chat_id: int) -> str:
    return user_modes.get(chat_id, "normal")

def set_mode(chat_id: int, mode: str):
    user_modes[chat_id] = mode

def get_user_location(chat_id: int):
    return user_locations.get(chat_id, DEFAULT_LOCATION.copy())

def set_user_location(chat_id: int, lat: float, lng: float, name: str):
    user_locations[chat_id] = {"lat": lat, "lng": lng, "name": name}

# ============================================
# VOICE PROCESSING
# ============================================

async def transcribe_voice(audio_path: str) -> str:
    """Transcribe voice using Whisper."""
    if not openai_client:
        return ""
    
    try:
        with open(audio_path, 'rb') as audio:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio,
                language="es"
            )
        return transcript.text
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return ""

def has_many_numbers(text: str) -> bool:
    """Check if text has many numbers (don't read those aloud)."""
    numbers = re.findall(r'\d+', text)
    return len(numbers) > 5

# ============================================
# COMMAND HANDLERS
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '👋 Hola! Soy **Claudette**, tu asistente ejecutiva.\n\n'
        '**Comandos:**\n'
        '/profundo - Modo análisis profundo con modelos mentales\n'
        '/normal - Modo asistente rápido\n'
        '/ubicacion - Ver/actualizar ubicación\n'
        '/clear - Borrar historial\n\n'
        '**Capacidades:**\n'
        '📅 Calendario y tareas\n'
        '📧 Gmail\n'
        '📁 Google Drive\n'
        '📍 Lugares cercanos\n'
        '🧠 Sistema Jarvis (modo profundo)\n\n'
        '¿En qué te ayudo?',
        parse_mode='Markdown'
    )

async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_history(update.message.chat_id)
    await update.message.reply_text('✅ Historial borrado.')

async def profundo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    set_mode(chat_id, "profundo")
    await update.message.reply_text(
        '🧠 **Modo Profundo activado**\n\n'
        'Sistema Jarvis con 216 modelos mentales disponibles.\n'
        'Puedo hacer análisis extendidos, reflexiones filosóficas, '
        'y ayudarte a resolver problemas complejos.\n\n'
        'Cuando lo necesite, cargaré automáticamente:\n'
        '• MODELS_DEEP.md - 176 modelos especializados\n'
        '• FRAMEWORK.md - Metodología paso-a-paso\n'
        '• ANTIPATTERNS.md - Cuándo NO usar modelos\n'
        '• TEMPLATES.md - Plantillas ejecutables\n\n'
        '¿Qué quieres analizar?',
        parse_mode='Markdown'
    )

async def normal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    set_mode(chat_id, "normal")
    await update.message.reply_text('⚡ Modo normal activado. Respuestas rápidas y precisas.')

async def ubicacion_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loc = get_user_location(update.message.chat_id)
    await update.message.reply_text(
        '📍 Para actualizar tu ubicación, envíame tu ubicación usando el botón 📎 → Ubicación en Telegram.\n\n'
        f'Ubicación actual: {loc.get("name", "San José, Costa Rica")}'
    )

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle location updates from user."""
    chat_id = update.message.chat_id
    loc = update.message.location
    set_user_location(chat_id, loc.latitude, loc.longitude, "Tu ubicación actual")
    await update.message.reply_text(f'✅ Ubicación actualizada: {loc.latitude}, {loc.longitude}')

# ============================================
# MESSAGE PROCESSING
# ============================================

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not openai_client:
        await update.message.reply_text("Voz no disponible.")
        return
    
    try:
        voice = await update.message.voice.get_file()
        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.ogg')
        await voice.download_to_drive(temp.name)
        
        transcript = await transcribe_voice(temp.name)
        os.unlink(temp.name)
        
        if not transcript:
            await update.message.reply_text("No entendí el audio.")
            return
        
        logger.info(f"🎤 Voice: {transcript}")
        await process_message(update, context, transcript, is_voice=True)
        
    except Exception as e:
        logger.error(f"Voice error: {e}")
        await update.message.reply_text(f"Error: {str(e)}")

async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, is_voice: bool = False):
    chat_id = update.message.chat_id
    mode = get_mode(chat_id)
    
    logger.info(f"💬 [{mode}] {text}")
    add_to_history(chat_id, "user", text)
    
    try:
        # 1. Recuperar memoria dinámica (base de datos)
        try:
            db_facts = get_all_facts()
            if db_facts:
                dynamic_memory = "\n".join([f"- {k}: {v}" for k, v in db_facts.items()])
            else:
                dynamic_memory = "Sin datos aprendidos aún."
        except Exception as e:
            logger.error(f"Error reading DB facts: {e}")
            dynamic_memory = "Error accediendo a memoria."

        # 2. Configurar contexto temporal
        tz = pytz.timezone('America/Costa_Rica')
        now = datetime.now(tz)
        today = now.strftime("%Y-%m-%d")
        day_name = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"][now.weekday()]
        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        loc = get_user_location(chat_id)
        
        # 3. Construir System Prompt con MEMORIA PERSISTENTE
        base_prompt = f"""{CLAUDETTE_CORE}

=== PERFIL DE USUARIO (ESTÁTICO - user_profile.md) ===
{USER_PROFILE}

=== MEMORIA APRENDIDA (DINÁMICA - Base de Datos) ===
{dynamic_memory}
"""

        if mode == "profundo":
            system_prompt = f"""{base_prompt}

=== CONTEXTO ACTUAL ===
FECHA: {day_name} {today} (2026), {now.strftime("%H:%M")}
UBICACIÓN: {loc.get('name', 'Costa Rica')} ({loc['lat']}, {loc['lng']})

=== MODO PROFUNDO ACTIVADO ===
Tienes acceso a read_knowledge_file para cargar modelos especializados.
Recuerda: Integra modelos en narrativa natural, NO bullets académicos."""
        else:
            system_prompt = f"""{base_prompt}

=== CONTEXTO ACTUAL ===
FECHA: {day_name} {today} (2026), {now.strftime("%H:%M")}
MAÑANA: {tomorrow}
UBICACIÓN: {loc.get('name', 'Costa Rica')} ({loc['lat']}, {loc['lng']})

=== MODO NORMAL (ASISTENTE RÁPIDO) ===
INSTRUCCIONES:
1. Sé CONCISO.
2. Usa herramientas proactivamente.
3. Para buscar lugares usa search_nearby_places.
"""

        messages = get_history(chat_id).copy()
        
        logger.info(f"🚀 Calling {DEFAULT_MODEL}...")
        
        response = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=4096,
            system=system_prompt,
            tools=TOOLS,
            messages=messages
        )
        
        # Handle tool use
        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    logger.info(f"🔧 Tool: {block.name}")
                    result = execute_tool(block.name, block.input, chat_id)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result)
                    })
            
            # Get final response
            follow_up = client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=4096,
                system=system_prompt,
                tools=TOOLS,
                messages=messages + [
                    {"role": "assistant", "content": response.content},
                    {"role": "user", "content": tool_results}
                ]
            )
            
            text_blocks = [b.text for b in follow_up.content if hasattr(b, "text")]
            final_response = "\n".join(text_blocks) if text_blocks else "✅ Hecho!"
        else:
            text_blocks = [b.text for b in response.content if hasattr(b, "text")]
            final_response = "\n".join(text_blocks)
        
        add_to_history(chat_id, "assistant", final_response)
        
        # ===========================================
        # RESPUESTA AL USUARIO
        # ===========================================
        
        # Caso 1: Usuario usó VOZ y tenemos ElevenLabs activo
        if is_voice and elevenlabs_client:
            if has_many_numbers(final_response):
                await update.message.reply_text("📝 *Te envío texto porque hay muchos datos numéricos:*\n\n" + final_response, parse_mode='Markdown')
            else:
                try:
                    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="record_voice")
                    
                    audio_stream = elevenlabs_client.text_to_speech.convert(
                        text=final_response,
                        voice_id=ELEVENLABS_VOICE_ID,
                        model_id="eleven_multilingual_v2",
                        output_format="mp3_44100_128"
                    )
                    
                    audio_bytes = b"".join(audio_stream)
                    await update.message.reply_voice(voice=audio_bytes)
                    
                except Exception as e:
                    logger.error(f"❌ Error generando voz ElevenLabs: {e}")
                    await update.message.reply_text(final_response, parse_mode='Markdown')

        # Caso 2: Usuario escribió TEXTO
        else:
            await update.message.reply_text(final_response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        await update.message.reply_text(f"Error: {str(e)}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_message(update, context, update.message.text, is_voice=False)

# ============================================
# MAIN
# ============================================

def main():
    logger.info("🗄️ Setting up database...")
    setup_database()
    
    logger.info("📚 Loading Claudette Core System...")
    logger.info(f"✅ Core loaded: {len(CLAUDETTE_CORE)} chars")
    
    logger.info(f"🤖 Starting Claudette v2 (Jarvis) with {DEFAULT_MODEL}...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(CommandHandler("profundo", profundo_cmd))
    app.add_handler(CommandHandler("normal", normal_cmd))
    app.add_handler(CommandHandler("ubicacion", ubicacion_cmd))
    
    # Messages
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("✅ Claudette v2 (Jarvis Edition) ready!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
