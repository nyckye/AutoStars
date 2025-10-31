import asyncio
import logging
import httpx
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_IDS, SHOP_NAME, GROQ_API_KEY, DAILY_BONUS_AMOUNT, STAR_PRICE_RUB, update_config, get_config, reload_config
from fragment import FragmentClient, buy_stars_process

class BuyStars(StatesGroup):
    waiting_for_stars = State()
    waiting_for_username = State()
    waiting_for_confirm = State()

class ProfileStates(StatesGroup):
    waiting_for_promo_code = State()

class TicketStates(StatesGroup):
    waiting_for_subject = State()
    waiting_for_message = State()
    waiting_for_ai_question = State()
    waiting_for_ticket_message = State()

class AdminStates(StatesGroup):
    waiting_for_new_code = State()
    waiting_for_new_balance = State()
    waiting_for_delete_code = State()
    waiting_for_block_user_id = State()
    waiting_for_unblock_user_id = State()
    waiting_for_broadcast = State()
    waiting_for_star_price = State()
    waiting_for_daily_bonus = State()
    waiting_for_button_text = State()
    waiting_for_button_url = State()
    waiting_for_delete_button_id = State()
    waiting_for_add_balance_user_id = State()
    waiting_for_add_balance_amount = State()
    waiting_for_ticket_response = State()
    waiting_for_api_value = State()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def get_groq_response(question):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama3-8b-8192",
                    "messages": [
                        {"role": "system", "content": f"Ты помощник магазина {SHOP_NAME}. Мы продаем Telegram Stars. Отвечай кратко и по делу на русском языке."},
                        {"role": "user", "content": question}
                    ]
                },
                timeout=30.0
            )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
    except:
        pass
    return "Извините, ИИ-помощник временно недоступен."

def get_main_menu_keyboard(db, user_id):
    keyboard = [
        [InlineKeyboardButton(text="⭐️ Купить звезды", callback_data="buy_stars")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile"), InlineKeyboardButton(text="🆘 Поддержка", callback_data="support")]
    ]
    menu_buttons = db.get_menu_buttons()
    for btn_id, btn_text, btn_url in menu_buttons:
        if btn_url:
            keyboard.append([InlineKeyboardButton(text=btn_text, url=btn_url)])
        else:
            keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"custom_{btn_id}")])
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton(text="🔥 Админ-меню", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back_to_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💙 Главное меню", callback_data="main_menu")]])

def get_back_keyboard(callback_data="main_menu"):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=callback_data)]])

def get_support_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Создать тикет", callback_data="create_ticket")],
        [InlineKeyboardButton(text="⚙️ Мои тикеты", callback_data="my_tickets"), InlineKeyboardButton(text="🤖 ИИ - помощь", callback_data="ai_help")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ])

def get_profile_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="add_balance")],
        [InlineKeyboardButton(text="🎁 Ежедневный бонус", callback_data="daily_bonus")],
        [InlineKeyboardButton(text="🎫 Выдача по коду", callback_data="use_promo")],
        [InlineKeyboardButton(text="📥 Последние пополнения", callback_data="last_deposits")],
        [InlineKeyboardButton(text="📤 Последние покупки", callback_data="last_purchases")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ])

def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить промокод", callback_data="admin_add_code")],
        [InlineKeyboardButton(text="❌ Удалить промокод", callback_data="admin_delete_code")],
        [InlineKeyboardButton(text="📋 Список промокодов", callback_data="admin_list_codes")],
        [InlineKeyboardButton(text="👥 Список пользователей", callback_data="admin_list_users")],
        [InlineKeyboardButton(text="🚫 Заблокировать", callback_data="admin_block_user")],
        [InlineKeyboardButton(text="✅ Разблокировать", callback_data="admin_unblock_user")],
        [InlineKeyboardButton(text="💰 Начислить баланс", callback_data="admin_add_balance")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="💲 Цена звезды", callback_data="admin_star_price")],
        [InlineKeyboardButton(text="🎁 Бонус", callback_data="admin_daily_bonus")],
        [InlineKeyboardButton(text="🔘 Добавить кнопку", callback_data="admin_add_button")],
        [InlineKeyboardButton(text="🗑 Удалить кнопку", callback_data="admin_delete_button")],
        [InlineKeyboardButton(text="🎫 Тикеты", callback_data="admin_tickets")],
        [InlineKeyboardButton(text="⚙️ Настройки API", callback_data="admin_api_settings")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ])

def get_api_settings_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 BOT_TOKEN", callback_data="api_set_BOT_TOKEN")],
        [InlineKeyboardButton(text="💎 API_TON", callback_data="api_set_API_TON")],
        [InlineKeyboardButton(text="🧠 GROQ_API_KEY", callback_data="api_set_GROQ_API_KEY")],
        [InlineKeyboardButton(text="🔑 MNEMONIC", callback_data="api_set_MNEMONIC")],
        [InlineKeyboardButton(text="🍪 STEL_SSID", callback_data="api_set_STEL_SSID")],
        [InlineKeyboardButton(text="🕐 STEL_DT", callback_data="api_set_STEL_DT")],
        [InlineKeyboardButton(text="🎟️ STEL_TON_TOKEN", callback_data="api_set_STEL_TON_TOKEN")],
        [InlineKeyboardButton(text="🎫 STEL_TOKEN", callback_data="api_set_STEL_TOKEN")],
        [InlineKeyboardButton(text="# FRAGMENT_HASH", callback_data="api_set_FRAGMENT_HASH")],
        [InlineKeyboardButton(text="🔐 FRAGMENT_PUBLICKEY", callback_data="api_set_FRAGMENT_PUBLICKEY")],
        [InlineKeyboardButton(text="👛 FRAGMENT_WALLETS", callback_data="api_set_FRAGMENT_WALLETS")],
        [InlineKeyboardButton(text="📍 FRAGMENT_ADDRES", callback_data="api_set_FRAGMENT_ADDRES")],
        [InlineKeyboardButton(text="👨‍💼 ADMIN_IDS", callback_data="api_set_ADMIN_IDS")],
        [InlineKeyboardButton(text="🔄 Перезагрузить", callback_data="api_reload")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_menu")]
    ])

