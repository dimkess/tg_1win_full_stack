import asyncio
import sqlite3
import threading
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from dotenv import load_dotenv
import os

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
app = FastAPI()

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER,
        user_id TEXT,
        status TEXT,
        PRIMARY KEY (telegram_id, user_id)
    )
""")
conn.commit()

@dp.message_handler()
async def handle_user_id(message: Message):
    if message.text.isdigit():
        telegram_id = message.from_user.id
        user_id = message.text.strip()

        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()

        if user:
            await message.answer("⏳ ID уже на проверке.")
            return

        cursor.execute(
            "INSERT INTO users (telegram_id, user_id, status) VALUES (?, ?, ?)",
            (telegram_id, user_id, "id_sent")
        )
        conn.commit()
        await message.answer(f"🕐 ID {user_id} на проверке. Напишу, как только будет подтверждение регистрации.")
    else:
        await message.answer("❗ Отправь только ID, без лишнего текста.")

@app.get("/postback")
async def postback(event: str, user_id: str, sub1: str, amount: str = "0"):
    if not sub1.isdigit():
        print(f"❌ sub1 не является числом: {sub1}")
        return {"status": "invalid telegram_id"}

    telegram_id = int(sub1)

    cursor.execute("SELECT * FROM users WHERE telegram_id = ? AND user_id = ?", (telegram_id, user_id))
    user = cursor.fetchone()

    if not user:
        cursor.execute(
            "INSERT OR IGNORE INTO users (telegram_id, user_id, status) VALUES (?, ?, ?)",
            (telegram_id, user_id, event)
        )
    else:
        cursor.execute(
            "UPDATE users SET status = ? WHERE telegram_id = ? AND user_id = ?",
            (event, telegram_id, user_id)
        )
    conn.commit()

    if event == "registration":
        text = f"✅ Регистрация подтверждена для ID {user_id}"
    elif event == "deposit":
        text = f"💰 Депозит подтверждён на сумму {amount}₽ для ID {user_id}"
    else:
        text = f"📩 Событие {event} для ID {user_id}"

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(send_notification(telegram_id, text))
    except RuntimeError:
        asyncio.run(send_notification(telegram_id, text))
    except Exception as e:
        print(f"Ошибка при отправке уведомления: {e}")

    return {"status": "ok"}

async def send_notification(chat_id, text):
    try:
        await bot.send_message(chat_id, text)
    except Exception as e:
        print(f"Ошибка при отправке уведомления: {e}")

def start_bot():
    asyncio.run(dp.start_polling())

def start():
    threading.Thread(target=start_bot).start()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    start()
