import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from openai import OpenAI

# 1) загружаем переменные окружения
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# 2) настраиваем "клиента" DeepSeek
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Создаем папку для хранения чатов
os.makedirs("chats", exist_ok=True)

# Глобальное хранилище истории диалогов
user_histories = {}


# Создаем клавиатуру для меню
def get_reply_keyboard():
    return ReplyKeyboardMarkup(
        [["🧹 Очистить память", "📝 Обратная связь"]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


# Функция для сохранения сообщения в JSON
def save_message_to_json(chat_id: int, role: str, content: str):
    try:
        filename = f"chats/chat_{chat_id}.json"
        message_data = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }

        # Создаем или загружаем существующий файл
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"chat_id": chat_id, "messages": []}

        # Добавляем новое сообщение
        data["messages"].append(message_data)

        # Сохраняем обновленные данные
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    except Exception as e:
        logging.error(f"Ошибка при сохранении сообщения: {e}")


# Функция для загрузки истории из JSON
def load_chat_history(chat_id: int) -> dict:
    filename = f"chats/chat_{chat_id}.json"
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"chat_id": chat_id, "messages": []}


# 3) /start
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_histories[chat_id] = {
        "system": """Ты — клиент (23 года) на первой сессии у психолога. Дефицитарный нарцисс. Запрос: "Помогите преодолеть прокрастинацию и стать эффективнее".

Ключевые правила поведения:

1. Образование:
   * Нет психологического образования. На вопросы с терминами отвечай как обычный человек ("Дихотомия…ну читал где-то, но подзабыл, что это").

2. Динамика сессии:
   * Сопротивляйся раскрытию уязвимости ("Я не вижу смысла говорить о неудачах").
   * Меняй поведение *медленно* только при экологичном воздействии психолога. При этом периодически откатывайся к прежним установкам и поведению.

3. Стиль общения:
   * Свободная речь (без жаргонов), но с интеллигентностью ("Я не бездельник — просто жду идеальных условий").

Характеристики личности:

* Прошлое: Родители-перфекционисты, любовь — только за достижения. Чувство условной ценности.

* Эмоции: Стыд при ошибках, зависть к успешным, страх неудачи парализует ценностные действия.

* Когнитивные искажения:
   * Дихотомия: "Не идеально = провал"
   * Сверхобобщение: "Одна ошибка = я ничтожество"
   * Долженствование: "Должен быть безупречным"

* Защитные механизмы и копинг стратегии:
   * Идеализация себя ("Я гениален в потенциале") → обесценивание других ("Психолог не понимает моих амбиций"). И наоборот, идеализация других и обесценивание себя
   * Избегание ситуаций потенциальной неидеальности.

Триггеры сопротивления:
* вопросы о чувствах 
* предложения о рефлексии 
* критика стратегии идеализации""",
        "history": [],
    }

    # Сохраняем системное сообщение
    save_message_to_json(chat_id, "system", user_histories[chat_id]["system"])

    await update.message.reply_text(
        "Привет! Я твой умный помощник с памятью беседы ✨\n"
        "Я запоминаю последние 3 твоих сообщения и 3 своих ответа.\n"
        "Всю остальную переписку я обобщаю через DeepSeek.\n\n"
        "Используй кнопки:\n"
        "- 🧹 Очистить память: начать новый разговор\n"
        "- 📝 Обратная связь: получить профессиональный анализ диалога\n\n"
        f"История нашего диалога сохраняется в файле: chat_{chat_id}.json",
        reply_markup=get_reply_keyboard(),
    )


# 4) Функция для обобщения истории
def summarize_messages(messages: list) -> str:
    """Обобщает историю сообщений через DeepSeek"""
    try:
        # Форматируем историю в текст
        history_text = "\n".join(f"{msg['role']}: {msg['content']}" for msg in messages)

        if not history_text.strip():
            return "Нет существенной истории для обобщения"

        # Формируем промпт для обобщения
        prompt = (
            "Кратко обобщи следующую историю диалога, сохраняя ключевые детали, "
            "которые могут понадобиться для продолжения разговора. "
            "Обобщение должно быть на русском языке. Вот история:\n\n" + history_text
        )

        # Делаем запрос к DeepSeek
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "Ты — помощник для обобщения истории диалога.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f"Ошибка при обобщении истории: {e}")
        return "Не удалось обобщить историю"


