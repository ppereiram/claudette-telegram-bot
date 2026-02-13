import os
import logging
import json
import pytz
import re
import base64
import io
import requests 
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic
# Asegúrate de que estos módulos existen en tu proyecto
import google_calendar
import gmail_service
import google_tasks
import google_drive
import google_contacts
import google_places
from memory_manager import setup_database, save_fact, get_fact, get_all_facts
from openai import OpenAI
from elevenlabs.client import ElevenLabs
from duckduckgo_search import DDGS
import tempfile
import pypdf
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ENV VARS
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
ELEVENLABS_VOICE_ID = os.environ.get('ELEVENLABS_VOICE_ID', 'JBFqnCBsd6RMkjVDRZzb')
OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY')

if not TELEGRAM_BOT_TOKEN or not ANTHROPIC_API_KEY:
    raise ValueError("Faltan variables de entorno requeridas.")

# Clientes
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY) if ELEVENLABS_API_KEY else None

# --- ESTADO GLOBAL ---
conversation_history = {}
user_locations = {}
user_modes = {} 
MAX_HISTORY_LENGTH = 15
DEFAULT_LOCATION = {"lat": 9.9281, "lng": -84.0907, "name": "San José, Costa Rica (Default)"}

# Modelo correcto según tu entorno
DEFAULT_MODEL = "claude-sonnet-4-20250514"

# --- CARGADORES ---
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

CLAUDETTE_CORE = load_file_content('CLAUDETTE_CORE.md', "Eres Claudette, asistente inteligente.")
USER_PROFILE = load_file_content('user_profile.md', "")

# --- FUNCIONES DE APOYO (HELPERS) ---
def clean_date_iso(date_str, is_end=False):
    if 'T' not in date_str:
        time_part = "T23:59:59" if is_end else "T00:00:00"
        return f"{date_str}{time_part}-06:00"
    return date_str

def get_weather(lat, lon):
    """Obtiene el clima actual desde OpenWeatherMap"""
    if not OPENWEATHER_API_KEY: 
        return "⚠️ No tengo configurada la API Key de OpenWeather."
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=es"
        res = requests.get(url).json()
        if res.get('cod') != 200: 
            return f"Error clima: {res.get('message')}"
        
        desc = res['weather'][0]['description']
        temp = res['main']['temp']
        hum = res['main']['humidity']
        city = res['name']
        
        return f"🌦️ El clima en {city}: {desc.capitalize()}, {temp}°C, Humedad {hum}%."
    except Exception as e:
        return f"Error obteniendo clima: {e}"

def search_web_ddg(query: str, max_results=5):
    try:
        if "2026" in query: query = query.replace("2026", "").strip()
        results = []
        with DDGS() as ddgs:
            search_gen = ddgs.text(query, region='wt-wt', safesearch='off', timelimit='d', max_results=max_results)
            for r in search_gen:
                results.append(f"📰 {r['title']}\n🔗 {r['href']}\n📝 {r['body']}\n")
        return "\n".join(results) if results else "No encontré resultados."
    except Exception as e:
        return f"Error búsqueda web: {str(e)}"

# --- LIBROS Y PDF ---
def extract_text_from_pdf(file_path):
    text = ""
    try:
        reader = pypdf.PdfReader(file_path)
        max_pages = min(len(reader.pages), 50) 
        for i in range(max_pages): text += reader.pages[i].extract_text() + "\n"
    except: pass
    return text

def read_book_from_drive_tool(query):
    files = google_drive.search_files(query)
    if not files or "No se encontraron" in str(files): return "No encontré ese libro."
    service = google_drive.get_drive_service()
    if not service: return "Error Drive."
    try:
        results = service.files().list(q=f"name contains '{query}' and mimeType != 'application/vnd.google-apps.folder'", pageSize=1).execute()
        items = results.get('files', [])
        if not items: return "No hallado."
        
        file_id, file_name = items[0]['id'], items[0]['name']
        request = service.files().get_media(fileId=file_id)
        file_content = request.execute()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file_name}") as temp_file:
            temp_file.write(file_content)
            temp_path = temp_file.name
            
        content = ""
        if file_name.lower().endswith('.pdf'): content = extract_text_from_pdf(temp_path)
        else: content = "Formato no soportado para lectura directa, pero el archivo existe."
        
        os.unlink(temp_path)
        return f"📖 {file_name} (Fragmento):\n{content[:8000]}..."
    except Exception as e: return f"Error leyendo libro: {e}"

