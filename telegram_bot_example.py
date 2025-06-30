#!/usr/bin/env python3
"""
Простой пример Telegram бота
Замените YOUR_BOT_TOKEN на токен вашего бота
"""

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Замените на токен вашего бота
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправить сообщение когда выдана команда /start."""
    user = update.effective_user
    await update.message.reply_html(
        f"Привет {user.mention_html()}!\n"
        f"Я простой бот. Отправь мне любое сообщение!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправить сообщение когда выдана команда /help."""
    await update.message.reply_text("Помощь! /start - начать, /help - эта помощь")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Повторить сообщение пользователя."""
    await update.message.reply_text(f"Ты написал: {update.message.text}")

def main() -> None:
    """Запустить бота."""
    # Создать приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавить обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Обработчик обычных сообщений (не команд)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Запустить бота
    print("Бот запущен! Нажмите Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
