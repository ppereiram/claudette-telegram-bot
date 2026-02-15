from config import OPENAI_API_KEY, logger
from openai import OpenAI
import json
# IMPORTA TUS SERVICIOS AQUI (google_calendar, etc...)

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

TOOLS_SCHEMA = [
    # ... (Tus herramientas anteriores: weather, calendar, tasks, memory) ...
    # ... AÑADE ESTA NUEVA:
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

async def execute_tool(name, args, chat_id, context):
    try:
        if name == "generate_image":
            if not openai_client: return "OpenAI no configurado."
            msg = await context.bot.send_message(chat_id, "🎨 Pintando tu idea...")
            response = openai_client.images.generate(
                model="dall-e-3", prompt=args['prompt'], size="1024x1024", quality="standard", n=1
            )
            # Enviar imagen y borrar mensaje de espera
            await context.bot.send_photo(chat_id, photo=response.data[0].url, caption=f"🎨 {args['prompt']}")
            await context.bot.delete_message(chat_id, msg.message_id)
            return "✅ Imagen generada y enviada."

        # ... (Aquí va tu lógica anterior: if name == 'get_weather': return ...)

    except Exception as e:
        logger.error(f"Tool Error {name}: {e}")
        return f"Error en herramienta: {e}"