# --- DEFINICIÓN DE HERRAMIENTAS (TOOLS) ---
TOOLS = [
    {
        "name": "get_current_weather",
        "description": "Obtener el clima actual basado en latitud y longitud.",
        "input_schema": {
            "type": "object",
            "properties": {"lat": {"type": "number"}, "lon": {"type": "number"}},
            "required": ["lat", "lon"]
        }
    },
    {
        "name": "search_nearby_places",
        "description": "Buscar lugares físicos (restaurantes, tiendas, etc) cerca del usuario usando Google Maps.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Qué buscar (ej: pizza, gasolinera)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_contact_and_call",
        "description": "Busca un contacto en Google y devuelve su tarjeta para llamar.",
        "input_schema": {
            "type": "object",
            "properties": {"name_query": {"type": "string", "description": "Nombre a buscar"}},
            "required": ["name_query"]
        }
    },
    {
        "name": "read_book_from_drive",
        "description": "Leer contenido de un libro o PDF de Google Drive.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
    },
    {
        "name": "save_user_fact",
        "description": "Guardar un dato importante en la memoria a largo plazo.",
        "input_schema": {"type": "object", "properties": {"category": {"type": "string"}, "key": {"type": "string"}, "value": {"type": "string"}}, "required": ["category", "key", "value"]}
    },
    {
        "name": "search_web",
        "description": "Buscar información actual en internet.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
    },
    {
        "name": "get_calendar_events",
        "description": "Consultar eventos del calendario.",
        "input_schema": {"type": "object", "properties": {"start_date": {"type": "string"}, "end_date": {"type": "string"}}, "required": ["start_date", "end_date"]}
    },
    {
        "name": "create_calendar_event",
        "description": "Agendar un evento.",
        "input_schema": {"type": "object", "properties": {"summary": {"type": "string"}, "start_time": {"type": "string"}, "end_time": {"type": "string"}}, "required": ["summary", "start_time", "end_time"]}
    },
    {
        "name": "create_task",
        "description": "Crear una tarea en Google Tasks.",
        "input_schema": {"type": "object", "properties": {"title": {"type": "string"}, "notes": {"type": "string"}}, "required": ["title"]}
    },
    {
        "name": "list_tasks",
        "description": "Listar tareas pendientes.",
        "input_schema": {"type": "object", "properties": {"show_completed": {"type": "boolean"}}}
    },
    {
        "name": "search_emails",
        "description": "Buscar correos en Gmail.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
    }
]

