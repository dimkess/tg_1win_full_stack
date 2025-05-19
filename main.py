import asyncio
import os
import sqlite3
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_polling
from dotenv import load_dotenv
import threading

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

@dp.message_handler(commands=["start"])
async def handle_start(message: types.Message):
    sub1 = message.from_user.id
    link = f"https://1wtsmf.com/v3/aviator-fire?p=1ylh&sub1={sub1}"
    await message.answer(f"""Привет! Зарегистрируйся по ссылке:
{link}

После регистрации пришли сюда свой ID аккаунта 1win.""")

@dp.message_handler(lambda message: message.text.isdigit())
async def handle_user_id(message: types.Message):
    telegram_id = message.from_user.id
    user_id = message.text.strip()

    cursor.execute("SELECT * FROM users WHERE telegram_id = ? AND user_id = ?", (telegram_id, user_id))
    existing = cursor.fetchone()

    if existing:
        await message.answer(f"📝 Ты уже отправлял этот ID: {user_id}")
    else:
        cursor.execute("INSERT OR IGNORE INTO users (telegram_id, user_id, status) VALUES (?, ?, ?)", (telegram_id, user_id, "id_sent"))
        conn.commit()
        await message.answer(f"🕐 ID {user_id} на проверке. Напишу, как только будет подтверждение регистрации.")

async def send_notification(telegram_id: int, message_text: str):
    try:
        await bot.send_message(chat_id=telegram_id, text=message_text)
    except Exception as e:
        print(f"Ошибка при отправке сообщения {telegram_id}: {e}")

@app.get("/postback")
async def postback(event: str, user_id: str, sub1: str, amount: str = "0"):
    if not sub1.isdigit():
        print(f"❌ sub1 не является числом: {sub1}")
        return {"status": "invalid telegram_id"}

    telegram_id = int(sub1)

    cursor.execute("SELECT * FROM users WHERE telegram_id = ? AND user_id = ?", (telegram_id, user_id))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT OR IGNORE INTO users (telegram_id, user_id, status) VALUES (?, ?, ?)", (telegram_id, user_id, event))
    else:
        cursor.execute("UPDATE users SET status = ? WHERE telegram_id = ? AND user_id = ?", (event, telegram_id, user_id))
    conn.commit()

    if event == "registration":
        text = f"✅ Регистрация подтверждена для ID {user_id}"
    elif event == "deposit":
        text = f"💰 Депозит подтверждён на сумму {amount}₽ для ID {user_id}"
    else:
        text = f"📩 Событие {event} для ID {user_id}"

    try:
        asyncio.create_task(send_notification(telegram_id, text))
    except Exception as e:
        print(f"Ошибка при отправке уведомления: {e}")

    return {"status": "ok"}

def start_bot():
    asyncio.run(dp.start_polling())

def start():
    threading.Thread(target=start_bot).start()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    start()
