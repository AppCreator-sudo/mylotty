import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from uuid import uuid4
from typing import Dict, Optional
from cryptopay import CryptoPay
import random
from db import AsyncDatabase
import os
from dotenv import load_dotenv

load_dotenv()
db = AsyncDatabase(os.getenv("DATABASE_URL"))

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
API_TOKEN = os.getenv('API_TOKEN')
CRYPTOPAY_TOKEN = os.getenv('CRYPTOPAY_TOKEN')

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()

# Инициализация CryptoPay
cryptopay = CryptoPay(token=CRYPTOPAY_TOKEN)

ADMIN_ID = int(os.getenv('ADMIN_ID'))  # Замените на свой Telegram user_id

# Словарь переводов
translations = {
    "start": {
        "ru": "🎉 Добро пожаловать!\nВаш баланс: {balance:.2f} TON",
        "en": "🎉 Welcome!\nYour balance: {balance:.2f} TON"
    },
    "choose_language": {
        "ru": "Выберите язык:",
        "en": "Select language:"
    },
    "button_ru": {
        "ru": "Русский",
        "en": "Russian"
    },
    "button_en": {
        "ru": "Английский",
        "en": "English"
    },
    "play": {
        "ru": "🦋 Играть",
        "en": "🦋 Play"
    },
    "balance": {
        "ru": "💰 Баланс",
        "en": "💰 Balance"
    },
    "deposit": {
        "ru": "💳 Пополнить",
        "en": "💳 Deposit"
    },
    "withdraw": {
        "ru": "📤 Вывод",
        "en": "📤 Withdraw"
    },
    "promo_btn": {
        "ru": "🎁 Акции",
        "en": "🎁 Promotions"
    },
    "rules_btn": {
        "ru": "📜 Правила",
        "en": "📜 Rules"
    },
    "referral": {
        "ru": "👥 Рефералы",
        "en": "👥 Referrals"
    },
    "back": {
        "ru": "‹ Назад",
        "en": "‹ Back"
    },
    "main_menu": {
        "ru": "🏠 В меню",
        "en": "🏠 Main menu"
    },
    "change_lang": {
        "ru": "🌐 Язык",
        "en": "🌐 Language"
    },
    "add10": {
        "ru": "💸 Начислить 10 TON",
        "en": "💸 Add 10 TON"
    },
    "agree_lottery": {
        "ru": "🎰 Перед началом игры вы должны согласиться с тем, что выигрыши определяются случайным образом и не гарантированы.\n\nНажимая 'Продолжить', вы подтверждаете согласие с этими условиями.",
        "en": "🎰 Before you start playing, you must agree that winnings are determined randomly and are not guaranteed.\n\nBy clicking 'Continue', you confirm your agreement with these terms."
    },
    "agree_button": {
        "ru": "✅ Я согласен(на)",
        "en": "✅ I agree"
    },
    "choose_tickets": {
        "ru": "🎟️ Выберите количество билетов:",
        "en": "🎟️ Choose the number of tickets:"
    },
    "ticket_1": {
        "ru": "1 билет — 1 TON",
        "en": "1 ticket — 1 TON"
    },
    "ticket_3": {
        "ru": "3 билета — 2.9 TON",
        "en": "3 tickets — 2.9 TON"
    },
    "ticket_10": {
        "ru": "10 билетов — 9 TON",
        "en": "10 tickets — 9 TON"
    },
    "not_enough_funds": {
        "ru": "❌ Недостаточно средств для покупки {tickets} билетов.\nВаш баланс: {balance:.2f} TON",
        "en": "❌ Not enough funds to buy {tickets} tickets.\nYour balance: {balance:.2f} TON"
    },
    "win_result": {
        "ru": "🎉 Вы приняли участие в лотерее и купили {tickets} билет(ов)!\nРезультат розыгрыша: Вы выиграли!\nСумма выигрыша: {win_amount} TON\nБаланс: {balance:.2f} TON",
        "en": "🎉 You participated in the lottery and bought {tickets} ticket(s)!\nResult: You won!\nWinnings: {win_amount} TON\nBalance: {balance:.2f} TON"
    },
    "lose_result": {
        "ru": "🎉 Вы приняли участие в лотерее и купили {tickets} билет(ов)!\nРезультат розыгрыша: Вы не выиграли.\nСумма выигрыша: {win_amount} TON\nБаланс: {balance:.2f} TON",
        "en": "🎉 You participated in the lottery and bought {tickets} ticket(s)!\nResult: You did not win.\nWinnings: {win_amount} TON\nBalance: {balance:.2f} TON"
    },
    "balance_text": {
        "ru": "💰 Ваш баланс: {balance:.2f} TON\nДоступно для вывода: {balance:.2f} TON",
        "en": "💰 Your balance: {balance:.2f} TON\nAvailable for withdrawal: {balance:.2f} TON"
    },
    "history": {
        "ru": "\n\n<b>История операций:</b>\n",
        "en": "\n\n<b>Transaction history:</b>\n"
    },
    "no_history": {
        "ru": "Нет операций.",
        "en": "No transactions."
    },
    "deposit_menu": {
        "ru": "💳 Пополнение баланса\n\nВыберите сумму:",
        "en": "💳 Deposit balance\n\nChoose the amount:"
    },
    "deposit_pay": {
        "ru": "🔗 Ссылка для оплаты {amount} TON:\n\nСчет действителен 1 час.",
        "en": "🔗 Payment link for {amount} TON:\n\nInvoice is valid for 1 hour."
    },
    "deposit_error": {
        "ru": "❌ Ошибка при создании счета. Попробуйте позже.",
        "en": "❌ Error creating invoice. Please try again later."
    },
    "check_payment_paid": {
        "ru": "✅ Баланс пополнен на {amount} TON!",
        "en": "✅ Balance topped up by {amount} TON!"
    },
    "check_payment_active": {
        "ru": "⏳ Оплата ещё не поступила. Попробуйте позже.",
        "en": "⏳ Payment not received yet. Please try again later."
    },
    "check_payment_status": {
        "ru": "❌ Статус инвойса: {status}",
        "en": "❌ Invoice status: {status}"
    },
    "check_payment_not_found": {
        "ru": "❌ Оплата не найдена или произошла ошибка.",
        "en": "❌ Payment not found or an error occurred."
    },
    "withdraw_menu": {
        "ru": "📤 Вывод средств\n\nДоступно: {balance:.2f} TON\nВведите сумму для вывода (например: <code>1.5</code>):\n\n<b>Перед первым выводом обязательно запустите @CryptoBot, чтобы создать кошелёк!</b>",
        "en": "📤 Withdraw funds\n\nAvailable: {balance:.2f} TON\nEnter the amount to withdraw (e.g.: <code>1.5</code>):\n\n<b>Before your first withdrawal, be sure to start @CryptoBot to create a wallet!</b>"
    },
    "withdraw_min": {
        "ru": "❌ Минимальная сумма для вывода: 1 TON",
        "en": "❌ Minimum withdrawal amount: 1 TON"
    },
    "withdraw_success": {
        "ru": "✅ {amount} TON отправлены в ваш CryptoBot-кошелёк!",
        "en": "✅ {amount} TON sent to your CryptoBot wallet!"
    },
    "withdraw_error": {
        "ru": "❌ Ошибка при выводе. Убедитесь, что вы запускали @CryptoBot и попробуйте позже.",
        "en": "❌ Withdrawal error. Make sure you have started @CryptoBot and try again."
    },
    "withdraw_not_enough": {
        "ru": "❌ Недостаточно средств.",
        "en": "❌ Not enough funds."
    },
    "promo_text": {
        "ru": "🎁 Акции и бонусы\n\nСкоро здесь появятся специальные предложения!",
        "en": "🎁 Promotions and bonuses\n\nSpecial offers will appear here soon!"
    },
    "rules_text": {
        "ru": "📜 Правила и поддержка\n\n1. Минимальная ставка: 1 TON\n2. Вывод средств в течение 24 часов\n3. Запрещено использование ботов\n\nПо вопросам: @support",
        "en": "📜 Rules and support\n\n1. Minimum bet: 1 TON\n2. Withdrawals within 24 hours\n3. Use of bots is prohibited\n\nFor questions: @support"
    },
    "referral_menu": {
        "ru": "👥 Реферальная программа\n\nВаша реферальная ссылка:\n{ref_link}\n\nПриглашено: {total_referrals} (активных: {total_active})\nЗаработано за всё время: {earned} TON\nПокупок билетов рефералами: {total_purchases}\n",
        "en": "👥 Referral program\n\nYour referral link:\n{ref_link}\n\nInvited: {total_referrals} (active: {total_active})\nEarned all time: {earned} TON\nTickets bought by referrals: {total_purchases}\n"
    },
    "referral_last_active": {
        "ru": "Последние активные рефералы (user_id):\n",
        "en": "Last active referrals (user_id):\n"
    },
    "referral_bonus_info": {
        "ru": "\nВы получаете 15% от всех покупок ваших рефералов!",
        "en": "\nYou receive 15% from all your referrals' ticket purchases!"
    },
    "test_deposit_success": {
        "ru": "🧪 Тестовое пополнение успешно! На ваш баланс начислен 1 TON.",
        "en": "🧪 Test deposit successful! 1 TON has been credited to your balance."
    },
    "add10_success": {
        "ru": "✅ На ваш баланс начислено 10 TON!",
        "en": "✅ 10 TON have been credited to your balance!"
    },
    "no_access": {
        "ru": "Нет доступа",
        "en": "No access"
    },
    "history_game": {
        "ru": "Покупка {tickets} билет(ов)",
        "en": "Purchase of {tickets} ticket(s)"
    },
    "history_win": {
        "ru": "Выигрыш в лотерее: {amount} TON",
        "en": "Lottery win: {amount} TON"
    },
    "history_referral_bonus": {
        "ru": "Бонус за покупку билета рефералом {ref_id}",
        "en": "Bonus for referral's ticket purchase {ref_id}"
    },
    "history_deposit": {
        "ru": "Пополнение через CryptoBot ({amount} TON)",
        "en": "Deposit via CryptoBot ({amount} TON)"
    },
    "history_withdraw": {
        "ru": "Вывод в CryptoBot ({amount} TON)",
        "en": "Withdrawal to CryptoBot ({amount} TON)"
    },
    "history_test_deposit": {
        "ru": "Тестовое пополнение (без реальных денег)",
        "en": "Test deposit (no real money)"
    },
    # ... остальные переводы будут добавлены по ходу ...
}

