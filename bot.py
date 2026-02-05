import os
import logging
import json
import pytz
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic
import google_calendar
import gmail_service
import google_tasks
import google_drive
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

# Get tokens from environment
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

# Initialize clients
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY) if ELEVENLABS_API_KEY else None

# Conversation history storage (in-memory, per chat)
conversation_history = {}
MAX_HISTORY_LENGTH = 10

# ============================================
# MODEL CONFIGURATION - CORRECTED!
# ============================================
DEFAULT_MODEL = "claude-sonnet-4-20250514"  # Sonnet 4 - the correct model name!

# Tool definitions for Claude
TOOLS = [
    # Calendar tools
    {
        "name": "get_calendar_events",
        "description": "Obtener eventos del calendario entre dos fechas. Usar cuando el usuario pregunte por su agenda, eventos, reuniones, citas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Fecha inicio en formato ISO (ej: '2026-02-05T00:00:00-06:00')"},
                "end_date": {"type": "string", "description": "Fecha fin en formato ISO"}
            },
            "required": ["start_date", "end_date"]
        }
    },
    {
        "name": "create_calendar_event",
        "description": "Crear un nuevo evento en el calendario. Usar cuando el usuario quiera agendar, programar, o crear una cita/reunión.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Título del evento"},
                "start_time": {"type": "string", "description": "Hora inicio en formato ISO. SIEMPRE usar año 2026."},
                "end_time": {"type": "string", "description": "Hora fin en formato ISO. SIEMPRE usar año 2026."},
                "location": {"type": "string", "description": "Ubicación del evento (opcional)"}
            },
            "required": ["summary", "start_time", "end_time"]
        }
    },
    # File tools
    {
        "name": "read_local_file",
        "description": "Leer archivos locales. Para datos personales (pasaporte, cédula, DIMEX, dirección, teléfonos) usar 'user_profile.md'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Nombre del archivo (ej: 'user_profile.md')"}
            },
            "required": ["filename"]
        }
    },
    # Memory tools
    {
        "name": "save_user_fact",
        "description": "Guardar información sobre el usuario para recordar en el futuro.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Categoría del dato"},
                "value": {"type": "string", "description": "El valor a guardar"}
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "get_user_fact",
        "description": "Recuperar un dato específico guardado sobre el usuario.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "La categoría a buscar"}
            },
            "required": ["key"]
        }
    },
    {
        "name": "get_all_user_facts",
        "description": "Obtener todos los datos guardados sobre el usuario.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    # Gmail tools
    {
        "name": "search_emails",
        "description": "Buscar emails en Gmail. Sintaxis: 'is:unread', 'from:email@ejemplo.com', 'subject:palabra'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Consulta de búsqueda Gmail"},
                "max_results": {"type": "integer", "description": "Máximo de emails (default 10)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "read_email",
        "description": "Leer el contenido completo de un email específico usando su ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "email_id": {"type": "string", "description": "ID del email"}
            },
            "required": ["email_id"]
        }
    },
    {
        "name": "send_email",
        "description": "Enviar un email.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Email del destinatario"},
                "subject": {"type": "string", "description": "Asunto del email"},
                "body": {"type": "string", "description": "Contenido del email"},
                "reply_to_id": {"type": "string", "description": "ID del email a responder (opcional)"}
            },
            "required": ["to", "subject", "body"]
        }
    },
    # Google Tasks tools
    {
        "name": "list_tasks",
        "description": "Listar tareas pendientes de Google Tasks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "show_completed": {"type": "boolean", "description": "Incluir tareas completadas (default: false)"},
                "max_results": {"type": "integer", "description": "Máximo de tareas (default: 20)"}
            },
            "required": []
        }
    },
    {
        "name": "create_task",
        "description": "Crear una nueva tarea.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Título de la tarea"},
                "notes": {"type": "string", "description": "Notas adicionales (opcional)"},
                "due_date": {"type": "string", "description": "Fecha límite YYYY-MM-DD (opcional). Usar año 2026."}
            },
            "required": ["title"]
        }
    },
    {
        "name": "complete_task",
        "description": "Marcar una tarea como completada.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "ID de la tarea"}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "delete_task",
        "description": "Eliminar una tarea.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "ID de la tarea"}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "update_task",
        "description": "Actualizar una tarea existente.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "ID de la tarea"},
                "title": {"type": "string", "description": "Nuevo título (opcional)"},
                "notes": {"type": "string", "description": "Nuevas notas (opcional)"},
                "due_date": {"type": "string", "description": "Nueva fecha YYYY-MM-DD (opcional)"}
            },
            "required": ["task_id"]
        }
    },
    # Google Drive tools
    {
        "name": "search_drive",
        "description": "Buscar archivos en Google Drive por nombre o contenido.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Palabras clave para buscar"},
                "max_results": {"type": "integer", "description": "Máximo de archivos (default: 10)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "list_recent_files",
        "description": "Listar archivos recientes en Google Drive.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "description": "Máximo de archivos (default: 10)"}
            },
            "required": []
        }
    },
    {
        "name": "get_file_info",
        "description": "Obtener información detallada de un archivo por su ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "ID del archivo en Drive"}
            },
            "required": ["file_id"]
        }
    },
    {
        "name": "list_folder_contents",
        "description": "Listar contenido de una carpeta en Drive.",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder_name": {"type": "string", "description": "Nombre de la carpeta"},
                "max_results": {"type": "integer", "description": "Máximo de archivos (default: 20)"}
            },
            "required": ["folder_name"]
        }
    }
]

