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

# Главное меню
def main_menu(user_id=None):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🦋 Играть", callback_data="play"),
        InlineKeyboardButton(text="💰 Баланс", callback_data="balance")
    )
    builder.row(
        InlineKeyboardButton(text="💳 Пополнить", callback_data="deposit"),
        InlineKeyboardButton(text="📤 Вывод", callback_data="withdraw")
    )
    builder.row(
        InlineKeyboardButton(text="🎁 Акции", callback_data="promo"),
        InlineKeyboardButton(text="📜 Правила", callback_data="rules")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Рефералы", callback_data="referral")
    )
    # Кнопка для начисления 10 TON только для админа
    if user_id == ADMIN_ID:
        builder.row(InlineKeyboardButton(text="💸 Начислить 10 TON", callback_data="add10"))
    return builder.as_markup()

# Обработчики команд
@dp.message(CommandStart())
async def start_command(message: types.Message, command: CommandObject):
    user = await db.get_user(message.from_user.id)
    ref_id = None
    # Проверяем, есть ли аргумент ref_
    if command.args and command.args.startswith("ref_"):
        ref_id = int(command.args.split("_")[1])
        if ref_id != message.from_user.id:
            # Сохраняем пригласившего
            if not getattr(user, "invited_by", None):
                user.invited_by = ref_id
                await db.update_user(user)
            ref_user = await db.get_user(ref_id)
            referrals = db.get_referrals(ref_user)
            if message.from_user.id not in referrals:
                referrals.append(message.from_user.id)
                db.set_referrals(ref_user, referrals)
                await db.update_user(ref_user)
    await message.answer(
        f"🎉 \U0001F98B Добро пожаловать!\nВаш баланс: {user.balance:.2f} TON",
        reply_markup=main_menu(message.from_user.id)
    )

# Раздел игры — согласие с правилами
@dp.callback_query(F.data == "play")
async def play_handler(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Я согласен(на)", callback_data="agree_lottery"))
    builder.add(InlineKeyboardButton(text="‹ Назад", callback_data="back_to_main"))
    await callback.message.edit_text(
        "🎰 Перед началом игры вы должны согласиться с тем, что выигрыши определяются случайным образом и не гарантированы.\n\n"
        "Нажимая 'Продолжить', вы подтверждаете согласие с этими условиями.",
        reply_markup=builder.as_markup()
    )

# После согласия — выбор количества билетов
@dp.callback_query(F.data == "agree_lottery")
async def agree_lottery_handler(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="1 билет — 1 TON", callback_data="buy_1"))
    builder.row(InlineKeyboardButton(text="3 билета — 2.9 TON", callback_data="buy_3"))
    builder.row(InlineKeyboardButton(text="10 билетов — 9 TON", callback_data="buy_10"))
    builder.row(InlineKeyboardButton(text="‹ Назад", callback_data="back_to_play"))
    await callback.message.edit_text(
        "🎟️ Выберите количество билетов:",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "back_to_play")
