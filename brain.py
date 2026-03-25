"""
Brain de Claudette Bot.
System prompt rico + loop de herramientas multi-ronda + safe history trimming.
Portado completo desde bot.py monolÃ­tico.
"""

import os
import json
import anthropic
import pytz
from datetime import datetime
from config import ANTHROPIC_API_KEY, DEFAULT_MODEL, MAX_HISTORY, MAX_TOOL_ROUNDS, MAX_TOKENS_NORMAL, MAX_TOKENS_DOCUMENT, logger
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
    """Carga archivos de prompts/ o raÃ­z."""
    try:
        path = f'prompts/{filename}'
        if not os.path.exists(path):
            path = filename
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                logger.info(f"ðŸ“š Loaded {filename}")
                return f.read()
    except Exception as e:
        logger.error(f"âš ï¸ Error loading {filename}: {e}")
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
    # No empezar con un tool_use sin su tool_result despuÃ©s
    while trimmed and _is_tool_use_message(trimmed[0]) and not _next_is_tool_result(trimmed, 0):
        trimmed = trimmed[1:]
    return trimmed if trimmed else messages[-2:]


# =====================================================
# SERIALIZACIÃ“N (convierte objetos Anthropic â†’ JSON)
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
    """Construye el system prompt completo con contexto dinÃ¡mico."""
    tz = pytz.timezone('America/Costa_Rica')
    now = datetime.now(tz)

    # Cargar memoria persistente
    all_facts = get_all_facts() or {}
    memory_text = ""
    if all_facts:
        memory_lines = [f"- {k}: {v}" for k, v in all_facts.items()
                        if not k.startswith("System_Location")]
        if memory_lines:
            memory_text = "\n=== MEMORIA PERSISTENTE (datos que el usuario me pidiÃ³ recordar) ===\n" + "\n".join(memory_lines) + "\n"

    # UbicaciÃ³n
    from config import DEFAULT_LOCATION
    loc = user_locations.get(chat_id, DEFAULT_LOCATION)

    # Modo
    current_mode = user_modes.get(chat_id, "normal")
    mode_instruction = "MODO: NORMAL âš¡. SÃ© breve."
    if current_mode == "profundo":
        mode_instruction = "MODO: PROFUNDO ðŸ§˜â€â™€ï¸. Analiza detalladamente."

    # Mini-calendario de referencia (prÃ³ximos 7 dÃ­as)
    from datetime import timedelta
    dias_semana = ['lunes', 'martes', 'miÃ©rcoles', 'jueves', 'viernes', 'sÃ¡bado', 'domingo']
    week_ref = []
    for i in range(7):
        d = now + timedelta(days=i)
        dia_nombre = dias_semana[d.weekday()]
        prefix = "HOY" if i == 0 else ("MAÃ‘ANA" if i == 1 else dia_nombre.upper())
        week_ref.append(f"  {prefix}: {dia_nombre} {d.strftime('%d/%m/%Y')}")
    week_calendar = "\n".join(week_ref)

    return f"""{CLAUDETTE_CORE}
{USER_PROFILE}
{memory_text}
=== BIBLIOTECA Y ESCRITOS DE PABLO ===
Tienes acceso a los escritos, libros y biblioteca de Pablo en Google Drive.
- Usa 'read_book_from_drive("INDICE_BIBLIOTECA")' para consultar quÃ© hay disponible.
- Usa 'read_book_from_drive("[titulo]")' para leer un texto especÃ­fico.
- Cuando analices noticias, decisiones o temas filosÃ³ficos, cruza con los escritos de Pablo si es relevante.
- NO cargues todo â€” solo busca cuando el contexto lo amerite.

=== LECTURA DE URLs ===
Puedes leer pÃ¡ginas web, tweets, artÃ­culos y links que Pablo comparta.
- Usa 'fetch_url' cuando Pablo mande una URL o link.
- Funciona con X/Twitter, noticias, blogs, y pÃ¡ginas pÃºblicas.
- Si Pablo manda un link sin contexto, lÃ©elo y resumilo.

=== GENERACIÃ“N DE DOCUMENTOS ===
Puedes generar documentos largos (.docx Word o .md Markdown) que se envÃ­an como archivo descargable.
- Usa 'generate_document' cuando Pablo pida reportes, bitÃ¡coras, ensayos, compilaciones o cualquier texto extenso.
- El contenido del documento NO tiene el lÃ­mite de 4000 chars de Telegram â€” puede ser tan largo como necesites.
- Usa formato Markdown en el contenido (# tÃ­tulos, ## secciones, **negrita**, *cursiva*, listas, citas con >).
- Se convierte automÃ¡ticamente en un Word profesional con tipografÃ­a Georgia y mÃ¡rgenes elegantes.

Puedes generar hojas de cÃ¡lculo Excel (.xlsx) con formato profesional.
- Usa 'generate_spreadsheet' cuando Pablo pida tablas, comparativas, presupuestos, tracking o datos tabulares.
- Soporta mÃºltiples hojas, encabezados formateados, filtros automÃ¡ticos.
- Los datos se pasan como headers + rows estructurados.

=== BIBLIOTECA PERSONAL (2100+ LIBROS) ===
Pablo tiene una biblioteca indexada de ~2100 libros con extractos sustanciales.
- Usa 'search_library' para buscar por tema, concepto o palabra clave (ej: "nihilismo", "atenciÃ³n", "democracia digital").
- Usa 'search_library_by_author' para ver todos los libros de un autor (ej: "Byung-Chul Han", "Jung", "Wittgenstein").
- Usa 'search_library_by_tag' para buscar por etiqueta (ej: "zen", "posestructuralismo", "capitalismo-vigilancia").
- Usa 'get_book_detail' para leer el extracto completo de un libro especÃ­fico.
- Usa 'library_stats' para dar estadÃ­sticas generales.
- IMPORTANTE: Cuando Pablo haga preguntas filosÃ³ficas, existenciales, o sobre cualquier tema intelectual, BUSCA PRIMERO en la biblioteca antes de responder genÃ©ricamente. Sus extractos son profundos y relevantes.
- Cruza informaciÃ³n entre libros cuando sea pertinente (ej: conectar a Han con Heidegger, o a Jung con Weil).

=== CONTEXTO ===
ðŸ“… {now.strftime("%A %d-%m-%Y %H:%M")} (hora Costa Rica, UTC-6)
ðŸ“ {loc['name']} (GPS: {loc['lat']}, {loc['lng']})

ðŸ“† CALENDARIO DE REFERENCIA (NO te confundas de fecha):
{week_calendar}
âš ï¸ IMPORTANTE: Cuando Pablo diga un dÃ­a de la semana, usa EXACTAMENTE la fecha de arriba. NO calcules fechas mentalmente.

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

    # Recuperar ubicaciÃ³n guardada si no la tenemos
    if chat_id not in user_locations:
        try:
            saved_lat = get_fact(f"System_Location_Lat_{chat_id}")
            saved_lng = get_fact(f"System_Location_Lng_{chat_id}")
            if saved_lat and saved_lng:
                user_locations[chat_id] = {
                    "lat": float(saved_lat),
                    "lng": float(saved_lng),
                    "name": "UbicaciÃ³n Guardada"
                }
                logger.info(f"ðŸ“ Recuperado de memoria: {saved_lat}, {saved_lng}")
        except Exception as e:
            logger.error(f"Error recuperando ubicaciÃ³n: {e}")

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

        # Detectar si el mensaje pide generaciÃ³n de documentos â†’ mÃ¡s tokens
        doc_keywords = ['documento', 'reporte', 'informe', 'bitÃ¡cora', 'bitacora',
                        'compila', 'genera un doc', 'genera un archivo', 'word',
                        'ensayo largo', 'resumen extenso', 'docx', 'exporta',
                        'excel', 'xlsx', 'spreadsheet', 'hoja de cÃ¡lculo', 'tabla comparativa']
        text_lower = text.lower() if isinstance(text, str) else ""
        needs_document = any(kw in text_lower for kw in doc_keywords)
        max_tokens = MAX_TOKENS_DOCUMENT if needs_document else MAX_TOKENS_NORMAL

        # Primera llamada a Claude
        response = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=max_tokens,
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
                    logger.info(f"ðŸ”§ Tool (ronda {round_num + 1}): {block.name}")
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

            # Si se usÃ³ generate_document o generate_spreadsheet, asegurar tokens altos
            for block in response.content:
                if hasattr(block, 'name') and block.name in ('generate_document', 'generate_spreadsheet'):
                    max_tokens = MAX_TOKENS_DOCUMENT

            # Siguiente ronda
            response = client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=max_tokens,
                system=system_prompt,
                tools=TOOLS_SCHEMA,
                messages=messages
            )
        else:
            # AgotÃ³ las rondas â†’ extraer lo que haya
            for block in response.content:
                if block.type == "text":
                    final_text += block.text

        if not final_text:
            final_text = "âœ… He procesado la solicitud."


        # AUTO SELF-LEARNING: guardar decisiones en KB automaticamente
        try:
            from knowledge_base import kb_save_insight
            _tl = text.lower() if isinstance(text, str) else ""
            _dtriggers = ["he decidido", "voy a ", "decidi ", "el plan es", "mi decision es"]
            _projs = ["midas", "arepartir", "claudette", "novela", "arquimath"]
            if any(t in _tl for t in _dtriggers):
                _proj = next((p.capitalize() for p in _projs if p in _tl), "General")
                kb_save_insight(
                    category="decision",
                    title=text[:80] if len(text) > 80 else text,
                    content="Pablo dijo: " + text + "\n\nRespuesta: " + final_text[:500],
                    project=_proj
                )
                logger.info("Self-learning: decision guardada - " + _proj)
        except Exception as _sl_err:
            logger.warning("Self-learning error: " + str(_sl_err))

        messages.append({"role": "assistant", "content": final_text})
        return final_text

    except Exception as e:
        logger.error(f"Brain Error: {e}", exc_info=True)
        return f"ðŸ¤¯ Error interno: {e}"


# =====================================================
# RESUMEN MATUTINO INTELIGENTE
# =====================================================

async def generate_morning_summary(chat_id):
    """
    Genera el resumen matutino completo pasando por Claude.
    Pre-busca datos (clima, agenda, tareas, noticias) + un libro aleatorio
    de la biblioteca para provocaciÃ³n intelectual.
    """
    import google_calendar
    import google_tasks
    from tools_registry import get_weather, search_news, user_locations
    from config import DEFAULT_LOCATION

    tz = pytz.timezone('America/Costa_Rica')
    now = datetime.now(tz)

    # --- 1. Recolectar datos brutos ---
    raw_data = []
    raw_data.append(f"FECHA: {now.strftime('%A %d de %B, %Y')} â€” {now.strftime('%H:%M')} hora Costa Rica")

    # Clima
    try:
        loc = user_locations.get(chat_id, DEFAULT_LOCATION)
        weather = get_weather(loc['lat'], loc['lng'])
        raw_data.append(f"\nCLIMA:\n{weather}")
    except Exception as e:
        logger.warning(f"Morning weather error: {e}")

    # Agenda
    try:
        start = now.replace(hour=0, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%S-06:00")
        end = now.replace(hour=23, minute=59, second=59).strftime("%Y-%m-%dT%H:%M:%S-06:00")
        events = google_calendar.get_calendar_events(start, end)
        if events and "No hay eventos" not in str(events):
            raw_data.append(f"\nAGENDA DEL DÃA:\n{events}")
        else:
            raw_data.append("\nAGENDA: Sin eventos programados hoy.")
    except Exception as e:
        logger.warning(f"Morning calendar error: {e}")

    # Tareas
    try:
        tasks = google_tasks.list_tasks(False)
        if tasks and "No hay tareas" not in str(tasks):
            raw_data.append(f"\nTAREAS PENDIENTES:\n{tasks}")
    except Exception as e:
        logger.warning(f"Morning tasks error: {e}")

    # Noticias
    try:
        news = search_news()
        if news:
            raw_data.append(f"\nNOTICIAS RECIENTES:\n{news}")
    except Exception as e:
        logger.warning(f"Morning news error: {e}")

    # --- BIBLIOTECA: Libro aleatorio del dÃ­a ---
    book_data = ""
    try:
        from library import _get_conn
        conn = _get_conn()
        cur = conn.cursor()
        # Seleccionar un libro al azar que tenga contenido sustancial
        cur.execute("""
            SELECT title, author, category, tags, content
            FROM library
            WHERE word_count > 200
            ORDER BY RANDOM()
            LIMIT 1
        """)
        row = cur.fetchone()
        if row:
            b_title, b_author, b_category, b_tags, b_content = row
            b_tags_str = ', '.join(b_tags) if b_tags else ''
            # Limitar contenido para no explotar tokens
            if len(b_content) > 3000:
                b_content = b_content[:3000] + "\n[...]"
            book_data = f"""
