"""
Brain de Claudette Bot.
System prompt rico + loop de herramientas multi-ronda + safe history trimming.
Portado completo desde bot.py monolítico.
"""

import os
import json
import anthropic
import pytz
from datetime import datetime
from config import ANTHROPIC_API_KEY, DEFAULT_MODEL, MAX_HISTORY, MAX_TOOL_ROUNDS, logger
from tools_registry import TOOLS_SCHEMA, execute_tool, user_locations
from memory_manager import get_all_facts, get_fact, save_fact

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# --- HISTORIAL EN MEMORIA ---
conversation_history = {}

# --- USER MODES ---
user_modes = {}


# =====================================================
# CARGADOR DE ARCHIVOS PROMPT
# =====================================================

def load_file_content(filename, default_text=""):
    """Carga archivos de prompts/ o raíz."""
    try:
        path = f'prompts/{filename}'
        if not os.path.exists(path):
            path = filename
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                logger.info(f"📚 Loaded {filename}")
                return f.read()
    except Exception as e:
        logger.error(f"⚠️ Error loading {filename}: {e}")
    return default_text


CLAUDETTE_CORE = load_file_content('CLAUDETTE_CORE.md', "Eres Claudette, asistente inteligente de Pablo.")
USER_PROFILE = load_file_content('user_profile.md', "")


# =====================================================
# SAFE HISTORY TRIMMING (evita error 400 tool_use/tool_result)
# =====================================================

def _is_tool_result_message(msg):
    content = msg.get('content', [])
    if isinstance(content, list):
        return any(
            isinstance(block, dict) and block.get('type') == 'tool_result'
            for block in content
        )
    return False


def _is_tool_use_message(msg):
    content = msg.get('content', [])
    if isinstance(content, list):
        return any(
            (isinstance(block, dict) and block.get('type') == 'tool_use') or
            (hasattr(block, 'type') and block.type == 'tool_use')
            for block in content
        )
    return False


def _next_is_tool_result(messages, index):
    if index + 1 < len(messages):
        return _is_tool_result_message(messages[index + 1])
    return False


def trim_history_safe(messages, max_length=20):
    """Recorta historial sin romper pares tool_use/tool_result."""
    if len(messages) <= max_length:
        return messages
    trimmed = messages[-max_length:]
    # No empezar con un tool_result suelto
    while trimmed and _is_tool_result_message(trimmed[0]):
        trimmed = trimmed[1:]
    # No empezar con un tool_use sin su tool_result después
    while trimmed and _is_tool_use_message(trimmed[0]) and not _next_is_tool_result(trimmed, 0):
        trimmed = trimmed[1:]
    return trimmed if trimmed else messages[-2:]


# =====================================================
# SERIALIZACIÓN (convierte objetos Anthropic → JSON)
# =====================================================

def serialize_content(content_obj):
    """Convierte objetos complejos de Anthropic a diccionarios JSON."""
    if isinstance(content_obj, str):
        return content_obj

    if isinstance(content_obj, list):
        serialized = []
        for block in content_obj:
            if hasattr(block, 'type'):
                if block.type == 'text':
                    serialized.append({"type": "text", "text": block.text})
                elif block.type == 'tool_use':
                    serialized.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })
            else:
                serialized.append(block)  # Ya es dict
        return serialized
    return str(content_obj)


# =====================================================
# SYSTEM PROMPT BUILDER
# =====================================================

