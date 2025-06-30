import os, logging
from dotenv import load_dotenv               
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, filters, ContextTypes,
)
from openai import OpenAI                    

# 1) загружаем переменные окружения
load_dotenv()
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# 2) настраиваем "клиента" DeepSeek
client = OpenAI(
    api_key = DEEPSEEK_API_KEY,
    base_url = "https://api.deepseek.com", 
)

logging.basicConfig(level=logging.INFO)       # чтобы видеть сообщения в терминале

# 3) /start
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Напиши мне что-нибудь 🙂")

# 4) чат-обработчик
async def chat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    question = update.message.text
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user",   "content": question},
        ],
    )
    await update.message.reply_text(response.choices[0].message.content)

# 5) «Собираем» приложение и запускаем long-polling
def main() -> None:
    app = (ApplicationBuilder()               
           .token(TELEGRAM_TOKEN)
           .build())

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    app.run_polling()                         # слушаем Telegram

if __name__ == "__main__":
    main()