LIBRO DEL DÃA (seleccionado al azar de la biblioteca de Pablo):
ðŸ“– TÃ­tulo: {b_title}
ðŸ‘¤ Autor: {b_author}
ðŸ“‚ CategorÃ­a: {b_category}
ðŸ·ï¸ Tags: {b_tags_str}

EXTRACTO:
{b_content}
"""
        cur.close()
        conn.close()
    except Exception as e:
        logger.warning(f"Morning library error: {e}")
        book_data = "\n(Biblioteca no disponible hoy)\n"

    context_block = "\n".join(raw_data)

    # --- 2. Prompt matutino para Claude ---
    morning_prompt = f"""Eres Claudette generando el RESUMEN MATUTINO de Pablo.

DATOS DISPONIBLES:
{context_block}

{book_data}

INSTRUCCIONES:
Genera un resumen matutino siguiendo EXACTAMENTE esta estructura:

1. **Saludo breve** â€” fecha y clima en una lÃ­nea

2. **Agenda del dÃ­a** â€” eventos si los hay, breve

3. **Tareas pendientes** â€” una sola menciÃ³n, sin repetir despuÃ©s

4. **3-4 noticias curadas** â€” SOLO geopolÃ­tica, economÃ­a/finanzas, filosofÃ­a, ciencia, tecnologÃ­a con impacto social, IA. EXCLUIR deportes, farÃ¡ndula, crÃ­menes, accidentes