def get_conversation_history(chat_id: int) -> list:
    """Get conversation history for a chat."""
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []
    return conversation_history[chat_id]

def add_to_history(chat_id: int, role: str, content: str):
    """Add a message to conversation history."""
    history = get_conversation_history(chat_id)
    history.append({"role": role, "content": content})
    
    if len(history) > MAX_HISTORY_LENGTH * 2:
        conversation_history[chat_id] = history[-(MAX_HISTORY_LENGTH * 2):]

def clear_history(chat_id: int):
    """Clear conversation history for a chat."""
    if chat_id in conversation_history:
        conversation_history[chat_id] = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    chat_id = update.message.chat_id
    clear_history(chat_id)
    await update.message.reply_text(
        '¡Hola Pablo! Soy Claudette, tu asistente personal potenciada por Sonnet 4. '
        'Puedo ayudarte con:\n\n'
        '📅 Calendario\n'
        '📧 Email\n'
        '✅ Tareas\n'
        '📁 Google Drive\n'
        '🧠 Memoria\n\n'
        '¿En qué puedo ayudarte?'
    )

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation history."""
    chat_id = update.message.chat_id
    clear_history(chat_id)
    await update.message.reply_text('✅ Historial borrado.')

def read_local_file(filename):
    """Read a local file from the repository."""
    try:
        file_path = os.path.join(os.path.dirname(__file__), filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"❌ Archivo '{filename}' no encontrado."
    except Exception as e:
        return f"❌ Error: {str(e)}"

async def transcribe_voice(voice_file):
    """Transcribe voice message using Whisper."""
    if not openai_client:
        return None
    
    try:
        with open(voice_file, 'rb') as audio_file:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="es"
            )
        return transcript.text
    except Exception as e:
        logger.error(f"❌ Error transcribing: {e}")
        return None

async def text_to_speech(text):
    """Convert text to speech using ElevenLabs."""
    if not elevenlabs_client:
        return None
    
    try:
        audio = elevenlabs_client.text_to_speech.convert(
            text=text,
            voice_id="2fzSNSOmb5nntInhUtfm",
            model_id="eleven_multilingual_v2"
        )
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        with open(temp_file.name, 'wb') as f:
            for chunk in audio:
                f.write(chunk)
        return temp_file.name
    except Exception as e:
        logger.error(f"❌ Error TTS: {e}")
        return None

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages."""
    if not openai_client:
        await update.message.reply_text("Transcripción de voz no disponible.")
        return
    
    try:
        voice_file = await update.message.voice.get_file()
        temp_voice = tempfile.NamedTemporaryFile(delete=False, suffix='.ogg')
        await voice_file.download_to_drive(temp_voice.name)
        
        transcript = await transcribe_voice(temp_voice.name)
        
        if not transcript:
            await update.message.reply_text("No pude entender el audio.")
            return
        
        logger.info(f"🎤 Voice: {transcript}")
        await process_user_message(update, context, transcript, is_voice=True)
        
    except Exception as e:
        logger.error(f"❌ Voice error: {e}")
        await update.message.reply_text(f"Error: {str(e)}")
    finally:
        try:
            os.unlink(temp_voice.name)
        except:
            pass