async def show_main_menu(message_or_callback, db, edit=False):
    if isinstance(message_or_callback, CallbackQuery):
        user_id = message_or_callback.from_user.id
        message = message_or_callback.message
    else:
        user_id = message_or_callback.from_user.id
        message = message_or_callback
    balance = db.get_balance(user_id)
    text = f"💙 Главное меню\n\n💰 Ваш баланс: {balance:.2f} ₽"
    if edit and isinstance(message_or_callback, CallbackQuery):
        try:
            await message.edit_text(text, reply_markup=get_main_menu_keyboard(db, user_id))
        except:
            await message.answer(text, reply_markup=get_main_menu_keyboard(db, user_id))
    else:
        await message.answer(text, reply_markup=get_main_menu_keyboard(db, user_id))

def register_all_handlers(dp: Dispatcher, db, bot: Bot):
    
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message, state: FSMContext):
        user = message.from_user
        db.add_user(user.id, user.username, user.first_name, user.last_name)
        if db.is_user_blocked(user.id):
            await message.answer("🚫 Вы заблокированы и не можете использовать бота.")
            return
        if db.is_user_welcomed(user.id):
            await show_main_menu(message, db)
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✔️ Продолжить", callback_data="continue_welcome")]])
            await message.answer(f"👋 Добро пожаловать в {SHOP_NAME}\n\n🎁 Мы продаем TG-звезды, чтобы купить:\n- Оплатите в любой удобной валюте\n- Введите @user или свой аккаунт\n- Подтвердите и получите ⭐️\n\n💙 Нажимай кнопку ниже 👇", reply_markup=keyboard)
    
    @dp.callback_query(F.data == "continue_welcome")
    async def continue_welcome(callback: CallbackQuery):
        db.set_welcomed(callback.from_user.id)
        await callback.message.delete()
        await show_main_menu(callback, db)
    
    @dp.callback_query(F.data == "main_menu")
    async def main_menu_callback(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.delete()
        await show_main_menu(callback, db)
    
    @dp.callback_query(F.data == "buy_stars")
    async def buy_stars_callback(callback: CallbackQuery, state: FSMContext):
        await callback.message.delete()
        await callback.message.answer("⭐️ Купить звезды\n\nВведите количество звезд:", reply_markup=get_back_keyboard("main_menu"))
        await state.set_state(BuyStars.waiting_for_stars)
    
    @dp.message(BuyStars.waiting_for_stars)
    async def process_stars_amount(message: types.Message, state: FSMContext):
        try:
            stars = int(message.text.strip())
            if stars <= 0:
                await message.answer("❌ Количество звезд должно быть больше 0.")
                return
            star_price = float(db.get_setting("star_price", STAR_PRICE_RUB))
            total_cost = stars * star_price
            user_balance = db.get_balance(message.from_user.id)
            if user_balance < total_cost:
                await message.answer(f"❌ Недостаточно средств!\n\nСтоимость: {total_cost:.2f} ₽\nВаш баланс: {user_balance:.2f} ₽\nНе хватает: {(total_cost - user_balance):.2f} ₽", reply_markup=get_back_to_menu_keyboard())
                return
            await state.update_data(stars_amount=stars, total_cost=total_cost)
            username = f"@{message.from_user.username}" if message.from_user.username else "без username"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"👤 Себе, {username}", callback_data="send_to_self")], [InlineKeyboardButton(text="⬅️ Назад", callback_data="buy_stars")]])
            await message.answer(f"💰 Стоимость: {total_cost:.2f} ₽\n\n👤 Введите @username аккаунта:", reply_markup=keyboard)
            await state.set_state(BuyStars.waiting_for_username)
        except ValueError:
            await message.answer("❌ Введите корректное число.")
    
    @dp.message(BuyStars.waiting_for_username)
    async def process_username_text(message: types.Message, state: FSMContext):
        username = message.text.strip()
        if not username.startswith("@"):
            username = f"@{username}"
        checking_msg = await message.answer("🔍 Проверяю аккаунт...")
        client = FragmentClient()
        recipient = await client.fetch_recipient(username)
        await checking_msg.delete()
        if not recipient:
            await message.answer("❌ Аккаунт не найден в Fragment.", reply_markup=get_back_keyboard("buy_stars"))
            return
        await state.update_data(recipient_username=username)
        data = await state.get_data()
        recipient = data.get("recipient_username")
        stars = data.get("stars_amount")
        total_cost = data.get("total_cost")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_purchase")], [InlineKeyboardButton(text="⬅️ Назад", callback_data="buy_stars")]])
        await message.answer(f"✔️ Подтверждение:\n\n👤 Кому: {recipient}\n⭐️ Звезд: {stars}\n💰 К оплате: {total_cost:.2f} ₽", reply_markup=keyboard)
        await state.set_state(BuyStars.waiting_for_confirm)
    
    @dp.callback_query(F.data == "send_to_self", BuyStars.waiting_for_username)
    async def process_send_to_self(callback: CallbackQuery, state: FSMContext):
        user = callback.from_user
        username = f"@{user.username}" if user.username else None
        if not username:
            await callback.answer("❌ У вас нет username!", show_alert=True)
            return
        checking_msg = await callback.message.answer("🔍 Проверяю аккаунт...")
        client = FragmentClient()
        recipient = await client.fetch_recipient(username)
        await checking_msg.delete()
        if not recipient:
            await callback.message.answer("❌ Аккаунт не найден.", reply_markup=get_back_keyboard("buy_stars"))
            return
        await state.update_data(recipient_username=username)
        data = await state.get_data()
        recipient = data.get("recipient_username")
        stars = data.get("stars_amount")
        total_cost = data.get("total_cost")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_purchase")], [InlineKeyboardButton(text="⬅️ Назад", callback_data="buy_stars")]])
        await callback.message.answer(f"✔️ Подтверждение:\n\n👤 Кому: {recipient}\n⭐️ Звезд: {stars}\n💰 К оплате: {total_cost:.2f} ₽", reply_markup=keyboard)
        await state.set_state(BuyStars.waiting_for_confirm)
    
    @dp.callback_query(F.data == "confirm_purchase", BuyStars.waiting_for_confirm)
    async def process_confirm_purchase(callback: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        recipient = data.get("recipient_username")
        stars = data.get("stars_amount")
        total_cost = data.get("total_cost")
        await callback.message.delete()
        sending_msg = await callback.message.answer("🎁 Отправляю...")
        purchase_id = db.add_star_purchase(callback.from_user.id, recipient, stars, total_cost)
        try:
            success, tx_hash = await buy_stars_process(recipient, stars)
            await asyncio.sleep(5)
            await sending_msg.delete()
            if success and tx_hash:
                db.subtract_balance(callback.from_user.id, total_cost)
                db.update_star_purchase(purchase_id, tx_hash, "completed")
                db.add_transaction(callback.from_user.id, "purchase", -total_cost, f"Покупка {stars} звезд")
                await callback.message.answer(f"✅ Успешно!\n\n⭐️ Отправлено: {stars}\n👤 Получатель: {recipient}\n💰 Списано: {total_cost:.2f} ₽\n\n🔗 https://tonviewer.com/transaction/{tx_hash}\n\nСделано с 💙", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💙 Главное меню", callback_data="main_menu")]]))
            else:
                db.update_star_purchase(purchase_id, None, "failed")
                await callback.message.answer("❌ Ошибка. Обратитесь к админу.", reply_markup=get_back_to_menu_keyboard())
        except Exception as e:
            logging.error(f"Ошибка: {e}")
            db.update_star_purchase(purchase_id, None, "failed")
            await callback.message.answer(f"❌ Ошибка: {str(e)}", reply_markup=get_back_to_menu_keyboard())
        await state.clear()
    
    @dp.callback_query(F.data == "profile")
    async def profile_callback(callback: CallbackQuery):
        await callback.message.delete()
        user = db.get_user(callback.from_user.id)
        user_id, username, first_name, last_name, balance, is_blocked, is_welcomed, created_at, last_daily = user
        name = f"{first_name or ''} {last_name or ''}".strip() or "Без имени"
        username_text = f"@{username}" if username else "Без username"
        created_date = created_at[:10] if created_at else "Неизвестно"
        await callback.message.answer(f"👤 Профиль\n\n🆔 ID: <code>{user_id}</code>\n📝 Username: {username_text}\n👤 Имя: {name}\n💰 Баланс: {balance:.2f} ₽\n📅 Регистрация: {created_date}", reply_markup=get_profile_keyboard(), parse_mode="HTML")
    
    @dp.callback_query(F.data == "add_balance")
    async def add_balance_callback(callback: CallbackQuery):
        await callback.answer("💳 В разработке", show_alert=True)
    
    @dp.callback_query(F.data == "daily_bonus")
    async def daily_bonus_callback(callback: CallbackQuery):
        if db.can_claim_daily_bonus(callback.from_user.id):
            bonus_amount = float(db.get_setting("daily_bonus", DAILY_BONUS_AMOUNT))
            db.claim_daily_bonus(callback.from_user.id, bonus_amount)
            db.add_transaction(callback.from_user.id, "bonus", bonus_amount, "Ежедневный бонус")
            await callback.answer(f"🎁 Получено {bonus_amount:.2f} ₽!", show_alert=True)
            await profile_callback(callback)
        else:
            await callback.answer("⏳ Уже получали сегодня!", show_alert=True)
    
    @dp.callback_query(F.data == "use_promo")
    async def use_promo_callback(callback: CallbackQuery, state: FSMContext):
        await callback.message.delete()
        await callback.message.answer("🎫 Введите промокод:", reply_markup=get_back_keyboard("profile"))
        await state.set_state(ProfileStates.waiting_for_promo_code)
    
    @dp.message(ProfileStates.waiting_for_promo_code)
    async def process_promo_code(message: types.Message, state: FSMContext):
        code = message.text.strip()
        promo = db.check_promo_code(code)
        if not promo:
            await message.answer("❌ Код не найден.", reply_markup=get_back_keyboard("profile"))
            return
        if promo["is_used"]:
            await message.answer("❌ Код использован.", reply_markup=get_back_keyboard("profile"))
            return
        if db.use_promo_code(code, message.from_user.id):
            db.add_balance(message.from_user.id, promo["balance_amount"])
            db.add_transaction(message.from_user.id, "promo", promo["balance_amount"], f"Промокод {code}")
            await message.answer(f"✅ Активирован!\n\n💰 Начислено: {promo['balance_amount']:.2f} ₽", reply_markup=get_back_to_menu_keyboard())
        else:
            await message.answer("❌ Ошибка активации.", reply_markup=get_back_keyboard("profile"))
        await state.clear()
    
    @dp.callback_query(F.data == "last_deposits")
    async def last_deposits_callback(callback: CallbackQuery):
        transactions = db.get_user_transactions(callback.from_user.id, "deposit", 10)
        if not transactions:
            await callback.answer("📥 Пополнений нет", show_alert=True)
            return
        text = "📥 Последние пополнения:\n\n"
        for trans_type, amount, description, created_at in transactions:
            text += f"💰 +{amount:.2f} ₽\n📝 {description}\n📅 {created_at[:19]}\n\n"
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=get_back_keyboard("profile"))
    
    @dp.callback_query(F.data == "last_purchases")
    async def last_purchases_callback(callback: CallbackQuery):
        purchases = db.get_user_star_purchases(callback.from_user.id, 10)
        if not purchases:
            await callback.answer("📤 Покупок нет", show_alert=True)
            return
        text = "📤 Последние покупки:\n\n"
        for recipient, stars, balance_spent, status, created_at in purchases:
            status_emoji = "✅" if status == "completed" else "❌"
            text += f"{status_emoji} {stars} ⭐️ → {recipient}\n💰 {balance_spent:.2f} ₽\n📅 {created_at[:19]}\n\n"
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=get_back_keyboard("profile"))
    
    @dp.callback_query(F.data == "support")
    async def support_callback(callback: CallbackQuery):
        await callback.message.delete()
        text = f"🆘 Поддержка\n\n❓ FAQ:\n\nQ: Как купить?\nA: Пополните баланс, выберите звезды.\n\nQ: Как пополнить?\nA: Через профиль.\n\nQ: Цена?\nA: {db.get_setting('star_price', STAR_PRICE_RUB)} ₽"
        await callback.message.answer(text, reply_markup=get_support_keyboard())
    
    @dp.callback_query(F.data == "create_ticket")
    async def create_ticket_callback(callback: CallbackQuery, state: FSMContext):
        if db.get_user_open_ticket(callback.from_user.id):
            await callback.answer("❌ Уже есть открытый тикет!", show_alert=True)
            return
        await callback.message.delete()
        await callback.message.answer("📝 Тема тикета (до 20 символов):", reply_markup=get_back_keyboard("support"))
        await state.set_state(TicketStates.waiting_for_subject)
    
    @dp.message(TicketStates.waiting_for_subject)
    async def process_ticket_subject(message: types.Message, state: FSMContext):
        subject = message.text.strip()[:20]
        await state.update_data(ticket_subject=subject)
        await message.answer(f"Тема: {subject}\n\nВведите сообщение:", reply_markup=get_back_keyboard("support"))
        await state.set_state(TicketStates.waiting_for_message)
    
    @dp.message(TicketStates.waiting_for_message)
    async def process_ticket_message(message: types.Message, state: FSMContext):
        data = await state.get_data()
        subject = data.get("ticket_subject")
        ticket_id = db.create_ticket(message.from_user.id, subject)
        db.add_ticket_message(ticket_id, message.from_user.id, message.text)
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, f"🎫 Новый тикет #{ticket_id}\n\n👤 От: {message.from_user.first_name} (@{message.from_user.username or 'нет'})\n🆔 ID: {message.from_user.id}\n📋 Тема: {subject}\n💬 {message.text}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📩 Ответить", callback_data=f"admin_reply_{ticket_id}")]]))
            except:
                pass
        await message.answer(f"✅ Тикет #{ticket_id} создан!", reply_markup=get_back_to_menu_keyboard())
        await state.clear()
    
    @dp.callback_query(F.data == "my_tickets")
    async def my_tickets_callback(callback: CallbackQuery):
        tickets = db.get_user_tickets(callback.from_user.id)
        if not tickets:
            await callback.answer("🎫 Тикетов нет", show_alert=True)
            return
        keyboard_buttons = []
        for ticket_id, subject, status, created_at in tickets:
            status_emoji = "🟢" if status == "open" else "🔴"
            keyboard_buttons.append([InlineKeyboardButton(text=f"{status_emoji} #{ticket_id} - {subject}", callback_data=f"view_ticket_{ticket_id}")])
        keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="support")])
        await callback.message.delete()
        await callback.message.answer("🎫 Ваши тикеты:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons))
    
    @dp.callback_query(F.data.startswith("view_ticket_"))
    async def view_ticket_callback(callback: CallbackQuery):
        ticket_id = int(callback.data.split("_")[2])
        ticket = db.get_ticket(ticket_id)
        if not ticket or ticket[1] != callback.from_user.id:
            await callback.answer("❌ Тикет не найден", show_alert=True)
            return
        messages = db.get_ticket_messages(ticket_id)
        text = f"🎫 Тикет #{ticket_id}\n📋 Тема: {ticket[2]}\n\n💬 Диалог:\n\n"
        for msg_user_id, msg_text, msg_created_at in messages:
            if msg_user_id == callback.from_user.id:
                text += f"👤 Вы ({msg_created_at[:19]}):\n{msg_text}\n\n"
            else:
                text += f"👨‍💼 Админ ({msg_created_at[:19]}):\n{msg_text}\n\n"
        keyboard_buttons = []
        if ticket[3] == "open":
            keyboard_buttons.append([InlineKeyboardButton(text="💬 Добавить сообщение", callback_data=f"add_msg_{ticket_id}")])
            keyboard_buttons.append([InlineKeyboardButton(text="✅ Закрыть тикет", callback_data=f"close_ticket_{ticket_id}")])
        keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="my_tickets")])
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons))
    
    @dp.callback_query(F.data.startswith("add_msg_"))
    async def add_message_callback(callback: CallbackQuery, state: FSMContext):
        ticket_id = int(callback.data.split("_")[2])
        await state.update_data(ticket_id=ticket_id)
        await callback.message.delete()
        await callback.message.answer("💬 Введите сообщение:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=f"view_ticket_{ticket_id}")]]))
        await state.set_state(TicketStates.waiting_for_ticket_message)
    
    @dp.message(TicketStates.waiting_for_ticket_message)
    async def process_ticket_new_message(message: types.Message, state: FSMContext):
        data = await state.get_data()
        ticket_id = data.get("ticket_id")
        db.add_ticket_message(ticket_id, message.from_user.id, message.text)
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, f"💬 Новое сообщение в тикете #{ticket_id}\n\n👤 От: {message.from_user.first_name}\n💬 {message.text}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📩 Ответить", callback_data=f"admin_reply_{ticket_id}")]]))
            except:
                pass
        await message.answer("✅ Сообщение отправлено!", reply_markup=get_back_keyboard(f"view_ticket_{ticket_id}"))
        await state.clear()
    
    @dp.callback_query(F.data.startswith("close_ticket_"))
    async def close_ticket_callback(callback: CallbackQuery):
        ticket_id = int(callback.data.split("_")[2])
        ticket = db.get_ticket(ticket_id)
        if ticket and ticket[1] == callback.from_user.id:
            db.close_ticket(ticket_id)
            await callback.answer("✅ Тикет закрыт", show_alert=True)
            await callback.message.delete()
            await support_callback(callback)
    
    @dp.callback_query(F.data == "ai_help")
    async def ai_help_callback(callback: CallbackQuery, state: FSMContext):
        await callback.message.delete()
        await callback.message.answer("🤖 ИИ-помощник\n\nЗадайте вопрос:", reply_markup=get_back_keyboard("support"))
        await state.set_state(TicketStates.waiting_for_ai_question)
    
    @dp.message(TicketStates.waiting_for_ai_question)
    async def process_ai_question(message: types.Message, state: FSMContext):
        thinking_msg = await message.answer("🤔 Думаю...")
        response = await get_groq_response(message.text)
        await thinking_msg.delete()
        await message.answer(f"🤖 Ответ:\n\n{response}", reply_markup=get_back_keyboard("support"))
        await state.clear()
    
    @dp.callback_query(F.data == "admin_menu")
    async def admin_menu_callback(callback: CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        await state.clear()
        await callback.message.delete()
        await callback.message.answer("🔥 Админ-меню\n\nВыберите действие:", reply_markup=get_admin_keyboard())
    
    @dp.callback_query(F.data == "admin_add_code")
    async def admin_add_code_callback(callback: CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id):
            return
        await callback.message.delete()
        await callback.message.answer("➕ Введите код:", reply_markup=get_back_keyboard("admin_menu"))
        await state.set_state(AdminStates.waiting_for_new_code)
    
    @dp.message(AdminStates.waiting_for_new_code)
    async def process_new_code(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        code = message.text.strip()
        await state.update_data(new_code=code)
        await message.answer(f"Код: <code>{code}</code>\n\nВведите сумму (₽):", reply_markup=get_back_keyboard("admin_menu"), parse_mode="HTML")
        await state.set_state(AdminStates.waiting_for_new_balance)
    
    @dp.message(AdminStates.waiting_for_new_balance)
    async def process_new_balance(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        try:
            balance = float(message.text.strip())
            if balance <= 0:
                await message.answer("❌ Сумма должна быть больше 0.")
                return
            data = await state.get_data()
            code = data.get("new_code")
            if db.add_promo_code(code, balance):
                await message.answer(f"✅ Промокод добавлен!\n\nКод: <code>{code}</code>\nБаланс: {balance:.2f} ₽", reply_markup=get_admin_keyboard(), parse_mode="HTML")
            else:
                await message.answer("❌ Промокод существует.", reply_markup=get_admin_keyboard())
            await state.clear()
        except ValueError:
            await message.answer("❌ Введите число.")
    
    @dp.callback_query(F.data == "admin_delete_code")
    async def admin_delete_code_callback(callback: CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id):
            return
        await callback.message.delete()
        await callback.message.answer("❌ Введите код для удаления:", reply_markup=get_back_keyboard("admin_menu"))
        await state.set_state(AdminStates.waiting_for_delete_code)
    
    @dp.message(AdminStates.waiting_for_delete_code)
    async def process_delete_code(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        code = message.text.strip()
        if db.delete_promo_code(code):
            await message.answer(f"✅ Промокод <code>{code}</code> удален!", reply_markup=get_admin_keyboard(), parse_mode="HTML")
        else:
            await message.answer("❌ Промокод не найден.", reply_markup=get_admin_keyboard())
        await state.clear()
    
    @dp.callback_query(F.data == "admin_list_codes")
    async def admin_list_codes_callback(callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            return
        codes = db.get_all_promo_codes()
        if not codes:
            await callback.message.delete()
            await callback.message.answer("📋 Промокодов нет.", reply_markup=get_back_keyboard("admin_menu"))
            return
        text = "📋 Список промокодов\n\n"
        for code, balance, is_used, created_at, used_at, used_by in codes[:30]:
            status = "✅ Использован" if is_used else "⏳ Активен"
            text += f"🔹 <code>{code}</code> - {balance:.2f} ₽\n   {status}\n\n"
        if len(codes) > 30:
            text += f"\n... и еще {len(codes) - 30}"
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=get_back_keyboard("admin_menu"), parse_mode="HTML")
    
    @dp.callback_query(F.data == "admin_list_users")
    async def admin_list_users_callback(callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            return
        users = db.get_all_users()
        if not users:
            await callback.message.delete()
            await callback.message.answer("👥 Пользователей нет.", reply_markup=get_back_keyboard("admin_menu"))
            return
        text = "👥 Список пользователей\n\n"
        for user_id, username, first_name, last_name, balance, is_blocked, created_at in users[:15]:
            name = f"{first_name or ''} {last_name or ''}".strip() or "Без имени"
            username_text = f"@{username}" if username else "Без username"
            status = "🚫 Заблокирован" if is_blocked else "✅ Активен"
            text += f"👤 {name} ({username_text})\n   ID: <code>{user_id}</code>\n   Баланс: {balance:.2f} ₽\n   {status}\n\n"
        if len(users) > 15:
            text += f"\n... и еще {len(users) - 15}"
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=get_back_keyboard("admin_menu"), parse_mode="HTML")
    
    @dp.callback_query(F.data == "admin_block_user")
    async def admin_block_user_callback(callback: CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id):
            return
        await callback.message.delete()
        await callback.message.answer("🚫 Введите ID пользователя:", reply_markup=get_back_keyboard("admin_menu"))
        await state.set_state(AdminStates.waiting_for_block_user_id)
    
    @dp.message(AdminStates.waiting_for_block_user_id)
    async def process_block_user(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        try:
            user_id = int(message.text.strip())
            if db.block_user(user_id):
                await message.answer(f"✅ Пользователь <code>{user_id}</code> заблокирован!", reply_markup=get_admin_keyboard(), parse_mode="HTML")
            else:
                await message.answer("❌ Пользователь не найден.", reply_markup=get_admin_keyboard())
            await state.clear()
        except ValueError:
            await message.answer("❌ Введите ID.")
    
    @dp.callback_query(F.data == "admin_unblock_user")
    async def admin_unblock_user_callback(callback: CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id):
            return
        await callback.message.delete()
        await callback.message.answer("✅ Введите ID пользователя:", reply_markup=get_back_keyboard("admin_menu"))
        await state.set_state(AdminStates.waiting_for_unblock_user_id)
    
    @dp.message(AdminStates.waiting_for_unblock_user_id)
    async def process_unblock_user(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        try:
            user_id = int(message.text.strip())
            if db.unblock_user(user_id):
                await message.answer(f"✅ Пользователь <code>{user_id}</code> разблокирован!", reply_markup=get_admin_keyboard(), parse_mode="HTML")
            else:
                await message.answer("❌ Пользователь не найден.", reply_markup=get_admin_keyboard())
            await state.clear()
        except ValueError:
            await message.answer("❌ Введите ID.")
    
    @dp.callback_query(F.data == "admin_add_balance")
    async def admin_add_balance_callback(callback: CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id):
            return
        await callback.message.delete()
        await callback.message.answer("💰 Введите ID пользователя:", reply_markup=get_back_keyboard("admin_menu"))
        await state.set_state(AdminStates.waiting_for_add_balance_user_id)
    
    @dp.message(AdminStates.waiting_for_add_balance_user_id)
    async def process_add_balance_user_id(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        try:
            user_id = int(message.text.strip())
            if not db.get_user(user_id):
                await message.answer("❌ Пользователь не найден.")
                return
            await state.update_data(target_user_id=user_id)
            await message.answer(f"ID: <code>{user_id}</code>\n\nВведите сумму (₽):", reply_markup=get_back_keyboard("admin_menu"), parse_mode="HTML")
            await state.set_state(AdminStates.waiting_for_add_balance_amount)
        except ValueError:
            await message.answer("❌ Введите ID.")
    
    @dp.message(AdminStates.waiting_for_add_balance_amount)
    async def process_add_balance_amount(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        try:
            amount = float(message.text.strip())
            if amount <= 0:
                await message.answer("❌ Сумма должна быть больше 0.")
                return
            data = await state.get_data()
            user_id = data.get("target_user_id")
            db.add_balance(user_id, amount)
            db.add_transaction(user_id, "admin_add", amount, f"Начисление администратором")
            await message.answer(f"✅ Баланс начислен!\n\nПользователь: <code>{user_id}</code>\nСумма: {amount:.2f} ₽", reply_markup=get_admin_keyboard(), parse_mode="HTML")
            try:
                await bot.send_message(user_id, f"💰 Вам начислено {amount:.2f} ₽ администратором!")
            except:
                pass
            await state.clear()
        except ValueError:
            await message.answer("❌ Введите число.")
    
    @dp.callback_query(F.data == "admin_broadcast")
    async def admin_broadcast_callback(callback: CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id):
            return
        await callback.message.delete()
        await callback.message.answer("📢 Введите текст рассылки:", reply_markup=get_back_keyboard("admin_menu"))
        await state.set_state(AdminStates.waiting_for_broadcast)
    
    @dp.message(AdminStates.waiting_for_broadcast)
    async def process_broadcast(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        users = db.get_all_users()
        success_count = 0
        fail_count = 0
        status_msg = await message.answer(f"📤 Рассылка: 0/{len(users)}")
        for idx, user_data in enumerate(users, 1):
            user_id = user_data[0]
            is_blocked = user_data[5]
            if not is_blocked:
                try:
                    await bot.send_message(user_id, message.text)
                    success_count += 1
                except:
                    fail_count += 1
            if idx % 10 == 0:
                try:
                    await status_msg.edit_text(f"📤 Рассылка: {idx}/{len(users)}")
                except:
                    pass
        await status_msg.delete()
        await message.answer(f"✅ Рассылка завершена!\n\nОтправлено: {success_count}\nОшибок: {fail_count}", reply_markup=get_admin_keyboard())
        await state.clear()
    
    @dp.callback_query(F.data == "admin_star_price")
    async def admin_star_price_callback(callback: CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id):
            return
        current_price = db.get_setting("star_price", STAR_PRICE_RUB)
        await callback.message.delete()
        await callback.message.answer(f"💲 Текущая цена: {current_price} ₽\n\nВведите новую цену:", reply_markup=get_back_keyboard("admin_menu"))
        await state.set_state(AdminStates.waiting_for_star_price)
    
    @dp.message(AdminStates.waiting_for_star_price)
    async def process_star_price(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        try:
            price = float(message.text.strip())
            if price <= 0:
                await message.answer("❌ Цена должна быть больше 0.")
                return
            db.set_setting("star_price", str(price))
            await message.answer(f"✅ Цена изменена на {price:.2f} ₽", reply_markup=get_admin_keyboard())
            await state.clear()
        except ValueError:
            await message.answer("❌ Введите число.")
    
    @dp.callback_query(F.data == "admin_daily_bonus")
    async def admin_daily_bonus_callback(callback: CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id):
            return
        current_bonus = db.get_setting("daily_bonus", DAILY_BONUS_AMOUNT)
        await callback.message.delete()
        await callback.message.answer(f"🎁 Текущий бонус: {current_bonus} ₽\n\nВведите новую сумму:", reply_markup=get_back_keyboard("admin_menu"))
        await state.set_state(AdminStates.waiting_for_daily_bonus)
    
    @dp.message(AdminStates.waiting_for_daily_bonus)
    async def process_daily_bonus(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        try:
            bonus = float(message.text.strip())
            if bonus <= 0:
                await message.answer("❌ Сумма должна быть больше 0.")
                return
            db.set_setting("daily_bonus", str(bonus))
            await message.answer(f"✅ Бонус изменен на {bonus:.2f} ₽", reply_markup=get_admin_keyboard())
            await state.clear()
        except ValueError:
            await message.answer("❌ Введите число.")
    
    @dp.callback_query(F.data == "admin_add_button")
    async def admin_add_button_callback(callback: CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id):
            return
        await callback.message.delete()
        await callback.message.answer("🔘 Введите текст кнопки:", reply_markup=get_back_keyboard("admin_menu"))
        await state.set_state(AdminStates.waiting_for_button_text)
    
    @dp.message(AdminStates.waiting_for_button_text)
    async def process_button_text(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        button_text = message.text.strip()
        await state.update_data(button_text=button_text)
        await message.answer(f"Текст: {button_text}\n\nВведите URL (или '-' без ссылки):", reply_markup=get_back_keyboard("admin_menu"))
        await state.set_state(AdminStates.waiting_for_button_url)
    
    @dp.message(AdminStates.waiting_for_button_url)
    async def process_button_url(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        button_url = message.text.strip()
        if button_url == "-":
            button_url = None
        data = await state.get_data()
        button_text = data.get("button_text")
        db.add_menu_button(button_text, button_url)
        await message.answer(f"✅ Кнопка добавлена!\n\nТекст: {button_text}\nURL: {button_url or 'Без ссылки'}", reply_markup=get_admin_keyboard())
        await state.clear()
    
    @dp.callback_query(F.data == "admin_delete_button")
    async def admin_delete_button_callback(callback: CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id):
            return
        buttons = db.get_menu_buttons()
        if not buttons:
            await callback.answer("❌ Нет кнопок", show_alert=True)
            return
        await callback.message.delete()
        text = "🗑 Список кнопок:\n\n"
        for btn_id, btn_text, btn_url in buttons:
            text += f"ID: {btn_id} - {btn_text}\n"
        text += "\nВведите ID для удаления:"
        await callback.message.answer(text, reply_markup=get_back_keyboard("admin_menu"))
        await state.set_state(AdminStates.waiting_for_delete_button_id)
    
    @dp.message(AdminStates.waiting_for_delete_button_id)
    async def process_delete_button_id(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        try:
            button_id = int(message.text.strip())
            if db.delete_menu_button(button_id):
                await message.answer(f"✅ Кнопка ID {button_id} удалена!", reply_markup=get_admin_keyboard())
            else:
                await message.answer("❌ Кнопка не найдена.", reply_markup=get_admin_keyboard())
            await state.clear()
        except ValueError:
            await message.answer("❌ Введите ID.")
    
    @dp.callback_query(F.data == "admin_tickets")
    async def admin_tickets_callback(callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            return
        tickets = db.get_all_open_tickets()
        if not tickets:
            await callback.answer("🎫 Нет открытых тикетов", show_alert=True)
            return
        keyboard_buttons = []
        for ticket_id, user_id, subject, created_at, username, first_name in tickets:
            keyboard_buttons.append([InlineKeyboardButton(text=f"#{ticket_id} - {subject} ({first_name})", callback_data=f"admin_view_ticket_{ticket_id}")])
        keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_menu")])
        await callback.message.delete()
        await callback.message.answer("🎫 Открытые тикеты:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons))
    
    @dp.callback_query(F.data.startswith("admin_view_ticket_"))
    async def admin_view_ticket_callback(callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            return
        ticket_id = int(callback.data.split("_")[3])
        ticket = db.get_ticket(ticket_id)
        if not ticket:
            await callback.answer("❌ Тикет не найден", show_alert=True)
            return
        messages = db.get_ticket_messages(ticket_id)
        text = f"🎫 Тикет #{ticket_id}\n📋 Тема: {ticket[2]}\n👤 От: ID {ticket[1]}\n\n💬 Диалог:\n\n"
        for msg_user_id, msg_text, msg_created_at in messages:
            if msg_user_id == ticket[1]:
                text += f"👤 Пользователь ({msg_created_at[:19]}):\n{msg_text}\n\n"
            else:
                text += f"👨‍💼 Админ ({msg_created_at[:19]}):\n{msg_text}\n\n"
        keyboard_buttons = [[InlineKeyboardButton(text="📩 Ответить", callback_data=f"admin_reply_{ticket_id}")], [InlineKeyboardButton(text="✅ Закрыть", callback_data=f"admin_close_{ticket_id}")], [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_tickets")]]
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons))
    
    @dp.callback_query(F.data.startswith("admin_reply_"))
    async def admin_reply_callback(callback: CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id):
            return
        ticket_id = int(callback.data.split("_")[2])
        await state.update_data(reply_ticket_id=ticket_id)
        await callback.message.delete()
        await callback.message.answer(f"📩 Ответ на тикет #{ticket_id}\n\nВведите сообщение:", reply_markup=get_back_keyboard("admin_tickets"))
        await state.set_state(AdminStates.waiting_for_ticket_response)
    
    @dp.message(AdminStates.waiting_for_ticket_response)
    async def process_admin_ticket_response(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        data = await state.get_data()
        ticket_id = data.get("reply_ticket_id")
        ticket = db.get_ticket(ticket_id)
        if not ticket:
            await message.answer("❌ Тикет не найден.")
            await state.clear()
            return
        user_id = ticket[1]
        db.add_ticket_message(ticket_id, message.from_user.id, message.text)
        try:
            await bot.send_message(user_id, f"💬 Новый ответ на тикет #{ticket_id}\n\n👨‍💼 Администратор:\n{message.text}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📩 Просмотреть", callback_data=f"view_ticket_{ticket_id}")]]))
        except:
            pass
        await message.answer("✅ Ответ отправлен!", reply_markup=get_admin_keyboard())
        await state.clear()
    
    @dp.callback_query(F.data.startswith("admin_close_"))
    async def admin_close_ticket_callback(callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            return
        ticket_id = int(callback.data.split("_")[2])
        ticket = db.get_ticket(ticket_id)
        if ticket:
            db.close_ticket(ticket_id)
            try:
                await bot.send_message(ticket[1], f"✅ Ваш тикет #{ticket_id} закрыт администратором.")
            except:
                pass
            await callback.answer("✅ Тикет закрыт", show_alert=True)
            await callback.message.delete()
            await admin_tickets_callback(callback)
    
    @dp.callback_query(F.data == "admin_api_settings")
    async def admin_api_settings_callback(callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            return
        await callback.message.delete()
        await callback.message.answer("⚙️ Настройки API\n\nВыберите параметр:", reply_markup=get_api_settings_keyboard())
    
    @dp.callback_query(F.data.startswith("api_set_"))
    async def api_set_callback(callback: CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id):
            return
        api_key = callback.data.replace("api_set_", "")
        await state.update_data(api_key=api_key)
        current_value = get_config(api_key, "Не установлено")
        if len(current_value) > 50:
            current_value = current_value[:50] + "..."
        api_names = {"BOT_TOKEN": "Токен бота", "API_TON": "API ключ TON", "GROQ_API_KEY": "API ключ Groq", "MNEMONIC": "Мнемоническая фраза (через запятую)", "STEL_SSID": "STEL_SSID", "STEL_DT": "STEL_DT", "STEL_TON_TOKEN": "STEL_TON_TOKEN", "STEL_TOKEN": "STEL_TOKEN", "FRAGMENT_HASH": "Fragment Hash", "FRAGMENT_PUBLICKEY": "Fragment Public Key", "FRAGMENT_WALLETS": "Fragment Wallets", "FRAGMENT_ADDRES": "Fragment Address", "ADMIN_IDS": "ID администраторов (через запятую)"}
        await callback.message.delete()
        await callback.message.answer(f"⚙️ Настройка: {api_names.get(api_key, api_key)}\n\nТекущее значение:\n<code>{current_value}</code>\n\nВведите новое значение:", reply_markup=get_back_keyboard("admin_api_settings"), parse_mode="HTML")
        await state.set_state(AdminStates.waiting_for_api_value)
    
    @dp.message(AdminStates.waiting_for_api_value)
    async def process_api_value(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        data = await state.get_data()
        api_key = data.get("api_key")
        new_value = message.text.strip()
        if api_key == "MNEMONIC":
            if " " in new_value and "," not in new_value:
                new_value = new_value.replace(" ", ",")
            words = [w.strip() for w in new_value.replace(",", " ").split() if w.strip()]
            if len(words) != 24:
                await message.answer(f"❌ Ошибка! Должно быть 24 слова.\nВы ввели: {len(words)} слов.\n\nПопробуйте еще раз:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_api_settings")]]))
                return
            new_value = ",".join(words)
        elif api_key == "ADMIN_IDS":
            if " " in new_value and "," not in new_value:
                new_value = new_value.replace(" ", ",")
            ids = [i.strip() for i in new_value.replace(",", " ").split() if i.strip()]
            try:
                [int(i) for i in ids]
                new_value = ",".join(ids)
            except ValueError:
                await message.answer(f"❌ Ошибка! ADMIN_IDS должны быть числами.\n\nПример: 123456789,987654321\n\nПопробуйте еще раз:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_api_settings")]]))
                return
        update_config(api_key, new_value)
        preview_value = new_value
        if len(preview_value) > 100:
            preview_value = preview_value[:100] + "..."
        await message.answer(f"✅ Параметр {api_key} обновлен!\n\nНовое значение:\n<code>{preview_value}</code>\n\n⚠️ Нажмите '🔄 Перезагрузить' для применения.", reply_markup=get_api_settings_keyboard(), parse_mode="HTML")
        await state.clear()
    
    @dp.callback_query(F.data == "api_reload")
    async def api_reload_callback(callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            return
        try:
            reload_config()
            await callback.answer("✅ Конфигурация перезагружена!", show_alert=True)
        except Exception as e:
            await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
    
    @dp.callback_query(F.data == "admin_stats")
    async def admin_stats_callback(callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            return
        stats = db.get_stats()
        text = f"📊 Статистика бота\n\n👥 Всего пользователей: <b>{stats['total_users']}</b>\n🚫 Заблокировано: <b>{stats['blocked_users']}</b>\n\n🎫 Всего промокодов: <b>{stats['total_codes']}</b>\n✅ Использовано: <b>{stats['used_codes']}</b>\n\n💳 Завершенных покупок: <b>{stats['completed_purchases']}</b>\n⭐️ Всего выдано звезд: <b>{stats['total_stars']}</b>\n\n💰 Общий баланс пользователей: <b>{stats['total_balance']:.2f} ₽</b>"
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=get_back_keyboard("admin_menu"), parse_mode="HTML")
