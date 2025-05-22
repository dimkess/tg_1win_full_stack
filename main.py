import asyncio
import sqlite3
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.exceptions import BotBlocked, ChatNotFound, RetryAfter
from dotenv import load_dotenv
import os
import uvicorn
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
        telegram_id INTEGER PRIMARY KEY,
        user_id TEXT,
        status TEXT
    )
""")
conn.commit()

DEBUG_TELEGRAM_ID = 1266217883

@dp.message_handler(commands=['start'])
async def send_welcome(message: Message):
    telegram_id = message.from_user.id
    cursor.execute("SELECT status FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    
    if user and user[0] in ["registration", "deposit"]:
        await message.answer("✅ Вы уже зарегистрированы. Внесите депозит, чтобы получить доступ к приложению.")
        return

    keyboard = InlineKeyboardMarkup()
    button = InlineKeyboardButton(text="Ҳа, мен ҳаётимни ўзгартиришга тайёрман!", callback_data="ready_to_change")
    keyboard.add(button)

    welcome_text = (
        "👋 **Салом, азиз дўст!**\n\n"
        "Мен — тажрибали дастурчи, ва менда сен учун ҳақиқий лайфхак бор! 💡\n\n"
        "💻 Дастурчилар яхши пул топишади, лекин *ҳаммадан кўпроқ* даромад қилмоқчимисиз?\n\n"
        "🤖 Мен ChatGPT асосида ишлайдиган бот ва илова яратдим. У **Aviator** ўйинидаги сигналарни *95% аниқликда* тахмин қилади! 🎯\n\n"
        "🔁 Бу имконият ҳаётингизни ўзгартиришга ёрдам беради!\n\n"
        "✨ **Ҳаётингизни ўзгартиришга тайёрмисиз?**"
    )

    photo_url = "https://i.ibb.co/fd2zyZ0D/1a3411a4-db55-46b3-84a8-f4da1b57aeff.png"
    cursor.execute("INSERT OR IGNORE INTO users (telegram_id, user_id, status) VALUES (?, ?, ?)",
                   (telegram_id, '', 'waiting_for_button'))
    conn.commit()

    await message.answer_photo(photo=photo_url, caption=welcome_text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data == "ready_to_change")
async def handle_button(callback_query: types.CallbackQuery):
    telegram_id = callback_query.from_user.id
    link = f"https://1wtsmf.com/v3/aviator-fire?p=1ylh&sub1={telegram_id}"

    register_keyboard = InlineKeyboardMarkup()
    register_button = InlineKeyboardButton(text="📝 Рўйхатдан ўтиш", url=link)
    register_keyboard.add(register_button)
    register_keyboard.add(InlineKeyboardButton('↩️ Вернуться к главному меню', callback_data='menu'))

    caption = (
        f"🚀 <b>Қара, дўстим!</b>\n\n"
        f"Аввало мана бу ҳавола орқали рўйхатдан ўтишинг керак:\n👉 <a href=\"{link}\">{link}</a>\n\n"
        "🔑 Кейин бот ўзингни автоматик таниб олади.\n\n"
        "⏳ Агар 5 дақиқа ичида хабар келмаса — \n"
        "1️⃣ Балки сен рўйхатдан ўтмагансан.\n"
        "2️⃣ Ёки сенда олдиндан мавжуд бўлган аккаунт бор.\n\n"
        "📖 <b>Йўриқномани ўқиб, янги аккаунт ярат!</b>"
    )

    cursor.execute("UPDATE users SET status = ? WHERE telegram_id = ?", ("waiting_postback", telegram_id))
    conn.commit()

    await callback_query.message.answer_photo(
        photo="https://i.ibb.co/xtnY7Dvn/255ef825-defe-483d-a576-e5c6066e940b.png",
        caption=caption,
        reply_markup=register_keyboard,
        parse_mode="HTML"
    )
    await callback_query.answer()

@app.get("/postback")
async def postback(event: str, user_id: str, sub1: str, amount: str = "0"):
    if not sub1.isdigit():
        await send_notification(DEBUG_TELEGRAM_ID, f"❌ sub1 не число: {sub1}")
        return {"status": "invalid telegram_id"}

    telegram_id = int(sub1)

    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT OR IGNORE INTO users (telegram_id, user_id, status) VALUES (?, ?, ?)",
                       (telegram_id, user_id, event))
    else:
        cursor.execute("UPDATE users SET user_id = ?, status = ? WHERE telegram_id = ?",
                       (user_id, event, telegram_id))
    conn.commit()

    if event == "registration":
        text = (
            f"✅ Регистрация подтверждена для ID {user_id}\n"
            f"📥 Пожалуйста, сделайте депозит для активации сигналов!"
        )
    elif event == "deposit":
        text = (
            f"💰 Депозит на {amount}₽ подтверждён для ID {user_id}\n"
            f"🎉 Сигналы активированы! Играйте и выигрывайте!"
        )
    else:
        text = f"📩 Событие {event} для ID {user_id}"

    await send_notification(telegram_id, text)
    return {"status": "ok"}

async def send_notification(chat_id, text):
    try:
        await bot.send_message(chat_id, text)
    except BotBlocked:
        await send_notification(DEBUG_TELEGRAM_ID, f"❌ Бот заблокирован Telegram ID {chat_id}")
    except ChatNotFound:
        await send_notification(DEBUG_TELEGRAM_ID, f"❌ Чат не найден Telegram ID {chat_id}")
    except RetryAfter as e:
        await asyncio.sleep(e.timeout)
        await bot.send_message(chat_id, text)
    except Exception as e:
        await send_notification(DEBUG_TELEGRAM_ID, f"❌ Ошибка: {e}")

@dp.callback_query_handler(lambda c: c.data == "menu")
async def handle_main_menu(callback_query: types.CallbackQuery):
    telegram_id = callback_query.from_user.id
    cursor.execute("SELECT status FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()

    photo = "https://i.ibb.co/fd2zyZ0D/1a3411a4-db55-46b3-84a8-f4da1b57aeff.png"
    caption = "👋 <b>Хуш келибсан!</b>\n\nБу ерда сен 1WIN учун ишончли сигналлар оласан.\n"

    if user and user[1] in ["registration", "deposit"]:
        caption += "✅ Сен рўйхатдан ўтгансан. Энди депозит кирит ва сигналлар фаоллашади. 💰"
    else:
        caption += "📝 Илтимос, рўйхатдан ўтиш учун тугмани бос ва янги аккаунт ярат."

    await callback_query.message.answer_photo(photo=photo, caption=caption, reply_markup=get_main_menu(), parse_mode="HTML")
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == "register")
async def handle_register_button(callback_query: types.CallbackQuery):
    telegram_id = callback_query.from_user.id
    link = f"https://1wtsmf.com/v3/aviator-fire?p=1ylh&sub1={telegram_id}"

    cursor.execute("SELECT status FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()

    if user and user[0] in ["registration", "deposit"]:
        text = "✅ Сен аллақачон рўйхатдан ўтгансан.\n\n💰 Илтимос, депозит кирит ва сигналлар фаоллашади."
    else:
        text = (
            f"📝 Илтимос, аввал мана бу ҳавола орқали рўйхатдан ўт:\n"
            f"👉 <a href=\"{link}\">{link}</a>\n\n"
            "🔑 Кейин бот сени автоматик таниб олади."
        )

    await callback_query.message.answer(text, parse_mode="HTML", reply_markup=back_to_menu_button())
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == "instruction")
async def handle_instruction_button(callback_query: types.CallbackQuery):
    text = (
        "📖 <b>Йўриқнома:</b>\n\n"
        "1️⃣ Рўйхатдан ўт мана бу ҳавола орқали\n"
        "2️⃣ Бот сени автоматик таниб олади\n"
        "3️⃣ Депозит кирит\n"
        "4️⃣ Сигналлар фаол бўлади ✅"
    )
    await callback_query.message.answer(text, parse_mode="HTML", reply_markup=back_to_menu_button())
    await callback_query.answer()

@dp.message_handler(commands=["menu"])
async def show_menu_command(message: Message):
    telegram_id = message.from_user.id
    cursor.execute("SELECT status FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()

    photo = "https://i.ibb.co/fd2zyZ0D/1a3411a4-db55-46b3-84a8-f4da1b57aeff.png"
    caption = "👋 <b>Хуш келибсан!</b>\n\nБу ерда сен 1WIN учун ишончли сигналлар оласан.\n"

    if user and user[1] in ["registration", "deposit"]:
        caption += "✅ Сен рўйхатдан ўтгансан. Энди депозит кирит ва сигналлар фаоллашади. 💰"
    else:
        caption += "📝 Илтимос, рўйхатдан ўтиш учун тугмани бос ва янги аккаунт ярат."

    await message.answer_photo(photo=photo, caption=caption, reply_markup=get_main_menu(), parse_mode="HTML")

def get_main_menu():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📝 Регистрация", callback_data="register"))
    keyboard.add(InlineKeyboardButton("📖 Инструкция", callback_data="instruction"))
    keyboard.add(InlineKeyboardButton("💬 Help", url="https://t.me/YOUR_ADMIN_USERNAME"))
    return keyboard

def back_to_menu_button():
    return InlineKeyboardMarkup().add(InlineKeyboardButton("↩️ Вернуться к главному меню", callback_data="menu"))

def start_api():
    uvicorn.run("main:app", host="0.0.0.0", port=8000)

def start_bot():
    executor.start_polling(dp, skip_updates=True)

if __name__ == "__main__":
    threading.Thread(target=start_api).start()
    start_bot()