5. **ðŸ“– RincÃ³n de la Biblioteca** â€” Esta es la secciÃ³n nueva y mÃ¡s importante. Con el LIBRO DEL DÃA:
   a) PresentÃ¡ el libro: tÃ­tulo, autor, una lÃ­nea sobre su tesis central
   b) ExtraÃ© UNA frase memorable o una idea poderosa del extracto â€” citala textual si la encontrÃ¡s
   c) ConectÃ¡ esa idea con algo actual: una noticia del dÃ­a, una tendencia, un dilema contemporÃ¡neo. Que no sea forzado â€” si la conexiÃ³n es obvia, mejor. Si no, hacÃ© una conexiÃ³n inesperada pero inteligente.
   d) LanzÃ¡ UNA pregunta provocadora que obligue a Pablo a pensar. No preguntas retÃ³ricas fÃ¡ciles. Preguntas que incomoden, que cuestionen, que abran una puerta. Ejemplos del nivel que busco:
      - "Si Byung-Chul Han dice que la transparencia es violencia, Â¿tu obsesiÃ³n por documentar todo en Obsidian es un acto de control o de resistencia?"
      - "Taleb dirÃ­a que tu portafolio de inversiones tiene fragilidad oculta. Â¿DÃ³nde estÃ¡ tu antifragilidad personal?"
      - "Jung habla del encuentro con la sombra. Â¿CuÃ¡l es la parte de vos que deliberadamente no querÃ©s ver hoy?"
   e) SugerÃ­ una conexiÃ³n con OTRO libro o autor de la biblioteca que cruce con el tema. "Esto conecta con lo que dice X en Y" â€” asÃ­ Pablo puede buscar despuÃ©s.

