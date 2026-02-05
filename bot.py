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

# Tool definitions for Claude
TOOLS = [
    {
        "name": "get_calendar_events",
        "description": "Get calendar events between two dates",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Start date in ISO format (e.g., '2026-02-04T00:00:00-06:00')"},
                "end_date": {"type": "string", "description": "End date in ISO format"}
            },
            "required": ["start_date", "end_date"]
        }
    },
    {
        "name": "create_calendar_event",
        "description": "Create a new calendar event. IMPORTANT: Always use year 2026 for dates.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Event title"},
                "start_time": {"type": "string", "description": "Start time in ISO format with timezone. MUST use year 2026. Example: '2026-02-05T15:00:00-06:00'"},
                "end_time": {"type": "string", "description": "End time in ISO format with timezone. MUST use year 2026."},
                "location": {"type": "string", "description": "Event location (optional)"}
            },
            "required": ["summary", "start_time", "end_time"]
        }
    },
    {
        "name": "create_reminder",
        "description": "Create a reminder for the user",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "The reminder message"},
                "time": {"type": "string", "description": "When to remind (e.g., '2pm', 'in 30 minutes')"}
            },
            "required": ["message", "time"]
        }
    },
    {
        "name": "read_local_file",
        "description": "Read contents of a local file in the repository (e.g., user_profile.md with user's personal information, documents, etc.)",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Name of the file to read (e.g., 'user_profile.md')"}
            },
            "required": ["filename"]
        }
    },
    {
        "name": "save_user_fact",
        "description": "Save a fact about the user for future reference",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Category or key for the fact (e.g., 'favorite_color', 'birthday')"},
                "value": {"type": "string", "description": "The fact to remember"}
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "get_user_fact",
        "description": "Retrieve a specific fact about the user",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "The key to look up"}
            },
            "required": ["key"]
        }
    },
    {
        "name": "get_all_user_facts",
        "description": "Get all saved facts about the user",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "search_emails",
        "description": "Search emails in Gmail. Use Gmail search syntax: 'from:email@example.com', 'subject:keyword', 'is:unread', 'after:2026/01/01', 'has:attachment'. Can combine: 'from:boss@company.com is:unread'",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Gmail search query (e.g., 'is:unread', 'from:nombre@email.com', 'subject:reunión')"},
                "max_results": {"type": "integer", "description": "Maximum emails to return (default 10, max 20)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "read_email",
        "description": "Read the full content of a specific email by its ID. Use after search_emails to get the complete body of an email.",
        "input_schema": {
            "type": "object",
            "properties": {
                "email_id": {"type": "string", "description": "The email ID from search_emails results"}
            },
            "required": ["email_id"]
        }
    },
    {
        "name": "send_email",
        "description": "Send an email. Can also reply to existing emails by providing reply_to_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body content"},
                "reply_to_id": {"type": "string", "description": "Optional: email ID to reply to (maintains thread)"}
            },
            "required": ["to", "subject", "body"]
        }
    }
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        '¡Hola! Soy Claudette, tu asistente personal. '
        'Puedo ayudarte con tu calendario, emails, recordatorios y más. '
        '¿En qué puedo ayudarte?'
    )