def t(key, lang, **kwargs):
    return translations[key][lang].format(**kwargs)

# Главное меню
def main_menu(user_id=None, lang='ru'):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t("play", lang), callback_data="play"),
        InlineKeyboardButton(text=t("balance", lang), callback_data="balance")
    )
    builder.row(
        InlineKeyboardButton(text=t("deposit", lang), callback_data="deposit"),
        InlineKeyboardButton(text=t("withdraw", lang), callback_data="withdraw")
    )
    builder.row(
        InlineKeyboardButton(text=t("promo_btn", lang), callback_data="promo"),
        InlineKeyboardButton(text=t("rules_btn", lang), callback_data="rules")
    )
    builder.row(
        InlineKeyboardButton(text=t("referral", lang), callback_data="referral")
    )
    builder.row(
        InlineKeyboardButton(text=t("change_lang", lang), callback_data="change_lang")
    )
    if user_id == ADMIN_ID:
        builder.row(InlineKeyboardButton(text=t("add10", lang), callback_data="add10"))
    return builder.as_markup()

# Обработчики команд
@dp.message(CommandStart())
async def start_command(message: types.Message, command: CommandObject):
    user = await db.get_user(message.from_user.id)
    if not getattr(user, "lang", None):
        # Показываем выбор языка
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=translations["button_ru"]["ru"], callback_data="lang_ru"),
            InlineKeyboardButton(text=translations["button_en"]["en"], callback_data="lang_en")
        )
        await message.answer(
            translations["choose_language"]["ru"] + "\n" + translations["choose_language"]["en"],
            reply_markup=builder.as_markup()
        )
        return
    # Дальше обычная логика, но все тексты через t(..., user.lang)
    await message.answer(
        t("start", user.lang, balance=user.balance),
        reply_markup=main_menu(message.from_user.id, lang=user.lang)
    )