6. **Pensamiento del cierre** â€” UNA cita filosÃ³fica (puede ser del libro del dÃ­a o de otro autor: Marco Aurelio, Epicteto, SÃ©neca, Kierkegaard, Nietzsche, Heidegger, Han, Weil, Campbell, Jung). Breve, cortante, sin explicaciÃ³n.

REGLAS:
- Todo el resumen debe caber en UN mensaje de Telegram (mÃ¡ximo 4000 caracteres)
- Tono: directo, filosÃ³fico, sin condescendencia
- No uses "Â¡Excelente!" ni frases de chatbot
- La secciÃ³n de Biblioteca es la mÃ¡s valiosa â€” dedÃ­cale espacio y profundidad
- La pregunta provocadora debe ser PERSONAL, dirigida a Pablo, no genÃ©rica
- Si encontrÃ¡s frases memorables textuales en el extracto, usalas
- BuscÃ¡ lo incÃ³modo, lo que Pablo preferirÃ­a no pensar a las 6am
- Mejor una provocaciÃ³n que incomode que un cumplido intelectual
"""

    # --- 3. Llamar a Claude ---
    try:
        system = build_system_prompt(chat_id)
        response = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": morning_prompt}]
        )

        result = ""
        for block in response.content:
            if block.type == "text":
                result += block.text

        return result if result else "â˜€ï¸ Buenos dÃ­as, Pablo. No pude generar el resumen completo hoy."

    except Exception as e:
        logger.error(f"Morning Claude error: {e}")
        return f"â˜€ï¸ Buenos dÃ­as, Pablo.\n{context_block}\n\nâ€” Claudette"

