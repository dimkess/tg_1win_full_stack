import asyncio
import sqlite3
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.exceptions import BotBlocked, ChatNotFound, RetryAfter
from dotenv import load_dotenv
import os
import uvicorn

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

# Ваш Telegram ID для отладки
DEBUG_TELEGRAM_ID = 1266217883

@dp.message_handler(commands=['start'])
async def send_welcome(message: Message):
    telegram_id = message.from_user.id
    # Создаём кнопку
    keyboard = InlineKeyboardMarkup()
    button = InlineKeyboardButton(text="Ҳа, мен ҳаётимни ўзгартиришга тайёрман!", callback_data="ready_to_change")
    keyboard.add(button)
    
    # Текст приветствия
    welcome_text = (
        "Салом, азиз дўст! Мен кўп йиллик тажрибага эга бўлган дастурчиман. "
        "Дастурчилар кўп даромад олишади, лекин янада кўпроқ истаганда нима қилиш керак? "
        "Мен ChatGPT билан бевосита ишлайдиган бот ва иловани яратдим, у Aviator ўйинидаги "
        "сигналларни 95% ҳолатда тўғри тахмин қилади. Ҳаётингизни ўзгартиришга тайёрмисиз?"
    )
    
    # Отправляем сообщение с картинкой и кнопкой
    # Замени 'photo_url' на реальную ссылку на картинку
    photo_url = "https://cdn.geekvibesnation.com/wp-media-folder-geek-vibes-nation/wp-content/uploads/2024/04/aviator-game-review-1024x475.png"  # Укажи свою картинку
    cursor.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
    cursor.execute(
        "INSERT INTO users (telegram_id, user_id, status) VALUES (?, ?, ?)",
        (telegram_id, "", "waiting_for_button")
    )
    conn.commit()
    await message.answer_photo(photo=photo_url, caption=welcome_text, reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == "ready_to_change")
async def handle_button(callback_query: types.CallbackQuery):
    telegram_id = callback_query.from_user.id
    link = f"https://1wtsmf.com/v3/aviator-fire?p=1ylh&sub1={telegram_id}"
    cursor.execute(
        "UPDATE users SET status = ? WHERE telegram_id = ?",
        ("waiting_for_user_id", telegram_id)
    )
    conn.commit()
    await callback_query.message.answer(
        f"Қара, дўстим, аввало мана бу ҳавола орқали рўйхатдан ўтишинг керак: {link}\n"
        "ва ID рақамингни менга юбор.\n\n"
        "Муҳими — менинг ботим ва иловам фақат янги 1WIN аккаунтлари билан ишлайди.\n"
        "Сен тугатганингдан сўнг, бот автоматик тарзда рўйхатдан ўтишни тасдиқлайди "
        "ёки ID рақамни ўзинг юборсан ҳам бўлади."
    )
    await callback_query.answer()

@dp.message_handler()
async def handle_user_id(message: Message):
    telegram_id = message.from_user.id
    user_id = message.text.strip()

    cursor.execute("SELECT status FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()

    if not user:
        await message.answer("❗ Отправь /start, чтобы начать.")
        return

    if user[0] not in ["waiting_for_user_id", "waiting_for_button"]:
        await message.answer("⏳ ID уже отправлен. Жду регистрации или депозита.")
        return

    if not user_id.isdigit():
        await message.answer("❗ Отправь только ID 1win (цифры).")
        return

    cursor.execute("SELECT status FROM users WHERE telegram_id = ? AND user_id = ?", (telegram_id, user_id))
    existing_user = cursor.fetchone()

    if existing_user:
        if existing_user[0] in ["registration", "deposit"]:
            await message.answer(f"✅ ID {user_id} уже зарегистрирован. Статус: {existing_user[0]}.")
            return
        else:
            await message.answer("⏳ ID уже отправлен. Жду регистрации или депозита.")
            return

    cursor.execute(
        "UPDATE users SET user_id = ?, status = ? WHERE telegram_id = ? AND user_id = ''",
        (user_id, "id_sent", telegram_id)
    )
    if cursor.rowcount == 0:
        cursor.execute(
            "INSERT INTO users (telegram_id, user_id, status) VALUES (?, ?, ?)",
            (telegram_id, user_id, "id_sent")
        )
    conn.commit()
    await message.answer(f"🕐 ID {user_id} принят. Жду регистрации.")

@app.get("/postback")
async def postback(event: str, user_id: str, sub1: str, amount: str = "0"):
    if not sub1.isdigit():
        print(f"❌ sub1 не число: {sub1}")
        await send_notification(DEBUG_TELEGRAM_ID, f"❌ sub1 не число: {sub1}")
        return {"status": "invalid telegram_id"}

    telegram_id = int(sub1)

    cursor.execute("SELECT * FROM users WHERE telegram_id = ? AND user_id = ?", (telegram_id, user_id))
    user = cursor.fetchone()

    if not user:
        cursor.execute(
            "INSERT OR IGNORE INTO users (telegram_id, user_id, status) VALUES (?, ?, ?)",
            (telegram_id, user_id, event)
        )
        conn.commit()
        print(f"ℹ️ Новый пользователь telegram_id={telegram_id}, user_id={user_id} добавлен из постбэка")
        await send_notification(DEBUG_TELEGRAM_ID, f"ℹ️ Новый пользователь telegram_id={telegram_id}, user_id={user_id} добавлен из постбэка")
    else:
        cursor.execute(
            "UPDATE users SET status = ? WHERE telegram_id = ? AND user_id = ?",
            (event, telegram_id, user_id)
        )
        conn.commit()

    if event == "registration":
        text = f"✅ Регистрация подтверждена для ID {user_id}"
    elif event == "deposit":
        text = f"💰 Депозит на {amount}₽ подтверждён для ID {user_id}"
    else:
        text = f"📩 Событие {event} для ID {user_id}"

    await send_notification(telegram_id, text)
    return {"status": "ok"}

async def send_notification(chat_id, text):
    try:
        print(f"📤 Отправляю Telegram ID {chat_id}: {text}")
        await bot.send_message(chat_id, text)
        print(f"✅ Отправлено Telegram ID {chat_id}")
    except BotBlocked:
        print(f"❌ Бот заблокирован Telegram ID {chat_id}")
        await send_notification(DEBUG_TELEGRAM_ID, f"❌ Бот заблокирован Telegram ID {chat_id}")
    except ChatNotFound:
        print(f"❌ Чат не найден Telegram ID {chat_id}")
        await send_notification(DEBUG_TELEGRAM_ID, f"❌ Чат не найден Telegram ID {chat_id}")
    except RetryAfter as e:
        print(f"❌ Лимит, жду {e.timeout} сек")
        await asyncio.sleep(e.timeout)
        await bot.send_message(chat_id, text)
    except Exception as e:
        print(f"❌ Ошибка Telegram ID {chat_id}: {e}")
        await send_notification(DEBUG_TELEGRAM_ID, f"❌ Ошибка: {e}")

async def start_bot_polling():
    try:
        await dp.start_polling()
    finally:
        await bot.session.close()

def start():
    loop = asyncio.get_event_loop()
    loop.create_task(start_bot_polling())
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="asyncio")
    server = uvicorn.Server(config)
    loop.run_until_complete(server.serve())

if __name__ == "__main__":
    start()
