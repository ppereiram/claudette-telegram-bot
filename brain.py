import anthropic
import json
import os
from config import ANTHROPIC_API_KEY, DEFAULT_MODEL, MAX_HISTORY, logger
from tools_registry import TOOLS_SCHEMA, execute_tool
from memory_manager import get_all_facts

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# --- PERSISTENCIA ---
HISTORY_FILE = 'chat_history.json'

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_history(history):
    try:
        with open(HISTORY_FILE, 'w') as f: json.dump(history, f, indent=2)
    except Exception as e:
        logger.error(f"Error guardando historial: {e}")

conversation_history = load_history()

# --- HELPER: SERIALIZADOR (LA CLAVE PARA ARREGLAR EL ERROR) ---
def serialize_content(content_obj):
    """Convierte objetos complejos de Anthropic a diccionarios JSON simples"""
    if isinstance(content_obj, str):
        return content_obj
    
    # Si es una lista de bloques (texto + herramientas)
    if isinstance(content_obj, list):
        serialized_blocks = []
        for block in content_obj:
            if hasattr(block, 'type'):
                if block.type == 'text':
                    serialized_blocks.append({"type": "text", "text": block.text})
                elif block.type == 'tool_use':
                    serialized_blocks.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })
            else:
                serialized_blocks.append(block) # Ya es un dict
        return serialized_blocks
    return str(content_obj)

def get_system_prompt():
    facts = get_all_facts()
    memory_text = "\n".join([f"- {k}: {v}" for k, v in facts.items()]) if facts else "Sin datos guardados."
    return f"""Eres Claudette, una asistente AI avanzada.
    === MEMORIA DE LARGO PLAZO ===
    {memory_text}
    Usa herramientas proactivamente. Si te piden imagen, usa 'generate_image'.
    """

async def process_chat(update, context, user_text, image_data=None):
    chat_id = str(update.effective_chat.id)
    if chat_id not in conversation_history: conversation_history[chat_id] = []
    
    # 1. Input Usuario
    content = user_text
    if image_data:
        content = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_data}}, {"type": "text", "text": user_text}]
    
    conversation_history[chat_id].append({"role": "user", "content": content})
    
    # Trim historial
    if len(conversation_history[chat_id]) > MAX_HISTORY:
        conversation_history[chat_id] = conversation_history[chat_id][-MAX_HISTORY:]

    try:
        # 2. Primera llamada a Claude
        response = client.messages.create(
            model=DEFAULT_MODEL, max_tokens=4096, system=get_system_prompt(),
            messages=conversation_history[chat_id], tools=TOOLS_SCHEMA
        )

        final_text = ""

        # 3. Manejo de Herramientas
        if response.stop_reason == "tool_use":
            # AQUI ESTABA EL ERROR: Ahora usamos serialize_content
            clean_content = serialize_content(response.content)
            conversation_history[chat_id].append({"role": "assistant", "content": clean_content})
            
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    await context.bot.send_chat_action(chat_id, action="typing")
                    result = await execute_tool(block.name, block.input, chat_id, context)
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(result)})
            
            conversation_history[chat_id].append({"role": "user", "content": tool_results})
            
            # Segunda llamada con resultados
            response2 = client.messages.create(
                model=DEFAULT_MODEL, max_tokens=4096, system=get_system_prompt(),
                messages=conversation_history[chat_id], tools=TOOLS_SCHEMA
            )
            final_text = response2.content[0].text
        else:
            final_text = response.content[0].text

        conversation_history[chat_id].append({"role": "assistant", "content": final_text})
        save_history(conversation_history) # Ahora sí funcionará
        return final_text

    except Exception as e:
        logger.error(f"Brain Error: {e}")
        return f"🤯 Tuve un error interno: {e}"
