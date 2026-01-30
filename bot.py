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
from datetime import datetime

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

PERSONALIDAD:
- Profesional pero cálida (asistente ejecutiva sofisticada)
- Velocidad conversacional normal
- Acento español neutro
- Respuestas naturales y fluidas

CALENDARIO & PRODUCTIVIDAD:
- Tienes acceso al Google Calendar de Pablo
- Cuando Pablo pregunte sobre su agenda, eventos, reuniones o citas, consulta el calendario automáticamente
- Puedes ver eventos de hoy, mañana, esta semana
- Frases clave: "agenda", "calendario", "qué tengo hoy", "reuniones", "eventos", "citas"
- Responde de forma natural integrando la información del calendario

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
    welcome_message = """🎯 Hola Pablo, soy Claudette, tu asistente ejecutiva con acceso a tus 216 modelos mentales y tu Google Calendar.

Puedo ayudarte con:
- Ver tu agenda y eventos
- Análisis de decisiones estratégicas
- Evaluación de oportunidades de negocio
- Aplicación de frameworks filosóficos y de pensamiento sistémico
- Cualquier consulta donde necesites perspectivas multidimensionales

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
                "description": "Obtiene los eventos del calendario de Pablo para hoy o días específicos. Úsala cuando Pablo pregunte sobre su agenda, reuniones o eventos.",
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
                "description": "Crea un nuevo evento en el calendario de Pablo. Úsala cuando Pablo pida crear una reunión, cita o evento.",
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
                "description": "Crea un recordatorio en el calendario de Pablo. Úsala cuando Pablo pida que le recuerdes algo.",
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
            }
        ]
        
        # First message to Claude
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_text}],
            tools=tools
        )
        
        # Check if Claude wants to use tools
        while message.stop_reason == "tool_use":
            tool_results = []
            
            for content_block in message.content:
                if content_block.type == "tool_use":
                    tool_name = content_block.name
                    tool_input = content_block.input
                    
                    # Execute the tool
                    if tool_name == "get_calendar_events":
                        events = google_calendar.get_today_events()
                        if events:
                            result = google_calendar.format_events_for_context(events)
                        else:
                            result = "No hay eventos hoy"
                    
                    elif tool_name == "create_calendar_event":
                        from datetime import datetime, timedelta
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
                        else:
                            result = "❌ Error al crear el evento"
                    
                    elif tool_name == "create_reminder":
                        from datetime import datetime, timedelta
                        reminder_dt = datetime.fromisoformat(tool_input['reminder_time'])
                        
                        # Create 15-minute reminder event
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
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": result
                    })
            
            # Continue conversation with tool results
            message = anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_text},
                    {"role": "assistant", "content": message.content},
                    {"role": "user", "content": tool_results}
                ],
                tools=tools
            )
        
        # Extract final text response
        bot_reply = ""
        for content_block in message.content:
            if hasattr(content_block, 'text'):
                bot_reply += content_block.text
        
        # Send response
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
```

---

## ✅ ACTUALIZA bot.py

1. GitHub → bot.py → Edit
2. **Reemplaza SOLO la función `handle_text`** (línea ~130) con el código de arriba
3. Commit changes

---

## 🎯 QUÉ CAMBIA:

**ANTES:**
```
Tú: "Crea reunión con Liliana mañana 4pm"
Claudette: "Claro, necesito más detalles..."
[No hace nada]
```

**AHORA:**
```
Tú: "Crea reunión con Liliana mañana 4pm"
Claudette: [USA TOOL] → Crea el evento
"✅ Evento creado: Reunión con Liliana - 31/01/2026 4:00 PM"
```

**Y RECORDATORIOS:**
```
Tú: "Recuérdame 4 horas antes"
Claudette: [USA TOOL] → Crea recordatorio
"✅ Recordatorio creado: Reunión con Liliana - 31/01/2026 12:00 PM"
```

---

## 📋 PRÓXIMO PASO (MEMORIA):

Después de esto, agregamos **memoria persistente** para que recuerde contexto entre conversaciones.

---

**Actualiza bot.py con esa función y commit.** 

Después del deploy (~3 min) prueba:
```
"Claudette, crea reunión Feline Canopy mañana 3pm, 1 hora"
    chat_id = update.effective_chat.id
    
    try:
        # Get voice file
        voice = await update.message.voice.get_file()
        voice_bytes = await voice.download_as_bytearray()
        
        # Save temporarily as OGG file
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_audio:
            temp_audio.write(voice_bytes)
            temp_audio_path = temp_audio.name
        
        # Transcribe with Whisper
        with open(temp_audio_path, 'rb') as audio_file:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="es"
            )
        
        user_text = transcript.text
        log_to_db(chat_id, 'user', f'[Voice: {user_text}]', 'voice')
        
        # Send to Claude
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_text}]
        )
        bot_reply = message.content[0].text
        
        # Generate voice response with ElevenLabs
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
        
        # Save audio response
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_response:
            for chunk in audio_generator:
                temp_response.write(chunk)
            temp_response_path = temp_response.name
        
        # Send transcription text first
        await context.bot.send_message(chat_id=chat_id, text=f"🎤 Escuché: \"{user_text}\"")
        
        # Send voice response
        with open(temp_response_path, 'rb') as audio_file:
            await context.bot.send_voice(chat_id=chat_id, voice=audio_file)
        
        # Log bot reply
        log_to_db(chat_id, 'bot', bot_reply, 'voice')
        
        # Clean up temp files
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
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        start_handler = CommandHandler('start', start)
        text_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text)
        voice_handler = MessageHandler(filters.VOICE, handle_voice)
        
        application.add_handler(start_handler)
        application.add_handler(text_handler)
        application.add_handler(voice_handler)
        
        print("🤖 Claudette Bot iniciado y escuchando...")
        application.run_polling()
