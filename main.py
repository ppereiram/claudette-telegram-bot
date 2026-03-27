"""
Claudette Bot - Entry Point Modular.
Todos los handlers: texto, voz, foto, ubicaciÃ³n, comandos, recordatorios.
"""

import os
import io
import re
import base64
import tempfile
import pytz
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

from config import (
    TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE_ID, OWNER_CHAT_ID, DEFAULT_LOCATION, logger
)
from brain import process_chat, conversation_history, user_modes, build_system_prompt, generate_morning_summary
from tools_registry import (
    user_locations, get_weather, search_news, search_web_google
)
from utils_security import restricted, get_youtube_transcript
from memory_manager import get_all_facts, save_fact, get_fact, setup_database

# --- Inicializar base de datos ---
setup_database()

# --- Clients opcionales ---
openai_client = None
elevenlabs_client = None

if OPENAI_API_KEY:
    from openai import OpenAI
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

if ELEVENLABS_API_KEY:
    from elevenlabs.client import ElevenLabs
    elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# Google services ya no necesarios aquÃ­ â€” brain.py los importa para el resumen matutino


# =====================================================
# MENÃš VISUAL
# =====================================================

async def show_menu(update, context):
    keyboard = [
        [
            InlineKeyboardButton("â˜€ï¸ Buenos DÃ­as", callback_data='btn_morning'),
            InlineKeyboardButton("ðŸ§˜ Modo Profundo", callback_data='btn_deep'),
        ],
        [
            InlineKeyboardButton("ðŸ“° Noticias", callback_data='btn_news'),
            InlineKeyboardButton("ðŸŽ¨ Crear Imagen", callback_data='btn_img'),
        ],
        [
            InlineKeyboardButton("ðŸ§  Ver Memoria", callback_data='btn_mem'),
            InlineKeyboardButton("ðŸ—‘ï¸ Borrar Chat", callback_data='btn_clear'),
        ],
        [
            InlineKeyboardButton("âš¡ Modo Normal", callback_data='btn_normal'),
            InlineKeyboardButton("ðŸ“ Mi UbicaciÃ³n", callback_data='btn_location'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("ðŸŽ›ï¸ **Centro de Control Claudette**:", reply_markup=reply_markup)


async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    if query.data == 'btn_morning':
        await query.edit_message_text("â˜• Preparando tu resumen matutino...")
        try:
            summary = await generate_morning_summary(chat_id)
            await send_long_message_raw(context, chat_id, summary)
        except Exception as e:
            await context.bot.send_message(chat_id, f"âš ï¸ Error: {e}")

    elif query.data == 'btn_news':
        await query.edit_message_text("ðŸ“° Buscando noticias...")
        try:
            news = search_news()
            if len(news) > 4000:
                news = news[:4000] + "\n\n[... Truncado.]"
            await context.bot.send_message(chat_id, news)
        except Exception as e:
            await context.bot.send_message(chat_id, f"âš ï¸ Error: {e}")

    elif query.data == 'btn_deep':
        user_modes[chat_id] = "profundo"
        await query.edit_message_text("ðŸ§˜â€â™€ï¸ Modo Profundo activado.")

    elif query.data == 'btn_normal':
        user_modes[chat_id] = "normal"
        await query.edit_message_text("âš¡ Modo Normal activado.")

    elif query.data == 'btn_clear':
        conversation_history[chat_id] = []
        await query.edit_message_text("ðŸ§¹ Chat reiniciado. (Memoria persistente intacta)")

    elif query.data == 'btn_mem':
        all_facts = get_all_facts() or {}
        lines = [f"â€¢ {k}: {v}" for k, v in all_facts.items() if not k.startswith("System_Location")]
        if lines:
            memory_text = "ðŸ§  Lo que recuerdo de ti:\n\n" + "\n".join(lines)
            if len(memory_text) > 4000:
                memory_text = memory_text[:4000] + "\n\n[... Truncado]"
        else:
            memory_text = "ðŸ§  Memoria vacÃ­a. Dime cosas y las recordarÃ©."
        await query.edit_message_text(memory_text)

    elif query.data == 'btn_location':
        loc = user_locations.get(chat_id, DEFAULT_LOCATION)
        await query.edit_message_text(f"ðŸ“ {loc['name']} ({loc['lat']}, {loc['lng']})")

    elif query.data == 'btn_img':
        await query.edit_message_text("ðŸŽ¨ EscrÃ­beme quÃ© imagen quieres que genere.")


# =====================================================
# =====================================================
# RECORDATORIOS PROACTIVOS
# =====================================================

async def check_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Resumen matutino inteligente â€” UNA VEZ al dÃ­a a las 9am CR. Pasa por Claude."""
    if not OWNER_CHAT_ID:
        return

    chat_id = int(OWNER_CHAT_ID)

    try:
        summary = await generate_morning_summary(chat_id)
        await send_long_message_raw(context, chat_id, summary)
        logger.info(f"â˜€ï¸ Resumen matutino inteligente enviado a {chat_id}")
    except Exception as e:
        logger.error(f"Error resumen matutino: {e}")


# =====================================================
# HANDLERS PRINCIPALES
# =====================================================

@restricted
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler de mensajes de texto."""
    chat_id = update.effective_chat.id
    text = update.message.text

    # Feedback visual
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # Detectar solicitud de boletin matutino
    text_lower = text.lower()
    morning_triggers = ["resumen matutino", "boletin matutino", "buenos dias claudette",
                        "genera el boletin", "boletin del dia", "genera el resumen"]
    if any(t in text_lower for t in morning_triggers):
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        summary = await generate_morning_summary(chat_id)
        await send_long_message(update, summary)
        return

    # Detectar YouTube
    yt_transcript = get_youtube_transcript(text)
    if yt_transcript:
        text += f"\n\n[SISTEMA]: El usuario enviÃ³ un video. {yt_transcript}"

    # Procesar con brain
    response = await process_chat(update, context, text)

    # Enviar respuesta (split si es muy larga para Telegram)
    await send_long_message(update, response)


@restricted
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler de notas de voz â†’ Whisper â†’ Claude â†’ ElevenLabs."""
    if not openai_client:
        return await update.message.reply_text("Whisper no configurado.")
    try:
        file = await context.bot.get_file(update.message.voice.file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            await file.download_to_drive(f.name)
            path = f.name

        with open(path, "rb") as audio_file:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1", file=audio_file
            ).text
        os.unlink(path)

        await update.message.reply_text(f"ðŸŽ¤ {transcript}")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        response = await process_chat(update, context, transcript)
        await send_long_message(update, response)

        # Respuesta por voz
        if elevenlabs_client:
            try:
                text_clean = re.sub(r'[^\w\s,.?Â¡!]', '', response)
                audio = elevenlabs_client.text_to_speech.convert(
                    text=text_clean,
                    voice_id=ELEVENLABS_VOICE_ID,
                    model_id="eleven_multilingual_v2"
                )
                await update.effective_message.reply_voice(voice=b"".join(audio))
            except Exception as e:
                logger.error(f"âŒ ElevenLabs Error: {e}")

    except Exception as e:
        await update.message.reply_text(f"Error voz: {e}")


@restricted
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler de fotos â†’ visiÃ³n Claude."""
    photo_file = await update.message.photo[-1].get_file()
    with io.BytesIO() as f:
        await photo_file.download_to_memory(out=f)
        image_data = base64.b64encode(f.getvalue()).decode("utf-8")

    caption = update.message.caption or "Analiza esta imagen."

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    response = await process_chat(update, context, caption, image_data=image_data)
    await send_long_message(update, response)


@restricted
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler de documentos â€” extrae contenido de archivos enviados por Telegram."""
    doc = update.message.document
    if not doc:
        return

    chat_id = update.effective_chat.id
    file_name = doc.file_name or "archivo"
    file_size = doc.file_size or 0
    caption = update.message.caption or ""

    # LÃ­mite de tamaÃ±o: 20MB (Telegram permite hasta 20MB para bots)
    if file_size > 20 * 1024 * 1024:
        await update.message.reply_text("âš ï¸ Archivo demasiado grande (mÃ¡x 20MB).")
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # Determinar tipo y extensiÃ³n
    lower_name = file_name.lower()
    supported_extensions = ('.txt', '.md', '.csv', '.json', '.py', '.js', '.html',
                            '.pdf', '.docx', '.xlsx', '.xls')

    if not any(lower_name.endswith(ext) for ext in supported_extensions):
        # Tipo no soportado â€” pasar solo el nombre
        msg_text = f"El usuario enviÃ³ un archivo: {file_name}"
        if caption:
            msg_text += f"\nMensaje: {caption}"
        msg_text += "\n(Formato no soportado para lectura directa. SugerÃ­ subirlo a Drive.)"
        response = await process_chat(update, context, msg_text)
        await send_long_message(update, response)
        return

    try:
        # Descargar archivo
        tg_file = await context.bot.get_file(doc.file_id)
        file_bytes = io.BytesIO()
        await tg_file.download_to_memory(out=file_bytes)
        file_bytes.seek(0)

        extracted_text = ""

        # --- TEXT-BASED: .txt, .md, .csv, .json, .py, .js, .html ---
        if any(lower_name.endswith(ext) for ext in ('.txt', '.md', '.csv', '.json', '.py', '.js', '.html')):
            try:
                extracted_text = file_bytes.read().decode('utf-8', errors='ignore')
            except Exception:
                extracted_text = file_bytes.read().decode('latin-1', errors='ignore')

        # --- PDF ---
        elif lower_name.endswith('.pdf'):
            try:
                import pypdf
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                    tmp.write(file_bytes.read())
                    tmp_path = tmp.name
                reader = pypdf.PdfReader(tmp_path)
                pages = min(len(reader.pages), 50)
                extracted_text = "\n".join(
                    reader.pages[i].extract_text() or "" for i in range(pages)
                )
                os.unlink(tmp_path)
            except Exception as e:
                extracted_text = f"(Error leyendo PDF: {e})"

        # --- DOCX ---
        elif lower_name.endswith('.docx'):
            try:
                from docx import Document as DocxDoc
                with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
                    tmp.write(file_bytes.read())
                    tmp_path = tmp.name
                doc_obj = DocxDoc(tmp_path)
                extracted_text = "\n".join(p.text for p in doc_obj.paragraphs if p.text.strip())
                os.unlink(tmp_path)
            except Exception as e:
                extracted_text = f"(Error leyendo DOCX: {e})"

        # --- XLSX / XLS ---
        elif lower_name.endswith(('.xlsx', '.xls')):
            try:
                import openpyxl
                with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                    tmp.write(file_bytes.read())
                    tmp_path = tmp.name
                wb = openpyxl.load_workbook(tmp_path, read_only=True, data_only=True)
                sheets_text = []
                for sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    rows = []
                    for row in ws.iter_rows(values_only=True):
                        row_str = " | ".join(str(c) if c is not None else "" for c in row)
                        if row_str.strip(" |"):
                            rows.append(row_str)
                    if rows:
                        sheets_text.append(f"--- Hoja: {sheet_name} ---\n" + "\n".join(rows))
                extracted_text = "\n\n".join(sheets_text)
                wb.close()
                os.unlink(tmp_path)
            except Exception as e:
                extracted_text = f"(Error leyendo Excel: {e})"

        # Truncar si es muy largo
        if len(extracted_text) > 12000:
            extracted_text = extracted_text[:12000] + "\n\n[... Contenido truncado. PedÃ­ una secciÃ³n especÃ­fica.]"

        # Construir mensaje para Claude con el contenido del archivo
        msg_text = f"ðŸ“Ž El usuario enviÃ³ el archivo '{file_name}'.\n"
        if caption:
            msg_text += f"Mensaje: {caption}\n"
        msg_text += f"\n--- CONTENIDO DEL ARCHIVO ---\n{extracted_text}\n--- FIN DEL ARCHIVO ---"

        response = await process_chat(update, context, msg_text)
        await send_long_message(update, response)

    except Exception as e:
        logger.error(f"Document handler error: {e}", exc_info=True)
        await update.message.reply_text(f"âš ï¸ Error procesando archivo: {e}")


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler de ubicaciÃ³n compartida."""
    msg = update.effective_message
    if not msg or not msg.location:
        return

    lat, lng = msg.location.latitude, msg.location.longitude
    chat_id = update.effective_chat.id

    user_locations[chat_id] = {"lat": lat, "lng": lng, "name": "UbicaciÃ³n Telegram"}

    try:
        save_fact(f"System_Location_Lat_{chat_id}", str(lat))
        save_fact(f"System_Location_Lng_{chat_id}", str(lng))
        logger.info(f"ðŸ’¾ UbicaciÃ³n guardada: {lat}, {lng}")
    except Exception as e:
        logger.error(f"Error guardando ubicaciÃ³n: {e}")

    if not update.edited_message:
        await msg.reply_text("ðŸ“ UbicaciÃ³n actualizada.")


# =====================================================
# COMANDOS DIRECTOS
# =====================================================

@restricted
async def cmd_buenos_dias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text("â˜• Preparando tu resumen matutino...")
    try:
        summary = await generate_morning_summary(chat_id)
        await send_long_message(update, summary)
    except Exception as e:
        await update.message.reply_text(f"âš ï¸ Error: {e}")


@restricted
async def cmd_noticias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ðŸ“° Buscando noticias...")
    try:
        news = search_news()
        if len(news) > 4000:
            news = news[:4000] + "\n\n[... Truncado.]"
        await update.message.reply_text(news)
    except Exception as e:
        await update.message.reply_text(f"âš ï¸ Error: {e}")


@restricted
async def cmd_profundo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_modes[update.effective_chat.id] = "profundo"
    await update.message.reply_text("ðŸ§˜â€â™€ï¸ Modo Profundo activado.")


@restricted
async def cmd_normal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_modes[update.effective_chat.id] = "normal"
    await update.message.reply_text("âš¡ Modo Normal activado.")


@restricted
async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conversation_history[update.effective_chat.id] = []
    await update.message.reply_text("ðŸ§¹ Memoria de conversaciÃ³n borrada. (Memoria persistente intacta)")


@restricted
async def cmd_memoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_facts = get_all_facts() or {}
    lines = [f"â€¢ {k}: {v}" for k, v in all_facts.items() if not k.startswith("System_Location")]
    if lines:
        memory_text = "ðŸ§  Lo que recuerdo de ti:\n\n" + "\n".join(lines)
        if len(memory_text) > 4000:
            memory_text = memory_text[:4000] + "\n\n[... Truncado]"
    else:
        memory_text = "ðŸ§  Memoria vacÃ­a. Dime cosas y las recordarÃ©."
    await update.message.reply_text(memory_text)


@restricted
async def cmd_progreso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Panel de progreso: KB stats + Biblioteca + insights guardados."""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    lines = ["=== PANEL DE PROGRESO - CLAUDETTE ===\n"]

    # KB stats (Vault Obsidian)
    try:
        from knowledge_base import kb_list
        lines.append(kb_list(mode="stats"))
    except Exception as e:
        lines.append(f"KB: error ({e})")

    # Tags mas usados (top 10)
    try:
        from knowledge_base import kb_list
        lines.append("\n" + kb_list(mode="tags", limit=10))
    except Exception:
        pass

    # Biblioteca stats
    try:
        from library import get_library_stats
        lines.append("\n" + get_library_stats())
    except Exception as e:
        lines.append(f"\nBiblioteca: error ({e})")

    # Memoria rapida (hechos guardados)
    try:
        all_facts = get_all_facts() or {}
        fact_count = len([k for k in all_facts if not k.startswith("System_")])
        lines.append(f"\nMemoria rapida: {fact_count} hechos guardados")
    except Exception:
        pass

    # Ultimas notas indexadas
    try:
        from knowledge_base import kb_list
        lines.append("\n" + kb_list(mode="recent", limit=5))
    except Exception:
        pass

    await send_long_message(update, "\n".join(lines))


# =====================================================
# UTILIDADES
# =====================================================

async def send_long_message(update, text, max_length=4000):
    """EnvÃ­a mensajes largos dividiÃ©ndolos si superan el lÃ­mite de Telegram."""
    if len(text) <= max_length:
        await update.effective_message.reply_text(text)
        return

    # Dividir en chunks respetando saltos de lÃ­nea
    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break
        # Buscar un buen punto de corte
        cut = text.rfind('\n', 0, max_length)
        if cut == -1:
            cut = max_length
        chunks.append(text[:cut])
        text = text[cut:].lstrip('\n')

    for chunk in chunks:
        if chunk.strip():
            await update.effective_message.reply_text(chunk)


async def send_long_message_raw(context, chat_id, text, max_length=4000):
    """EnvÃ­a mensajes largos usando context.bot directamente (sin Update)."""
    if len(text) <= max_length:
        await context.bot.send_message(chat_id=chat_id, text=text)
        return

    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break
        cut = text.rfind('\n', 0, max_length)
        if cut == -1:
            cut = max_length
        chunks.append(text[:cut])
        text = text[cut:].lstrip('\n')

    for chunk in chunks:
        if chunk.strip():
            await context.bot.send_message(chat_id=chat_id, text=chunk)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception:", exc_info=context.error)


# =====================================================
# MAIN
# =====================================================

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start", show_menu))
    app.add_handler(CommandHandler("menu", show_menu))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("profundo", cmd_profundo))
    app.add_handler(CommandHandler("normal", cmd_normal))
    app.add_handler(CommandHandler("buenosdias", cmd_buenos_dias))
    app.add_handler(CommandHandler("noticias", cmd_noticias))
    app.add_handler(CommandHandler("memoria", cmd_memoria))
    app.add_handler(CommandHandler("progreso", cmd_progreso))

    # Botones inline
    app.add_handler(CallbackQueryHandler(button_handler))

    # Mensajes
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))

    # Recordatorio matutino â€” UNA SOLA VEZ al dÃ­a a las 6:00 AM Costa Rica
    try:
        if OWNER_CHAT_ID and app.job_queue:
            from datetime import time as dt_time
            # 6:00 AM Costa Rica = 12:00 UTC (GMT-6)
            morning_time = dt_time(hour=12, minute=0, second=0)
            app.job_queue.run_daily(
                check_reminders,
                time=morning_time,
                name="morning_reminder"
            )
            logger.info(f"ðŸ”” Recordatorio matutino (6:00 AM CR) activado para chat_id: {OWNER_CHAT_ID}")
        else:
            logger.warning("âš ï¸ Recordatorios desactivados (falta OWNER_CHAT_ID o job-queue).")
    except Exception as e:
        logger.warning(f"âš ï¸ Recordatorios no disponibles: {e}")

    app.add_error_handler(error_handler)
    print("ðŸš€ Claudette 2.0 (Modular + YouTube + Google Services) ONLINE")
    app.run_polling()


if __name__ == '__main__':
    main()