def execute_tool(tool_name: str, tool_input: dict, chat_id: int) -> str:
    """Execute a tool and return the result."""
    
    # Calendar
    if tool_name == "get_calendar_events":
        return google_calendar.get_calendar_events(
            start_date=tool_input.get("start_date"),
            end_date=tool_input.get("end_date")
        )
    
    elif tool_name == "create_calendar_event":
        return google_calendar.create_calendar_event(
            summary=tool_input.get("summary"),
            start_time=tool_input.get("start_time"),
            end_time=tool_input.get("end_time"),
            location=tool_input.get("location")
        )
    
    # Files
    elif tool_name == "read_local_file":
        return read_local_file(tool_input.get("filename"))
    
    # Memory
    elif tool_name == "save_user_fact":
        save_fact(chat_id, tool_input.get("key"), tool_input.get("value"))
        return f"✅ Guardado: {tool_input.get('key')} = {tool_input.get('value')}"
    
    elif tool_name == "get_user_fact":
        fact = get_fact(chat_id, tool_input.get("key"))
        return fact if fact else f"No tengo información sobre '{tool_input.get('key')}'"
    
    elif tool_name == "get_all_user_facts":
        facts = get_all_facts(chat_id)
        if facts:
            return "Información guardada:\n" + "\n".join([f"• {k}: {v}" for k, v in facts.items()])
        return "No tengo información guardada."
    
    # Gmail
    elif tool_name == "search_emails":
        result = gmail_service.search_emails(
            tool_input.get("query", ""),
            min(tool_input.get("max_results", 10), 20)
        )
        if result["success"] and result.get("emails"):
            text = f"📧 {result['count']} emails:\n\n"
            for i, email in enumerate(result["emails"], 1):
                text += f"{i}. **{email['subject']}**\n"
                text += f"   De: {email['from']}\n"
                text += f"   Fecha: {email['date']}\n"
                text += f"   ID: `{email['id']}`\n\n"
            return text
        return result.get("message", "No se encontraron emails.")
    
    elif tool_name == "read_email":
        result = gmail_service.get_email(tool_input.get("email_id", ""))
        if result["success"]:
            return f"📧 **{result['subject']}**\nDe: {result['from']}\nFecha: {result['date']}\n\n{result['body']}"
        return f"Error: {result['error']}"
    
    elif tool_name == "send_email":
        result = gmail_service.send_email(
            tool_input.get("to", ""),
            tool_input.get("subject", ""),
            tool_input.get("body", ""),
            tool_input.get("reply_to_id")
        )
        return f"✅ {result['message']}" if result["success"] else f"❌ {result['error']}"
    
    # Tasks
    elif tool_name == "list_tasks":
        result = google_tasks.list_tasks(
            show_completed=tool_input.get("show_completed", False),
            max_results=tool_input.get("max_results", 20)
        )
        if result["success"] and result.get("tasks"):
            text = f"📋 {result['count']} tareas:\n\n"
            for i, task in enumerate(result["tasks"], 1):
                icon = "✅" if task['status'] == 'completed' else "⬜"
                text += f"{i}. {icon} {task['title']}\n"
                if task.get('due_formatted'):
                    text += f"   📅 {task['due_formatted']}\n"
                text += f"   ID: `{task['id']}`\n\n"
            return text
        return result.get("message", "No hay tareas.")
    
    elif tool_name == "create_task":
        result = google_tasks.create_task(
            title=tool_input.get("title", ""),
            notes=tool_input.get("notes"),
            due_date=tool_input.get("due_date")
        )
        return f"✅ {result['message']}" if result["success"] else f"❌ {result['error']}"
    
    elif tool_name == "complete_task":
        result = google_tasks.complete_task(tool_input.get("task_id", ""))
        return f"✅ {result['message']}" if result["success"] else f"❌ {result['error']}"
    
    elif tool_name == "delete_task":
        result = google_tasks.delete_task(tool_input.get("task_id", ""))
        return f"✅ {result['message']}" if result["success"] else f"❌ {result['error']}"
    
    elif tool_name == "update_task":
        result = google_tasks.update_task(
            task_id=tool_input.get("task_id", ""),
            title=tool_input.get("title"),
            notes=tool_input.get("notes"),
            due_date=tool_input.get("due_date")
        )
        return f"✅ {result['message']}" if result["success"] else f"❌ {result['error']}"
    
    # Drive
    elif tool_name == "search_drive":
        result = google_drive.search_files(
            tool_input.get("query", ""),
            tool_input.get("max_results", 10)
        )
        if result["success"] and result.get("files"):
            text = f"🔍 {result['count']} archivos:\n\n"
            for i, f in enumerate(result["files"], 1):
                text += f"{i}. {f['type']} **{f['name']}**\n"
                text += f"   📅 {f['modified']} | 📦 {f['size']}\n"
                text += f"   🔗 {f['link']}\n\n"
            return text
        return f"No encontré archivos con '{tool_input.get('query', '')}'."
    
    elif tool_name == "list_recent_files":
        result = google_drive.list_recent_files(tool_input.get("max_results", 10))
        if result["success"] and result.get("files"):
            text = f"📁 {result['count']} archivos recientes:\n\n"
            for i, f in enumerate(result["files"], 1):
                text += f"{i}. {f['type']} **{f['name']}**\n"
                text += f"   🔗 {f['link']}\n\n"
            return text
        return "No hay archivos recientes."
    
    elif tool_name == "get_file_info":
        result = google_drive.get_file_info(tool_input.get("file_id", ""))
        if result["success"]:
            return f"📄 **{result['name']}**\nTipo: {result['type']}\nTamaño: {result['size']}\n🔗 {result['link']}"
        return f"Error: {result['error']}"
    
    elif tool_name == "list_folder_contents":
        result = google_drive.list_files_in_folder(
            tool_input.get("folder_name", ""),
            tool_input.get("max_results", 20)
        )
        if result["success"] and result.get("files"):
            text = f"📁 '{result['folder']}' ({result['count']} archivos):\n\n"
            for i, f in enumerate(result["files"], 1):
                text += f"{i}. {f['type']} {f['name']}\n"
                text += f"   🔗 {f['link']}\n\n"
            return text
        return result.get("error", "Carpeta vacía.")
    
    return f"Herramienta '{tool_name}' no implementada."

