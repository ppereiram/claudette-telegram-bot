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

# Environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')

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
    
    # Places - NUEVO
    {
        "name": "search_nearby_places",
        "description": "Buscar lugares cercanos: restaurantes, ferreterías, farmacias, gasolineras, etc. Usar cuando Pablo pregunte 'dónde puedo comer', 'hay una ferretería cerca', 'necesito una farmacia'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Qué buscar: 'restaurante', 'ferretería', 'farmacia', etc."},
                "radius": {"type": "integer", "description": "Radio en metros (default 2000)"}
            },
            "required": ["query"]
        }
    },
    
    # Phone - NUEVO
    {
        "name": "make_phone_call",
        "description": "Generar link para hacer llamada telefónica. Usar cuando Pablo diga 'llámame a X', 'necesito llamar a', 'comunícame con'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone_number": {"type": "string", "description": "Número de teléfono"},
                "contact_name": {"type": "string", "description": "Nombre del contacto (opcional)"}
            },
            "required": ["phone_number"]
        }
    },
    
    # Memory
    {
        "name": "save_user_fact",
        "description": "Guardar información del usuario.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "value": {"type": "string"}
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "get_all_user_facts",
        "description": "Ver toda la información guardada.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    
    # Profile
    {
        "name": "read_local_file",
        "description": "Leer archivo local. user_profile.md tiene datos personales.",
        "input_schema": {
            "type": "object",
            "properties": {"filename": {"type": "string"}},
            "required": ["filename"]
        }
    },
    
    # === CAPA 2: Modelos Mentales ===
    {
        "name": "load_mental_models",
        "description": "Cargar los 216 modelos mentales para análisis profundo. Usar en modo /profundo o cuando Pablo pida análisis, reflexión, o resolver problemas complejos.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    
    # === CAPA 3: Web Search (futuro) ===
    {
        "name": "web_search",
        "description": "Buscar información actual en la web. (Pendiente de implementación)",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"]
        }
    }
]

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_history(chat_id: int) -> list:
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []
    return conversation_history[chat_id]

def add_to_history(chat_id: int, role: str, content: str):
    history = get_history(chat_id)
    history.append({"role": role, "content": content})
    if len(history) > MAX_HISTORY_LENGTH * 2:
        conversation_history[chat_id] = history[-(MAX_HISTORY_LENGTH * 2):]

def clear_history(chat_id: int):
    conversation_history[chat_id] = []

def get_user_location(chat_id: int) -> dict:
    return user_locations.get(chat_id, DEFAULT_LOCATION)

def set_user_location(chat_id: int, lat: float, lng: float, name: str = ""):
    user_locations[chat_id] = {"lat": lat, "lng": lng, "name": name}

def get_mode(chat_id: int) -> str:
    return user_modes.get(chat_id, "normal")

def set_mode(chat_id: int, mode: str):
    user_modes[chat_id] = mode

def has_many_numbers(text: str) -> bool:
    """Check if text has many numbers (for voice fix)."""
    # Find all number sequences
    numbers = re.findall(r'\d+', text)
    # If more than 3 number sequences or any number longer than 4 digits
    if len(numbers) > 3:
        return True
    for num in numbers:
        if len(num) > 4:
            return True
    return False

def read_local_file(filename: str) -> str:
    try:
        path = os.path.join(os.path.dirname(__file__), filename)
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error: {str(e)}"

# ============================================
# VOICE FUNCTIONS
# ============================================

async def transcribe_voice(voice_file):
    if not openai_client:
        return None
    try:
        with open(voice_file, 'rb') as f:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1", file=f, language="es"
            )
        return transcript.text
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return None

async def text_to_speech(text):
    if not elevenlabs_client:
        return None
    try:
        audio = elevenlabs_client.text_to_speech.convert(
            text=text,
            voice_id="2fzSNSOmb5nntInhUtfm",
            model_id="eleven_multilingual_v2"
        )
        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        with open(temp.name, 'wb') as f:
            for chunk in audio:
                f.write(chunk)
        return temp.name
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return None

# ============================================
# TOOL EXECUTION
# ============================================