# Раздел игры — согласие с правилами
@dp.callback_query(F.data == "play")
async def play_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=t("agree_button", user.lang), callback_data="agree_lottery"))
    builder.add(InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main"))
    await callback.message.edit_text(
        t("agree_lottery", user.lang),
        reply_markup=builder.as_markup()
    )

# После согласия — выбор количества билетов
@dp.callback_query(F.data == "agree_lottery")
async def agree_lottery_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t("ticket_1", user.lang), callback_data="buy_1"))
    builder.row(InlineKeyboardButton(text=t("ticket_3", user.lang), callback_data="buy_3"))
    builder.row(InlineKeyboardButton(text=t("ticket_10", user.lang), callback_data="buy_10"))
    builder.row(InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_play"))
    await callback.message.edit_text(
        t("choose_tickets", user.lang),
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "back_to_play")
async def back_to_play_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=t("agree_button", user.lang), callback_data="agree_lottery"))
    builder.add(InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main"))
    await callback.message.edit_text(
        t("agree_lottery", user.lang),
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    # Если сообщение содержит '❌ Оплата не найдена или произошла ошибка.', всегда отправляем новое сообщение
    if callback.message.text and "❌ Оплата не найдена или произошла ошибка." in callback.message.text:
        await callback.message.answer(
            "🎉 Добро пожаловать в лотерейный бот!\nЗдесь вы можете испытать удачу и выиграть призы!",
            reply_markup=main_menu(callback.from_user.id, lang=user.lang)
        )
        return
    # Если сообщение без текста (например, после стикера или отдельного сообщения с результатом), всегда отправляем новое сообщение
    if not callback.message.text:
        await callback.message.answer(
            "🎉 Добро пожаловать в лотерейный бот!\nЗдесь вы можете испытать удачу и выиграть призы!",
            reply_markup=main_menu(callback.from_user.id, lang=user.lang)
        )
        return
    try:
        await callback.message.edit_text(
            "🎉 Добро пожаловать в лотерейный бот!\nЗдесь вы можете испытать удачу и выиграть призы!",
            reply_markup=main_menu(callback.from_user.id, lang=user.lang)
        )
    except Exception:
        await callback.message.answer(
            "🎉 Добро пожаловать в лотерейный бот!\nЗдесь вы можете испытать удачу и выиграть призы!",
            reply_markup=main_menu(callback.from_user.id, lang=user.lang)
        )

# Покупка билетов и розыгрыш
@dp.callback_query(F.data.in_(["buy_1", "buy_3", "buy_10"]))
async def buy_tickets_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    ticket_map = {
        "buy_1": (1, 1.0),
        "buy_3": (3, 2.9),
        "buy_10": (10, 9.0)
    }
    tickets, price = ticket_map[callback.data]
    if user.balance < price:
        await callback.message.edit_text(
            t("not_enough_funds", user.lang, tickets=tickets, balance=user.balance),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main")
            ]])
        )
        return
    # Списываем средства
    user.balance -= price
    # Учёт покупок для рефералов
    user.ref_purchases = getattr(user, "ref_purchases", 0) + 1
    await db.update_user(user)
    # История операций
    history = db.get_history(user)
    history.append({"type": "game", "tickets": tickets, "amount": -price})
    # Реферальный бонус (15% от покупки)
    if getattr(user, "invited_by", None):
        ref_user = await db.get_user(user.invited_by)
        bonus = round(price * 0.15, 2)
        ref_user.balance += bonus
        ref_user.earned = getattr(ref_user, "earned", 0.0) + bonus
        ref_history = db.get_history(ref_user)
        ref_history.append({"type": "referral_bonus", "ref_id": user.user_id, "amount": bonus})
        db.set_history(ref_user, ref_history)
        await db.update_user(ref_user)
    # Выигрыш: случайно от 10% до 50% от суммы покупки
    win_percent = random.uniform(0.1, 0.5)
    win_amount = round(price * win_percent, 2)
    if win_amount > 0:
        user.balance += win_amount
        history.append({"type": "win", "amount": win_amount})
        db.set_history(user, history)
        await db.update_user(user)
        # Стикер победителя
        await callback.message.answer_sticker("CAACAgIAAxkBAAEOhK9oKl600GvZPoV6OROtfhAJOr1glAACAwEAAladvQoC5dF4h-X6TzYE")
        await callback.message.answer(
            t("win_result", user.lang, tickets=tickets, win_amount=win_amount, balance=user.balance),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=t("main_menu", user.lang), callback_data="lottery_back_to_main")
            ]])
        )
    else:
        db.set_history(user, history)
        await db.update_user(user)
        await callback.message.edit_text(
            t("lose_result", user.lang, tickets=tickets, win_amount=win_amount, balance=user.balance),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main")
            ]])
        )

