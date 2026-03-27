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
# SERIALIZACIÃ“N (convierte objetos Anthropic → JSON)
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
        mode_instruction = "MODO: PROFUNDO ðŸ§˜â€â™€️. Analiza detalladamente."

    # Mini-calendario de referencia (próximos 7 días)
    from datetime import timedelta
    dias_semana = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
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
- Usa 'read_book_from_drive("INDICE_BIBLIOTECA")' para consultar qué hay disponible.
- Usa 'read_book_from_drive("[titulo]")' para leer un texto específico.
- Cuando analices noticias, decisiones o temas filosóficos, cruza con los escritos de Pablo si es relevante.
- NO cargues todo — solo busca cuando el contexto lo amerite.

=== LECTURA DE URLs ===
Puedes leer páginas web, tweets, artículos y links que Pablo comparta.
- Usa 'fetch_url' cuando Pablo mande una URL o link.
- Funciona con X/Twitter, noticias, blogs, y páginas públicas.
- Si Pablo manda un link sin contexto, léelo y resumilo.


=== REDDIT & HACKER NEWS ===
Tienes acceso a Reddit y Hacker News en tiempo real.
- Usa 'search_reddit' para buscar debates, opiniones, noticias en Reddit. Util para temas de tecnologia, trading, filosofia, cultura, etc.
- Usa 'fetch_hackernews_top' para ver las historias mas populares de HN. Mejor fuente tech que DuckDuckGo.
- Cuando Pablo mencione Reddit, HN, Hacker News, o pida noticias tech/startup, usa estos tools en vez de search_news.

=== ANALIZADOR PROFUNDO 8 MODOS ===
Usa 'analyze_content_deep' cuando Pablo pida analisis profundo de cualquier contenido.
ACTIVAR cuando Pablo diga: analiza esto, 8 modos, analisis profundo, que piensas de esto (con contenido extenso), dame el analisis completo.
TAMBIEN ACTIVAR cuando Pablo mande un link o transcript de YouTube y quiera reflexion, no solo resumen.
Los 8 modos son: modelos mentales, detector de humo, ideas de negocio, estructura narrativa, puntos ciegos, plan de accion, subtexto, conexion filosofica.

=== ESCUDO DE VERACIDAD (FAKE NEWS DETECTOR) ===
Usa 'verify_content' para verificar si una noticia, URL o claim es real o desinformacion.
ACTIVAR AUTOMATICAMENTE cuando Pablo:
- Comparta una URL de noticia y no haya pedido explicitamente que la leas (ofrece verificarla)
- Diga "es esto verdad?", "es fake?", "verifica esto", "es real?", "chequea esto"
- Mande algo que suene a noticia viral, sensacionalista o improbable
- Mande algo de X/Twitter sobre noticias o politica
El tool busca el mismo tema en 3 fuentes independientes (Reddit, HN, web) y da un veredicto:
VERIFICADO / NO CONFIRMADO / PROBABLE FAKE / INSUFICIENTE PARA JUZGAR

=== BUSQUEDA CRUZADA KB + BIBLIOTECA ===
Usa 'search_everything' como primera opcion cuando Pablo busque informacion que podria estar en sus notas O en algun libro.
PREFERIR sobre kb_search o search_library por separado cuando:
- Pablo pregunte sobre un tema intelectual (filosofia, trading, estoicismo, IA, etc.)
- Pablo diga "busca todo sobre X", "que tengo de X", "que notas y libros tengo de X"
- La busqueda podria estar en el vault de Obsidian O en la biblioteca
Retorna resultados de ambas fuentes en una sola respuesta.

=== GRAFO DE CONOCIMIENTO (D) ===
Usa 'kb_graph' para mostrar las conexiones entre notas del vault (via wikilinks de Obsidian).
USAR cuando Pablo diga 'que notas se relacionan con X', 'muestra las conexiones de esta nota', 'como esta conectado X en el vault'.
Retorna: notas que esta nota enlaza + notas que la enlazan.

=== MODELOS MENTALES TRACKER (E) ===
REGISTRA SILENCIOSAMENTE con 'track_mental_model' cada vez que apliques uno de los 216 modelos mentales.
NO lo anuncias, simplemente lo llamas en segundo plano cuando uses un modelo.
Ejemplos: si aplicas Navaja de Occam, llama track_mental_model(model_name='Navaja de Occam', context='...', project='General').
Usa 'mental_models_stats' cuando Pablo pida ver que modelos usamos mas, su perfil de pensamiento, o en /progreso.

=== GEOLOCALIZACIÓN INTELIGENTE (G) ===
Cuando Pablo mencione estar en un lugar ('estoy en Madrid', 'llegue a Tokyo', 'voy a Guadalupe'):
- El sistema ya detecta el texto y obtiene el clima automaticamente
- Tu TAREA: usar esa info de ubicacion para personalizar la respuesta (clima, zona horaria, sugerencias locales)
- Usa 'get_weather_by_city' para obtener clima de cualquier ciudad por nombre
- Si Pablo pregunta el clima de una ciudad sin dar GPS, usa este tool