def execute_tool(name: str, inputs: dict, chat_id: int) -> str:
    
    # Calendar
    if name == "get_calendar_events":
        return google_calendar.get_calendar_events(inputs.get("start_date"), inputs.get("end_date"))
    
    elif name == "create_calendar_event":
        return google_calendar.create_calendar_event(
            inputs.get("summary"), inputs.get("start_time"),
            inputs.get("end_time"), inputs.get("location")
        )
    
    # Tasks
    elif name == "list_tasks":
        result = google_tasks.list_tasks(inputs.get("show_completed", False), inputs.get("max_results", 20))
        if result["success"] and result.get("tasks"):
            text = f"📋 {result['count']} tareas:\n\n"
            for i, t in enumerate(result["tasks"], 1):
                icon = "✅" if t['status'] == 'completed' else "⬜"
                text += f"{i}. {icon} {t['title']}\n"
                if t.get('due_formatted'):
                    text += f"   📅 {t['due_formatted']}\n"
                text += f"   ID: `{t['id']}`\n\n"
            return text
        return result.get("message", "No hay tareas.")
    
    elif name == "create_task":
        result = google_tasks.create_task(inputs.get("title"), inputs.get("notes"), inputs.get("due_date"))
        return f"✅ {result['message']}" if result["success"] else f"❌ {result['error']}"
    
    elif name == "complete_task":
        result = google_tasks.complete_task(inputs.get("task_id"))
        return f"✅ {result['message']}" if result["success"] else f"❌ {result['error']}"
    
    elif name == "delete_task":
        result = google_tasks.delete_task(inputs.get("task_id"))
        return f"✅ {result['message']}" if result["success"] else f"❌ {result['error']}"
    
    # Email
    elif name == "search_emails":
        result = gmail_service.search_emails(inputs.get("query", ""), min(inputs.get("max_results", 10), 20))
        if result["success"] and result.get("emails"):
            text = f"📧 {result['count']} emails:\n\n"
            for i, e in enumerate(result["emails"], 1):
                text += f"{i}. **{e['subject']}**\n   De: {e['from']}\n   ID: `{e['id']}`\n\n"
            return text
        return result.get("message", "No hay emails.")
    
    elif name == "read_email":
        result = gmail_service.get_email(inputs.get("email_id"))
        if result["success"]:
            return f"📧 **{result['subject']}**\nDe: {result['from']}\n\n{result['body']}"
        return f"Error: {result['error']}"
    
    elif name == "send_email":
        result = gmail_service.send_email(inputs.get("to"), inputs.get("subject"), inputs.get("body"), inputs.get("reply_to_id"))
        return f"✅ {result['message']}" if result["success"] else f"❌ {result['error']}"
    
    # Drive
    elif name == "search_drive":
        result = google_drive.search_files(inputs.get("query"), inputs.get("max_results", 10))
        if result["success"] and result.get("files"):
            text = f"🔍 {result['count']} archivos:\n\n"
            for i, f in enumerate(result["files"], 1):
                text += f"{i}. {f['type']} **{f['name']}**\n   🔗 {f['link']}\n\n"
            return text
        return "No encontré archivos."
    
    elif name == "list_recent_files":
        result = google_drive.list_recent_files(inputs.get("max_results", 10))
        if result["success"] and result.get("files"):
            text = f"📁 {result['count']} recientes:\n\n"
            for i, f in enumerate(result["files"], 1):
                text += f"{i}. {f['type']} {f['name']}\n   🔗 {f['link']}\n\n"
            return text
        return "No hay archivos recientes."
    
    # Places - NUEVO
    elif name == "search_nearby_places":
        loc = get_user_location(chat_id)
        result = google_places.search_nearby_places(
            inputs.get("query"),
            loc["lat"],
            loc["lng"],
            inputs.get("radius", 2000)
        )
        if result["success"] and result.get("places"):
            return google_places.format_places_response(result["places"])
        return result.get("message", result.get("error", "No encontré lugares."))
    
    # Phone - NUEVO
    elif name == "make_phone_call":
        phone = inputs.get("phone_number", "").replace(" ", "").replace("-", "")
        name_contact = inputs.get("contact_name", "")
        
        # Format phone link
        tel_link = f"tel:{phone}"
        
        response = f"📞 **Llamar a {name_contact}**\n\n" if name_contact else "📞 **Hacer llamada**\n\n"
        response += f"Número: {phone}\n\n"
        response += f"👆 [Toca aquí para llamar]({tel_link})"
        
        return response
    
    # Memory
    elif name == "save_user_fact":
        save_fact(chat_id, inputs.get("key"), inputs.get("value"))
        return f"✅ Guardado: {inputs.get('key')}"
    
    elif name == "get_all_user_facts":
        facts = get_all_facts(chat_id)
        if facts:
            return "🧠 Lo que sé:\n" + "\n".join([f"• {k}: {v}" for k, v in facts.items()])
        return "No tengo información guardada."
    
    # Files
    elif name == "read_local_file":
        return read_local_file(inputs.get("filename"))
    
    # Mental Models - CAPA 2
    elif name == "load_mental_models":
        return read_local_file("modelos_mentales.md")
    
    # Web Search - CAPA 3 (pendiente)
    elif name == "web_search":
        return "⚠️ Web search aún no implementado. Próximamente."
    
    return f"Tool '{name}' no implementada."