# Раздел баланса с историей
@dp.callback_query(F.data == "balance")
async def balance_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    history = db.get_history(user)
    history_text = t("history", user.lang)
    if history:
        for h in history[-10:][::-1]:
            desc = ""
            amount = ""
            if isinstance(h, dict):
                if h.get("type") == "game":
                    desc = t("history_game", user.lang, tickets=h.get("tickets"))
                    amount = h.get("amount", "")
                elif h.get("type") == "win":
                    desc = t("history_win", user.lang, amount=h.get("amount"))
                    amount = h.get("amount", "")
                elif h.get("type") == "referral_bonus":
                    desc = t("history_referral_bonus", user.lang, ref_id=h.get("ref_id"))
                    amount = h.get("amount", "")
                elif h.get("type") == "deposit":
                    desc = t("history_deposit", user.lang, amount=h.get("amount"))
                    amount = h.get("amount", "")
                elif h.get("type") == "withdraw":
                    desc = t("history_withdraw", user.lang, amount=h.get("amount"))
                    amount = h.get("amount", "")
                elif h.get("type") == "test_deposit":
                    desc = t("history_test_deposit", user.lang)
                    amount = h.get("amount", "")
                else:
                    desc = str(h)
            else:
                desc = str(h)
            if amount != "":
                history_text += f"• {desc} ({amount} TON)\n"
            else:
                history_text += f"• {desc}\n"
    else:
        history_text += t("no_history", user.lang)
    await callback.message.edit_text(
        t("balance_text", user.lang, balance=user.balance) +
        history_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main")
        ]])
    )