# --- EJECUCIÓN DE HERRAMIENTAS ---
async def execute_tool_async(tool_name: str, tool_input: dict, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    
    if tool_name == "get_current_weather":
        return get_weather(tool_input['lat'], tool_input['lon'])

    elif tool_name == "search_contact_and_call":
        query = tool_input['name_query']
        results = google_contacts.search_contact(query)
        if not results: return f"❌ No encontré a '{query}' en contactos."
        contact = results[0]
        await context.bot.send_contact(chat_id=chat_id, phone_number=contact['phone'], first_name=contact['name'])
        return f"✅ Tarjeta enviada para {contact['name']}."

    elif tool_name == "search_nearby_places":
        loc = user_locations.get(chat_id, DEFAULT_LOCATION)
        return google_places.search_nearby_places(tool_input['query'], loc['lat'], loc['lng'])
        
    elif tool_name == "read_book_from_drive":
        return read_book_from_drive_tool(tool_input['query'])

    elif tool_name == "save_user_fact":
        full_key = f"{tool_input.get('category', 'General')}: {tool_input.get('key', 'Dato')}"
        save_fact(full_key, tool_input['value'])
        return f"✅ Memoria guardada: {full_key}"
        
    elif tool_name == "search_web": return search_web_ddg(tool_input['query'])
    
    elif tool_name == "get_calendar_events":
        return google_calendar.get_calendar_events(clean_date_iso(tool_input['start_date']), clean_date_iso(tool_input['end_date'], True))
    
    elif tool_name == "create_calendar_event":
        return google_calendar.create_calendar_event(tool_input['summary'], clean_date_iso(tool_input['start_time']), clean_date_iso(tool_input['end_time']))
    
    elif tool_name == "create_task":
        return google_tasks.create_task(tool_input['title'], tool_input.get('notes'))
        
    elif tool_name == "list_tasks":
        return google_tasks.list_tasks(tool_input.get('show_completed', False))
        
    elif tool_name == "search_emails": return gmail_service.search_emails(tool_input['query'])
    
    return "Herramienta no encontrada."

# --- PROCESAMIENTO DEL MENSAJE (CEREBRO BLINDADO) ---
async def process_message(update, context, text, is_voice=False, image_data=None):
    # SEGURIDAD: Usar effective_chat para evitar NoneType en Live Location
    chat_id = update.effective_chat.id
    
    # Manejo de historial
    if chat_id not in conversation_history: conversation_history[chat_id] = []
    
    # Agregar mensaje de usuario
    user_msg_content = text
    if image_data:
        user_msg_content = [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_data}},
            {"type": "text", "text": text}
        ]
    conversation_history[chat_id].append({"role": "user", "content": user_msg_content})
    
    if len(conversation_history[chat_id]) > MAX_HISTORY_LENGTH:
        conversation_history[chat_id] = conversation_history[chat_id][-MAX_HISTORY_LENGTH:]

    try:
        # Contexto Dinámico & Recuperación de Ubicación
        tz = pytz.timezone('America/Costa_Rica')
        now = datetime.now(tz)
        
        # Lógica de Recuperación: Si no hay ubicación en RAM, buscar en BD
        if chat_id not in user_locations:
            saved_lat = get_fact("System_Location", "latitude")
            saved_lng = get_fact("System_Location", "longitude")
            if saved_lat and saved_lng:
                try:
                    user_locations[chat_id] = {
                        "lat": float(saved_lat), 
                        "lng": float(saved_lng), 
                        "name": "Ubicación Guardada (BD)"
                    }
                    logger.info(f"📍 Ubicación recuperada de la BD para {chat_id}")
                except:
                    pass # Si falla conversión, usa default

        loc = user_locations.get(chat_id, DEFAULT_LOCATION)
        
        current_mode = user_modes.get(chat_id, "normal")
        mode_instruction = "MODO: NORMAL ⚡. Sé breve y eficiente."
        if current_mode == "profundo":
            mode_instruction = "MODO: PROFUNDO 🧘‍♀️. Respuestas detalladas y analíticas."

        system_prompt = f"""{CLAUDETTE_CORE}
{USER_PROFILE}

=== CONTEXTO ACTUAL ===
📅 FECHA: {now.strftime("%A %d-%m-%Y %H:%M")}
📍 UBICACIÓN: {loc['name']} (Lat: {loc['lat']}, Lon: {loc['lng']})
{mode_instruction}
"""
        
        # 1. Primera Llamada a Claude
        messages = conversation_history[chat_id]
        response = client.messages.create(
            model=DEFAULT_MODEL, 
            max_tokens=4096, 
            system=system_prompt, 
            tools=TOOLS, 
            messages=messages
        )
        
        final_text = ""

        # 2. Manejo de Herramientas (Tool Use)
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            
            for block in response.content:
                if block.type == "tool_use":
                    logger.info(f"🔧 Tool: {block.name}")
                    try:
                        tool_result = await execute_tool_async(block.name, block.input, chat_id, context)
                    except Exception as e:
                        tool_result = f"Error ejecutando herramienta: {str(e)}"
                    
                    messages.append({
                        "role": "user", 
                        "content": [{
                            "type": "tool_result", 
                            "tool_use_id": block.id, 
                            "content": str(tool_result)
                        }]
                    })
            
            # 3. Segunda llamada
            response2 = client.messages.create(
                model=DEFAULT_MODEL, max_tokens=2000, system=system_prompt, tools=TOOLS, messages=messages
            )
            
            for block in response2.content:
                if block.type == "text":
                    final_text += block.text

        else:
            for block in response.content:
                if block.type == "text":
                    final_text += block.text

        if not final_text:
            final_text = "✅ He procesado la solicitud."

        # Respuesta final
        conversation_history[chat_id].append({"role": "assistant", "content": final_text})
        await update.effective_message.reply_text(final_text)

        # Audio (si aplica)
        if is_voice and elevenlabs_client:
            try:
                text_clean = re.sub(r'[^\w\s,.?¡!]', '', final_text)
                audio = elevenlabs_client.generate(text=text_clean, voice=ELEVENLABS_VOICE_ID, model="eleven_multilingual_v2")
                audio_bytes = b"".join(audio)
                await update.effective_message.reply_voice(voice=audio_bytes)
            except Exception as e:
                logger.error(f"Error audio: {e}")

    except Exception as e:
        logger.error(f"Error principal: {e}")
        try:
            await update.effective_message.reply_text(f"⚠️ Error en IA: {str(e)}")
        except: pass

