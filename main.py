import asyncio
import sqlite3
import os
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.exceptions import BotBlocked, ChatNotFound, RetryAfter
from dotenv import load_dotenv
import uvicorn

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в .env")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
app = FastAPI()

# Подключение к SQLite
db_path = os.getenv("DB_PATH", "users.db")
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        user_id TEXT,
        status TEXT
    )
    """
)
conn.commit()

# Формирование главного меню
def get_main_menu() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("Готов изменить жизнь!", callback_data="register"),
        InlineKeyboardButton("Инструкция", callback_data="instruction"),
        InlineKeyboardButton("Help", callback_data="help")
    )
    return keyboard

# Обработчики Telegram
@dp.message_handler(commands=["start", "menu"])
async def cmd_start(message: types.Message):
    telegram_id = message.from_user.id
    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id, status) VALUES (?, ?)"\,
        (telegram_id, "start")
    )
    conn.commit()

    photo_url = "https://i.ibb.co/xtnY7Dvn/255ef825-defe-483d-a576-e5c6066e940b.png"
    caption = (
        "👋 Привет!\n"
        "Я бот для автоматической регистрации и уведомлений через 1WIN.\n"
        "Нажми кнопку \"Готов изменить жизнь!\" чтобы начать."
    )
    await message.answer_photo(
        photo=photo_url,
        caption=caption,
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

@dp.callback_query_handler(lambda c: c.data == "register")
async def process_register(callback_query: types.CallbackQuery):
    telegram_id = callback_query.from_user.id
    link = f"https://1win.example.com/registration?sub1={telegram_id}"

    photo_url = "https://i.ibb.co/xtnY7Dvn/255ef825-defe-483d-a576-e5c6066e940b.png"
    caption = (
        "🚀 Дружище!\n\n"
        "Чтобы зарегистрироваться на 1WIN, используй эту ссылку:\n"
        f"👉 <b><a href=\"{link}\">Регистрируйся здесь</a></b>\n\n"
        "После успешной регистрации и депозита ты моментально получишь уведомление здесь."
    )
    await callback_query.message.answer_photo(
        photo=photo_url,
        caption=caption,
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data in ["instruction", "help"])
async def show_help(callback_query: types.CallbackQuery):
    text = (
        "ℹ️ Инструкция:\n"
        "1. Нажми \"Готов изменить жизнь!\".\n"
        "2. Пройди регистрацию по ссылке.\n"
        "3. После депозита жди уведомления от бота.\n"
    )
    await callback_query.message.answer(text, reply_markup=get_main_menu())
    await callback_query.answer()

# Webhook FastAPI
@app.post("/postback")
async def postback(event: str = None, user_id: str = None, sub1: str = None, amount: float = 0):
    if not sub1 or not sub1.isdigit():
        return {"status": "error", "reason": "invalid sub1"}

    telegram_id = int(sub1)
    cursor.execute(
        "INSERT OR REPLACE INTO users (telegram_id, user_id, status) VALUES (?, ?, ?)"\,
        (telegram_id, user_id, event)
    )
    conn.commit()

    try:
        if event == "registration":
            text = "✅ Регистрация подтверждена! Внеси депозит для активации сигналов."
        elif event == "deposit":
            text = f"💰 Депозит на {amount}₽ подтверждён. Сигналы активированы!"
        else:
            text = f"🔔 Событие {event} получено."
        await bot.send_message(chat_id=telegram_id, text=text)
    except BotBlocked:
        cursor.execute(
            "UPDATE users SET status = ? WHERE telegram_id = ?"\,
            ("bot_blocked", telegram_id)
        )
        conn.commit()
    except ChatNotFound:
        pass
    except RetryAfter as e:
        await asyncio.sleep(e.timeout)

    return {"status": "ok"}

# Запуск

def main():
    from threading import Thread
    def start_api():
        uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    Thread(target=start_api, daemon=True).start()
    executor.start_polling(dp, skip_updates=True)

if __name__ == "__main__":
    main()
