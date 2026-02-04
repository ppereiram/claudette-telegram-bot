import os
import logging
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic
import google_calendar
from memory_manager import setup_database, save_fact, get_fact, get_all_facts

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get tokens from environment
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Tool definitions for Claude
TOOLS = [
            {
                "name": "get_calendar_events",
                "description": "Get calendar events between two dates",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "start_date": {"type": "string", "description": "Start date in ISO format (e.g., '2024-01-01T00:00:00-06:00')"},
                        "end_date": {"type": "string", "description": "End date in ISO format"}
                    },
                    "required": ["start_date", "end_date"]
                }
            },
            {
                "name": "create_calendar_event",
                "description": "Create a new calendar event. If user mentions reminder time (e.g., 'remind me 2 hours before', '30 minutes before'), include reminder_minutes parameter. If no reminder mentioned, leave it null and ask user after creating the event.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string", "description": "Event title"},
                        "start_time": {"type": "string", "description": "Start time in ISO format with timezone (e.g., '2024-01-15T14:00:00-06:00')"},
                        "end_time": {"type": "string", "description": "End time in ISO format with timezone"},
                        "location": {"type": "string", "description": "Event location (optional)"},
                        "reminder_minutes": {"type": "integer", "description": "Minutes before event to send reminder (e.g., 60 for 1 hour, 120 for 2 hours). Only include if user explicitly mentions reminder time. Leave null otherwise."}
                    },
                    "required": ["summary", "start_time", "end_time"]
                }
            },
            {
                "name": "update_event_reminder",
                "description": "Update or set reminder for an existing calendar event. Use this when user wants to add/change reminder after event is created.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "event_id": {"type": "string", "description": "The event ID from the created event"},
                        "reminder_minutes": {"type": "integer", "description": "Minutes before event to remind (e.g., 60 for 1 hour, 120 for 2 hours). Use 0 for no reminder."}
                    },
                    "required": ["event_id", "reminder_minutes"]
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
            }
        ]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        '¡Hola! Soy Claudette, tu asistente personal. '
        'Puedo ayudarte con tu calendario, recordatorios y más. '
        '¿En qué puedo ayudarte?'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages."""
    user_message = update.message.text
    chat_id = update.message.chat_id
    
    logger.info(f"💬 USER MESSAGE: {user_message}")
    
    try:
        # Call Claude API
        logger.info(f"🚀 CALLING CLAUDE API...")
        
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=4096,
            tools=TOOLS,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        
        logger.info(f"🤖 CLAUDE RESPONSE - Stop Reason: {response.stop_reason}")
        logger.info(f"🤖 CLAUDE CONTENT: {json.dumps([{'type': block.type, 'text': block.name if hasattr(block, 'name') else ''} for block in response.content], indent=2)}")
        
        # Check if Claude wants to use tools
        if response.stop_reason == "tool_use":
            logger.info(f"🔧 CLAUDE REQUESTED TOOLS")
            
            # Extract tool calls
            tool_results = []
            tool_calls = [block for block in response.content if block.type == "tool_use"]
            
            logger.info(f"🔧 FOUND {len(tool_calls)} TOOL CALLS")
            
            for tool_call in tool_calls:
                tool_name = tool_call.name
                tool_input = tool_call.input
                tool_id = tool_call.id
                
                logger.info(f"🔨 Executing: {tool_name}")
                logger.info(f"⚙️ EXECUTING TOOL: {tool_name}")
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
                        location=tool_input.get("location"),
                        reminder_minutes=tool_input.get("reminder_minutes")
                    )
                elif tool_name == "update_event_reminder":
                    result = google_calendar.update_event_reminder(
                        event_id=tool_input.get("event_id"),
                        reminder_minutes=tool_input.get("reminder_minutes")
                    )
                elif tool_name == "create_reminder":
                    result = f"⏰ Recordatorio creado: {tool_input.get('message')} para {tool_input.get('time')}"
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
                else:
                    result = f"Tool {tool_name} not implemented yet"
                
                logger.info(f"📤 TOOL RESULT: {result}")
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": result
                })
            
            # Call Claude again with tool results
            logger.info(f"🔄 CALLING CLAUDE AGAIN WITH TOOL RESULTS...")
            
            follow_up_response = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4096,
                tools=TOOLS,
                messages=[
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": response.content},
                    {"role": "user", "content": tool_results}
                ]
            )
            
            logger.info(f"🤖 CLAUDE SECOND RESPONSE - Stop Reason: {follow_up_response.stop_reason}")
            
            # Extract text response
            text_blocks = [block.text for block in follow_up_response.content if hasattr(block, "text")]
            final_response = "\n".join(text_blocks) if text_blocks else "✅ Hecho!"
            
        else:
            # Direct text response
            text_blocks = [block.text for block in response.content if hasattr(block, "text")]
            final_response = "\n".join(text_blocks)
        
        logger.info(f"📨 SENDING TO USER: {final_response}")
        await update.message.reply_text(final_response)
        
    except Exception as e:
        logger.error(f"❌ ERROR: {e}", exc_info=True)
        await update.message.reply_text(f"Lo siento, ocurrió un error: {str(e)}")

def main():
    """Start the bot."""
    logger.info(f"🗄️ Setting up database...")
    setup_database()
    
    logger.info(f"🤖 Creating Telegram application...")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    logger.info(f"✅ Bot started and listening...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
