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
import google_calendar
import gmail_service
import google_tasks
import google_drive
import google_contacts
import google_places
from memory_manager import setup_database, save_fact, get_fact, get_all_facts
from openai import OpenAI
from elevenlabs.client import ElevenLabs
# REEMPLAZO: Usamos googlesearch en lugar de duckduckgo
try:
    from googlesearch import search as google_search_func
except ImportError:
    google_search_func = None
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

# --- FUNCIONES DE APOYO ---
def clean_date_iso(date_str, is_end=False):
    if 'T' not in date_str:
        time_part = "T23:59:59" if is_end else "T00:00:00"
        return f"{date_str}{time_part}-06:00"
    return date_str

def get_weather(lat, lon):
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

# --- NUEVA BÚSQUEDA GOOGLE ---
def search_web_google(query, max_results=5):
    """Realiza una búsqueda en Google Web."""
    if not google_search_func:
        return "⚠️ Error: Falta instalar `googlesearch-python`."
    
    try:
        results = []
        # advanced=True devuelve objetos con titulo, descripcion y url
        for result in google_search_func(query, num_results=max_results, advanced=True, lang="es"):
            results.append(f"📰 {result.title}\n🔗 {result.url}\n📝 {result.description}\n")
        
        if not results:
            return "Google no devolvió resultados."
        return "\n".join(results)
    except Exception as e:
        return f"Error Google Search: {str(e)}"

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

# --- HERRAMIENTAS ---
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
        "description": "Buscar lugares cercanos (restaurantes, tiendas, etc).",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Qué buscar (ej: pizza, veterinaria)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_contact_and_call",
        "description": "Busca un contacto en Google y devuelve su tarjeta.",
        "input_schema": {
            "type": "object",
            "properties": {"name_query": {"type": "string"}},
            "required": ["name_query"]
        }
    },
    {
        "name": "read_book_from_drive",
        "description": "Leer contenido de Drive.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
    },
    {
        "name": "save_user_fact",
        "description": "Guardar dato en memoria.",
        "input_schema": {"type": "object", "properties": {"category": {"type": "string"}, "key": {"type": "string"}, "value": {"type": "string"}}, "required": ["category", "key", "value"]}
    },
    {
        "name": "search_web",
        "description": "Buscar en Google Web.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
    },
    {
        "name": "get_calendar_events",
        "description": "Consultar calendario.",
        "input_schema": {"type": "object", "properties": {"start_date": {"type": "string"}, "end_date": {"type": "string"}}, "required": ["start_date", "end_date"]}
    },
    {
        "name": "create_calendar_event",
        "description": "Agendar evento.",
        "input_schema": {"type": "object", "properties": {"summary": {"type": "string"}, "start_time": {"type": "string"}, "end_time": {"type": "string"}}, "required": ["summary", "start_time", "end_time"]}
    },
    {
        "name": "create_task",
        "description": "Crear tarea.",
        "input_schema": {"type": "object", "properties": {"title": {"type": "string"}, "notes": {"type": "string"}}, "required": ["title"]}
    },
    {
        "name": "list_tasks",
        "description": "Listar tareas.",
        "input_schema": {"type": "object", "properties": {"show_completed": {"type": "boolean"}}}
    },
    {
        "name": "search_emails",
        "description": "Buscar correos.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
    }
]

