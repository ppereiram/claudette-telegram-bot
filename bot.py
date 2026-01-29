import logging
import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from anthropic import Anthropic
import psycopg2
from datetime import datetime

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if not TELEGRAM_TOKEN or not CLAUDE_API_KEY:
    logging.error("TELEGRAM_TOKEN or CLAUDE_API_KEY is missing!")
    # We won't exit, just log error, but bot won't work well.

# Initialize Anthropic client
anthropic_client = Anthropic(api_key=CLAUDE_API_KEY)

# System prompt para Claudette
SYSTEM_PROMPT = """Eres Claudette, asistente ejecutiva IA de Pablo con acceso a sus 216 modelos mentales universales.

IDENTIDAD:
- Tu nombre es Claudette (NO Claude)
- Eres su asistente ejecutiva personal
- Tienes acceso completo a sus 216 modelos mentales

PERSONALIDAD:
- Profesional pero cálida (asistente ejecutiva sofisticada)
- Velocidad conversacional normal
- Acento español neutro
- Respuestas naturales y fluidas

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
    welcome_message = """🎯 Hola Pablo, soy Claudette, tu asistente ejecutiva con acceso a tus 216 modelos mentales.

Puedo ayudarte con:
- Análisis de decisiones estratégicas
- Evaluación de oportunidades de negocio
- Aplicación de frameworks filosóficos y de pensamiento sistémico
- Cualquier consulta donde necesites perspectivas multidimensionales

¿En qué puedo ayudarte hoy?"""
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_message)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.effective_chat.id
    
    # Log user message
    log_to_db(chat_id, 'user', user_text, 'text')
    
    try:
        # Call Claude API (Sonnet 4) con system prompt de Claudette
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_text}
            ]
        )
        bot_reply = message.content[0].text
        
        # Send reply
        await context.bot.send_message(chat_id=chat_id, text=bot_reply)
        
        # Log bot reply
        log_to_db(chat_id, 'bot', bot_reply, 'text')
        
    except Exception as e:
        logging.error(f"Error calling Claude or sending message: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Lo siento Pablo, encontré un error al procesar tu solicitud. Por favor intenta de nuevo.")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    # Log voice receipt
    log_to_db(chat_id, 'user', '[Voice Note Received]', 'voice')
    
    await context.bot.send_message(
        chat_id=chat_id, 
        text="📝 Recibí tu nota de voz, Pablo. Por ahora procesar audio requiere configurar OpenAI Whisper API. ¿Prefieres que configuremos eso o seguimos con mensajes de texto?"
    )
    
    # Log bot reply
    log_to_db(chat_id, 'bot', 'Voice note acknowledgment', 'text')

if __name__ == '__main__':
    if not TELEGRAM_TOKEN:
        print("Error: TELEGRAM_TOKEN not found.")
    else:
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        start_handler = CommandHandler('start', start)
        text_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text)
        voice_handler = MessageHandler(filters.VOICE, handle_voice)
        
        application.add_handler(start_handler)
        application.add_handler(text_handler)
        application.add_handler(voice_handler)
        
        print("🤖 Claudette Bot iniciado y escuchando...")
        application.run_polling()