async def process_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE, user_message: str, is_voice: bool = False):
    """Process user message."""
    chat_id = update.message.chat_id
    
    logger.info(f"💬 USER: {user_message}")
    add_to_history(chat_id, "user", user_message)
    
    try:
        costa_rica_tz = pytz.timezone('America/Costa_Rica')
        now = datetime.now(costa_rica_tz)
        today_str = now.strftime("%Y-%m-%d")
        day_name = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"][now.weekday()]
        tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        
        system_prompt = f"""Eres Claudette, la asistente personal de Pablo en Costa Rica. Respondes en español de manera natural, inteligente y conversacional.

FECHA ACTUAL: {day_name} {today_str} (año 2026), hora: {now.strftime("%H:%M")}
MAÑANA: {tomorrow_str}

HERRAMIENTAS DISPONIBLES:
- Calendario: ver eventos, crear citas
- Gmail: buscar, leer, enviar emails
- Tasks: gestionar tareas pendientes
- Drive: buscar archivos, ver carpetas
- Memoria: guardar/recuperar información del usuario
- Archivo local: user_profile.md contiene datos personales (pasaporte, cédula, etc.)

INSTRUCCIONES:
1. Usa las herramientas proactivamente cuando sea relevante
2. Siempre incluye links de Drive para que el usuario pueda abrir los archivos
3. Muestra IDs de tareas/emails para referencias futuras
4. Mantén el contexto de la conversación
5. Sé conciso pero completo
6. Usa el año 2026 para todas las fechas"""

        messages = get_conversation_history(chat_id).copy()
        
        logger.info(f"🚀 Calling {DEFAULT_MODEL} with {len(messages)} messages...")
        
        response = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=4096,
            system=system_prompt,
            tools=TOOLS,
            messages=messages
        )
        
        logger.info(f"🤖 Response: {response.stop_reason}")
        
        # Handle tool use
        if response.stop_reason == "tool_use":
            tool_results = []
            
            for block in response.content:
                if block.type == "tool_use":
                    logger.info(f"🔧 Tool: {block.name}")
                    result = execute_tool(block.name, block.input, chat_id)
                    logger.info(f"📤 Result: {str(result)[:100]}...")
                    
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
        
        logger.info(f"📨 Response: {final_response[:100]}...")
        
        # Send response
        if is_voice and elevenlabs_client:
            voice_file = await text_to_speech(final_response)
            if voice_file:
                await update.message.reply_voice(voice=open(voice_file, 'rb'))
                os.unlink(voice_file)
            else:
                await update.message.reply_text(final_response)
        else:
            await update.message.reply_text(final_response)
        
    except Exception as e:
        logger.error(f"❌ ERROR: {e}", exc_info=True)
        await update.message.reply_text(f"Error: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages."""
    await process_user_message(update, context, update.message.text, is_voice=False)

def main():
    """Start the bot."""
    logger.info(f"🗄️ Setting up database...")
    setup_database()
    
    logger.info(f"🤖 Starting Claudette with {DEFAULT_MODEL}...")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info(f"✅ Claudette ready with Sonnet 4!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