# ============================================
# COMMAND HANDLERS
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    clear_history(chat_id)
    set_mode(chat_id, "normal")
    await update.message.reply_text(
        '¡Hola Pablo! Soy Claudette con Sonnet 4 🧠\n\n'
        '**Comandos:**\n'
        '/profundo - Modo análisis con 216 modelos mentales\n'
        '/normal - Modo asistente rápido\n'
        '/ubicacion - Actualizar mi ubicación\n'
        '/clear - Borrar historial\n\n'
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
        'Tengo acceso a tus 216 modelos mentales.\n'
        'Ahora puedo hacer análisis extendidos, reflexiones filosóficas, '
        'y ayudarte a resolver problemas complejos.\n\n'
        '¿Qué quieres analizar?',
        parse_mode='Markdown'
    )

async def normal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    set_mode(chat_id, "normal")
    await update.message.reply_text('⚡ Modo normal. Respuestas rápidas y precisas.')

async def ubicacion_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '📍 Para actualizar tu ubicación, envíame tu ubicación usando el botón 📎 → Ubicación en Telegram.\n\n'
        f'Ubicación actual: {get_user_location(update.message.chat_id).get("name", "San José, Costa Rica")}'
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
        tz = pytz.timezone('America/Costa_Rica')
        now = datetime.now(tz)
        today = now.strftime("%Y-%m-%d")
        day_name = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"][now.weekday()]
        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        loc = get_user_location(chat_id)
        
        # System prompt varies by mode
        if mode == "profundo":
            system_prompt = f"""Eres Claudette, asistente ejecutiva de Pablo con acceso a 216 modelos mentales.

MODO: PROFUNDO - Análisis extendido, reflexión filosófica, resolución de problemas complejos.

FECHA: {day_name} {today} (2026), {now.strftime("%H:%M")}
UBICACIÓN: {loc.get('name', 'Costa Rica')} ({loc['lat']}, {loc['lng']})

INSTRUCCIONES MODO PROFUNDO:
1. USA load_mental_models para cargar el framework completo
2. Aplica múltiples modelos mentales (5-15) al problema
3. Da análisis extensos y multidimensionales
4. Usa filosofía continental, sistemas, estrategia
5. Sé reflexivo y profundo, no superficial

CONTEXTO DE PABLO:
- Arquitecto/desarrollador inmobiliario, 56 años
- Filosofía de slowness post-pandemia
- Trader NQ futures, ultra-endurance athlete (Ultraman)
- Intereses: filosofía continental, geopolítica, IA
- Proyectos: Feline Sanctuary, TEDx 2026, AI agents"""
        else:
            system_prompt = f"""Eres Claudette, asistente personal de Pablo en Costa Rica.

MODO: NORMAL - Respuestas rápidas, precisas, accionables.

FECHA: {day_name} {today} (2026), {now.strftime("%H:%M")}
MAÑANA: {tomorrow}
UBICACIÓN: {loc.get('name', 'Costa Rica')} ({loc['lat']}, {loc['lng']})

HERRAMIENTAS:
- Calendario, Email, Tareas, Drive
- Lugares cercanos (restaurantes, ferreterías, etc.)
- Llamadas telefónicas
- Datos personales en user_profile.md

INSTRUCCIONES:
1. Sé CONCISO - respuestas breves y útiles
2. Usa herramientas proactivamente
3. Para lugares: search_nearby_places
4. Para llamadas: make_phone_call con número
5. Incluye links de Drive y Maps
6. Año 2026 para todas las fechas

Si Pablo pide análisis profundo o reflexión, sugiere /profundo."""

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
        
        # Send response
        # FIX VOZ: Si es voz y tiene muchos números, enviar texto
        if is_voice and elevenlabs_client and not has_many_numbers(final_response):
            voice_file = await text_to_speech(final_response)
            if voice_file:
                await update.message.reply_voice(voice=open(voice_file, 'rb'))
                os.unlink(voice_file)
            else:
                await update.message.reply_text(final_response, parse_mode='Markdown')
        else:
            # Si tiene números o no es voz, enviar texto
            if is_voice and has_many_numbers(final_response):
                await update.message.reply_text("📝 *Te envío esto por escrito porque tiene datos numéricos:*\n\n" + final_response, parse_mode='Markdown')
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
    
    logger.info(f"🤖 Starting Claudette v2 with {DEFAULT_MODEL}...")
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
    
    logger.info("✅ Claudette v2 ready!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
