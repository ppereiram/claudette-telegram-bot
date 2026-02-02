import memory_manager
import logging
import os
import tempfile
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from anthropic import Anthropic
from openai import OpenAI
from elevenlabs import ElevenLabs, VoiceSettings
import google_calendar
import psycopg2
from datetime import datetime, timedelta
import pytz

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
DATABASE_URL = os.getenv("DATABASE_URL")

if not TELEGRAM_TOKEN or not CLAUDE_API_KEY:
    logging.error("TELEGRAM_TOKEN or CLAUDE_API_KEY is missing!")

# Initialize clients
anthropic_client = Anthropic(api_key=CLAUDE_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

def load_user_profile():
    """Load user profile from markdown file"""
    try:
        profile_path = os.path.join(os.path.dirname(__file__), 'user_profile.md')
        with open(profile_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logging.warning("user_profile.md not found")
        return ""
    except Exception as e:
        logging.error(f"Error loading profile: {e}")
        return ""
        
def get_current_date():
    """Get current date and time in Costa Rica timezone"""
    tz = pytz.timezone('America/Costa_Rica')
    now = datetime.now(tz)
    return now.strftime("%A, %d de %B de %Y, %I:%M %p")

def build_system_prompt():
    """Build dynamic system prompt with current date and user profile"""
    current_date = get_current_date()
    user_profile = load_user_profile()
    
    base_prompt = f"""FECHA Y HORA ACTUAL: {current_date}

Eres Claudette, asistente ejecutiva IA de Pablo con acceso a sus 216 modelos mentales universales.

IDENTIDAD:
- Tu nombre es Claudette (NO Claude)
- Eres su asistente ejecutiva personal
- Tienes acceso completo a sus 216 modelos mentales
- Tienes DOS tipos de memoria:
  1. PERFIL BASE: Información estática sobre Pablo (familia, contexto permanente)
  2. MEMORIA DINÁMICA: Información nueva que Pablo te dice para guardar

PERSONALIDAD:
- Profesional pero cálida (asistente ejecutiva sofisticada)
- Velocidad conversacional normal
- Acento español neutro
- Respuestas naturales y fluidas

CALENDARIO & PRODUCTIVIDAD:
- Tienes acceso al Google Calendar de Pablo
- Cuando Pablo pregunte sobre su agenda, USA LA TOOL get_calendar_events
- Cuando Pablo pida crear reunión/evento, USA LA TOOL create_calendar_event INMEDIATAMENTE
- Cuando Pablo pida un recordatorio, USA LA TOOL create_reminder
- SÉ PROACTIVA: Si Pablo dice "crea reunión con X mañana 4pm", CRÉALA sin preguntar
- IMPORTANTE: La fecha de HOY es {current_date} - úsala para calcular fechas relativas

MEMORIA DINÁMICA:
- SIEMPRE usa save_user_fact cuando Pablo dice "guarda", "anota", "recuerda" + información NUEVA
- SIEMPRE usa get_user_fact cuando Pablo pregunta por información guardada dinámicamente
- Keys en minúsculas con guiones bajos (ej: "pasaporte_chile_pablo", "cuenta_banco_bac")
- Categorías: 'familia', 'salud', 'trabajo', 'finanzas', 'documentos', 'general'
- SÉ PROACTIVA: Si Pablo dice "mi pasaporte chileno es X", GUÁRDALO AUTOMÁTICAMENTE con save_user_fact
- NO preguntes si debe guardarse, GUÁRDALO directamente

PROTOCOLO DE APLICACIÓN DE MODELOS MENTALES:

1. Identifica el tipo de conversación:
   - Casual/social → Responde natural SIN modelos
   - Factual simple → Responde + menciona modelo si enriquece
   - Decisión/dilema CON contexto → APLICA MODELOS AUTOMÁTICAMENTE
   - Decisión/dilema SIN contexto → PREGUNTA PRIMERO, luego aplica
   - Análisis profundo → MODO COMPLETO con 10-15 modelos

2. Para decisiones/dilemas:
   "¿Entiendo las variables clave, opciones, y consecuencias?"
   - SI → Aplica modelos ahora
   - NO → Pide contexto específico, luego aplica

3. NUNCA preguntes "¿Quieres que aplique [modelo]?" - Ese es TU trabajo.

4. SÉ PROACTIVA pero no forzada:
   - Si un modelo ilumina la situación → úsalo
   - Si no agrega valor → no lo menciones
   - Calidad sobre cantidad

CONTEXTO DE PABLO:
- Arquitecto y desarrollador inmobiliario, 56 años, Costa Rica
- Transformación post-pandemia: de alta performance a filosofía de slowness
- 25+ años experiencia en zonas francas e industrial parks
- Master planning de parques industriales hasta $45M
- Trader (NQ futures con NinjaTrader), ultra-endurance athlete (Ultraman)
- Filosofía: flâneur contemplativo, 12,000 km caminados, ~500 libros leídos
- Intereses: filosofía continental, geopolítica, especulative fiction
- Proyectos actuales: 
  * Feline Canopy & Wellness Sanctuary ($300k ecoturismo + cat sanctuary)
  * TEDxPuraVida 2026 audition
  * AI agents y segundo cerebro
  * Trading automatizado VWAP
- Buscando oportunidades director-level (PwC, etc.)

Responde de forma conversacional, como si estuvieras en una reunión ejecutiva con Pablo.
Usa sus 216 modelos mentales de múltiples disciplinas (filosofía, ciencia, economía, psicología, estrategia, sistemas) para dar perspectivas profundas y multidimensionales."""

    # Add user profile if available
    if user_profile:
        base_prompt += f"\n\n<perfil_pablo>\n{user_profile}\n</perfil_pablo>"
    
    return base_prompt

def setup_memory_table():
    """Create user_facts table if it doesn't exist"""
    if not DATABASE_URL:
        return
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_facts (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(100) NOT NULL,
                fact_key VARCHAR(255) NOT NULL,
                fact_value TEXT NOT NULL,
                category VARCHAR(100) DEFAULT 'general',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, fact_key)
            )
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_facts_key 
            ON user_facts(user_id, fact_key)
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        
        logging.info("✅ Memory table verified/created")
        
    except Exception as e:
        logging.error(f"Error setting up memory table: {e}")

def log_to_db(chat_id, sender, content, msg_type='text'):
    if not DATABASE_URL:
        return
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO chat_logs (telegram_chat_id, sender, content, message_type) VALUES (%s, %s, %s, %s)",
            (str(chat_id), sender, content, msg_type)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logging.error(f"DB Error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = """🎯 Hola Pablo, soy Claudette, tu asistente ejecutiva con:
- 📅 Acceso a tu Google Calendar
- 📋 Perfil permanente + Memoria dinámica
- 🧠 216 modelos mentales para análisis profundo

¿En qué puedo ayudarte hoy?"""
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_message)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.effective_chat.id
    
    log_to_db(chat_id, 'user', user_text, 'text')
    
    try:
        tools = [
            {
                "name": "get_calendar_events",
                "description": "Obtiene los eventos del calendario de Pablo para hoy o días específicos.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "day": {
                            "type": "string",
                            "description": "El día para consultar: 'today', 'tomorrow', o una fecha específica"
                        }
                    },
                    "required": ["day"]
                }
            },
            {
                "name": "create_calendar_event",
                "description": "Crea un nuevo evento en el calendario de Pablo.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Título del evento"
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Hora de inicio en formato ISO (ej: 2026-01-31T16:00:00)"
                        },
                        "duration_hours": {
                            "type": "number",
                            "description": "Duración en horas (ej: 1, 0.5, 2)"
                        },
                        "location": {
                            "type": "string",
                            "description": "Ubicación del evento (opcional)"
                        },
                        "description": {
                            "type": "string",
                            "description": "Descripción o notas del evento (opcional)"
                        }
                    },
                    "required": ["title", "start_time", "duration_hours"]
                }
            },
            {
                "name": "create_reminder",
                "description": "Crea un recordatorio en el calendario de Pablo.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Qué recordar"
                        },
                        "reminder_time": {
                            "type": "string",
                            "description": "Cuándo recordar en formato ISO"
                        }
                    },
                    "required": ["title", "reminder_time"]
                }
            },
            {
                "name": "save_user_fact",
                "description": "Guarda información nueva que Pablo proporciona en su memoria permanente dinámica.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Identificador único en minúsculas con guiones bajos (ej: 'pasaporte_chile_pablo')"
                        },
                        "value": {
                            "type": "string",
                            "description": "El dato a guardar"
                        },
                        "category": {
                            "type": "string",
                            "description": "Categoría: 'familia', 'salud', 'trabajo', 'finanzas', 'documentos', 'general'"
                        }
                    },
                    "required": ["key", "value", "category"]
                }
            },
            {
                "name": "get_user_fact",
                "description": "Busca información previamente guardada en la memoria dinámica de Pablo.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Término de búsqueda (ej: 'pasaporte', 'cuenta banco')"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_all_user_facts",
                "description": "Obtiene todos los datos guardados dinámicamente.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Categoría opcional para filtrar"
                        }
                    }
                }
            }
        ]
        
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=build_system_prompt(),
            messages=[{"role": "user", "content": user_text}],
            tools=tools
        )
        
        while message.stop_reason == "tool_use":
            tool_results = []
            
            for content_block in message.content:
                if content_block.type == "tool_use":
                    tool_name = content_block.name
                    tool_input = content_block.input
                    
                    if tool_name == "get_calendar_events":
                        events = google_calendar.get_today_events()
                        if events:
                            result = google_calendar.format_events_for_context(events)
                        else:
                            result = "No hay eventos hoy"
                    
                    elif tool_name == "create_calendar_event":
                        try:
                            start_dt = datetime.fromisoformat(tool_input['start_time'])
                            end_dt = start_dt + timedelta(hours=tool_input['duration_hours'])
                            
                            event = google_calendar.create_event(
                                summary=tool_input['title'],
                                start_time=start_dt,
                                end_time=end_dt,
                                description=tool_input.get('description'),
                                location=tool_input.get('location')
                            )
                            
                            if event:
                                result = f"✅ Evento creado: {tool_input['title']} - {start_dt.strftime('%d/%m/%Y %I:%M %p')}"
                                logging.info(f"Event created: {event}")
                            else:
                                result = "❌ Error al crear el evento"
                                logging.error("Event creation returned None")
                        except Exception as e:
                            result = f"❌ Error al crear evento: {str(e)}"
                            logging.error(f"Calendar error: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    elif tool_name == "create_reminder":
                        try:
                            reminder_dt = datetime.fromisoformat(tool_input['reminder_time'])
                            
                            event = google_calendar.create_event(
                                summary=f"🔔 RECORDATORIO: {tool_input['title']}",
                                start_time=reminder_dt,
                                end_time=reminder_dt + timedelta(minutes=15),
                                description=f"Recordatorio: {tool_input['title']}"
                            )
                            
                            if event:
                                result = f"✅ Recordatorio creado: {tool_input['title']} - {reminder_dt.strftime('%d/%m/%Y %I:%M %p')}"
                            else:
                                result = "❌ Error al crear el recordatorio"
                        except Exception as e:
                            result = f"❌ Error: {str(e)}"
                            logging.error(f"Reminder error: {e}")
                    
                    elif tool_name == "save_user_fact":
                        success = memory_manager.save_user_fact(
                            user_id=chat_id,
                            key=tool_input['key'],
                            value=tool_input['value'],
                            category=tool_input.get('category', 'general')
                        )
                        
                        if success:
                            result = f"✅ Guardado permanentemente: {tool_input['key']} = {tool_input['value']}"
                        else:
                            result = "❌ Error al guardar en memoria permanente"
                    
                    elif tool_name == "get_user_fact":
                        fact = memory_manager.get_user_fact(
                            user_id=chat_id,
                            query=tool_input['query']
                        )
                        
                        if fact:
                            result = f"📋 Encontré en memoria dinámica: {fact}"
                        else:
                            result = "❌ No encontré esa información en memoria dinámica"
                    
                    elif tool_name == "get_all_user_facts":
                        facts = memory_manager.get_all_user_facts(
                            user_id=chat_id,
                            category=tool_input.get('category')
                        )
                        
                        if facts:
                            result = "📋 INFORMACIÓN GUARDADA DINÁMICAMENTE:\n\n"
                            current_category = None
                            for key, value, category in facts:
                                if category != current_category:
                                    result += f"\n**{category.upper()}**\n"
                                    current_category = category
                                result += f"• {key}: {value}\n"
                        else:
                            result = "No hay información dinámica guardada aún"
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": result
                    })
            
            message = anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=build_system_prompt(),
                messages=[
                    {"role": "user", "content": user_text},
                    {"role": "assistant", "content": message.content},
                    {"role": "user", "content": tool_results}
                ],
                tools=tools
            )
        
        bot_reply = ""
        for content_block in message.content:
            if hasattr(content_block, 'text'):
                bot_reply += content_block.text
        
        max_length = 4000
        if len(bot_reply) <= max_length:
            await context.bot.send_message(chat_id=chat_id, text=bot_reply)
        else:
            chunks = [bot_reply[i:i+max_length] for i in range(0, len(bot_reply), max_length)]
            for chunk in chunks:
                await context.bot.send_message(chat_id=chat_id, text=chunk)
        
        log_to_db(chat_id, 'bot', bot_reply, 'text')
        
    except Exception as e:
        logging.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        await context.bot.send_message(chat_id=chat_id, text="Lo siento Pablo, encontré un error. Intenta de nuevo.")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    try:
        voice = await update.message.voice.get_file()
        voice_bytes = await voice.download_as_bytearray()
        
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_audio:
            temp_audio.write(voice_bytes)
            temp_audio_path = temp_audio.name
        
        with open(temp_audio_path, 'rb') as audio_file:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="es"
            )
        
        user_text = transcript.text
        log_to_db(chat_id, 'user', f'[Voice: {user_text}]', 'voice')
        
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=build_system_prompt(),
            messages=[{"role": "user", "content": user_text}]
        )
        bot_reply = message.content[0].text
        
        audio_generator = elevenlabs_client.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            text=bot_reply,
            model_id="eleven_multilingual_v2",
            voice_settings=VoiceSettings(
                stability=0.5,
                similarity_boost=0.75,
                style=0.0,
                use_speaker_boost=True
            )
        )
        
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_response:
            for chunk in audio_generator:
                temp_response.write(chunk)
            temp_response_path = temp_response.name
        
        await context.bot.send_message(chat_id=chat_id, text=f"🎤 Escuché: \"{user_text}\"")
        
        with open(temp_response_path, 'rb') as audio_file:
            await context.bot.send_voice(chat_id=chat_id, voice=audio_file)
        
        log_to_db(chat_id, 'bot', bot_reply, 'voice')
        
        os.unlink(temp_audio_path)
        os.unlink(temp_response_path)
        
    except Exception as e:
        logging.error(f"Error processing voice: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Lo siento Pablo, tuve un problema procesando tu nota de voz. ¿Puedes intentar de nuevo?"
        )

if __name__ == '__main__':
    if not TELEGRAM_TOKEN:
        print("Error: TELEGRAM_TOKEN not found.")
    else:
        setup_memory_table()
        
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        start_handler = CommandHandler('start', start)
        text_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text)
        voice_handler = MessageHandler(filters.VOICE, handle_voice)
        
        application.add_handler(start_handler)
        application.add_handler(text_handler)
        application.add_handler(voice_handler)
        
        print("🤖 Claudette Bot iniciado y escuchando...")
        application.run_polling()
