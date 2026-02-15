import anthropic
import json
import os
from config import ANTHROPIC_API_KEY, DEFAULT_MODEL, MAX_HISTORY, logger
from tools_registry import TOOLS_SCHEMA, execute_tool

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# --- PERSISTENCIA SIMPLE ---
HISTORY_FILE = 'chat_history.json'

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_history(history):
    with open(HISTORY_FILE, 'w') as f: json.dump(history, f)

conversation_history = load_history()

async def process_chat(update, context, user_text, image_data=None):
    chat_id = str(update.effective_chat.id)
    if chat_id not in conversation_history: conversation_history[chat_id] = []
    
    # 1. Añadir mensaje usuario
    content = user_text
    if image_data:
        content = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_data}}, {"type": "text", "text": user_text}]
    
    conversation_history[chat_id].append({"role": "user", "content": content})
    
    # 2. Recorte de historial (para ahorrar tokens)
    if len(conversation_history[chat_id]) > MAX_HISTORY:
        conversation_history[chat_id] = conversation_history[chat_id][-MAX_HISTORY:]

    # 3. Loop de Claude (Pensamiento + Herramientas)
    try:
        # Aquí va tu lógica de system prompt (fecha, ubicación, perfil)
        system_prompt = "Eres Claudette..." 
        
        response = client.messages.create(
            model=DEFAULT_MODEL, max_tokens=4096, system=system_prompt,
            messages=conversation_history[chat_id], tools=TOOLS_SCHEMA
        )

        final_text = ""
        
        # Manejo de respuesta y tools (simplificado)
        if response.stop_reason == "tool_use":
            conversation_history[chat_id].append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    # INDICADOR VISUAL: "Claudette está usando Google Calendar..."
                    await context.bot.send_chat_action(chat_id, action="typing")
                    
                    res = await execute_tool(block.name, block.input, chat_id, context)
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(res)})
            
            conversation_history[chat_id].append({"role": "user", "content": tool_results})
            
            # Segunda llamada con resultados
            response2 = client.messages.create(
                model=DEFAULT_MODEL, max_tokens=4096, system=system_prompt,
                messages=conversation_history[chat_id], tools=TOOLS_SCHEMA
            )
            final_text = response2.content[0].text
        else:
            final_text = response.content[0].text

        # 4. Guardar y Responder
        conversation_history[chat_id].append({"role": "assistant", "content": final_text})
        save_history(conversation_history) # Guardamos en disco
        return final_text

    except Exception as e:
        logger.error(f"Brain Error: {e}")
        return f"🤯 Tuve un cortocircuito: {e}"
