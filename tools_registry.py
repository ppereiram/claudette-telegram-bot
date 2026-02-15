"""
Tools Registry para Claudette Bot.
Define TODOS los schemas de herramientas y su ejecución.
Portado completo desde bot.py monolítico.
"""

import os
import tempfile
import logging
import requests
from config import OPENAI_API_KEY, OPENWEATHER_API_KEY, DEFAULT_LOCATION, logger
from memory_manager import save_fact, get_fact

# --- Imports de servicios Google ---
import google_calendar
import gmail_service
import google_tasks
import google_drive
import google_contacts
import google_places

# --- Clients opcionales ---
from openai import OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# --- Imports para libros ---
try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
except ImportError:
    ebooklib = None

# --- Búsqueda web ---
try:
    from googlesearch import search as google_search_func
except ImportError:
    google_search_func = None


# =====================================================
# FUNCIONES DE APOYO
# =====================================================

def clean_date_iso(date_str, is_end=False):
    """Asegura formato ISO con timezone."""
    if 'T' not in date_str:
        time_part = "T23:59:59" if is_end else "T00:00:00"
        return f"{date_str}{time_part}-06:00"
    return date_str


def get_weather(lat, lon):
    """Obtener clima de OpenWeather."""
    if not OPENWEATHER_API_KEY:
        return "⚠️ No tengo configurada la API Key de OpenWeather."
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=es"
        res = requests.get(url, timeout=10).json()
        if res.get('cod') != 200:
            return f"Error clima: {res.get('message')}"
        desc = res['weather'][0]['description']
        temp = res['main']['temp']
        hum = res['main']['humidity']
        city = res['name']
        return f"🌦️ El clima en {city}: {desc.capitalize()}, {temp}°C, Humedad {hum}%."
    except Exception as e:
        return f"Error obteniendo clima: {e}"


def search_web_google(query, max_results=5):
    """Busca en web con fallback DuckDuckGo."""
    if google_search_func:
        try:
            results = []
            for result in google_search_func(query, num_results=max_results, advanced=True, lang="es"):
                results.append(f"📰 {result.title}\n🔗 {result.url}\n📝 {result.description}\n")
            if results:
                return "\n".join(results)
        except Exception as e:
            logger.warning(f"Google Search falló: {e}, usando DuckDuckGo...")

    try:
        from duckduckgo_search import DDGS
        ddgs = DDGS()
        results = []
        for r in ddgs.text(query, max_results=max_results, region="es-es"):
            results.append(f"📰 {r['title']}\n🔗 {r['href']}\n📝 {r['body']}\n")
        if results:
            return "\n".join(results)
    except Exception as e:
        logger.error(f"DuckDuckGo también falló: {e}")

    return "No se encontraron resultados."


def search_news(topics=None):
    """Busca noticias recientes usando DuckDuckGo."""
    from config import NEWS_TOPICS
    if not topics:
        topics = NEWS_TOPICS
    all_news = []
    try:
        from duckduckgo_search import DDGS
        ddgs = DDGS()
        for topic in topics:
            clean_topic = topic.replace(" noticias", "").strip().upper()
            try:
                results = ddgs.news(topic, max_results=3, region="es-es")
                lines = [f"• {r['title']}\n  🔗 {r['url']}" for r in results]
                if lines:
                    all_news.append(f"📌 {clean_topic}:\n" + "\n".join(lines))
                else:
                    all_news.append(f"📌 {clean_topic}: Sin resultados.")
            except Exception as e:
                all_news.append(f"📌 {clean_topic}: Error: {e}")
    except ImportError:
        return "⚠️ Falta instalar duckduckgo-search."
    return "\n\n".join(all_news)


def extract_text_from_pdf(file_path):
    """Extrae texto de PDF."""
    if not pypdf:
        return "Error: pypdf no está instalado."
    text = ""
    try:
        reader = pypdf.PdfReader(file_path)
        max_pages = min(len(reader.pages), 50)
        for i in range(max_pages):
            text += reader.pages[i].extract_text() + "\n"
    except Exception as e:
        logger.error(f"PDF Error: {e}")
    return text


def extract_text_from_epub(file_path):
    """Extrae texto de EPUB."""
    if not ebooklib:
        return "Error: ebooklib no está instalado."
    text = ""
    try:
        book = epub.read_epub(file_path, options={'ignore_ncx': True})
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            chapter_text = soup.get_text(separator='\n', strip=True)
            if chapter_text.strip():
                text += chapter_text + "\n\n"
    except Exception as e:
        logger.error(f"EPUB Error: {e}")
        text = f"Error leyendo EPUB: {e}"
    return text


