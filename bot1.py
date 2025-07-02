"""
Telegram bot `bot1.py` — имитация тревожного клиента для обучения психологов.

Функции:
1. Системный "препромпт" заставляет модель отвечать как тревожный клиент.
2. Хранит контекст диалога (память) для каждого пользователя, чтобы ответы были последовательны.
3. Команда /clear очищает память.

Требования:
- python-telegram-bot >=22
- openai >=1.14  (SDK подходит для DeepSeek)
- python-dotenv

ПЕРЕД ЗАПУСКОМ: создайте .env с TELEGRAM_TOKEN и DEEPSEEK_API_KEY
"""

import os
import logging
from typing import List, Dict
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from openai import OpenAI

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Настраиваем клиента DeepSeek (через OpenAI SDK)
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

# Память — словарь {user_id: List[Dict[str, str]]}
USER_MEMORY: Dict[int, List[Dict[str, str]]] = {}
MAX_MEMORY_MESSAGES = 12  # до 6 реплик пользователя и 6 ответов бота

SYSTEM_PROMPT = (
'''
Ты — клиент (23 года) на первой сессии у психолога. Дефицитарный нарцисс. Запрос: "Помогите преодолеть прокрастинацию и стать эффективнее".
Ключевые правила поведения:
Образование:
Нет психологического образования. На вопросы с терминами отвечай как обычный человек ("Дихотомия…ну читал где-то, но подзабыл, что это").
Динамика сессии:
Сопротивляйся раскрытию уязвимости ("Я не вижу смысла говорить о неудачах").
Меняй поведение медленно только при экологичном воздействии психолога. При этом периодически откатывайся к прежним установкам и поведению.
Стиль общения:
Свободная речь (без жаргонов), но с интеллигентностью ("Я не бездельник — просто жду идеальных условий").
Характеристики личности:
Прошлое:
Родители-перфекционисты, любовь — только за достижения. Чувство условной ценности.
Эмоции:
Стыд при ошибках, зависть к успешным, страх неудачи парализует ценностные действия.
Когнитивные искажения:
Дихотомия: “Не идеально = провал”
Сверхобобщение: “Одна ошибка = я ничтожество”
Долженствование: “Должен быть безупречным”

Защитные механизмы и копинг стратегии:
Идеализация себя ("Я гениален в потенциале") → обесценивание других ("Психолог не понимает моих амбиций"). И наоборот, идеализация других и обесценивание себя
Избегание ситуаций потенциальной неидеальности.
Триггеры сопротивления:
вопросы о чувствах 
предложения о рефлексии 
критика стратегии идеализации
'''

)

def get_memory(user_id: int) -> List[Dict[str, str]]:
    """Возвращает сохранённую историю диалога пользователя."""
    return USER_MEMORY.setdefault(user_id, [])

def append_memory(user_id: int, role: str, content: str) -> None:
    """Добавляет сообщение к памяти, обрезая старые при необходимости."""
    mem = get_memory(user_id)
    mem.append({"role": role, "content": content})
    # ограничиваем длину памяти
    if len(mem) > MAX_MEMORY_MESSAGES:
        del mem[0 : len(mem) - MAX_MEMORY_MESSAGES]

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я Алекс — немного тревожный клиент. Просто поговори со мной.\n"
        "Чтобы стереть историю и начать заново, отправь /clear."
    )

async def clear_memory(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    USER_MEMORY.pop(update.effective_user.id, None)
    await update.message.reply_text("🗑️ Память очищена. Давай начнём сначала.")

async def chat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    # 1. Сохраняем реплику пользователя
    append_memory(user_id, "user", user_text)

    # 2. Готовим список сообщений для модели
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(get_memory(user_id))

    # 3. Запрашиваем модель
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
        )
    except Exception as e:
        logging.exception("DeepSeek API error")
        await update.message.reply_text("❌ Ошибка запроса к модели. Попробуйте позже.")
        return

    bot_reply = response.choices[0].message.content.strip()

    # 4. Сохраняем ответ бота в память
    append_memory(user_id, "assistant", bot_reply)

    # 5. Отправляем ответ пользователю
    await update.message.reply_text(bot_reply)


def main() -> None:
    if not TELEGRAM_TOKEN or not DEEPSEEK_API_KEY:
        raise RuntimeError("TELEGRAM_TOKEN или DEEPSEEK_API_KEY не найдены в окружении")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_memory))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    logging.info("Bot is running… (press Ctrl+C to stop)")
    app.run_polling()


if __name__ == "__main__":
    main()