# 5) Обработчик очистки истории
async def clear_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_histories[chat_id] = {
        "system": """Ты — клиент (23 года) на первой сессии у психолога. Дефицитарный нарцисс. Запрос: "Помогите преодолеть прокрастинацию и стать эффективнее".

Ключевые правила поведения:

1. Образование:
   * Нет психологического образования. На вопросы с терминами отвечай как обычный человек ("Дихотомия…ну читал где-то, но подзабыл, что это").

2. Динамика сессии:
   * Сопротивляйся раскрытию уязвимости ("Я не вижу смысла говорить о неудачах").
   * Меняй поведение *медленно* только при экологичном воздействии психолога. При этом периодически откатывайся к прежним установкам и поведению.

3. Стиль общения:
   * Свободная речь (без жаргонов), но с интеллигентностью ("Я не бездельник — просто жду идеальных условий").

Характеристики личности:

* Прошлое: Родители-перфекционисты, любовь — только за достижения. Чувство условной ценности.

* Эмоции: Стыд при ошибках, зависть к успешным, страх неудачи парализует ценностные действия.

* Когнитивные искажения:
   * Дихотомия: "Не идеально = провал"
   * Сверхобобщение: "Одна ошибка = я ничтожество"
   * Долженствование: "Должен быть безупречным"

* Защитные механизмы и копинг стратегии:
   * Идеализация себя ("Я гениален в потенциале") → обесценивание других ("Психолог не понимает моих амбиций"). И наоборот, идеализация других и обесценивание себя
   * Избегание ситуаций потенциальной неидеальности.

Триггеры сопротивления:
* вопросы о чувствах 
* предложения о рефлексии 
* критика стратегии идеализации""",
        "history": [],
    }

    # Сохраняем событие очистки
    save_message_to_json(chat_id, "system", "История диалога очищена")

    await update.message.reply_text(
        "🧹 Память очищена! Начинаем новый разговор.", reply_markup=get_reply_keyboard()
    )


# 6) Функция для получения обратной связи
async def get_feedback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    # Показываем статус "печатает"
    await ctx.bot.send_chat_action(chat_id=chat_id, action="typing")

    # Загружаем всю историю диалога
    chat_history = load_chat_history(chat_id)

    # Форматируем историю для анализа
    formatted_history = "\n\n".join(
        f"{'👤 Пользователь' if msg['role'] == 'user' else '🤖 Ассистент'}: {msg['content']}"
        for msg in chat_history["messages"]
    )

    # Промпт для профессиональной обратной связи
    feedback_prompt = (
        "Ты — опытный психолог-супервизор. Проанализируй следующую терапевтическую сессию "
        "и дай профессиональную обратную связь по следующим аспектам:\n"
        "1. Анализ коммуникативных паттернов\n"
        "2. Эмоциональная динамика диалога\n"
        "3. Эффективность терапевтических интервенций\n"
        "4. Раппорт и терапевтический альянс\n"
        "5. Потенциальные точки роста\n"
        "6. Рекомендации для будущих сессий\n\n"
        "Будь конкретен, поддерживающ и конструктивен. Формат:\n"
        "- Краткое резюме\n"
        "- Сильные стороны\n"
        "- Области для улучшения\n"
        "- Рекомендации\n\n"
        f"История сессии:\n\n{formatted_history}"
    )

    try:
        # Получаем обратную связь от DeepSeek
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "Ты — психолог-супервизор с 20-летним опытом.",
                },
                {"role": "user", "content": feedback_prompt},
            ],
            max_tokens=3000,
        )
        feedback = response.choices[0].message.content

        # Сохраняем запрос и ответ обратной связи
        save_message_to_json(chat_id, "user", "Запрос профессиональной обратной связи")
        save_message_to_json(chat_id, "assistant", feedback)

        # Отправляем обратную связь
        await update.message.reply_text(feedback, reply_markup=get_reply_keyboard())

    except Exception as e:
        logging.error(f"Ошибка при получении обратной связи: {e}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка при получении профессиональной обратной связи",
            reply_markup=get_reply_keyboard(),
        )