async def back_to_play_handler(callback: types.CallbackQuery):
    # Возврат к согласию с правилами
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Я согласен(на)", callback_data="agree_lottery"))
    builder.add(InlineKeyboardButton(text="‹ Назад", callback_data="back_to_main"))
    await callback.message.edit_text(
        "🎰 Перед началом игры вы должны согласиться с тем, что выигрыши определяются случайным образом и не гарантированы.\n\n"
        "Нажимая 'Продолжить', вы подтверждаете согласие с этими условиями.",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: types.CallbackQuery):
    # Если сообщение содержит '❌ Оплата не найдена или произошла ошибка.', всегда отправляем новое сообщение
    if callback.message.text and "❌ Оплата не найдена или произошла ошибка." in callback.message.text:
        await callback.message.answer(
            "🎉 Добро пожаловать в лотерейный бот!\nЗдесь вы можете испытать удачу и выиграть призы!",
            reply_markup=main_menu(callback.from_user.id)
        )
        return
    # Если сообщение без текста (например, после стикера или отдельного сообщения с результатом), всегда отправляем новое сообщение
    if not callback.message.text:
        await callback.message.answer(
            "🎉 Добро пожаловать в лотерейный бот!\nЗдесь вы можете испытать удачу и выиграть призы!",
            reply_markup=main_menu(callback.from_user.id)
        )
        return
    try:
        await callback.message.edit_text(
            "🎉 Добро пожаловать в лотерейный бот!\nЗдесь вы можете испытать удачу и выиграть призы!",
            reply_markup=main_menu(callback.from_user.id)
        )
    except Exception:
        await callback.message.answer(
            "🎉 Добро пожаловать в лотерейный бот!\nЗдесь вы можете испытать удачу и выиграть призы!",
            reply_markup=main_menu(callback.from_user.id)
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
            f"❌ Недостаточно средств для покупки {tickets} билетов.\nВаш баланс: {user.balance:.2f} TON",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_main")
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
    history.append({
        "type": "game",
        "amount": -price,
        "desc": f"Покупка {tickets} билет(ов) на {price} TON"
    })
    # Реферальный бонус (15% от покупки)
    if getattr(user, "invited_by", None):
        ref_user = await db.get_user(user.invited_by)
        bonus = round(price * 0.15, 2)
        ref_user.balance += bonus
        ref_user.earned = getattr(ref_user, "earned", 0.0) + bonus
        ref_history = db.get_history(ref_user)
        ref_history.append({
            "type": "referral_bonus",
            "amount": bonus,
            "desc": f"Бонус за покупку билета рефералом {user.user_id}"
        })
        db.set_history(ref_user, ref_history)
        await db.update_user(ref_user)
    # Выигрыш: случайно от 10% до 50% от суммы покупки
    win_percent = random.uniform(0.1, 0.5)
    win_amount = round(price * win_percent, 2)
    if win_amount > 0:
        user.balance += win_amount
        history.append({
            "type": "win",
            "amount": win_amount,
            "desc": f"Выигрыш в лотерее: {win_amount} TON"
        })
        db.set_history(user, history)
        await db.update_user(user)
        # Стикер победителя
        await callback.message.answer_sticker("CAACAgIAAxkBAAEOhK9oKl600GvZPoV6OROtfhAJOr1glAACAwEAAladvQoC5dF4h-X6TzYE")
        await callback.message.answer(
            f"🎉 Вы приняли участие в лотерее и купили {tickets} билет(ов)!\n"
            f"Результат розыгрыша: Вы выиграли!\n"
            f"Сумма выигрыша: {win_amount} TON\n"
            f"Баланс: {user.balance:.2f} TON",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🏠 В меню", callback_data="lottery_back_to_main")
            ]])
        )
    else:
        db.set_history(user, history)
        await db.update_user(user)
        await callback.message.edit_text(
            f"🎉 Вы приняли участие в лотерее и купили {tickets} билет(ов)!\n"
            f"Результат розыгрыша: Вы не выиграли.\n"
            f"Сумма выигрыша: {win_amount} TON\n"
            f"Баланс: {user.balance:.2f} TON",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_main")
            ]])
        )

# Раздел баланса с историей
@dp.callback_query(F.data == "balance")
async def balance_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    history = db.get_history(user)
    history_text = "\n\n<b>История операций:</b>\n"
    if history:
        for h in history[-10:][::-1]:
            desc = h.get("desc") if isinstance(h, dict) else str(h)
            amount = h.get("amount") if isinstance(h, dict) else ""
            if amount != "":
                history_text += f"• {desc} ({amount} TON)\n"
            else:
                history_text += f"• {desc}\n"
    else:
        history_text += "Нет операций."
    await callback.message.edit_text(
        f"💰 Ваш баланс: {user.balance:.2f} TON\n"
        f"Доступно для вывода: {user.balance:.2f} TON"
        f"{history_text}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="‹ Назад", callback_data="back_to_main")
        ]])
    )