# --- HANDLERS (COMANDOS Y MENSAJES) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hola Pablo. Soy Claudette V5. Persistencia de ubicación activa.")

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conversation_history[update.effective_chat.id] = []
    await update.message.reply_text("🧹 Memoria a corto plazo borrada.")

async def cmd_mode_deep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_modes[update.effective_chat.id] = "profundo"
    await update.message.reply_text("🧘‍♀️ Modo Profundo activado.")

async def cmd_mode_normal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_modes[update.effective_chat.id] = "normal"
    await update.message.reply_text("⚡ Modo Normal activado.")

async def cmd_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    loc = user_locations.get(chat_id, DEFAULT_LOCATION)
    await update.message.reply_text(f"📍 Ubicación actual: {loc['name']}\nEnvíame tu ubicación por Telegram para actualizar.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_message(update, context, update.message.text)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not openai_client: return await update.message.reply_text("Whisper no configurado.")
    try:
        file = await context.bot.get_file(update.message.voice.file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            await file.download_to_drive(f.name)
            path = f.name
        with open(path, "rb") as audio_file:
            transcript = openai_client.audio.transcriptions.create(model="whisper-1", file=audio_file).text
        os.unlink(path)
        await update.message.reply_text(f"🎤 Oído: {transcript}")
        await process_message(update, context, transcript, is_voice=True)
    except Exception as e:
        await update.message.reply_text(f"Error voz: {e}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    with io.BytesIO() as f:
        await photo_file.download_to_memory(out=f)
        image_data = base64.b64encode(f.getvalue()).decode("utf-8")
    caption = update.message.caption or "¿Qué ves en esta imagen?"
    await process_message(update, context, caption, image_data=image_data)

# --- MANEJO DE UBICACIÓN (PERSISTENTE) ---
async def handle_location_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat_id = update.effective_chat.id

    if not message or not message.location:
        return 

    lat = message.location.latitude
    lon = message.location.longitude
    
    # 1. Actualizar memoria RAM
    user_locations[chat_id] = {"lat": lat, "lng": lon, "name": "Ubicación Telegram"}
    
    # 2. Guardar en Base de Datos (Persistencia)
    try:
        save_fact("System_Location", "latitude", str(lat))
        save_fact("System_Location", "longitude", str(lon))
        logger.info(f"💾 Ubicación guardada en BD: {lat}, {lon}")
    except Exception as e:
        logger.error(f"Error guardando ubicación en BD: {e}")
    
    if update.edited_message:
        logger.info(f"📍 Live Location Update para {chat_id}: {lat}, {lon}")
    else:
        await message.reply_text("📍 Ubicación actualizada y guardada en memoria permanente.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

# --- MAIN ---
def main():
    setup_database()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_history))
    app.add_handler(CommandHandler("profundo", cmd_mode_deep))
    app.add_handler(CommandHandler("normal", cmd_mode_normal))
    app.add_handler(CommandHandler("ubicacion", cmd_location))

    # Mensajes
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Ubicación (Live & Static)
    app.add_handler(MessageHandler(filters.LOCATION, handle_location_update))

    # Error Handler
    app.add_error_handler(error_handler)

    print("✅ Claudette Online")
    app.run_polling()

if __name__ == '__main__':
    main()
