import os
import logging
import json
import pytz
import re
import base64
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
# HELPERS
# ============================================

def clean_date_iso(date_str, is_end=False):
    """Google Calendar exige formato ISO con zona horaria."""
    if 'T' not in date_str:
        time_part = "T23:59:59" if is_end else "T00:00:00"
        return f"{date_str}{time_part}-06:00"
    return date_str

def search_web_ddg(query: str, max_results=5):
    """Búsqueda general en la web."""
    try:
        if "2026" in query: query = query.replace("2026", "").strip()
        results = []
        with DDGS() as ddgs:
            # Búsqueda de texto general
            search_gen = ddgs.text(query, region='wt-wt', safesearch='off', timelimit='d', max_results=max_results)
            for r in search_gen:
                results.append(f"📰 {r['title']}\n🔗 {r['href']}\n📝 {r['body']}\n")
        return "\n".join(results) if results else "No encontré resultados recientes."
    except Exception as e:
        logger.error(f"Search Error: {e}")
        return f"Error: {str(e)}"

def get_news_dashboard():
    """Obtiene titulares usando el motor de NOTICIAS de DDG."""
    summary = "🗞️ **DASHBOARD DE NOTICIAS (En Tiempo Real)**\n\n"
    
    try:
        with DDGS() as ddgs:
            # 1. Costa Rica - La Nación
            try:
                cr_news = ddgs.news(keywords="Costa Rica La Nación", region='cr-cr', safesearch='off', max_results=4)
                if cr_news:
                    summary += "🇨🇷 **COSTA RICA (La Nación & Locales):**\n"
                    for r in cr_news:
                        summary += f"• [{r['title']}]({r['url']}) - _{r['source']}_\n"
                    summary += "\n"
            except Exception as e:
                logger.error(f"Error Nacion: {e}")

            # 2. CNN en Español
            try:
                cnn_news = ddgs.news(keywords="CNN en Español últimas noticias", region='wt-wt', safesearch='off', max_results=3)
                if cnn_news:
                    summary += "🌎 **CNN EN ESPAÑOL:**\n"
                    for r in cnn_news:
                        summary += f"• [{r['title']}]({r['url']})\n"
                    summary += "\n"
            except Exception as e:
                logger.error(f"Error CNN: {e}")

            # 3. Reuters
            try:
                reu_news = ddgs.news(keywords="Reuters World News", region='us-en', safesearch='off', max_results=3)
                if reu_news:
                    summary += "🌐 **REUTERS (Global):**\n"
                    for r in reu_news:
                        summary += f"• [{r['title']}]({r['url']})\n"
            except Exception as e:
                logger.error(f"Error Reuters: {e}")

    except Exception as e:
        return f"Error generando dashboard: {str(e)}"
    
    if len(summary) < 60: 
        return "⚠️ No pude conectar con los servicios de noticias en este momento."
    return summary

# ============================================
# TOOLS
# ============================================

TOOLS = [
    {
        "name": "get_news_dashboard",
        "description": "Resumen ejecutivo de titulares (La Nación, CNN, Reuters).",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "search_web",
        "description": "Búsqueda libre en Google/Web. Úsalo SIEMPRE para: 1) Cultura pop, cine, farándula. 2) Investigar temas específicos. 3) Verificar datos 'triviales' que no están en tu memoria.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Término de búsqueda"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_calendar_events",
        "description": "Ver eventos del calendario.",
        "input_schema": {
            "type": "object",
            "properties": {"start_date": {"type": "string"}, "end_date": {"type": "string"}},
            "required": ["start_date", "end_date"]
        }
    },
    {
        "name": "create_calendar_event",
        "description": "Crear evento.",
        "input_schema": {
            "type": "object",
            "properties": {"summary": {"type": "string"}, "start_time": {"type": "string"}, "end_time": {"type": "string"}, "location": {"type": "string"}},
            "required": ["summary", "start_time", "end_time"]
        }
    },
    {
        "name": "list_tasks",
        "description": "Listar tareas.",
        "input_schema": {"type": "object", "properties": {"show_completed": {"type": "boolean"}}, "required": []}
    },
    {
        "name": "create_task",
        "description": "Crear tarea.",
        "input_schema": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "notes": {"type": "string"}, "due_date": {"type": "string"}},
            "required": ["title"]
        }
    },
    {
        "name": "complete_task",
        "description": "Completar tarea.",
        "input_schema": {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]}
    },
    {
        "name": "delete_task",
        "description": "Borrar tarea.",
        "input_schema": {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]}
    },
    {
        "name": "search_emails",
        "description": "Buscar emails.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
    },
    {
        "name": "read_email",
        "description": "Leer email.",
        "input_schema": {"type": "object", "properties": {"email_id": {"type": "string"}}, "required": ["email_id"]}
    },
    {
        "name": "send_email",
        "description": "Enviar email.",
        "input_schema": {
            "type": "object",
            "properties": {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}},
            "required": ["to", "subject", "body"]
        }
    },
    {
        "name": "search_drive",
        "description": "Buscar archivos.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
    },
    {
        "name": "list_recent_files",
        "description": "Archivos recientes.",
        "input_schema": {"type": "object", "properties": {"max_results": {"type": "integer"}}, "required": []}
    },
    {
        "name": "search_nearby_places",
        "description": "Buscar lugares.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
    },
    {
        "name": "save_user_fact",
        "description": "Aprender dato del usuario. ÚSALO SIEMPRE que extraigas información importante de una IMAGEN o DOCUMENTO.",
        "input_schema": {
            "type": "object",
            "properties": {"category": {"type": "string"}, "key": {"type": "string"}, "value": {"type": "string"}},
            "required": ["category", "key", "value"]
        }
    },
    {
        "name": "read_knowledge_file",
        "description": "Leer modelos mentales (Jarvis).",
        "input_schema": {
            "type": "object",
            "properties": {"filename": {"type": "string", "enum": ["MODELS_DEEP.md", "FRAMEWORK.md", "ANTIPATTERNS.md", "TEMPLATES.md"]}},
            "required": ["filename"]
        }
    }
]

