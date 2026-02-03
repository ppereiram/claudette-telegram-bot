import os
import logging
import traceback
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from anthropic import Anthropic
import json
import base64
import requests
from io import BytesIO

# Import custom modules
from google_calendar import (
    get_calendar_events,
    create_calendar_event
)
from memory_manager import (
    setup_database,
    save_fact,
    get_fact,
    get_all_facts
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize clients
anthropic_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Model selection
CLAUDE_MODEL = "claude-sonnet-4-20250514"

def get_user_profile():
    """Load user profile from file"""
    try:
        profile_path = os.path.join(os.path.dirname(__file__), 'user_profile.md')
        with open(profile_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error loading user profile: {e}")
        return ""

def get_current_date():
    """Get current date and time in Costa Rica timezone"""
    tz = pytz.timezone('America/Costa_Rica')
    now = datetime.now(tz)
    return now.strftime("%A, %B %d, %Y at %I:%M %p %Z")

def build_system_prompt():
    """Build the system prompt with user profile and current date"""
    user_profile = get_user_profile()
    current_date = get_current_date()
    
    system_prompt = f"""Eres Claudette, la asistente personal de Pablo Pereira.

FECHA Y HORA ACTUAL: {current_date}

PERFIL DEL USUARIO:
{user_profile}

SISTEMA DE DOS CAPAS - MUY IMPORTANTE:

CAPA 1 (DEFAULT - Asistente de Vida):
- Respuestas ULTRA CONCISAS: máximo 2-3 oraciones
- Directo al grano, sin explicaciones innecesarias
- Tono profesional pero amigable
- Para: consultas simples, tareas de calendario, recordatorios, datos
- NO uses los 216 modelos mentales en Capa 1

Ejemplos Capa 1:
- Usuario: "¿Tengo algo mañana?"
  Claudette: "Tienes 2 reuniones: 9am con el equipo y 3pm call con inversores."
  
- Usuario: "Recuérdame comprar leche"
  Claudette: "Listo. Te recordaré comprar leche."

- Usuario: "¿Cuándo es mi cita con el dentista?"
  Claudette: "El jueves 10 a las 4pm en Belén."

MALO Capa 1: "Hola Pablo, con mucho gusto puedo ayudarte a revisar tu calendario. Déjame verificar..."

CAPA 2 (Activación bajo demanda - Segundo Cerebro):
- Respuestas EXTENDIDAS con análisis profundo
- USA los 216 modelos mentales para perspectivas múltiples
- Análisis sistémico, estratégico, filosófico
- Para: decisiones complejas, dilemas, estrategia, filosofía

Activadores explícitos de Capa 2:
- "analiza", "profundiza", "usa tus modelos", "segundo cerebro"
- "qué opinas sobre", "ayúdame a pensar", "considera"

Activadores implícitos:
- Preguntas que requieren análisis profundo
- Decisiones con múltiples factores
- Dilemas éticos o estratégicos
- Palabras clave: "por qué", "evalúa", "considera", "qué implicaciones"

HERRAMIENTAS DISPONIBLES:
- get_calendar_events: Para consultar eventos del calendario
- create_calendar_event: Para crear eventos en el calendario
- create_reminder: Para recordatorios
- save_user_fact: Guardar información que Pablo te diga
- get_user_fact: Recuperar información específica
- get_all_user_facts: Ver todos los datos guardados

REGLAS DE ORO:
1. DEFAULT = Capa 1 (conciso)
2. Solo cambia a Capa 2 cuando sea solicitado explícita o implícitamente
3. Nunca mezcles estilos
4. Si dudas, pregunta: "¿Quieres análisis rápido o profundo?"
"""
    
    return system_prompt

# Tool definitions
tools = [
    {
        "name": "get_calendar_events",
        "description": "Obtiene eventos del calendario de Google entre dos fechas. Usa formato ISO 8601 con timezone (ej: 2024-01-20T09:00:00-06:00 para Costa Rica)",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Fecha/hora de inicio en formato ISO 8601 con timezone"
                },
                "end_date": {
                    "type": "string",
                    "description": "Fecha/hora de fin en formato ISO 8601 con timezone"
                }
            },
            "required": ["start_date", "end_date"]
        }
    },
    {
        "name": "create_calendar_event",
        "description": "Crea un evento en el calendario de Google. Usa formato ISO 8601 con timezone America/Costa_Rica",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Título del evento"
                },
                "start_time": {
                    "type": "string",
                    "description": "Fecha/hora de inicio en formato ISO 8601 (ej: 2024-01-20T14:00:00-06:00)"
                },
                "end_time": {
                    "type": "string",
                    "description": "Fecha/hora de fin en formato ISO 8601"
                },
                "location": {
                    "type": "string",
                    "description": "Ubicación del evento (opcional)"
                }
            },
            "required": ["summary", "start_time", "end_time"]
        }
    },
    {
        "name": "create_reminder",
        "description": "Crea un recordatorio simple",
        "input_schema": {
            "type": "object",
            "properties": {
                "reminder_text": {
                    "type": "string",
                    "description": "Texto del recordatorio"
                },
                "reminder_time": {
                    "type": "string",
                    "description": "Cuándo recordar (opcional, puede ser texto natural)"
                }
            },
            "required": ["reminder_text"]
        }
    },
    {
        "name": "save_user_fact",
        "description": "Guarda un dato importante que Pablo te diga (preferencias, información personal, etc)",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Categoría o nombre del dato (ej: 'comida_favorita', 'proyecto_actual')"
                },
                "value": {
                    "type": "string",
                    "description": "El dato a guardar"
                }
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "get_user_fact",
        "description": "Recupera un dato específico previamente guardado",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Nombre del dato a buscar"
                }
            },
            "required": ["key"]
        }
    },
    {
        "name": "get_all_user_facts",
        "description": "Obtiene todos los datos guardados del usuario",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

def execute_tool(tool_name: str, tool_input: dict, chat_id: int) -> str:
    """Execute a tool and return the result"""
    logger.info(f"⚙️ EXECUTING TOOL: {tool_name}")
    logger.info(f"📥 TOOL INPUT: {json.dumps(tool_input, indent=2)}")
    
    try:
        if tool_name == "get_calendar_events":
            result = get_calendar_events(
                tool_input["start_date"],
                tool_input["end_date"]
            )
        elif tool_name == "create_calendar_event":
            result = create_calendar_event(
                tool_input["summary"],
                tool_input["start_time"],
                tool_input["end_time"],
                tool_input.get("location")
            )
        elif tool_name == "create_reminder":
            result = f"✅ Recordatorio creado: {tool_input['reminder_text']}"
            if "reminder_time" in tool_input:
                result += f" para {tool_input['reminder_time']}"
        elif tool_name == "save_user_fact":
            save_fact(chat_id, tool_input["key"], tool_input["value"])
            result = f"✅ Guardado: {tool_input['key']}"
        elif tool_name == "get_user_fact":
            value = get_fact(chat_id, tool_input["key"])
            result = value if value else f"No encontré información sobre '{tool_input['key']}'"
        elif tool_name == "get_all_user_facts":
            facts = get_all_facts(chat_id)
            if facts:
                result = "Datos guardados:\n" + "\n".join([f"- {k}: {v}" for k, v in facts.items()])
            else:
                result = "No hay datos guardados aún"
        else:
            result = f"❌ Tool desconocido: {tool_name}"
        
        logger.info(f"📤 TOOL RESULT: {result}")
        return result
        
    except Exception as e:
        error_msg = f"❌ Error ejecutando {tool_name}: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return error_msg

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages"""
    chat_id = update.effective_chat.id
    user_message = update.message.text
    
    logger.info(f"💬 USER MESSAGE: {user_message}")
    
    try:
        # Build conversation with Claude
        messages = [{"role": "user", "content": user_message}]
        
        logger.info(f"🚀 CALLING CLAUDE API...")
        
        # Call Claude API
        response = anthropic_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=build_system_prompt(),
            tools=tools,
            messages=messages
        )
        
        logger.info(f"🤖 CLAUDE RESPONSE - Stop Reason: {response.stop_reason}")
        logger.info(f"🤖 CLAUDE CONTENT: {json.dumps([{'type': c.type, 'text': c.text if hasattr(c, 'text') else c.name if hasattr(c, 'name') else str(c)} for c in response.content], indent=2)}")
        
        # Process tool uses
        while response.stop_reason == "tool_use":
            logger.info(f"🔧 CLAUDE REQUESTED TOOLS")
            
            # Extract tool uses and text
            tool_uses = [block for block in response.content if block.type == "tool_use"]
            text_blocks = [block.text for block in response.content if hasattr(block, "text")]
            
            logger.info(f"🔧 FOUND {len(tool_uses)} TOOL CALLS")
            
            # Execute tools
            tool_results = []
            for tool_use in tool_uses:
                logger.info(f"🔨 Executing: {tool_use.name}")
                result = execute_tool(tool_use.name, tool_use.input, chat_id)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result
                })
            
            # Continue conversation with tool results
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            
            logger.info(f"🔄 CALLING CLAUDE AGAIN WITH TOOL RESULTS...")
            
            response = anthropic_client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=4096,
                system=build_system_prompt(),
                tools=tools,
                messages=messages
            )
            
            logger.info(f"🤖 CLAUDE SECOND RESPONSE - Stop Reason: {response.stop_reason}")
        
        # Extract final text response
        final_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                final_text += block.text
        
        if not final_text:
            final_text = "✅ Listo"
        
        logger.info(f"📨 SENDING TO USER: {final_text}")
        
        await update.message.reply_text(final_text)
        
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        await update.message.reply_text("❌ Hubo un error procesando tu mensaje. Intenta de nuevo.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "👋 Hola! Soy Claudette, tu asistente personal.\n\n"
        "Puedo ayudarte con:\n"
        "- 📅 Tu calendario\n"
        "- 💾 Guardar información importante\n"
        "- 🧠 Análisis profundo (activa 'segundo cerebro')\n\n"
        "¿En qué puedo ayudarte?"
    )

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages"""
    await update.message.reply_text("🎤 Funcionalidad de voz en desarrollo...")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages"""
    await update.message.reply_text("📸 Funcionalidad de fotos en desarrollo...")

def main():
    """Start the bot"""
    # Setup database
    logger.info("🗄️ Setting up database...")
    setup_database()
    
    # Get token
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
    
    # Create application
    logger.info("🤖 Creating Telegram application...")
    application = Application.builder().token(token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Start bot
    logger.info("✅ Bot started and listening...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
