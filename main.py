from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import TELEGRAM_BOT_TOKEN
from brain import process_chat, conversation_history
from utils_security import restricted, get_youtube_transcript
import logging

# --- MENÚ VISUAL ---
async def show_menu(update, context):
    keyboard = [
        [InlineKeyboardButton("☀️ Buenos Días", callback_data='btn_morning'), InlineKeyboardButton("🧘 Modo Profundo", callback_data='btn_deep')],
        [InlineKeyboardButton("📰 Noticias", callback_data='btn_news'), InlineKeyboardButton("🎨 Crear Imagen", callback_data='btn_img')],
        [InlineKeyboardButton("🧠 Ver Memoria", callback_data='btn_mem'), InlineKeyboardButton("🗑️ Borrar Chat", callback_data='btn_clear')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🎛️ **Centro de Control Claudette**:", reply_markup=reply_markup)

async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    
    # Simular comandos escribiendo texto como si fuera el usuario
    if query.data == 'btn_morning': await handle_message(update, context, text_override="/buenosdias")
    elif query.data == 'btn_news': await handle_message(update, context, text_override="/noticias")
    elif query.data == 'btn_clear': 
        conversation_history[str(update.effective_chat.id)] = []
        await query.edit_message_text("🧹 Chat reiniciado.")

# --- HANDLERS PRINCIPALES ---
@restricted
async def handle_message(update, context, text_override=None):
    chat_id = update.effective_chat.id
    text = text_override or update.message.text
    
    # 1. Feedback visual (Escribiendo...)
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # 2. Check YouTube
    yt_transcript = get_youtube_transcript(text)
    if yt_transcript:
        text += f"\n\n[SISTEMA]: El usuario envió un video. {yt_transcript}"

    # 3. Procesar
    response = await process_chat(update, context, text)
    
    # 4. Enviar respuesta (si no es un comando de botón que ya editó)
    if not text_override:
        await update.message.reply_text(response)
    else:
        # Si vino de un botón, enviamos mensaje nuevo
        await context.bot.send_message(chat_id, response)

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", show_menu)) # /start muestra el menú
    app.add_handler(CommandHandler("menu", show_menu))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🚀 Claudette 2.0 (Segura y Modular) ONLINE")
    app.run_polling()

if __name__ == '__main__':
    main()