=== SINTESIS SEMANAL (J) ===
Cada domingo a las 6pm CR, Claudette envia automaticamente la sintesis semanal.
Pablo tambien puede pedirla con /sintesis en cualquier momento.
La sintesis integra: vault reciente, modelos mentales aplicados, contexto global, memoria persistente.

=== GENERACIÃ“N DE DOCUMENTOS ===
Puedes generar documentos largos (.docx Word o .md Markdown) que se envían como archivo descargable.
- Usa 'generate_document' cuando Pablo pida reportes, bitácoras, ensayos, compilaciones o cualquier texto extenso.
- El contenido del documento NO tiene el límite de 4000 chars de Telegram — puede ser tan largo como necesites.
- Usa formato Markdown en el contenido (# títulos, ## secciones, **negrita**, *cursiva*, listas, citas con >).
- Se convierte automáticamente en un Word profesional con tipografía Georgia y márgenes elegantes.

Puedes generar hojas de cálculo Excel (.xlsx) con formato profesional.
- Usa 'generate_spreadsheet' cuando Pablo pida tablas, comparativas, presupuestos, tracking o datos tabulares.
- Soporta múltiples hojas, encabezados formateados, filtros automáticos.
- Los datos se pasan como headers + rows estructurados.

=== BIBLIOTECA PERSONAL (2100+ LIBROS) ===
Pablo tiene una biblioteca indexada de ~2100 libros con extractos sustanciales.
- Usa 'search_library' para buscar por tema, concepto o palabra clave (ej: "nihilismo", "atención", "democracia digital").
- Usa 'search_library_by_author' para ver todos los libros de un autor (ej: "Byung-Chul Han", "Jung", "Wittgenstein").
- Usa 'search_library_by_tag' para buscar por etiqueta (ej: "zen", "posestructuralismo", "capitalismo-vigilancia").
- Usa 'get_book_detail' para leer el extracto completo de un libro específico.
- Usa 'library_stats' para dar estadísticas generales.
- IMPORTANTE: Cuando Pablo haga preguntas filosóficas, existenciales, o sobre cualquier tema intelectual, BUSCA PRIMERO en la biblioteca antes de responder genéricamente. Sus extractos son profundos y relevantes.
- Cruza información entre libros cuando sea pertinente (ej: conectar a Han con Heidegger, o a Jung con Weil).

=== CONTEXTO ===
ðŸ“… {now.strftime("%A %d-%m-%Y %H:%M")} (hora Costa Rica, UTC-6)
ðŸ“ {loc['name']} (GPS: {loc['lat']}, {loc['lng']})

ðŸ“† CALENDARIO DE REFERENCIA (NO te confundas de fecha):
{week_calendar}
⚠️ IMPORTANTE: Cuando Pablo diga un día de la semana, usa EXACTAMENTE la fecha de arriba. NO calcules fechas mentalmente.

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
                logger.info(f"ðŸ“ Recuperado de memoria: {saved_lat}, {saved_lng}")
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

        # Detectar si el mensaje pide generación de documentos → más tokens
        doc_keywords = ['documento', 'reporte', 'informe', 'bitácora', 'bitacora',
                        'compila', 'genera un doc', 'genera un archivo', 'word',
                        'ensayo largo', 'resumen extenso', 'docx', 'exporta',
                        'excel', 'xlsx', 'spreadsheet', 'hoja de cálculo', 'tabla comparativa']
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

            # Si se usó generate_document o generate_spreadsheet, asegurar tokens altos
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
            # Agotó las rondas → extraer lo que haya
            for block in response.content:
                if block.type == "text":
                    final_text += block.text

        if not final_text:
            final_text = "✅ He procesado la solicitud."


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
    de la biblioteca para provocación intelectual.
    """
    import google_calendar
    import google_tasks
    from tools_registry import get_weather, search_news, user_locations
    from config import DEFAULT_LOCATION
    try:
        from midas_monitor import generate_midas_report
        _midas_available = True
    except Exception:
        _midas_available = False

    tz = pytz.timezone('America/Costa_Rica')
    now = datetime.now(tz)

    # --- 1. Recolectar datos brutos ---
    raw_data = []
    _dias = ['lunes','martes','miercoles','jueves','viernes','sabado','domingo']
    _meses = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
    _fecha_es = f"{_dias[now.weekday()]} {now.day} de {_meses[now.month-1]} de {now.year}"
    raw_data.append(f"FECHA: {_fecha_es} — {now.strftime('%H:%M')} hora Costa Rica")

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
            raw_data.append(f"\nAGENDA DEL DÍA:\n{events}")
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

    # Noticias enriquecidas: RSS titulos + contenido real de top articulos + HN
    try:
        from tools_registry import fetch_url, fetch_hackernews_top
        news_raw = search_news()
        if news_raw and len(news_raw) > 100:
            # Extraer URLs del output RSS para leer contenido real
            urls_found = re.findall(r'URL: (https?://[^\s\n]+)', news_raw)
            articles_content = []
            for url in urls_found[:3]:  # Leer max 3 articulos para no demorar
                try:
                    art = fetch_url(url)
                    if art and len(art) > 200:
                        # Truncar a 800 chars por articulo para no explotar tokens
                        articles_content.append(f"ARTICULO ({url}):\n{art[:800]}\n[...]")
                except Exception:
                    continue

            # HN para perspectiva tech
            hn_data = ""
            try:
                hn_data = fetch_hackernews_top(limit=5, min_points=100)
            except Exception:
                pass

            news_block = f"TITULARES RSS:\n{news_raw}"
            if articles_content:
                news_block += "\n\nCONTENIDO DE ARTICULOS (para que no inventes - usa esto):\n" + "\n\n".join(articles_content)
            if hn_data:
                news_block += f"\n\nHACKER NEWS (perspectiva tech/IA):\n{hn_data}"

            raw_data.append(f"\nNOTICIAS ENRIQUECIDAS:\n{news_block}")
        else:
            raw_data.append("\nNOTICIAS: No disponibles hoy (servicio temporalmente limitado). No inventes noticias.")
    except Exception as e:
        logger.warning(f"Morning news error: {e}")
        raw_data.append("\nNOTICIAS: No disponibles hoy. No inventes noticias.")

    # --- BIBLIOTECA: Libro aleatorio del día ---
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
LIBRO DEL DÍA (seleccionado al azar de la biblioteca de Pablo):
📖 Título: {b_title}
👤 Autor: {b_author}
📂 Categoría: {b_category}
🏷️ Tags: {b_tags_str}

EXTRACTO:
{b_content}
"""
        cur.close()
        conn.close()
    except Exception as e:
        logger.warning(f"Morning library error: {e}")
        book_data = "\n(Biblioteca no disponible hoy)\n"

    if _midas_available:
        try:
            midas_report = generate_midas_report()
            if midas_report:
                raw_data.append("\nMIDAS MONITOR:\n" + midas_report)
        except Exception as e:
            logger.warning("Morning midas error: " + str(e))

    context_block = "\n".join(raw_data)

    # --- 2. Prompt matutino para Claude ---
    morning_prompt = f"""Eres Claudette generando el RESUMEN MATUTINO de Pablo.

DATOS DISPONIBLES:
{context_block}

{book_data}

INSTRUCCIONES:
Genera un resumen matutino siguiendo EXACTAMENTE esta estructura:

1. **Saludo breve** — fecha y clima en una línea

2. **Agenda del día** — eventos si los hay, breve

3. **Tareas pendientes** — una sola mención, sin repetir después

4. **Midas Monitor** (SOLO si hay datos de MIDAS MONITOR):
   - Estado bot, PnL dia y semana, top 2 ganadoras y perdedoras, alerta si drawdown severo. Maximo 8 lineas.

5. **3-4 noticias curadas** — SOLO geopolitica, economia/finanzas, filosofia, ciencia, tecnologia, IA.
   EXCLUIR: deportes, farandula, crimenes, accidentes
   Para cada noticia:
   - **Titulo** + fuente (URL si la tienes en los datos)
   - 2-3 oraciones de contexto real usando el CONTENIDO DE ARTICULOS disponible — no inventes
   - Un angulo no obvio: que no dice la noticia, que implica, o perspectiva de HN/Reddit si hay


5. **📖 Rincón de la Biblioteca** — Esta es la sección nueva y más importante. Con el LIBRO DEL DÍA:
   a) Presentá el libro: título, autor, una línea sobre su tesis central
   b) Extraé UNA frase memorable o una idea poderosa del extracto — citala textual si la encontrás
   c) Conectá esa idea con algo actual: una noticia del día, una tendencia, un dilema contemporáneo. Que no sea forzado — si la conexión es obvia, mejor. Si no, hacé una conexión inesperada pero inteligente.
   d) Lanzá UNA pregunta provocadora que obligue a Pablo a pensar. No preguntas retóricas fáciles. Preguntas que incomoden, que cuestionen, que abran una puerta. Ejemplos del nivel que busco:
      - "Si Byung-Chul Han dice que la transparencia es violencia, ¿tu obsesión por documentar todo en Obsidian es un acto de control o de resistencia?"
      - "Taleb diría que tu portafolio de inversiones tiene fragilidad oculta. ¿Dónde está tu antifragilidad personal?"
      - "Jung habla del encuentro con la sombra. ¿Cuál es la parte de vos que deliberadamente no querés ver hoy?"
   e) Sugerí una conexión con OTRO libro o autor de la biblioteca que cruce con el tema. "Esto conecta con lo que dice X en Y" — así Pablo puede buscar después.

6. **Pensamiento del cierre** — UNA cita filosófica (puede ser del libro del día o de otro autor: Marco Aurelio, Epicteto, Séneca, Kierkegaard, Nietzsche, Heidegger, Han, Weil, Campbell, Jung). Breve, cortante, sin explicación.

REGLAS:
- CRITICO: Si no hay noticias disponibles, di "Sin noticias disponibles hoy" — NO inventes, NO rellenes con filosofia
- CRITICO: Usa EXACTAMENTE la fecha que aparece en FECHA: — no la cambies ni la recalcules
- CRITICO: La seccion Midas Monitor es OBLIGATORIA si hay datos de MIDAS MONITOR en los datos
- El resumen puede ocupar varios mensajes — no truncues secciones para ahorrar espacio, incluye TODO
- Tono: directo, filosófico, sin condescendencia
- No uses "¡Excelente!" ni frases de chatbot
- La sección de Biblioteca es la más valiosa — dedícale espacio y profundidad
- La pregunta provocadora debe ser PERSONAL, dirigida a Pablo, no genérica
- Si encontrás frases memorables textuales en el extracto, usalas
- Buscá lo incómodo, lo que Pablo preferiría no pensar a las 6am
- Mejor una provocación que incomode que un cumplido intelectual
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

        return result if result else "☀️ Buenos días, Pablo. No pude generar el resumen completo hoy."

    except Exception as e:
        logger.error(f"Morning Claude error: {e}")
        return f"☀️ Buenos días, Pablo.\n{context_block}\n\n— Claudette"



# =====================================================
# SINTESIS SEMANAL (J)
# =====================================================

async def generate_weekly_synthesis(chat_id: int) -> str:
    """
    Genera la sintesis semanal de aprendizajes, decisiones, modelos mentales
    e insights. Se envia domingos a las 6pm CR o bajo demanda con /sintesis.
    """
    tz = pytz.timezone('America/Costa_Rica')
    now = datetime.now(tz)

    kb_recent = ""
    mm_stats = ""
    news_context = ""

    try:
        from knowledge_base import kb_list
        kb_recent = kb_list(mode='recent', limit=8)
    except Exception:
        pass

    try:
        from knowledge_base import mental_models_stats
        mm_stats = mental_models_stats(top_n=5)
    except Exception:
        pass

    try:
        from tools_registry import search_news
        news_context = search_news()[:1200]
    except Exception:
        pass

    all_facts = get_all_facts() or {}
    memory_text = chr(10).join(
        "- " + k + ": " + v for k, v in all_facts.items() if not k.startswith("System_")
    )[:600]

    synthesis_prompt = f"""Genera la SINTESIS SEMANAL de Pablo. Es momento de integrar la semana.

DATOS DISPONIBLES:

=== NOTAS RECIENTES EN EL VAULT ===
{kb_recent or 'Sin actividad en el vault esta semana.'}

=== MODELOS MENTALES APLICADOS ESTA SEMANA ===
{mm_stats or 'Sin registros.'}

=== NOTICIAS DEL MUNDO ===
{news_context or 'Sin datos.'}

=== MEMORIA PERSISTENTE ===
{memory_text or 'Sin datos.'}

Genera la sintesis en este formato:

## Sintesis Semanal --- {now.strftime('%d/%m/%Y')}

### Temas centrales de la semana
[2-3 temas que dominaron la actividad de Pablo. Basa esto en los datos.]

### Insights clave
[Los 3 aprendizajes mas importantes que emergen de los datos.]

### Conexiones no obvias
[1-2 conexiones entre ideas de la semana que quizas no se vieron en el momento.]

### Modelos mentales dominantes
[Patrones de pensamiento aplicados. Si no hay registros, sugiere cuales dado el contexto.]

### El mundo esta semana
[1-2 tendencias globales relevantes para Pablo y sus proyectos.]

### Pregunta para la proxima semana
[UNA pregunta poderosa y personal que emerge de la sintesis.]

REGLAS: basa todo en los datos, tono reflexivo y directo, si hay pocos datos dilo, la pregunta debe ser personal e incomoda."""

    try:
        system = build_system_prompt(chat_id)
        response = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=2000,
            system=system,
            messages=[{"role": "user", "content": synthesis_prompt}]
        )
        result = "".join(b.text for b in response.content if b.type == "text")
        return result if result else "No se pudo generar la sintesis semanal."
    except Exception as e:
        logger.error(f"generate_weekly_synthesis error: {e}")
        return f"Error generando sintesis: {e}"
