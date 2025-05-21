import asyncio
import sqlite3
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, executor, types
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

DEBUG_TELEGRAM_ID = 1266217883

@dp.message_handler(commands=['start'])
async def send_welcome(message: Message):
    telegram_id = message.from_user.id
    cursor.execute("SELECT status FROM users WHERE telegram_id = ? AND user_id != ''", (telegram_id,))
    user = cursor.fetchone()
    if user and user[0] in ["registration", "deposit"]:
        await message.answer("✅ Вы уже зарегистрированы. Ваш ID в 1WIN - {user_id}. Внесите депозит, чтобы получить доступ к приложению")
        return

    keyboard = InlineKeyboardMarkup()
    button = InlineKeyboardButton(text="Ҳа, мен ҳаётимни ўзгартиришга тайёрман!", callback_data="ready_to_change")
    keyboard.add(button)

    welcome_text = (
        "👋 **Салом, азиз дўст!**\n\n"
        "Мен — тажрибали дастурчи, ва менда сен учун ҳақиқий лайфхак бор! 💡\n\n"
        "💻 Дастурчилар яхши пул топишади, лекин *ҳаммадан кўпроқ* даромад қилмоқчимисиз?\n\n"
        "🤖 Мен ChatGPT асосида ишлайдиган бот ва илова яратдим. У **Aviator** ўйинидаги "
        "сигналларни *95% аниқликда* тахмин қилади! 🎯\n\n"
        "🔁 Бу имконият ҳаётингизни ўзгартиришга ёрдам беради!\n\n"
        "✨ **Ҳаётингизни ўзгартиришга тайёрмисиз?**"
    )

    photo_url = "https://i.ibb.co/fd2zyZ0D/1a3411a4-db55-46b3-84a8-f4da1b57aeff.png"
    cursor.execute("DELETE FROM users WHERE telegram_id = ? AND user_id = ''", (telegram_id,))
    
    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id, user_id, status) VALUES (?, ?, ?)",
        (telegram_id, "", "waiting_for_button")
   )
    conn.commit()
    await message.answer_photo(
        photo=photo_url,
        caption=welcome_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query_handler(lambda c: c.data == "ready_to_change")
async def handle_button(callback_query: types.CallbackQuery):
    telegram_id = callback_query.from_user.id
    link = f"https://1wtsmf.com/v3/aviator-fire?p=1ylh&sub1={telegram_id}"

    register_keyboard = InlineKeyboardMarkup()
    register_button = InlineKeyboardButton(
        text="📝 Рўйхатдан ўтиш",
        url=link
    )
    register_keyboard.add(register_button)

    caption = (
        "🚀 <b>Қара, дўстим!</b>\n\n"
        "Аввало мана бу ҳавола орқали рўйхатдан ўтишинг керак:\n👉 <a href=\"{link}\">{link}</a>\n\n"
        "🔑 Кейин эса <b>1WIN ID рақамингни</b> менга юбор.\n\n"
        "⚠️ Муҳими — бот фақат <u>янги аккаунтлар</u> билан ишлайди.\n"
        "Аввал рўйхатдан ўт, сўнг бот автоматик текширади ✅\n\n"
        "📨 Агар автоматик бўлмаса, ID рақамни ўзи юборсан ҳам бўлади.\n\n"
        "⏳ <b>Кутаман!</b>"
    )

    cursor.execute("UPDATE users SET status = ? WHERE telegram_id = ?", ("waiting_for_user_id", telegram_id))
    conn.commit()

    await callback_query.message.answer_photo(
        photo="https://i.ibb.co/xtnY7Dvn/255ef825-defe-483d-a576-e5c6066e940b.png",
        caption=caption.format(link=link),
        reply_markup=register_keyboard,
        parse_mode="HTML"
    )
    await callback_query.answer()

@dp.message_handler()
async def handle_user_id(message: Message):
    telegram_id = message.from_user.id
    user_input = message.text.strip().lower()

    # Проверка: есть ли запись в базе
    cursor.execute("SELECT user_id, status FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()

    if not user:
        await message.answer("❗ Отправь /start, чтобы начать.")
        return

    user_id_in_db, status = user

    # ✅ Уже зарегистрирован
    if status in ["registration", "deposit"]:
        await message.answer(
            f"✅ Вы уже зарегистрированы. Ваш ID в 1WIN — {user_id_in_db}. "
            f"Внесите депозит, чтобы получить доступ к приложению."
        )
        return

    # ❗ Сообщение не является ID (не цифры)
    if not user_input.isdigit():
        text = (
            "🙌 Дўстим, барча саволларингга мамнуният билан жавоб бераман!\n\n"
            "Лекин аввал илтимос, ⏳ мана бу ҳавола орқали рўйхатдан ўт:\n"
            "👉 <b>Рўйхатдан ўтиш — бу биринчи ва муҳим қадам!</b> 📝\n\n"
            "Шундан сўнг ID рақамингни ёзсан, ҳаммасини давом эттирамиз! 🚀"
        )
        await message.answer(text, parse_mode="HTML")
        return

    user_id = user_input

    # Проверка: уже есть такой ID у этого пользователя
    cursor.execute("SELECT status FROM users WHERE telegram_id = ? AND user_id = ?", (telegram_id, user_id))
    existing_user = cursor.fetchone()

    if existing_user:
        existing_status = existing_user[0]
        if existing_status == "id_sent":
            await message.answer("⏳ ID уже отправлен. Жду подтверждение регистрации.")
            return
        elif existing_status in ["registration", "deposit"]:
            await message.answer(
                f"✅ Вы уже зарегистрированы. Ваш ID в 1WIN — {user_id}. "
                f"Внесите депозит, чтобы получить доступ к приложению."
            )
            return

    # Обновить если была пустая запись
    cursor.execute(
        "UPDATE users SET user_id = ?, status = ? WHERE telegram_id = ? AND user_id = ''",
        (user_id, "id_sent", telegram_id)
    )

    # Если не обновилось — вставить новую, но без дублирования
    if cursor.rowcount == 0:
        cursor.execute("SELECT 1 FROM users WHERE telegram_id = ? AND user_id = ?", (telegram_id, user_id))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (telegram_id, user_id, status) VALUES (?, ?, ?)",
                (telegram_id, user_id, "id_sent")
            )

    conn.commit()

    text = (
        f"🕐 <b>ID {user_id} қабул қилинди.</b> Бироз вақт ичида рўйхатдан ўтиш ҳақида хабар оласан. 📩\n\n"
        "<b>Агар 1 соат ичида ҳеч қандай хабар келмаса, 2 та сабаб бўлиши мумкин:</b>\n"
        "1️⃣ <b>Сен ҳавола орқали рўйхатдан ўтмадинг.</b>\n"
        "2️⃣ <b>Сенда олдиндан мавжуд бўлган аккаунт бор — у бот билан ишламайди.</b>\n\n"
        "📌 <i>Тўлиқ йўриқномани кўриш:</i> 👉 <a href=\"https://твоят-сайт.уз/instruction\">йўриқнома</a>"
    )

    await message.answer(text, parse_mode="HTML")

@app.get("/postback")
async def postback(event: str, user_id: str, sub1: str, amount: str = "0"):
    if not sub1.isdigit():
        await send_notification(DEBUG_TELEGRAM_ID, f"❌ sub1 не число: {sub1}")
        return {"status": "invalid telegram_id"}

    telegram_id = int(sub1)

    # Проверка: есть ли хоть какая-то запись по telegram_id
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()

    if not user:
        # Нет ничего — создаём новую строку
        cursor.execute(
            "INSERT OR IGNORE INTO users (telegram_id, user_id, status) VALUES (?, ?, ?)",
            (telegram_id, user_id, event)
        )
        conn.commit()
        if telegram_id != DEBUG_TELEGRAM_ID:
            text = f"ℹ️ Новый пользователь telegram_id={telegram_id}, user_id={user_id} добавлен из постбэка"
            await send_notification(DEBUG_TELEGRAM_ID, text)
    else:
        # Есть строка, но возможно старый user_id → обновим
        cursor.execute(
            "UPDATE users SET user_id = ?, status = ? WHERE telegram_id = ?",
            (user_id, event, telegram_id)
        )
        conn.commit()

    # Готовим уведомление пользователю
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

async def start_bot_polling():
    try:
        await dp.start_polling()
    finally:
        await bot.session.close()


# Главное меню
def get_main_menu():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📝 Регистрация", callback_data="register"))
    keyboard.add(InlineKeyboardButton("📖 Инструкция", callback_data="instruction"))
    keyboard.add(InlineKeyboardButton("💬 Help", url="https://t.me/YOUR_ADMIN_USERNAME"))  # Замени на своего админа
    return keyboard

def back_to_menu_button():
    return InlineKeyboardMarkup().add(
        InlineKeyboardButton("↩️ Вернуться к главному меню", callback_data="menu")
    )

@dp.callback_query_handler(lambda c: c.data == "menu")
async def handle_main_menu(callback_query: types.CallbackQuery):
    telegram_id = callback_query.from_user.id
    cursor.execute("SELECT user_id, status FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()

    photo = "https://i.ibb.co/fd2zyZ0D/1a3411a4-db55-46b3-84a8-f4da1b57aeff.png"
    caption = "👋 <b>Хуш келибсан!</b>\n\nБу ерда сен 1WIN учун ишончли сигналлар оласан.\n"

    if user and user[1] in ["registration", "deposit"]:
        caption += "✅ Сен рўйхатдан ўтгансан. Энди депозит кирит ва сигналлар фаоллашади. 💰"
    else:
        caption += "📝 Илтимос, рўйхатдан ўтиш учун тугмани бос ва янги аккаунт ярат."

    await callback_query.message.answer_photo(
        photo=photo,
        caption=caption,
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == "register")
async def handle_register_button(callback_query: types.CallbackQuery):
    telegram_id = callback_query.from_user.id
    link = f"https://1wtsmf.com/v3/aviator-fire?p=1ylh&sub1={telegram_id}"

    cursor.execute("SELECT status FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()

    if user and user[0] in ["registration", "deposit"]:
        text = (
            "✅ Сен аллақачон рўйхатдан ўтгансан.\n\n"
            "💰 Илтимос, депозит кирит ва сигналлар фаоллашади."
        )
    else:
        text = (
            f"📝 Илтимос, аввал мана бу ҳавола орқали рўйхатдан ўт:\n"
            f"👉 <a href=\"{link}\">{link}</a>\n\n"
            "🔑 Кейин эса ID рақамингни ботга юбор."
        )

    await callback_query.message.answer(text, parse_mode="HTML", reply_markup=back_to_menu_button())
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == "instruction")
async def handle_instruction_button(callback_query: types.CallbackQuery):
    text = (
        "📖 <b>Йўриқнома:</b>\n\n"
        "1️⃣ Рўйхатдан ўт мана бу ҳавола орқали\n"
        "2️⃣ ID рақамни ботга юбор\n"
        "3️⃣ Депозит кирит\n"
        "4️⃣ Сигналлар фаол бўлади ✅"
    )
    await callback_query.message.answer(text, parse_mode="HTML", reply_markup=back_to_menu_button())
    await callback_query.answer()

@dp.message_handler(commands=["menu"])
async def show_menu_command(message: Message):
    telegram_id = message.from_user.id
    cursor.execute("SELECT user_id, status FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()

    photo = "https://i.ibb.co/fd2zyZ0D/1a3411a4-db55-46b3-84a8-f4da1b57aeff.png"
    caption = "👋 <b>Хуш келибсан!</b>\n\nБу ерда сен 1WIN учун ишончли сигналлар оласан.\n"

    if user and user[1] in ["registration", "deposit"]:
        caption += "✅ Сен рўйхатдан ўтгансан. Энди депозит кирит ва сигналлар фаоллашади. 💰"
    else:
        caption += "📝 Илтимос, рўйхатдан ўтиш учун тугмани бос ва янги аккаунт ярат."

    await message.answer_photo(
        photo=photo,
        caption=caption,
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

def start():
    executor.start_polling(dp, skip_updates=True)

if __name__ == "__main__":
    start()