def build_system_prompt(chat_id):
    """Construye el system prompt completo con contexto dinámico."""
    tz = pytz.timezone('America/Costa_Rica')
    now = datetime.now(tz)

    # Cargar memoria persistente
    all_facts = get_all_facts() or {}
    memory_text = ""
    if all_facts:
        memory_lines = [f"- {k}: {v}" for k, v in all_facts.items()
                        if not k.startswith("System_Location")]
        if memory_lines:
            memory_text = "\n=== MEMORIA PERSISTENTE (datos que el usuario me pidió recordar) ===\n" + "\n".join(memory_lines) + "\n"

    # Ubicación
    from config import DEFAULT_LOCATION
    loc = user_locations.get(chat_id, DEFAULT_LOCATION)

    # Modo
    current_mode = user_modes.get(chat_id, "normal")
    mode_instruction = "MODO: NORMAL ⚡. Sé breve."
    if current_mode == "profundo":
        mode_instruction = "MODO: PROFUNDO 🧘‍♀️. Analiza detalladamente."

    return f"""{CLAUDETTE_CORE}
{USER_PROFILE}
{memory_text}
=== CONTEXTO ===
📅 {now.strftime("%A %d-%m-%Y %H:%M")}
📍 {loc['name']} (GPS: {loc['lat']}, {loc['lng']})
{mode_instruction}
"""


# =====================================================
# CEREBRO PRINCIPAL
# =====================================================

async def process_chat(update, context, text, image_data=None):
    """
    Procesa un mensaje completo:
    1. Construye historial
    2. Llama a Claude con herramientas
    3. Loop multi-ronda (hasta MAX_TOOL_ROUNDS)
    4. Retorna texto final
    """
    chat_id = update.effective_chat.id

    if chat_id not in conversation_history:
        conversation_history[chat_id] = []

    # Recuperar ubicación guardada si no la tenemos
    if chat_id not in user_locations:
        try:
            saved_lat = get_fact(f"System_Location_Lat_{chat_id}")
            saved_lng = get_fact(f"System_Location_Lng_{chat_id}")
            if saved_lat and saved_lng:
                user_locations[chat_id] = {
                    "lat": float(saved_lat),
                    "lng": float(saved_lng),
                    "name": "Ubicación Guardada"
                }
                logger.info(f"📍 Recuperado de memoria: {saved_lat}, {saved_lng}")
        except Exception as e:
            logger.error(f"Error recuperando ubicación: {e}")

    # Construir contenido del mensaje
    user_msg_content = text
    if image_data:
        user_msg_content = [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_data}},
            {"type": "text", "text": text}
        ]

    messages = conversation_history[chat_id]
    messages.append({"role": "user", "content": user_msg_content})

    # Safe trim
    if len(messages) > MAX_HISTORY:
        conversation_history[chat_id] = trim_history_safe(messages, MAX_HISTORY)
        messages = conversation_history[chat_id]

    try:
        system_prompt = build_system_prompt(chat_id)

        # Primera llamada a Claude
        response = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=4096,
            system=system_prompt,
            tools=TOOLS_SCHEMA,
            messages=messages
        )

        final_text = ""

        # Loop de herramientas (hasta MAX_TOOL_ROUNDS rondas)
        for round_num in range(MAX_TOOL_ROUNDS):
            if response.stop_reason != "tool_use":
                # Respuesta final de texto
                for block in response.content:
                    if block.type == "text":
                        final_text += block.text
                break

            # Serializar y guardar respuesta del asistente
            clean_content = serialize_content(response.content)
            messages.append({"role": "assistant", "content": clean_content})

            # Procesar herramientas
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    logger.info(f"🔧 Tool (ronda {round_num + 1}): {block.name}")
                    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
                    try:
                        tool_result = await execute_tool(block.name, block.input, chat_id, context)
                    except Exception as e:
                        tool_result = f"Error: {str(e)}"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(tool_result)
                    })

            messages.append({"role": "user", "content": tool_results})

            # Siguiente ronda
            response = client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=4096,
                system=system_prompt,
                tools=TOOLS_SCHEMA,
                messages=messages
            )
        else:
            # Agotó las rondas → extraer lo que haya
            for block in response.content:
                if block.type == "text":
                    final_text += block.text

        if not final_text:
            final_text = "✅ He procesado la solicitud."

        messages.append({"role": "assistant", "content": final_text})
        return final_text

    except Exception as e:
        logger.error(f"Brain Error: {e}", exc_info=True)
        return f"🤯 Error interno: {e}"