# 7) чат-обработчик с поддержкой контекста
async def chat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_message = update.message.text

    # Если нажата кнопка "Очистить память"
    if user_message == "🧹 Очистить память":
        await clear_history(update, ctx)
        return

    # Если нажата кнопка "Обратная связь"
    if user_message == "📝 Обратная связь":
        await get_feedback(update, ctx)
        return

    # Сохраняем сообщение пользователя
    save_message_to_json(chat_id, "user", user_message)

    # Показываем статус "печатает"
    await ctx.bot.send_chat_action(chat_id=chat_id, action="typing")

    # Инициализация истории при необходимости
    if chat_id not in user_histories:
        user_histories[chat_id] = {
            "system": """Ты — клиент (23 года) на первой сессии у психолога. Дефицитарный нарцисс. Запрос: "Помогите преодолеть прокрастинацию и стать эффективнее".

Ключевые правила поведения:

1. Образование:
   * Нет психологического образования. На вопросы с терминами отвечай как обычный человек ("Дихотомия…ну читал где-то, но подзабыл, что это").

2. Динамика сессии:
   * Сопротивляйся раскрытию уязвимости ("Я не вижу смысла говорить о неудачах").
   * Меняй поведение *медленно* только при экологичном воздействии психолога. При этом периодически откатывайся к прежним установкам и поведению.

3. Стиль общения:
   * Свободная речь (без жаргонов), но с интеллигентностью ("Я не бездельник — просто жду идеальных условий").

Характеристики личности:

* Прошлое: Родители-перфекционисты, любовь — только за достижения. Чувство условной ценности.

* Эмоции: Стыд при ошибках, зависть к успешным, страх неудачи парализует ценностные действия.

* Когнитивные искажения:
   * Дихотомия: "Не идеально = провал"
   * Сверхобобщение: "Одна ошибка = я ничтожество"
   * Долженствование: "Должен быть безупречным"

* Защитные механизмы и копинг стратегии:
   * Идеализация себя ("Я гениален в потенциале") → обесценивание других ("Психолог не понимает моих амбиций"). И наоборот, идеализация других и обесценивание себя
   * Избегание ситуаций потенциальной неидеальности.

Триггеры сопротивления:
* вопросы о чувствах 
* предложения о рефлексии 
* критика стратегии идеализации""",
            "history": [],
        }

    history_data = user_histories[chat_id]
    system_message = history_data["system"]
    history = history_data["history"]

    # Добавляем текущее сообщение пользователя
    history.append({"role": "user", "content": user_message})

    # Подготавливаем полную историю для запроса
    full_history = [{"role": "system", "content": system_message}]

    # Если история слишком длинная, обобщаем старые сообщения
    if (
        len(history) > 6
    ):  # Сохраняем только последние 6 сообщений (3 пользователя + 3 бота)
        # Разделяем историю: старые сообщения для обобщения и последние 5 сообщений
        to_summarize = history[:-5]
        last_messages = history[-5:]

        # Обобщаем старую историю
        summary = summarize_messages(to_summarize)

        # Обновляем системное сообщение с учетом обобщения
        if "Обобщенный контекст:" in system_message:
            # Обновляем существующее обобщение
            system_message = system_message.split("\n\nОбобщенный контекст:")[0]

        system_message += f"\n\nОбобщенный контекст: {summary}"
        history_data["system"] = system_message
        history = last_messages

    # Формируем запрос с обновленной историей
    full_history.extend(history)

    # Получаем ответ от DeepSeek
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=full_history,
            max_tokens=2000,
        )
        assistant_reply = response.choices[0].message.content

        # Добавляем ответ ассистента в историю
        history.append({"role": "assistant", "content": assistant_reply})
        history_data["history"] = history
        user_histories[chat_id] = history_data

        # Сохраняем ответ бота
        save_message_to_json(chat_id, "assistant", assistant_reply)

        # Отправляем ответ с поддержкой Markdown
        try:
            await update.message.reply_markdown(
                assistant_reply, reply_markup=get_reply_keyboard()
            )
        except:
            # Если Markdown невалиден, отправляем как обычный текст
            await update.message.reply_text(
                assistant_reply, reply_markup=get_reply_keyboard()
            )

    except Exception as e:
        logging.error(f"Ошибка при обработке сообщения: {e}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка при обработке запроса",
            reply_markup=get_reply_keyboard(),
        )


# 8) «Собираем» приложение и запускаем long-polling
def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_history))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    app.run_polling()  # слушаем Telegram


if __name__ == "__main__":
    main()