def read_local_file(filename):
    """Read a local file from the repository."""
    try:
        file_path = os.path.join(os.path.dirname(__file__), filename)
        logger.info(f"📂 Reading file: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.info(f"✅ File read successfully: {len(content)} characters")
        return content
    except FileNotFoundError:
        logger.error(f"❌ File not found: {filename}")
        return f"❌ Archivo '{filename}' no encontrado."
    except Exception as e:
        logger.error(f"❌ Error reading file: {e}")
        return f"❌ Error leyendo archivo: {str(e)}"

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
        logger.error(f"❌ Error transcribing voice: {e}")
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
        logger.error(f"❌ Error generating speech: {e}")
        return None

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages."""
    logger.info("🎤 Received voice message")
    
    if not openai_client:
        await update.message.reply_text("Lo siento, la transcripción de voz no está disponible.")
        return
    
    try:
        voice_file = await update.message.voice.get_file()
        temp_voice = tempfile.NamedTemporaryFile(delete=False, suffix='.ogg')
        await voice_file.download_to_drive(temp_voice.name)
        
        logger.info("🔄 Transcribing voice...")
        transcript = await transcribe_voice(temp_voice.name)
        
        if not transcript:
            await update.message.reply_text("Lo siento, no pude entender el audio.")
            return
        
        logger.info(f"📝 Transcript: {transcript}")
        await process_user_message(update, context, transcript, is_voice=True)
        
    except Exception as e:
        logger.error(f"❌ Error handling voice: {e}", exc_info=True)
        await update.message.reply_text(f"Error procesando voz: {str(e)}")
    finally:
        try:
            os.unlink(temp_voice.name)
        except:
            pass

async def process_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE, user_message: str, is_voice: bool = False):
    """Process user message (text or transcribed voice)."""
    chat_id = update.message.chat_id
    
    logger.info(f"💬 USER MESSAGE: {user_message}")
    
    try:
        costa_rica_tz = pytz.timezone('America/Costa_Rica')
        now = datetime.now(costa_rica_tz)
        today_str = now.strftime("%Y-%m-%d")
        tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        
        system_prompt = f"""You are Claudette, a helpful assistant in Costa Rica.

CRITICAL - CURRENT DATE: Today is {today_str} (February 4, 2026).

When user says:
- "hoy" or "today" = {today_str}
- "mañana" or "tomorrow" = {tomorrow_str}

You MUST use year 2026 for all calendar events. Do NOT use 2023 or any other year.

Example dates:
- "mañana a las 3pm" = "{tomorrow_str}T15:00:00-06:00"
- "hoy a las 5pm" = "{today_str}T17:00:00-06:00"

IMPORTANT: When the user asks for personal information (passport, ID, phone numbers, addresses, etc.), 
ALWAYS use the read_local_file tool to read "user_profile.md" first. This file contains all the user's 
personal information.

For email operations, use search_emails, read_email, and send_email tools.
"""
        
        logger.info(f"🚀 CALLING CLAUDE API...")
        
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=4096,
            system=system_prompt,
            tools=TOOLS,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        
        logger.info(f"🤖 CLAUDE RESPONSE - Stop Reason: {response.stop_reason}")
        
        if response.stop_reason == "tool_use":
            logger.info(f"🔧 CLAUDE REQUESTED TOOLS")
            
            tool_results = []
            tool_calls = [block for block in response.content if block.type == "tool_use"]
            
            logger.info(f"🔧 FOUND {len(tool_calls)} TOOL CALLS")
            
            for tool_call in tool_calls:
                tool_name = tool_call.name
                tool_input = tool_call.input
                tool_id = tool_call.id
                
                logger.info(f"🔨 Executing: {tool_name}")
                logger.info(f"📥 TOOL INPUT: {json.dumps(tool_input, indent=2)}")
                
                # Execute the appropriate tool
                if tool_name == "get_calendar_events":
                    result = google_calendar.get_calendar_events(
                        start_date=tool_input.get("start_date"),
                        end_date=tool_input.get("end_date")
                    )
                elif tool_name == "create_calendar_event":
                    result = google_calendar.create_calendar_event(
                        summary=tool_input.get("summary"),
                        start_time=tool_input.get("start_time"),
                        end_time=tool_input.get("end_time"),
                        location=tool_input.get("location")
                    )
                elif tool_name == "create_reminder":
                    result = f"⏰ Recordatorio creado: {tool_input.get('message')} para {tool_input.get('time')}"
                elif tool_name == "read_local_file":
                    result = read_local_file(tool_input.get("filename"))
                elif tool_name == "save_user_fact":
                    save_fact(chat_id, tool_input.get("key"), tool_input.get("value"))
                    result = f"✅ Guardado: {tool_input.get('key')} = {tool_input.get('value')}"
                elif tool_name == "get_user_fact":
                    fact = get_fact(chat_id, tool_input.get("key"))
                    result = fact if fact else f"No tengo información sobre {tool_input.get('key')}"
                elif tool_name == "get_all_user_facts":
                    facts = get_all_facts(chat_id)
                    if facts:
                        result = "Esto es lo que sé sobre ti:\n" + "\n".join([f"- {k}: {v}" for k, v in facts.items()])
                    else:
                        result = "Aún no tengo información guardada sobre ti."
                
                # Gmail tools
                elif tool_name == "search_emails":
                    query = tool_input.get("query", "")
                    max_results = min(tool_input.get("max_results", 10), 20)
                    search_result = gmail_service.search_emails(query, max_results)
                    
                    if search_result["success"]:
                        if search_result.get("emails"):
                            emails_text = f"Encontré {search_result['count']} emails:\n\n"
                            for i, email in enumerate(search_result["emails"], 1):
                                emails_text += f"{i}. **{email['subject']}**\n"
                                emails_text += f"   De: {email['from']}\n"
                                emails_text += f"   Fecha: {email['date']}\n"
                                emails_text += f"   Preview: {email['snippet']}\n"
                                emails_text += f"   [ID: {email['id']}]\n\n"
                            result = emails_text
                        else:
                            result = search_result.get("message", "No se encontraron emails.")
                    else:
                        result = f"Error: {search_result['error']}"
                
                elif tool_name == "read_email":
                    email_id = tool_input.get("email_id", "")
                    email_result = gmail_service.get_email(email_id)
                    
                    if email_result["success"]:
                        result = f"""📧 **{email_result['subject']}**

De: {email_result['from']}
Para: {email_result['to']}
Fecha: {email_result['date']}

---
{email_result['body']}
"""
                    else:
                        result = f"Error: {email_result['error']}"
                
                elif tool_name == "send_email":
                    to = tool_input.get("to", "")
                    subject = tool_input.get("subject", "")
                    body = tool_input.get("body", "")
                    reply_to = tool_input.get("reply_to_id")
                    
                    send_result = gmail_service.send_email(to, subject, body, reply_to)
                    
                    if send_result["success"]:
                        result = f"✅ {send_result['message']}"
                    else:
                        result = f"❌ Error: {send_result['error']}"
                
                else:
                    result = f"Tool {tool_name} not implemented yet"
                
                logger.info(f"📤 TOOL RESULT: {result}")
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": result
                })
            
            logger.info(f"🔄 CALLING CLAUDE AGAIN WITH TOOL RESULTS...")
            
            follow_up_response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=4096,
                system=system_prompt,
                tools=TOOLS,
                messages=[
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": response.content},
                    {"role": "user", "content": tool_results}
                ]
            )
            
            logger.info(f"🤖 CLAUDE SECOND RESPONSE - Stop Reason: {follow_up_response.stop_reason}")
            
            text_blocks = [block.text for block in follow_up_response.content if hasattr(block, "text")]
            final_response = "\n".join(text_blocks) if text_blocks else "✅ Hecho!"
            
        else:
            text_blocks = [block.text for block in response.content if hasattr(block, "text")]
            final_response = "\n".join(text_blocks)
        
        logger.info(f"📨 SENDING TO USER: {final_response}")
        
        if is_voice and elevenlabs_client:
            logger.info("🔊 Generating voice response...")
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
        await update.message.reply_text(f"Lo siento, ocurrió un error: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages."""
    user_message = update.message.text
    await process_user_message(update, context, user_message, is_voice=False)

def main():
    """Start the bot."""
    logger.info(f"🗄️ Setting up database...")
    setup_database()
    
    logger.info(f"🤖 Creating Telegram application...")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info(f"✅ Bot started and listening...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