# Раздел пополнения
@dp.callback_query(F.data == "deposit")
async def deposit_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="💳 1 TON", callback_data="deposit_1"))
    builder.add(InlineKeyboardButton(text="💳 5 TON", callback_data="deposit_5"))
    builder.add(InlineKeyboardButton(text="💳 10 TON", callback_data="deposit_10"))
    # Кнопка тестового пополнения
    builder.add(InlineKeyboardButton(text="🧪 Тестовое пополнение", callback_data="test_deposit"))
    builder.row(InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main"))
    await callback.message.edit_text(
        t("deposit_menu", user.lang),
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data.startswith("deposit_"))
async def deposit_amount_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    amount = float(callback.data.split("_")[1])
    user_id = callback.from_user.id

    invoice = await cryptopay.create_invoice(
        amount=amount,
        description=f"Пополнение баланса для {user_id}",
        payload=str(user_id)
    )

    if invoice.get("ok"):
        pay_url = invoice["result"]["pay_url"]
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="💳 Оплатить", url=pay_url))
        builder.add(InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_{invoice['result']['invoice_id']}"))
        builder.row(InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_deposit"))

        await callback.message.edit_text(
            t("deposit_pay", user.lang, amount=amount),
            reply_markup=builder.as_markup()
        )
    else:
        await callback.message.edit_text(t("deposit_error", user.lang))

@dp.callback_query(F.data == "back_to_deposit")
async def back_to_deposit_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="💳 1 TON", callback_data="deposit_1"))
    builder.add(InlineKeyboardButton(text="💳 5 TON", callback_data="deposit_5"))
    builder.add(InlineKeyboardButton(text="💳 10 TON", callback_data="deposit_10"))
    builder.row(InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main"))
    if callback.message.text and t("check_payment_not_found", user.lang) in callback.message.text:
        await callback.message.answer(
            t("deposit_menu", user.lang),
            reply_markup=builder.as_markup()
        )
    else:
        await callback.message.edit_text(
            t("deposit_menu", user.lang),
            reply_markup=builder.as_markup()
        )

@dp.callback_query(F.data.startswith("check_"))
async def check_payment_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    invoice_id = callback.data.split("_")[1]
    invoice = await cryptopay.check_invoice(invoice_id)
    menu_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_{invoice_id}")],
        [InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_deposit")]
    ])

    if invoice.get("ok") and invoice.get("result"):
        invoice_data = invoice["result"][0]
        status = invoice_data.get("status")
        if status == "paid":
            user_id = int(invoice_data.get("payload", callback.from_user.id))
            amount = float(invoice_data.get("amount", 0))
            user = await db.get_user(user_id)
            user.balance += amount
            history = db.get_history(user)
            history.append({"type": "deposit", "amount": amount, "desc": f"Пополнение через CryptoBot ({amount} TON)"})
            db.set_history(user, history)
            await db.update_user(user)
            await callback.message.edit_text(
                t("check_payment_paid", user.lang, amount=amount),
                reply_markup=menu_markup
            )
        elif status == "active":
            await callback.message.edit_text(
                t("check_payment_active", user.lang),
                reply_markup=menu_markup
            )
        else:
            await callback.message.edit_text(
                t("check_payment_status", user.lang, status=status),
                reply_markup=menu_markup
            )
    else:
        await callback.message.answer_sticker("CAACAgIAAxkBAAEOi95oMFEAAcgO-YbH4g76A2cfNt3zXzUAAgIBAAJWnb0KTuJsgctA5P82BA")
        await callback.message.answer(
            t("check_payment_not_found", user.lang),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_{invoice_id}")],
                [InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_deposit")]
            ])
        )