# Раздел пополнения
@dp.callback_query(F.data == "deposit")
async def deposit_handler(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="💳 1 TON", callback_data="deposit_1"))
    builder.add(InlineKeyboardButton(text="💳 5 TON", callback_data="deposit_5"))
    builder.add(InlineKeyboardButton(text="💳 10 TON", callback_data="deposit_10"))
    # Кнопка тестового пополнения
    builder.add(InlineKeyboardButton(text="🧪 Тестовое пополнение", callback_data="test_deposit"))
    builder.row(InlineKeyboardButton(text="‹ Назад", callback_data="back_to_main"))
    await callback.message.edit_text(
        "💳 Пополнение баланса\n\n"
        "Выберите сумму:",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data.startswith("deposit_"))
async def deposit_amount_handler(callback: types.CallbackQuery):
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
        builder.row(InlineKeyboardButton(text="‹ Назад", callback_data="back_to_deposit"))

        await callback.message.edit_text(
            f"🔗 Ссылка для оплаты {amount} TON:\n\n"
            f"Счет действителен 1 час.",
            reply_markup=builder.as_markup()
        )
    else:
        await callback.message.edit_text("❌ Ошибка при создании счета. Попробуйте позже.")

@dp.callback_query(F.data == "back_to_deposit")
async def back_to_deposit_handler(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="💳 1 TON", callback_data="deposit_1"))
    builder.add(InlineKeyboardButton(text="💳 5 TON", callback_data="deposit_5"))
    builder.add(InlineKeyboardButton(text="💳 10 TON", callback_data="deposit_10"))
    builder.row(InlineKeyboardButton(text="‹ Назад", callback_data="back_to_main"))
    # Если сообщение содержит ошибку — отправляем новое сообщение, а не редактируем
    if callback.message.text and "❌ Оплата не найдена или произошла ошибка." in callback.message.text:
        await callback.message.answer(
            "💳 Пополнение баланса\n\n"
            "Выберите сумму:",
            reply_markup=builder.as_markup()
        )
    else:
        await callback.message.edit_text(
            "💳 Пополнение баланса\n\n"
            "Выберите сумму:",
            reply_markup=builder.as_markup()
        )

@dp.callback_query(F.data.startswith("check_"))
async def check_payment_handler(callback: types.CallbackQuery):
    invoice_id = callback.data.split("_")[1]
    invoice = await cryptopay.check_invoice(invoice_id)
    menu_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_{invoice_id}")],
        [InlineKeyboardButton(text="‹ Назад", callback_data="back_to_deposit")]
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
            history.append({
                "type": "deposit",
                "amount": amount,
                "desc": f"Пополнение через CryptoBot ({amount} TON)"
            })
            db.set_history(user, history)
            await db.update_user(user)
            await callback.message.edit_text(
                f"✅ Баланс пополнен на {amount} TON!",
                reply_markup=menu_markup
            )
        elif status == "active":
            await callback.message.edit_text(
                "⏳ Оплата ещё не поступила. Попробуйте позже.",
                reply_markup=menu_markup
            )
        else:
            await callback.message.edit_text(
                f"❌ Статус инвойса: {status}",
                reply_markup=menu_markup
            )
    else:
        await callback.message.answer_sticker("CAACAgIAAxkBAAEOi95oMFEAAcgO-YbH4g76A2cfNt3zXzUAAgIBAAJWnb0KTuJsgctA5P82BA")
        await callback.message.answer(
            "❌ Оплата не найдена или произошла ошибка.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_{invoice_id}")],
                [InlineKeyboardButton(text="‹ Назад", callback_data="back_to_deposit")]
            ])
        )