# ============================================
# EXECUTION LOGIC
# ============================================

def execute_tool(tool_name: str, tool_input: dict, chat_id: int):
    # 🗞️ NEWS & WEB
    if tool_name == "get_news_dashboard":
        return get_news_dashboard()
    elif tool_name == "search_web":
        return search_web_ddg(tool_input['query'])
    
    # 📅 CALENDAR
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
    elif tool_name == "delete_task":
        return google_tasks.delete_task(tool_input['task_id'])
    
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
        # CORRECCION: Combinamos Categoria y Key para que memory_manager acepte solo 2 argumentos
        full_key = f"{tool_input.get('category', 'General')}: {tool_input.get('key', 'Dato')}"
        save_fact(full_key, tool_input['value'])
        return f"✅ Aprendido: {full_key}"

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
    # Si el contenido es una lista (imagen + texto), guardar solo un resumen texto para el historial local
    if isinstance(content, list):
        text_part = next((item['text'] for item in content if item['type'] == 'text'), "[Foto enviada]")
        hist.append({"role": role, "content": text_part})
    else:
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

async def start(update, context): await update.message.reply_text('👋 Soy Claudette. Tengo ojos (envíame fotos) y oídos (audio).')
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

async def handle_photo(update, context):
    """Maneja imágenes enviadas al bot."""
    chat_id = update.message.chat_id
    try:
        # 1. Obtener la foto de mayor resolución
        photo_file = await update.message.photo[-1].get_file()
        
        # 2. Descargar a memoria/temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_img:
            await photo_file.download_to_drive(temp_img.name)
            temp_path = temp_img.name
        
        # 3. Leer y codificar en Base64
        with open(temp_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
        os.unlink(temp_path) # Limpiar
        
        # 4. Obtener caption o usar texto default
        caption = update.message.caption or "Analiza esta imagen. Si es un documento, extrae los datos. Si es un lugar, dime qué es."
        
        # 5. Procesar con Visión
        await process_message(update, context, caption, is_voice=False, image_data=encoded_string)

    except Exception as e:
        logger.error(f"Photo error: {e}")
        await update.message.reply_text("❌ Error procesando la imagen.")


async def process_message(update, context, text, is_voice=False, image_data=None):
    chat_id = update.message.chat_id
    
    # Historial: Si hay imagen, guardamos un indicador
    log_text = f"[IMAGEN] {text}" if image_data else text
    add_to_history(chat_id, "user", log_text)
    
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
PERFIL: {USER_PROFILE}
HECHOS APRENDIDOS: {mem_str}

=== CONTEXTO ===
FECHA: {now.strftime("%A %d-%m-%Y %H:%M")} (Año simulado: 2026)
UBICACIÓN: {loc['name']}

=== PROTOCOLO DE VISIÓN (OJOS) ===
Si recibes una imagen:
1. **DOCUMENTOS (Pasaportes, IDs, Recibos):** Extrae TODOS los datos clave (números, fechas, nombres). 
   - IMPORTANTE: Usa la herramienta `save_user_fact` para guardar esa información en la memoria (ej: Category: "Documentos", Key: "Pasaporte Numero", Value: "12345").
2. **LUGARES/MONUMENTOS:** Identifica el lugar, su historia y contexto (ej: Camino de Santiago).
3. **LIBROS/TEXTO:** Lee el texto, resúmelo o analízalo según pida el usuario.

=== PROTOCOLO DE RESPUESTA ===
1. Eres versátil: Farándula, Negocios, Filosofía o Análisis de Imágenes. Todo es importante.
2. Si no sabes algo trivial (ej: chismes), BÚSCALO (`search_web`).
"""
        messages = get_history(chat_id).copy()
        
        # SI HAY IMAGEN, REEMPLAZAMOS EL ÚLTIMO MENSAJE DEL USER CON EL PAYLOAD MULTIMODAL
        if image_data:
            messages[-1] = {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_data
                        }
                    },
                    {
                        "type": "text",
                        "text": text
                    }
                ]
            }

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

        if not final_response: final_response = "✅ Procesado."
        add_to_history(chat_id, "assistant", final_response)

        # Output Handler
        if is_voice and elevenlabs_client:
            if len(re.findall(r'\d+', final_response)) > 8:
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
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("✅ Claudette Online")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