# Раздел вывода
@dp.callback_query(F.data == "withdraw")
async def withdraw_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    menu_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main")
    ]])
    if user.balance < 1:
        await callback.message.edit_text(t("withdraw_min", user.lang), reply_markup=menu_markup)
        return

    await callback.message.edit_text(
        t("withdraw_menu", user.lang, balance=user.balance),
        reply_markup=menu_markup
    )

@dp.message(F.text.regexp(r"^\d+(\.\d+)?$"))
async def process_withdrawal(message: types.Message):
    amount = float(message.text)
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    menu_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main")
    ]])

    if user.balance >= amount:
        success = await db.process_withdrawal(user_id, amount, cryptopay)
        if success:
            history = db.get_history(user)
            history.append({"type": "withdraw", "amount": amount, "desc": f"Вывод в CryptoBot ({amount} TON)"})
            db.set_history(user, history)
            await db.update_user(user)
            await message.answer(t("withdraw_success", user.lang, amount=amount), reply_markup=menu_markup)
        else:
            await message.answer(t("withdraw_error", user.lang), reply_markup=menu_markup)
    else:
        await message.answer(t("withdraw_not_enough", user.lang), reply_markup=menu_markup)

# Раздел акций
@dp.callback_query(F.data == "promo")
async def promo_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    await callback.message.edit_text(
        t("promo_text", user.lang),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[ 
            InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main")
        ]])
    )