# --- EJECUCIÓN ---
async def execute_tool_async(tool_name: str, tool_input: dict, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    
    if tool_name == "get_current_weather":
        return get_weather(tool_input['lat'], tool_input['lon'])

    elif tool_name == "search_contact_and_call":
        query = tool_input['name_query']
        results = google_contacts.search_contact(query)
        if not results: return f"❌ No encontré a '{query}'."
        contact = results[0]
        await context.bot.send_contact(chat_id=chat_id, phone_number=contact['phone'], first_name=contact['name'])
        return f"✅ Contacto: {contact['name']}."

    elif tool_name == "search_nearby_places":
        loc = user_locations.get(chat_id, DEFAULT_LOCATION)
        lat = loc['lat']
        lng = loc['lng']
        query = tool_input['query']

        # INTENTO 1: Google Places API (Oficial)
        try:
            places_result = google_places.search_nearby_places(query, lat, lng)
            if not places_result or "Error" in str(places_result) or "problema" in str(places_result):
                 raise Exception("API Places falló.")
            return places_result
        except Exception as e:
            logger.error(f"⚠️ Google Places API falló: {e}. Usando Google Web Search.")
            
            # INTENTO 2: Fallback Google Web Search (Scraper)
            # Usamos "loc:" para forzar búsqueda por coordenadas en Google
            fallback_query = f"{query} loc:{lat},{lng}"
            return search_web_google(fallback_query)

    elif tool_name == "read_book_from_drive":
        return read_book_from_drive_tool(tool_input['query'])

    elif tool_name == "save_user_fact":
        full_key = f"{tool_input.get('category', 'General')}: {tool_input.get('key', 'Dato')}"
        save_fact(full_key, tool_input['value'])
        return f"✅ Guardado: {full_key}"
        
    elif tool_name == "search_web": return search_web_google(tool_input['query'])
    
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

# --- CEREBRO ---
async def process_message(update, context, text, is_voice=False, image_data=None):
    chat_id = update.effective_chat.id
    if chat_id not in conversation_history: conversation_history[chat_id] = []
    
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
        tz = pytz.timezone('America/Costa_Rica')
        now = datetime.now(tz)
        
        # Recuperar ubicación de BD si RAM está vacía
        if chat_id not in user_locations:
            try:
                # CORREGIDO: get_fact solo acepta 1 argumento (la key)
                saved_lat = get_fact(f"System_Location_Lat_{chat_id}") 
                saved_lng = get_fact(f"System_Location_Lng_{chat_id}")
                
                if saved_lat and saved_lng:
                    user_locations[chat_id] = {
                        "lat": float(saved_lat), 
                        "lng": float(saved_lng), 
                        "name": "Ubicación Guardada"
                    }
                    logger.info(f"📍 Recuperado de BD: {saved_lat}, {saved_lng}")
            except Exception as e:
                logger.error(f"Error recuperando ubicación: {e}")

        loc = user_locations.get(chat_id, DEFAULT_LOCATION)
        
        current_mode = user_modes.get(chat_id, "normal")
        mode_instruction = "MODO: NORMAL ⚡. Sé breve."
        if current_mode == "profundo":
            mode_instruction = "MODO: PROFUNDO 🧘‍♀️. Analiza detalladamente."

        system_prompt = f"""{CLAUDETTE_CORE}
{USER_PROFILE}

=== CONTEXTO ===
📅 {now.strftime("%A %d-%m-%Y %H:%M")}
📍 {loc['name']} (GPS: {loc['lat']}, {loc['lng']})
{mode_instruction}
"""
        
        messages = conversation_history[chat_id]
        response = client.messages.create(
            model=DEFAULT_MODEL, max_tokens=4096, system=system_prompt, tools=TOOLS, messages=messages
        )
        
        final_text = ""

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            for block in response.content:
                if block.type == "tool_use":
                    logger.info(f"🔧 Tool: {block.name}")
                    try:
                        tool_result = await execute_tool_async(block.name, block.input, chat_id, context)
                    except Exception as e:
                        tool_result = f"Error: {str(e)}"
                    messages.append({
                        "role": "user", 
                        "content": [{"type": "tool_result", "tool_use_id": block.id, "content": str(tool_result)}]
                    })
            
            response2 = client.messages.create(
                model=DEFAULT_MODEL, max_tokens=2000, system=system_prompt, tools=TOOLS, messages=messages
            )
            for block in response2.content:
                if block.type == "text": final_text += block.text
        else:
            for block in response.content:
                if block.type == "text": final_text += block.text

        if not final_text: final_text = "✅ He procesado la solicitud."

        conversation_history[chat_id].append({"role": "assistant", "content": final_text})
        await update.effective_message.reply_text(final_text)

        if is_voice and elevenlabs_client:
            try:
                text_clean = re.sub(r'[^\w\s,.?¡!]', '', final_text)
                audio = elevenlabs_client.generate(text=text_clean, voice=ELEVENLABS_VOICE_ID, model="eleven_multilingual_v2")
                await update.effective_message.reply_voice(voice=b"".join(audio))
            except: pass

    except Exception as e:
        logger.error(f"Error Main: {e}")
        try: await update.effective_message.reply_text(f"⚠️ Error: {str(e)}")
        except: pass

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Soy Claudette V8. Corrección aplicada.")

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conversation_history[update.effective_chat.id] = []
    await update.message.reply_text("🧹 Memoria borrada.")

async def cmd_mode_deep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_modes[update.effective_chat.id] = "profundo"
    await update.message.reply_text("🧘‍♀️ Modo Profundo.")

async def cmd_mode_normal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_modes[update.effective_chat.id] = "normal"
    await update.message.reply_text("⚡ Modo Normal.")

async def cmd_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    loc = user_locations.get(chat_id, DEFAULT_LOCATION)
    await update.message.reply_text(f"📍 {loc['name']} ({loc['lat']}, {loc['lng']})")

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
        await update.message.reply_text(f"🎤 {transcript}")
        await process_message(update, context, transcript, is_voice=True)
    except Exception as e: await update.message.reply_text(f"Error voz: {e}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    with io.BytesIO() as f:
        await photo_file.download_to_memory(out=f)
        image_data = base64.b64encode(f.getvalue()).decode("utf-8")
    caption = update.message.caption or "Analiza esta imagen."
    await process_message(update, context, caption, image_data=image_data)

async def handle_location_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or not msg.location: return
    
    lat, lng = msg.location.latitude, msg.location.longitude
    chat_id = update.effective_chat.id
    
    user_locations[chat_id] = {"lat": lat, "lng": lng, "name": "Ubicación Telegram"}
    
    # FIX: Guardar correctamente usando 2 argumentos
    try:
        save_fact(f"System_Location_Lat_{chat_id}", str(lat))
        save_fact(f"System_Location_Lng_{chat_id}", str(lng))
        logger.info(f"💾 Guardado BD: {lat}, {lng}")
    except Exception as e:
        logger.error(f"Error BD Location: {e}")

    if not update.edited_message:
        await msg.reply_text("📍 Ubicación actualizada.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception:", exc_info=context.error)

def main():
    setup_database()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_history))
    app.add_handler(CommandHandler("profundo", cmd_mode_deep))
    app.add_handler(CommandHandler("normal", cmd_mode_normal))
    app.add_handler(CommandHandler("ubicacion", cmd_location))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location_update))
    app.add_error_handler(error_handler)
    print("✅ Claudette Online (V8 Fixed)")
    app.run_polling()

if __name__ == '__main__':
    main()