def read_book_from_drive(query):
    """Busca y lee libros desde Drive — soporta PDF, EPUB y TXT."""
    service = google_drive.get_drive_service()
    if not service:
        return "Error conectando a Drive."
    try:
        results = service.files().list(
            q=f"name contains '{query}' and mimeType != 'application/vnd.google-apps.folder'",
            pageSize=1
        ).execute()
        items = results.get('files', [])
        if not items:
            return "No hallé el archivo."

        file_id, file_name = items[0]['id'], items[0]['name']
        request = service.files().get_media(fileId=file_id)
        file_content = request.execute()

        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file_name}") as temp_file:
            temp_file.write(file_content)
            temp_path = temp_file.name

        content = ""
        lower_name = file_name.lower()
        if lower_name.endswith('.pdf'):
            content = extract_text_from_pdf(temp_path)
        elif lower_name.endswith('.epub'):
            content = extract_text_from_epub(temp_path)
        elif lower_name.endswith('.txt'):
            with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        else:
            content = f"Formato '{file_name.split('.')[-1]}' no soportado. Formatos válidos: PDF, EPUB, TXT."

        os.unlink(temp_path)

        if not content.strip():
            return f"📖 Encontré '{file_name}' pero no pude extraer texto."
        if len(content) > 8000:
            return f"📖 {file_name} (Primeras páginas):\n{content[:8000]}\n\n[... Truncado. Pídeme una sección específica.]"
        return f"📖 {file_name}:\n{content}"

    except Exception as e:
        return f"Error leyendo libro: {e}"


# =====================================================
# SCHEMAS DE HERRAMIENTAS (para Anthropic API)
# =====================================================

TOOLS_SCHEMA = [
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
        "description": "Buscar y leer libros o documentos desde Google Drive. Soporta PDF, EPUB y TXT.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Nombre o parte del nombre del libro/archivo"}},
            "required": ["query"]
        }
    },
    {
        "name": "save_user_fact",
        "description": "Guardar dato importante en memoria persistente. USA SIEMPRE esta herramienta cuando el usuario mencione: datos personales, ubicaciones, preferencias, datos de trabajo, nombres de mascotas, fechas importantes, o cuando diga 'recuerda', 'memoriza', 'anota'. Guarda proactivamente.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Categoría: Familia, Ubicacion, Preferencia, Trabajo, Personal, Fecha, etc."},
                "key": {"type": "string", "description": "Qué es (ej: 'mamá vive en', 'color favorito')"},
                "value": {"type": "string", "description": "El valor a recordar"}
            },
            "required": ["category", "key", "value"]
        }
    },
    {
        "name": "search_web",
        "description": "Buscar en Google Web.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"]
        }
    },
    {
        "name": "search_news",
        "description": "Buscar noticias recientes. Sin temas busca AI, geopolítica y mercados. Con topics personaliza.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de temas (opcional, ej: ['bitcoin', 'Venezuela'])"
                }
            }
        }
    },
    {
        "name": "get_calendar_events",
        "description": "Consultar calendario de Google.",
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
        "description": "Agendar evento en Google Calendar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "start_time": {"type": "string"},
                "end_time": {"type": "string"}
            },
            "required": ["summary", "start_time", "end_time"]
        }
    },
    {
        "name": "create_task",
        "description": "Crear tarea en Google Tasks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "notes": {"type": "string"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "list_tasks",
        "description": "Listar tareas de Google Tasks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "show_completed": {"type": "boolean"}
            }
        }
    },
    {
        "name": "search_emails",
        "description": "Buscar correos en Gmail. Usa sintaxis Gmail: from:, to:, subject:, is:unread, has:attachment, newer_than:2d, etc.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"]
        }
    },
    {
        "name": "get_email",
        "description": "Leer el contenido completo de un email específico por su ID (obtenido de search_emails).",
        "input_schema": {
            "type": "object",
            "properties": {"email_id": {"type": "string", "description": "ID del email"}},
            "required": ["email_id"]
        }
    },
    {
        "name": "send_email",
        "description": "Enviar un email desde Gmail. Puede enviar correos nuevos o responder a existentes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Email del destinatario"},
                "subject": {"type": "string", "description": "Asunto del correo"},
                "body": {"type": "string", "description": "Cuerpo del correo en texto plano"},
                "reply_to_id": {"type": "string", "description": "ID del email al que responder (opcional)"}
            },
            "required": ["to", "subject", "body"]
        }
    },
    {
        "name": "generate_image",
        "description": "Generar una imagen usando AI (DALL-E 3) basada en una descripción.",
        "input_schema": {
            "type": "object",
            "properties": {"prompt": {"type": "string", "description": "Descripción visual detallada"}},
            "required": ["prompt"]
        }
    }
]


