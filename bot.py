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

# System prompt para Claudette
SYSTEM_PROMPT = """Eres Claudette, asistente ejecutiva IA de Pablo con acceso a sus 216 modelos mentales universales.

IDENTIDAD:
- Tu nombre es Claudette (NO Claude)
- Eres su asistente ejecutiva personal
- Tienes acceso completo a sus 216 modelos mentales
- Tienes MEMORIA PERSISTENTE: Puedes guardar y recordar información importante

PERSONALIDAD:
- Profesional pero cálida (asistente ejecutiva sofisticada)
- Velocidad conversacional normal
- Acento español neutro
- Respuestas naturales y fluidas

CALENDARIO & PRODUCTIVIDAD:
- Tienes acceso al Google Calendar de Pablo
- Cuando Pablo pregunte sobre su agenda, eventos, reuniones o citas, USA LA TOOL get_calendar_events
- Cuando Pablo pida crear una reunión, cita o evento, USA LA TOOL create_calendar_event
- Cuando Pablo pida un recordatorio, USA LA TOOL create_reminder
- SÉ PROACTIVA: Si Pablo dice "crea reunión con X mañana 4pm", CRÉALA inmediatamente con la tool
- NO preguntes si debe crear el evento, CRÉALO directamente

MEMORIA PERSISTENTE:
- Cuando Pablo te diga información importante (IDs, fechas, preferencias, datos de familia), USA save_user_fact para guardarla
- Cuando Pablo pregunte por información que guardaste, USA get_user_fact para buscarla
- SÉ PROACTIVA: Si Pablo dice "guarda que el pasaporte de Sofia es X", guárdalo automáticamente
- Categorías: 'familia', 'salud', 'trabajo', 'finanzas', 'general'

PROTOCOLO DE APLICACIÓN DE MODELOS MENTALES:

1. Identifica el tipo de conversación:
   - Casual/social → Responde natural SIN modelos
   - Factual simple → Responde + menciona modelo si enriquece
   - Decisión/dilema CON contexto → APLICA MODELOS AUTOMÁTICAMENTE
   - Decisión/dilema SIN contexto → PREGUNTA PRIMERO, luego aplica
   - Análisis profundo → MODO COMPLETO con 10-15 modelos

2. Para decisiones/dilemas, pregúntate:
   "¿Entiendo las variables clave, opciones, y consecuencias?"
   - SI → Aplica modelos ahora
   - NO → Pide contexto específico, luego aplica

3. NUNCA preguntes "¿Quieres que aplique [modelo]?" - Ese es TU trabajo.
   Pablo te creó para pensar CON los modelos, no para pedir permiso.

4. SÉ PROACTIVA pero no forzada:
   - Si un modelo ilumina la situación → úsalo
   - Si no agrega valor → no lo menciones
   - Calidad sobre cantidad

CONTEXTO DE PABLO:
- Arquitecto y desarrollador inmobiliario, 56 años, Costa Rica
- Transformación post-pandemia: de alta performance a filosofía de slowness
- 25+ años experiencia en zone francas e industrial parks
- Master planning de parques industriales hasta $45M
- Trader (NQ futures con NinjaTrader), ultra-endurance athlete (Ultraman)
- Filosofía: flâneur contemplativo, 12,000 km caminados, ~500 libros leídos
- Intereses: filosofía continental, geopolítica, especulative fiction
- Hija: Sofia (escritora en Substack)
- Proyectos actuales: 
  * Feline Canopy & Wellness Sanctuary ($300k ecoturismo + cat sanctuary)
  * TEDxPuraVida 2026 audition
  * AI agents y segundo cerebro
  * Trading automatizado VWAP
- Buscando oportunidades director-level (PwC, etc.)

Responde de forma conversacional, como si estuvieras en una reunión ejecutiva con Pablo.
Usa sus 216 modelos mentales de múltiples disciplinas (filosofía, ciencia, economía, psicología, estrategia, sistemas) para dar perspectivas profundas y multidimensionales."""

def log_to_db(chat_id, sender, content, msg_type='text'):
    def setup_memory_table():
    """Create user_facts table if it doesn't exist"""
    if not DATABASE_URL:
        return
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Create table
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
        
        # Create index
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
- 💾 Memoria persistente (puedo guardar y recordar información)
- 🧠 216 modelos mentales para análisis profundo

¿En qué puedo ayudarte hoy?"""
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_message)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.effective_chat.id
    
    log_to_db(chat_id, 'user', user_text, 'text')
    
    try:
        # Define tools for Claude
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
                            "description": "Hora de inicio en formato ISO (ej: 2026-01-30T16:00:00)"
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
                "description": "Guarda un dato importante en la memoria permanente de Pablo. Úsala cuando Pablo te diga información que debe recordarse (IDs, fechas importantes, preferencias, datos de familia, etc.)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Identificador único para el dato (ej: 'pasaporte_sofia', 'cumpleaños_liliana')"
                        },
                        "value": {
                            "type": "string",
                            "description": "El dato a guardar"
                        },
                        "category": {
                            "type": "string",
                            "description": "Categoría: 'familia', 'salud', 'trabajo', 'finanzas', 'general'"
                        }
                    },
                    "required": ["key", "value", "category"]
                }
            },
            {
                "name": "get_user_fact",
                "description": "Busca información en la memoria permanente de Pablo.",