# Раздел вывода
@dp.callback_query(F.data == "withdraw")
async def withdraw_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    menu_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_main")
    ]])
    if user.balance < 1:
        await callback.message.edit_text("❌ Минимальная сумма для вывода: 1 TON", reply_markup=menu_markup)
        return

    await callback.message.edit_text(
        "📤 Вывод средств\n\n"
        f"Доступно: {user.balance:.2f} TON\n"
        "Введите сумму для вывода (например: <code>1.5</code>):\n\n"
        "<b>Перед первым выводом обязательно запустите @CryptoBot, чтобы создать кошелёк!</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="‹ Назад", callback_data="back_to_main")
        ]])
    )

# Обработка сообщения с суммой для вывода
@dp.message(F.text.regexp(r"^\d+(\.\d+)?$"))
async def process_withdrawal(message: types.Message):
    amount = float(message.text)
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    menu_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_main")
    ]])

    if user.balance >= amount:
        success = await db.process_withdrawal(user_id, amount, cryptopay)
        if success:
            history = db.get_history(user)
            history.append({
                "type": "withdraw",
                "amount": amount,
                "desc": f"Вывод в CryptoBot ({amount} TON)"
            })
            db.set_history(user, history)
            await db.update_user(user)
            await message.answer(f"✅ {amount} TON отправлены в ваш CryptoBot-кошелёк!", reply_markup=menu_markup)
        else:
            await message.answer("❌ Ошибка при выводе. Убедитесь, что вы запускали @CryptoBot и попробуйте позже.", reply_markup=menu_markup)
    else:
        await message.answer("❌ Недостаточно средств.", reply_markup=menu_markup)

# Раздел акций
@dp.callback_query(F.data == "promo")
async def promo_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🎁 Акции и бонусы\n\n"
        "Скоро здесь появятся специальные предложения!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="‹ Назад", callback_data="back_to_main")
        ]])
    )

# Раздел правил
@dp.callback_query(F.data == "rules")
async def rules_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📜 Правила и поддержка\n\n"
        "1. Минимальная ставка: 1 TON\n"
        "2. Вывод средств в течение 24 часов\n"
        "3. Запрещено использование ботов\n\n"
        "По вопросам: @support",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="‹ Назад", callback_data="back_to_main")
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
    text = (
        "👥 Реферальная программа\n\n"
        f"Ваша реферальная ссылка:\nhttps://t.me/{(await bot.get_me()).username}?start=ref_{user_id}\n\n"
        f"Приглашено: {total_referrals} (активных: {total_active})\n"
        f"Заработано за всё время: {earned} TON\n"
        f"Покупок билетов рефералами: {total_purchases}\n"
    )
    if last_active:
        text += "Последние активные рефералы (user_id):\n"
        for rid in last_active:
            text += f"- {rid}\n"
    text += "\nВы получаете 15% от всех покупок ваших рефералов!"
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="‹ Назад", callback_data="back_to_main")
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
            reply_markup=main_menu(callback.from_user.id)
        )
    else:
        await callback.answer("Нет доступа", show_alert=True)

# Добавляю отдельный обработчик для lottery_back_to_main
@dp.callback_query(F.data == "lottery_back_to_main")
async def lottery_back_to_main_handler(callback: types.CallbackQuery):
    await callback.message.answer(
        "🎉 Добро пожаловать в лотерейный бот!\nЗдесь вы можете испытать удачу и выиграть призы!",
        reply_markup=main_menu(callback.from_user.id)
    )

# Обработчик тестового пополнения
@dp.callback_query(F.data == "test_deposit")
async def test_deposit_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    user.balance += 1  # Тестовое пополнение на 1 TON
    history = db.get_history(user)
    history.append({
        "type": "test_deposit",
        "amount": 1,
        "desc": "Тестовое пополнение (без реальных денег)"
    })
    db.set_history(user, history)
    await db.update_user(user)
    await callback.message.edit_text(
        "🧪 Тестовое пополнение успешно! На ваш баланс начислен 1 TON.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_main")
        ]])
    )

# Запуск бота
async def main():
    await db.init()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