# =====================================================
# EJECUCIÓN DE HERRAMIENTAS
# =====================================================

# Estado global compartido con main.py
user_locations = {}


async def execute_tool(tool_name: str, tool_input: dict, chat_id: int, context):
    """Ejecuta una herramienta y retorna el resultado como string."""

    try:
        if tool_name == "get_current_weather":
            return get_weather(tool_input['lat'], tool_input['lon'])

        elif tool_name == "search_contact_and_call":
            query = tool_input['name_query']
            results = google_contacts.search_contact(query)
            if not results:
                return f"❌ No encontré a '{query}'."
            contact = results[0]
            await context.bot.send_contact(
                chat_id=chat_id,
                phone_number=contact['phone'],
                first_name=contact['name']
            )
            return f"✅ Contacto: {contact['name']}."

        elif tool_name == "search_nearby_places":
            loc = user_locations.get(chat_id, DEFAULT_LOCATION)
            lat, lng = loc['lat'], loc['lng']
            loc_name = loc.get('name', 'San José, Costa Rica')
            query = tool_input['query']

            try:
                places_result = google_places.search_nearby_places(query, lat, lng)
                if not places_result or "⚠️" in str(places_result):
                    raise Exception(str(places_result))
                return places_result
            except Exception as e:
                logger.warning(f"Places API falló: {e}. Fallback a web search.")
                fallback_query = f"{query} near {loc_name}"
                web_result = search_web_google(fallback_query)
                if web_result and "no devolvió resultados" not in web_result:
                    return f"🔍 (Búsqueda web, Places API no disponible):\n{web_result}"
                return f"🔍 (Búsqueda general):\n{search_web_google(f'{query} Costa Rica')}"

        elif tool_name == "read_book_from_drive":
            return read_book_from_drive(tool_input['query'])

        elif tool_name == "save_user_fact":
            full_key = f"{tool_input.get('category', 'General')}: {tool_input.get('key', 'Dato')}"
            save_fact(full_key, tool_input['value'])
            return f"✅ Guardado: {full_key}"

        elif tool_name == "search_web":
            return search_web_google(tool_input['query'])

        elif tool_name == "search_news":
            topics = tool_input.get('topics')
            return search_news(topics)

        elif tool_name == "get_calendar_events":
            return google_calendar.get_calendar_events(
                clean_date_iso(tool_input['start_date']),
                clean_date_iso(tool_input['end_date'], True)
            )

        elif tool_name == "create_calendar_event":
            return google_calendar.create_calendar_event(
                tool_input['summary'],
                clean_date_iso(tool_input['start_time']),
                clean_date_iso(tool_input['end_time'])
            )

        elif tool_name == "create_task":
            return google_tasks.create_task(
                tool_input['title'],
                tool_input.get('notes')
            )

        elif tool_name == "list_tasks":
            return google_tasks.list_tasks(tool_input.get('show_completed', False))

        elif tool_name == "search_emails":
            return gmail_service.search_emails(tool_input['query'])

        elif tool_name == "get_email":
            return gmail_service.get_email(tool_input['email_id'])

        elif tool_name == "send_email":
            return gmail_service.send_email(
                to=tool_input['to'],
                subject=tool_input['subject'],
                body=tool_input['body'],
                reply_to_id=tool_input.get('reply_to_id')
            )

        elif tool_name == "generate_image":
            if not openai_client:
                return "OpenAI no configurado."
            msg = await context.bot.send_message(chat_id, "🎨 Pintando tu idea...")
            response = openai_client.images.generate(
                model="dall-e-3",
                prompt=tool_input['prompt'],
                size="1024x1024",
                quality="standard",
                n=1
            )
            await context.bot.send_photo(
                chat_id,
                photo=response.data[0].url,
                caption=f"🎨 {tool_input['prompt']}"
            )
            await context.bot.delete_message(chat_id, msg.message_id)
            return "✅ Imagen generada y enviada."

        return f"Herramienta '{tool_name}' no encontrada."

    except Exception as e:
        logger.error(f"Tool Error {tool_name}: {e}")
        return f"Error en herramienta {tool_name}: {e}"