# Раздел правил
@dp.callback_query(F.data == "rules")
async def rules_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    await callback.message.edit_text(
        t("rules_text", user.lang),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[ 
            InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main")
        ]])
    )

# Реферальная программа
@dp.callback_query(F.data == "referral")
async def referral_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    referrals = db.get_referrals(user)
    total_referrals = len(referrals)
    active_referrals = []
    for rid in referrals:
        ref_user = await db.get_user(rid)
        if getattr(ref_user, "ref_purchases", 0) > 0:
            active_referrals.append(rid)
    total_active = len(active_referrals)
    earned = round(getattr(user, "earned", 0.0), 2)
    last_active = active_referrals[-3:]
    total_purchases = 0
    for rid in referrals:
        ref_user = await db.get_user(rid)
        total_purchases += getattr(ref_user, "ref_purchases", 0)
    lang = user.lang
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start=ref_{user_id}"
    text = t("referral_menu", lang, ref_link=ref_link, total_referrals=total_referrals, total_active=total_active, earned=earned, total_purchases=total_purchases)
    if last_active:
        text += t("referral_last_active", lang)
        for rid in last_active:
            text += f"- {rid}\n"
    text += t("referral_bonus_info", lang)
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t("back", lang), callback_data="back_to_main")
        ]])
    )

# Обработчик начисления 10 TON (только для админа)
@dp.callback_query(F.data == "add10")
async def add10_handler(callback: types.CallbackQuery):
    if callback.from_user.id == ADMIN_ID:
        user = await db.get_user(callback.from_user.id)
        user.balance += 10
        await db.update_user(user)
        await callback.message.edit_text(
            "✅ На ваш баланс начислено 10 TON!",
            reply_markup=main_menu(callback.from_user.id, lang=user.lang)
        )
    else:
        await callback.answer("Нет доступа", show_alert=True)

# Добавляю отдельный обработчик для lottery_back_to_main
@dp.callback_query(F.data == "lottery_back_to_main")
async def lottery_back_to_main_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    await callback.message.answer(
        "🎉 Добро пожаловать в лотерейный бот!\nЗдесь вы можете испытать удачу и выиграть призы!",
        reply_markup=main_menu(callback.from_user.id, lang=user.lang)
    )

# Обработчик тестового пополнения
@dp.callback_query(F.data == "test_deposit")
async def test_deposit_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    user.balance += 1  # Тестовое пополнение на 1 TON
    history = db.get_history(user)
    history.append({"type": "test_deposit", "amount": 1, "desc": "Тестовое пополнение (без реальных денег)"})
    db.set_history(user, history)
    await db.update_user(user)
    await callback.message.edit_text(
        t("test_deposit_success", user.lang),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t("main_menu", user.lang), callback_data="back_to_main")
        ]])
    )

# Обработчик выбора языка
@dp.callback_query(F.data.in_(["lang_ru", "lang_en"]))
async def set_language(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    lang = "ru" if callback.data == "lang_ru" else "en"
    user.lang = lang
    await db.update_user(user)
    await callback.message.edit_text(
        t("start", lang, balance=user.balance),
        reply_markup=main_menu(callback.from_user.id, lang=lang)
    )

# Обработчик смены языка
@dp.callback_query(F.data == "change_lang")
async def change_lang_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t("button_ru", user.lang), callback_data="lang_ru"),
        InlineKeyboardButton(text=t("button_en", user.lang), callback_data="lang_en")
    )
    await callback.message.edit_text(
        t("choose_language", user.lang),
        reply_markup=builder.as_markup()
    )

# Запуск бота
async def main():
    await db.init()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
