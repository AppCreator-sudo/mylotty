import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from uuid import uuid4
from typing import Dict, Optional
from cryptopay import CryptoPay
import random
from db import AsyncDatabase, User
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from aiogram.exceptions import TelegramBadRequest

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

# Состояния для FSM
class UserStates(StatesGroup):
    waiting_for_deposit_amount = State()
    waiting_for_withdraw_amount = State()

# Словарь переводов
translations = {
    "start": {
        "ru": "🎉 Добро пожаловать, {username}!\nВаш баланс: {balance:.2f} TON\n\nLOTTY TON — это современная лотерея с честными розыгрышами и реальными шансами на крупный выигрыш!\n\n• Главный джекпот — до 25 000 TON\n• Мгновенные выплаты через <a href=\"https://t.me/CryptoBot\">CryptoBot</a> — официальный платёжный сервис Telegram\n• Кэшбэк, бонусы и реферальная программа\n\nПопробуйте удачу — возможно, именно вы станете следующим победителем!",
        "en": "🎉 Welcome, {username}!\nYour balance: {balance:.2f} TON\n\nLOTTY TON is a modern lottery with fair draws and real chances to win big!\n\n• Main jackpot — up to 25,000 TON\n• Instant payouts via <a href=\"https://t.me/CryptoBot\">CryptoBot</a> — the official payment service of Telegram\n• Cashback, bonuses, and referral program\n\nTry your luck — maybe you'll be the next winner!"
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
        "ru": "🎫 LOTTY TON",
        "en": "🎫 LOTTY TON"
    },
    "balance": {
        "ru": "💰 Баланс",
        "en": "💰 Balance"
    },
    "deposit": {
        "ru": "📥 Пополнить",
        "en": "📥 Deposit"
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
        "ru": "🌐 Сменить язык",
        "en": "🌐 Change language"
    },
    "add10": {
        "ru": "💸 Начислить 10 TON",
        "en": "💸 Add 10 TON"
    },
    "agree_lottery": {
        "ru": "Перед началом игры, пожалуйста, подтвердите своё согласие с правилами лотереи.\n\nLOTTY TON — это честная и прозрачная лотерея, где каждый билет даёт шанс выиграть призы, включая главный джекпот до 25 000 TON!\n\nПокупая билет, вы принимаете участие в розыгрыше, где всё решает удача. Чем больше билетов — тем выше ваши шансы!\n\nЖелаем удачи! Пусть именно вы станете обладателем джекпота!",
        "en": "Before you start playing, please confirm your agreement with the lottery rules.\n\nLOTTY TON is a fair and transparent lottery where every ticket gives you a chance to win prizes, including the main jackpot of up to 25,000 TON!\n\nBy purchasing a ticket, you enter the draw where everything depends on luck. The more tickets you buy, the higher your chances!\n\nGood luck! Maybe you will be the next jackpot winner!"
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
        "ru": "📥 Пополнение баланса\n\n💰 Валюта: TON (Toncoin)\n💳 Способ пополнения: CryptoBot — официальный платёжный сервис Telegram\n\n📋 Как пополнить баланс:\n• Введите сумму для пополнения (минимум 1 TON)\n• Нажмите кнопку «Оплатить»\n• Перейдите в CryptoBot и подтвердите платёж\n• После оплаты нажмите «Проверить оплату»\n• Дождитесь зачисления средств на баланс\n\n⏱️ Счёт действителен 1 час\n💡 Комиссия CryptoBot: ~3% от суммы\n\nВведите сумму для пополнения:",
        "en": "📥 Deposit balance\n\n💰 Currency: TON (Toncoin)\n💳 Payment method: CryptoBot — official Telegram payment service\n\n📋 How to deposit:\n• Enter the amount to deposit (minimum 1 TON)\n• Click the «Pay» button\n• Go to CryptoBot and confirm the payment\n• After payment, click «Check payment»\n• Wait for funds to be credited to your balance\n\n⏱️ Invoice is valid for 1 hour\n💡 CryptoBot fee: ~3% of the amount\n\nEnter the amount to deposit:"
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
        "ru": "📤 Вывод средств\n\n💰 Валюта: TON (Toncoin)\n💳 Способ вывода: CryptoBot — официальный платёжный сервис Telegram\n\n📋 Как вывести средства:\n• Убедитесь, что у вас есть активный кошелёк в @CryptoBot\n• Введите сумму для вывода (минимум 1 TON)\n• Подтвердите вывод средств\n• Дождитесь поступления TON в ваш кошелёк\n\n💡 Комиссия за вывод: 0.1 TON\n⏱️ Время обработки: до 5 минут\n\nДоступно для вывода: {balance:.2f} TON\nВведите сумму для вывода (например: <code>1.5</code>):",
        "en": "📤 Withdraw funds\n\n💰 Currency: TON (Toncoin)\n💳 Withdrawal method: CryptoBot — official Telegram payment service\n\n📋 How to withdraw:\n• Make sure you have an active wallet in @CryptoBot\n• Enter the amount to withdraw (minimum 1 TON)\n• Confirm the withdrawal\n• Wait for TON to arrive in your wallet\n\n💡 Withdrawal fee: 0.1 TON\n⏱️ Processing time: up to 5 minutes\n\nAvailable for withdrawal: {balance:.2f} TON\nEnter the amount to withdraw (e.g.: <code>1.5</code>):"
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
        "ru": "<b>🎁 Акции и бонусы LOTTY TON</b>\n\n<b>1. Прогрессивная реферальная программа</b>\n"
        "— Приглашайте друзей по вашей реферальной ссылке (раздел 👥 Рефералы).\n"
        "— Получайте процент от всех покупок билетов вашими рефералами.\n"
        "— Чем больше приглашённых, тем выше ваш процент!\n"
        "— Уровни: 1-2 — 10%, 3-4 — 12%, 5-9 — 15%, 10-19 — 18%, 20-29 — 20%, 30-49 — 22%, 50+ — 25%.\n\n"
        "<b>2. Кэшбэк в выходные</b>\n"
        "— Каждую субботу и воскресенье (по UTC) вы получаете 3% кэшбэка на баланс с каждой покупки билетов.\n"
        "— ⏰ Время UTC: суббота 00:00 - воскресенье 23:59\n\n"
        "<b>3. Скидки на массовые покупки билетов</b>\n"
        "— 3 билета = 2.9 TON (экономия 0.1 TON)\n"
        "— 10 билетов = 9 TON (экономия 1 TON)\n\n"
        "<b>4. Еженедельный розыгрыш «Второй шанс»</b>\n"
        "— Каждое воскресенье в 18:00 UTC определяется случайный победитель среди участников.\n"
        "— Приз: 25 TON\n"
        "— Для участия достаточно купить хотя бы 1 билет в течение недели.\n"
        "— ⏰ Время розыгрыша UTC: воскресенье 18:00\n\n"
        "Следите за новыми акциями и бонусами — они будут появляться здесь!",
        "en": "<b>🎁 LOTTY TON Promotions and Bonuses</b>\n\n<b>1. Progressive Referral Program</b>\n"
        "— Invite friends using your referral link (see 👥 Referrals).\n"
        "— Get a percentage of all ticket purchases made by your referrals.\n"
        "— The more you invite, the higher your percentage!\n"
        "— Levels: 1-2 — 10%, 3-4 — 12%, 5-9 — 15%, 10-19 — 18%, 20-29 — 20%, 30-49 — 22%, 50+ — 25%.\n\n"
        "<b>2. Weekend Cashback</b>\n"
        "— Every Saturday and Sunday (UTC time) you receive 3% cashback on every ticket purchase.\n"
        "— ⏰ UTC time: Saturday 00:00 - Sunday 23:59\n\n"
        "<b>3. Discounts for bulk ticket purchases</b>\n"
        "— 3 tickets = 2.9 TON (save 0.1 TON)\n"
        "— 10 tickets = 9 TON (save 1 TON)\n\n"
        "<b>4. Weekly «Second Chance» Draw</b>\n"
        "— Every Sunday at 18:00 UTC, a random winner is selected among participants.\n"
        "— Prize: 25 TON\n"
        "— To participate, just buy at least 1 ticket during the week.\n"
        "— ⏰ Draw time UTC: Sunday 18:00\n\n"
        "Stay tuned for new promotions and bonuses — they will appear here!"
    },
    "rules_page1": {
        "ru": "<b>📜 Правила игры LOTTY TON</b>\n\n<b>1. Общие положения</b>\n- LOTTY TON — это лотерейный бот, где вы можете покупать билеты, участвовать в розыгрышах и получать призы.\n\n<b>2. Баланс и пополнение</b>\n- Ваш баланс отображается в TON (Toncoin).\n- Пополнить баланс можно через <a href='https://t.me/CryptoBot'>CryptoBot</a> (📥 Пополнить).\n- CryptoBot — это надёжный платёжный сервис, рекомендованный Telegram для работы с криптовалютой.\n- Минимальная сумма пополнения — 1 TON.\n\n<b>3. Покупка билетов и розыгрыш</b>\n- Для участия в лотерее купите билеты (🎫 LOTTY TON).\n- Доступны пакеты: 1 билет (1 TON), 3 билета (2.9 TON), 10 билетов (9 TON).\n- После покупки билетов происходит розыгрыш: вы можете выиграть от 0.01 TON до 25 000 TON.\n- Результат розыгрыша и история операций отображаются в разделе «Баланс».",
        "en": "<b>📜 LOTTY TON Game Rules</b>\n\n<b>1. General</b>\n- LOTTY TON is a lottery bot where you can buy tickets, participate in draws, and win prizes.\n\n<b>2. Balance and Deposit</b>\n- Your balance is shown in TON (Toncoin).\n- You can top up your balance via <a href='https://t.me/CryptoBot'>CryptoBot</a> (📥 Deposit).\n- CryptoBot is a reliable payment service recommended by Telegram for working with cryptocurrency.\n- Minimum deposit amount is 1 TON.\n\n<b>3. Ticket Purchase and Draw</b>\n- To participate, buy tickets (🎫 LOTTY TON).\n- Available packages: 1 ticket (1 TON), 3 tickets (2.9 TON), 10 tickets (9 TON).\n- After purchasing tickets, a draw takes place: you can win from 0.01 TON to 25,000 TON.\n- Draw results and transaction history are shown in the Balance section."
    },
    "rules_page2": {
        "ru": "<b>4. Вывод средств</b>\n- Вывести средства можно через CryptoBot (📤 Вывод).\n- Минимальная сумма для вывода — 1 TON.\n- Перед первым выводом убедитесь, что у вас есть действующий кошелёк в @CryptoBot.\n- На вывод средств может взиматься комиссия 0.1 TON.\n\n<b>5. Реферальная программа</b>\n- Приглашайте друзей по вашей реферальной ссылке (👥 Рефералы).\n- Вы получаете 15% от всех покупок билетов вашими рефералами.\n- В разделе «Рефералы» отображается ваша ссылка, статистика и заработанные бонусы.\n\n<b>6. Мультиязычность</b>\n- Бот поддерживает русский и английский языки. Сменить язык можно в главном меню («🌐 Сменить язык»).\n\n<b>7. История операций</b>\n- Вся ваша активность (пополнения, выводы, покупки билетов, выигрыши, бонусы) отображается в истории операций.\n\n<b>8. Безопасность и честность</b>\n- Использование ботов и автоматизированных скриптов запрещено.\n- Администрация оставляет за собой право заблокировать пользователя за нарушение правил.\n\n<b>9. Поддержка</b>\n- По всем вопросам обращайтесь: @support",
        "en": "<b>4. Withdrawals</b>\n- You can withdraw funds via CryptoBot (📤 Withdraw).\n- Minimum withdrawal amount is 1 TON.\n- Before your first withdrawal, make sure you have an active wallet in @CryptoBot.\n- A 0.1 TON fee may be charged for withdrawals.\n\n<b>5. Referral Program</b>\n- Invite friends using your referral link (👥 Referrals).\n- You receive 15% of all ticket purchases made by your referrals.\n- Your link, stats, and earned bonuses are shown in the Referrals section.\n\n<b>6. Multilanguage</b>\n- The bot supports Russian and English. You can change the language in the main menu ('🌐 Change language').\n\n<b>7. Transaction History</b>\n- All your activity (deposits, withdrawals, ticket purchases, winnings, bonuses) is shown in your transaction history.\n\n<b>8. Security and Fairness</b>\n- The use of bots and automated scripts is prohibited.\n- The administration reserves the right to block users for violating the rules.\n\n<b>9. Support</b>\n- For any questions, contact: @support"
    },
    "next": {"ru": "› Далее", "en": "› Next"},
    "prev": {"ru": "‹ Назад", "en": "‹ Back"},
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
        "ru": "\nВаш бонус зависит от количества приглашённых. Сейчас: {percent}%. Максимальный — 25%.",
        "en": "\nYour bonus depends on the number of invited users. Now: {percent}%. Maximum — 25%."
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
        "ru": "Пополнение {amount} TON",
        "en": "Deposit {amount} TON"
    },
    "history_withdraw": {
        "ru": "Вывод {amount} TON",
        "en": "Withdrawal {amount} TON"
    },
    "history_cashback": {
        "ru": "Кэшбек 3% за покупку билетов (выходные)",
        "en": "3% cashback for ticket purchase (weekend)"
    },
    "settings": {
        "ru": "⚙️ Настройки",
        "en": "⚙️ Settings"
    },
    "notifications": {
        "ru": "🔔 Уведомления: {status}",
        "en": "🔔 Notifications: {status}"
    },
    "notifications_on": {
        "ru": "Вкл.",
        "en": "On"
    },
    "notifications_off": {
        "ru": "Выкл.",
        "en": "Off"
    },
    "clear_history": {
        "ru": "🗑 Очистить историю",
        "en": "🗑 Clear history"
    },
    "profile": {
        "ru": "👤 Профиль",
        "en": "👤 Profile"
    },
    "delete_account": {
        "ru": "❌ Удалить аккаунт",
        "en": "❌ Delete account"
    },
    "history_cleared": {
        "ru": "История операций очищена!",
        "en": "Transaction history cleared!"
    },
    "profile_info": {
        "ru": "<b>Профиль</b>\nID: {user_id}\nЯзык: {lang_display}\nБаланс: {balance:.2f} TON\nДата регистрации: {created}",
        "en": "<b>Profile</b>\nID: {user_id}\nLanguage: {lang_display}\nBalance: {balance:.2f} TON\nRegistered: {created}"
    },
    "delete_confirm": {
        "ru": "Вы уверены, что хотите удалить аккаунт? Это действие необратимо!",
        "en": "Are you sure you want to delete your account? This action is irreversible!"
    },
    "delete_yes": {
        "ru": "Да, удалить",
        "en": "Yes, delete"
    },
    "delete_no": {
        "ru": "Нет, отмена",
        "en": "No, cancel"
    },
    "account_deleted": {
        "ru": "Ваш аккаунт удалён.",
        "en": "Your account has been deleted."
    },
    "language_changed": {
        "ru": "Язык успешно изменён!",
        "en": "Language changed successfully!"
    },
    "error_refresh": {
        "ru": "Не удалось обновить сообщение. Пожалуйста, откройте меню заново.",
        "en": "Failed to refresh message. Please reopen the menu."
    },
    "second_chance_winner": {
        "ru": "🎉 В еженедельном розыгрыше «Второй шанс» победил пользователь с id {winner_id}!\nОн получает 10 TON. Поздравляем!\nУчаствуйте в лотерее на этой неделе — и, возможно, удача улыбнётся вам!",
        "en": "🎉 In the weekly 'Second Chance' draw, the winner is user with id {winner_id}!\nThey receive 10 TON. Congratulations!\nTake part in the lottery this week — maybe you'll be the next lucky one!"
    },
    "pay": {
        "ru": "💳 Оплатить",
        "en": "💳 Pay"
    },
    "check_payment": {
        "ru": "🔄 Проверить оплату",
        "en": "🔄 Check payment"
    },
    "try_luck": {
        "ru": "🎫 Испытать удачу",
        "en": "🎫 Try your luck"
    },
    "deposit_min": {
        "ru": "❌ Минимальная сумма для пополнения: 1 TON",
        "en": "❌ Minimum deposit amount: 1 TON"
    },
    "cmd_start": {
        "ru": "🎉 Запустить бота",
        "en": "🎉 Start bot"
    },
    "cmd_help": {
        "ru": "❓ Помощь",
        "en": "❓ Help"
    },
    "cmd_balance": {
        "ru": "💰 Баланс",
        "en": "💰 Balance"
    },
    "cmd_deposit": {
        "ru": "📥 Пополнить",
        "en": "📥 Deposit"
    },
    "cmd_withdraw": {
        "ru": "📤 Вывести",
        "en": "📤 Withdraw"
    },
    "cmd_play": {
        "ru": "🎫 Играть",
        "en": "🎫 Play"
    },
    "cmd_rules": {
        "ru": "📜 Правила",
        "en": "📜 Rules"
    },
    "cmd_referral": {
        "ru": "👥 Рефералы",
        "en": "👥 Referrals"
    },
    "help_text": {
        "ru": "🎯 <b>Доступные команды:</b>\n\n/start - Запустить бота и показать главное меню\n/help - Показать эту справку\n/balance - Показать баланс и историю операций\n/deposit - Пополнить баланс\n/withdraw - Вывести средства\n/play - Участвовать в лотерее\n/rules - Показать правила игры\n/referral - Реферальная программа\n\n💡 <b>Совет:</b> Используйте кнопки в меню для быстрого доступа к функциям!",
        "en": "🎯 <b>Available commands:</b>\n\n/start - Start bot and show main menu\n/help - Show this help\n/balance - Show balance and transaction history\n/deposit - Deposit funds\n/withdraw - Withdraw funds\n/play - Participate in lottery\n/rules - Show game rules\n/referral - Referral program\n\n💡 <b>Tip:</b> Use menu buttons for quick access to functions!"
    },
    "history_lottery": {
        "ru": "Лотерея: {tickets} билет(ов), выигрыш {win} TON",
        "en": "Lottery: {tickets} ticket(s), win {win} TON"
    },
}

def t(key, lang, **kwargs):
    return translations[key][lang].format(**kwargs)

# Главное меню
def main_menu(user_id=None, lang='ru'):
    builder = InlineKeyboardBuilder()
    # Кнопка LOTTY TON сверху
    builder.row(
        InlineKeyboardButton(text=t("play", lang), callback_data="play")
    )
    # Остальные кнопки в два столбца
    builder.row(
        InlineKeyboardButton(text=t("balance", lang), callback_data="balance"),
        InlineKeyboardButton(text=t("promo_btn", lang), callback_data="promo")
    )
    builder.row(
        InlineKeyboardButton(text=t("deposit", lang), callback_data="deposit"),
        InlineKeyboardButton(text=t("withdraw", lang), callback_data="withdraw")
    )
    builder.row(
        InlineKeyboardButton(text=t("rules_btn", lang), callback_data="rules"),
        InlineKeyboardButton(text=t("referral", lang), callback_data="referral")
    )
    # Кнопка смены языка отдельной строкой
    builder.row(
        InlineKeyboardButton(text=t("change_lang", lang), callback_data="change_lang")
    )
    if user_id == ADMIN_ID:
        builder.row(InlineKeyboardButton(text="🧪 Тестовая рассылка Второй шанс", callback_data="second_chance_test"))
        builder.row(InlineKeyboardButton(text="🎉 Рассылка о выигрыше", callback_data="attraction_winner_test"))
        builder.row(InlineKeyboardButton(text=t("add10", lang), callback_data="add10"))
    return builder.as_markup()

# Обработчики команд
@dp.message(CommandStart())
async def start_command(message: types.Message, command: CommandObject):
    user = await db.get_user(message.from_user.id)
    username = message.from_user.username or message.from_user.first_name or "Пользователь"
    # Если пользователь только что создан и есть аргумент ref_
    ref_id = None
    if command.args and command.args.startswith("ref_"):
        try:
            ref_id = int(command.args[4:])
        except Exception:
            ref_id = None
    if ref_id and ref_id != message.from_user.id:
        # Сохраняем пригласившего
        user.invited_by = ref_id
        await db.update_user(user)
        # Добавляем этого пользователя в список рефералов пригласившего
        ref_user = await db.get_user(ref_id)
        referrals = db.get_referrals(ref_user)
        if message.from_user.id not in referrals:
            referrals.append(message.from_user.id)
            db.set_referrals(ref_user, referrals)
            await db.update_user(ref_user)
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
    await message.answer(
        t("start", user.lang, balance=user.balance, username=username),
        reply_markup=main_menu(message.from_user.id, lang=user.lang),
        disable_web_page_preview=True
    )

# Раздел игры — согласие с правилами
@dp.callback_query(F.data == "play")
async def play_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=t("agree_button", user.lang), callback_data="agree_lottery"))
    builder.add(InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main"))
    if (getattr(callback.message, 'sticker', None) or 
        getattr(callback.message, 'content_type', None) == 'sticker' or 
        (callback.message.text and (
            # Русские варианты
            "✅ Баланс пополнен на" in callback.message.text or 
            "✅ " in callback.message.text and "TON отправлены в ваш CryptoBot-кошелёк!" in callback.message.text or
            "🎉 Вы приняли участие в лотерее" in callback.message.text or
            # Английские варианты
            "✅ Balance topped up by" in callback.message.text or
            "✅ " in callback.message.text and "TON sent to your CryptoBot wallet!" in callback.message.text or
            "🎉 You participated in the lottery" in callback.message.text
        ))):
        await callback.message.answer(
            t("agree_lottery", user.lang),
            reply_markup=builder.as_markup()
        )
        return
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
    if (getattr(callback.message, 'sticker', None) or 
        getattr(callback.message, 'content_type', None) == 'sticker' or 
        (callback.message.text and (
            # Русские варианты
            "✅ Баланс пополнен на" in callback.message.text or 
            "✅ " in callback.message.text and "TON отправлены в ваш CryptoBot-кошелёк!" in callback.message.text or
            "🎉 Вы приняли участие в лотерее" in callback.message.text or
            # Английские варианты
            "✅ Balance topped up by" in callback.message.text or
            "✅ " in callback.message.text and "TON sent to your CryptoBot wallet!" in callback.message.text or
            "🎉 You participated in the lottery" in callback.message.text
        ))):
        await callback.message.answer(
            t("choose_tickets", user.lang),
            reply_markup=builder.as_markup()
        )
        return
    await callback.message.edit_text(
        t("choose_tickets", user.lang),
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "back_to_play")
async def back_to_play_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t("ticket_1", user.lang), callback_data="buy_1"))
    builder.row(InlineKeyboardButton(text=t("ticket_3", user.lang), callback_data="buy_3"))
    builder.row(InlineKeyboardButton(text=t("ticket_10", user.lang), callback_data="buy_10"))
    builder.row(InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main"))
    
    # Если последнее сообщение было стикером или содержит сообщения о выигрыше, отправляем новое
    if (getattr(callback.message, 'sticker', None) or 
        getattr(callback.message, 'content_type', None) == 'sticker' or
        (callback.message.text and (
            # Русские варианты
            "🎉 Вы приняли участие в лотерее" in callback.message.text or
            # Английские варианты
            "🎉 You participated in the lottery" in callback.message.text
        ))):
        await callback.message.answer(
            t("choose_tickets", user.lang),
            reply_markup=builder.as_markup()
        )
        return
    
    await callback.message.edit_text(
        t("choose_tickets", user.lang),
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await db.get_user(callback.from_user.id)
    await state.clear()
    
    # Проверяем, содержит ли последнее сообщение стикер или финальные сообщения
    if (getattr(callback.message, 'sticker', None) or 
        getattr(callback.message, 'content_type', None) == 'sticker' or 
        (callback.message.text and (
            # Русские варианты
            "✅ Баланс пополнен на" in callback.message.text or 
            ("✅ " in callback.message.text and "TON отправлены в ваш CryptoBot-кошелёк!" in callback.message.text) or
            "🎉 Вы приняли участие в лотерее" in callback.message.text or
            # Английские варианты
            "✅ Balance topped up by" in callback.message.text or
            ("✅ " in callback.message.text and "TON sent to your CryptoBot wallet!" in callback.message.text) or
            "🎉 You participated in the lottery" in callback.message.text
        ))):
        await callback.message.answer(
            t("start", user.lang, balance=user.balance, username=callback.from_user.username or callback.from_user.first_name or "Пользователь"),
            reply_markup=main_menu(callback.from_user.id, lang=user.lang),
            disable_web_page_preview=True
        )
        return
    
    try:
        await callback.message.edit_text(
            t("start", user.lang, balance=user.balance, username=callback.from_user.username or callback.from_user.first_name or "Пользователь"),
            reply_markup=main_menu(callback.from_user.id, lang=user.lang),
            disable_web_page_preview=True
        )
    except TelegramBadRequest:
        await callback.message.answer(
            t("start", user.lang, balance=user.balance, username=callback.from_user.username or callback.from_user.first_name or "Пользователь"),
            reply_markup=main_menu(callback.from_user.id, lang=user.lang),
            disable_web_page_preview=True
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
    # Кэшбек за выходные
    now = datetime.now(timezone.utc)
    if now.weekday() in [5, 6]:  # 5 - суббота, 6 - воскресенье
        cashback = round(price * 0.03, 2)
        user.balance += cashback
        history.append({"type": "cashback", "amount": cashback})
    # Реферальный бонус (прогрессивный процент)
    if getattr(user, "invited_by", None):
        ref_user = await db.get_user(user.invited_by)
        ref_count = len(db.get_referrals(ref_user))
        ref_percent = get_ref_percent(ref_count)
        bonus = round(price * ref_percent, 2)
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
        await callback.message.answer_sticker("CAACAgIAAxkBAAEOvPloVUPLwmRLS0gSrDAzbXBqSoqZRgAC9wADVp29CgtyJB1I9A0wNgQ")
        await callback.message.answer(
            t("win_result", user.lang, tickets=tickets, win_amount=win_amount, balance=user.balance),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_play")
            ]])
        )
    else:
        db.set_history(user, history)
        await db.update_user(user)
        await callback.message.edit_text(
            t("lose_result", user.lang, tickets=tickets, win_amount=win_amount, balance=user.balance),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_play")
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
                elif h.get("type") == "cashback":
                    desc = t("history_cashback", user.lang)
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
    # Если последнее сообщение было стикером или содержит ключевые фразы, отправляем новое сообщение
    if (getattr(callback.message, 'sticker', None) or 
        getattr(callback.message, 'content_type', None) == 'sticker' or 
        (callback.message.text and (
            # Русские варианты
            "✅ Баланс пополнен на" in callback.message.text or 
            ("✅ " in callback.message.text and "TON отправлены в ваш CryptoBot-кошелёк!" in callback.message.text) or
            "🎉 Вы приняли участие в лотерее" in callback.message.text or
            # Английские варианты
            "✅ Balance topped up by" in callback.message.text or
            ("✅ " in callback.message.text and "TON sent to your CryptoBot wallet!" in callback.message.text) or
            "🎉 You participated in the lottery" in callback.message.text
        ))):
        await callback.message.answer(
            t("balance_text", user.lang, balance=user.balance) + history_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main")
            ]])
        )
        return
    await callback.message.edit_text(
        t("balance_text", user.lang, balance=user.balance) + history_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main")
        ]])
    )

# Раздел пополнения
@dp.callback_query(F.data == "deposit")
async def deposit_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await db.get_user(callback.from_user.id)
    await state.set_state(UserStates.waiting_for_deposit_amount)
    await callback.message.edit_text(
        t("deposit_menu", user.lang),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main")
        ]])
    )

@dp.message(UserStates.waiting_for_deposit_amount, F.text.regexp(r"^\d+(\.\d+)?$"))
async def process_deposit(message: types.Message, state: FSMContext):
    amount = float(message.text)
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    menu_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("pay", user.lang), url="")],
        [InlineKeyboardButton(text=t("check_payment", user.lang), callback_data="check_")],
        [InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main")]
    ])

    if amount >= 1:
        invoice = await cryptopay.create_invoice(amount=amount, description=f"Пополнение баланса для {user_id}")
        if invoice and invoice.get("ok"):
            result = invoice["result"]
            pay_url = result["pay_url"]
            invoice_id = result["invoice_id"]
            menu_markup.inline_keyboard[0][0].url = pay_url
            menu_markup.inline_keyboard[1][0].callback_data = f"check_{invoice_id}"
            await message.answer(t("deposit_pay", user.lang, amount=amount), reply_markup=menu_markup)
            await state.clear()
        else:
            await message.answer(t("deposit_error", user.lang), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main")
            ]]))
            await state.clear()
    else:
        await message.answer(t("deposit_min", user.lang), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main")
        ]]))
        await state.clear()

# Раздел вывода
@dp.callback_query(F.data == "withdraw")
async def withdraw_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await db.get_user(callback.from_user.id)
    await state.set_state(UserStates.waiting_for_withdraw_amount)
    menu_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main")
    ]])
    if user.balance < 1:
        await callback.message.edit_text(t("withdraw_min", user.lang), reply_markup=menu_markup)
        await state.clear()
        return

    await callback.message.edit_text(
        t("withdraw_menu", user.lang, balance=user.balance),
        reply_markup=menu_markup
    )

@dp.message(UserStates.waiting_for_withdraw_amount, F.text.regexp(r"^\d+(\.\d+)?$"))
async def process_withdrawal(message: types.Message, state: FSMContext):
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
            # Отправляем стикер перед сообщением
            sticker_message = await message.answer_sticker("CAACAgIAAxkBAAEOthVoUFVeKz06CYbsn5GfPido8X8ftAACAQEAAladvQoivp8OuMLmNDYE")
            await message.answer(t("withdraw_success", user.lang, amount=amount), reply_markup=menu_markup)
            # Сохраняем ID стикера для возможного удаления
            user.last_sticker_id = sticker_message.message_id
            await db.update_user(user)
        else:
            await message.answer(t("withdraw_error", user.lang), reply_markup=menu_markup)
    else:
        await message.answer(t("withdraw_not_enough", user.lang), reply_markup=menu_markup)
    
    await state.clear()

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
    lang = user.lang
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t("next", lang), callback_data="rules_next"))
    builder.row(InlineKeyboardButton(text=t("back", lang), callback_data="back_to_main"))
    await callback.message.edit_text(
        t("rules_page1", lang),
        reply_markup=builder.as_markup(),
        disable_web_page_preview=True
    )

@dp.callback_query(F.data == "rules_next")
async def rules_next_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    lang = user.lang
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t("prev", lang), callback_data="rules_prev"))
    await callback.message.edit_text(
        t("rules_page2", lang),
        reply_markup=builder.as_markup(),
        disable_web_page_preview=True
    )

@dp.callback_query(F.data == "rules_prev")
async def rules_prev_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    lang = user.lang
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t("next", lang), callback_data="rules_next"))
    builder.row(InlineKeyboardButton(text=t("back", lang), callback_data="back_to_main"))
    await callback.message.edit_text(
        t("rules_page1", lang),
        reply_markup=builder.as_markup(),
        disable_web_page_preview=True
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
    ref_percent = int(get_ref_percent(total_referrals) * 100)
    next_level, next_percent = get_next_ref_level(total_referrals)
    max_percent = 25
    # Таблица уровней
    ref_table = (
        "<b>Уровни реферальной программы:</b>\n"
        "1-2 приглашённых — 10%\n"
        "3-4 — 12%\n"
        "5-9 — 15%\n"
        "10-19 — 18%\n"
        "20-29 — 20%\n"
        "30-49 — 22%\n"
        "50+ — 25%\n"
        if lang == 'ru' else
        "<b>Referral program levels:</b>\n"
        "1-2 invited — 10%\n"
        "3-4 — 12%\n"
        "5-9 — 15%\n"
        "10-19 — 18%\n"
        "20-29 — 20%\n"
        "30-49 — 22%\n"
        "50+ — 25%\n"
    )
    # Прогресс-бар
    bar_total = next_level if next_level else total_referrals
    bar_filled = min(total_referrals, bar_total)
    bar_length = 10
    filled = int(bar_length * bar_filled / bar_total) if bar_total else bar_length
    empty = bar_length - filled
    bar = "[" + "■" * filled + "□" * empty + "]"
    if next_level:
        progress_text = (
            f"\n<b>Ваш бонус:</b> {ref_percent}%  <b>({total_referrals} приглашённых)</b>\n"
            f"{bar} {total_referrals}/{next_level} до {int(next_percent*100)}%\n"
            f"Максимальный бонус: {max_percent}%"
        ) if lang == 'ru' else (
            f"\n<b>Your bonus:</b> {ref_percent}%  <b>({total_referrals} invited)</b>\n"
            f"{bar} {total_referrals}/{next_level} to {int(next_percent*100)}%\n"
            f"Maximum bonus: {max_percent}%"
        )
    else:
        progress_text = (
            f"\n<b>Ваш бонус:</b> {ref_percent}%  <b>({total_referrals} приглашённых)</b>\n"
            f"{bar} {total_referrals}/{total_referrals}\n"
            f"Вы достигли максимального бонуса!"
        ) if lang == 'ru' else (
            f"\n<b>Your bonus:</b> {ref_percent}%  <b>({total_referrals} invited)</b>\n"
            f"{bar} {total_referrals}/{total_referrals}\n"
            f"You have reached the maximum bonus!"
        )
    text = t("referral_menu", lang, ref_link=ref_link, total_referrals=total_referrals, total_active=total_active, earned=earned, total_purchases=total_purchases)
    text += ref_table + progress_text
    if last_active:
        text += "\n" + t("referral_last_active", lang)
        for rid in last_active:
            text += f"- {rid}\n"
    text += t("referral_bonus_info", lang, percent=ref_percent)
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

# Обработчик выбора языка
@dp.callback_query(F.data == "change_lang")
async def change_lang_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Русский", callback_data="lang_ru"),
        InlineKeyboardButton(text="English", callback_data="lang_en")
    )
    if (getattr(callback.message, 'sticker', None) or 
        getattr(callback.message, 'content_type', None) == 'sticker' or 
        (callback.message.text and (
            # Русские варианты
            "✅ Баланс пополнен на" in callback.message.text or 
            "✅ " in callback.message.text and "TON отправлены в ваш CryptoBot-кошелёк!" in callback.message.text or
            "🎉 Вы приняли участие в лотерее" in callback.message.text or
            # Английские варианты
            "✅ Balance topped up by" in callback.message.text or
            "✅ " in callback.message.text and "TON sent to your CryptoBot wallet!" in callback.message.text or
            "🎉 You participated in the lottery" in callback.message.text
        ))):
        await callback.message.answer(
            t("choose_language", user.lang),
            reply_markup=builder.as_markup()
        )
        return
    await callback.message.edit_text(
        t("choose_language", user.lang),
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data.in_(["lang_ru", "lang_en"]))
async def set_language(callback: types.CallbackQuery):
    lang = "ru" if callback.data == "lang_ru" else "en"
    await db.update_user_language(callback.from_user.id, lang)
    user = await db.get_user(callback.from_user.id)
    username = callback.from_user.username or callback.from_user.first_name or "Пользователь"
    try:
        await callback.message.edit_text(
            t("start", lang, balance=user.balance, username=username),
            reply_markup=main_menu(callback.from_user.id, lang=lang),
            disable_web_page_preview=True
        )
    except TelegramBadRequest:
        await callback.answer(t("language_changed", lang), show_alert=True)
    await callback.answer()

# Обработчик тестовой рассылки для администратора
@dp.callback_query(F.data == "second_chance_test")
async def second_chance_test_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    import random
    fake_id = str(random.randint(100000000, 999999999))
    winner_id_masked = fake_id[:-3] + "***"
    # Получаем всех пользователей
    async with db.async_session() as session:
        from sqlalchemy import select
        result = await session.execute(select(User))
        users = result.scalars().all()
    count = 0
    for user in users:
        lang = getattr(user, "lang", "ru")
        try:
            # Кнопка "Испытать удачу" для перехода в главное меню
            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(text=t("try_luck", lang), callback_data="back_to_main"))
            
            await bot.send_message(
                user.user_id,
                t("second_chance_winner", lang, winner_id=winner_id_masked),
                reply_markup=builder.as_markup()
            )
            count += 1
        except Exception as e:
            continue
    await callback.answer(f"Рассылка отправлена {count} пользователям", show_alert=True)

# Обработчик рассылки о выигрыше для администратора
@dp.callback_query(F.data == "attraction_winner_test")
async def attraction_winner_test_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    import random
    fake_id = str(random.randint(100000000, 999999999))
    winner_id_masked = fake_id[:-3] + "***"
    win_amount = random.randint(50, 1500)
    # Получаем всех пользователей
    async with db.async_session() as session:
        from sqlalchemy import select
        result = await session.execute(select(User))
        users = result.scalars().all()
    count = 0
    for user in users:
        lang = getattr(user, "lang", "ru")
        try:
            # Кнопка "Испытать удачу" для перехода в главное меню
            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(text=t("try_luck", lang), callback_data="back_to_main"))
            
            # Текст рассылки о выигрыше
            attraction_text = {
                "ru": f"🎉 ПОЗДРАВЛЯЕМ ПОБЕДИТЕЛЯ!\n\nПользователь с ID {winner_id_masked} только что выиграл {win_amount} TON в лотерее LOTTY TON! 🎊\n\nЭто может быть и вы! Присоединяйтесь к игре и испытайте свою удачу! 🍀\n\nLOTTY TON — честная лотерея с мгновенными выплатами через CryptoBot!",
                "en": f"🎉 CONGRATULATIONS TO THE WINNER!\n\nUser with ID {winner_id_masked} just won {win_amount} TON in the LOTTY TON lottery! 🎊\n\nThis could be you! Join the game and try your luck! 🍀\n\nLOTTY TON — fair lottery with instant payouts via CryptoBot!"
            }
            
            await bot.send_message(
                user.user_id,
                attraction_text[lang],
                reply_markup=builder.as_markup()
            )
            count += 1
        except Exception as e:
            continue
    await callback.answer(f"Рассылка о выигрыше отправлена {count} пользователям", show_alert=True)

# Обработчик проверки оплаты
@dp.callback_query(F.data.startswith("check_"))
async def check_payment_handler(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    invoice_id = callback.data.split("_")[1]
    invoice = await cryptopay.check_invoice(invoice_id)
    menu_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_{invoice_id}")],
        [InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main")]
    ])

    if invoice.get("ok") and invoice.get("result") and invoice["result"].get("items") and len(invoice["result"]["items"]) > 0:
        invoice_data = invoice["result"]["items"][0]
        status = invoice_data.get("status")
        if status == "paid":
            payload = invoice_data.get("payload")
            if payload and payload != 'None':
                try:
                    user_id = int(payload)
                except (ValueError, TypeError):
                    user_id = callback.from_user.id
            else:
                user_id = callback.from_user.id
            amount = float(invoice_data.get("amount", 0))
            user = await db.get_user(user_id)
            user.balance += amount
            history = db.get_history(user)
            history.append({"type": "deposit", "amount": amount, "desc": f"Пополнение через CryptoBot ({amount} TON)"})
            db.set_history(user, history)
            await db.update_user(user)
            # Сначала отправляем стикер
            await callback.message.answer_sticker("CAACAgIAAxkBAAEOvPloVUPLwmRLS0gSrDAzbXBqSoqZRgAC9wADVp29CgtyJB1I9A0wNgQ")
            # Кнопка "‹ Назад"
            menu_markup = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main")
            ]])
            await callback.message.answer(
                t("check_payment_paid", user.lang, amount=amount),
                reply_markup=menu_markup
            )
            return
        elif status == "active":
            try:
                await callback.message.edit_text(
                    t("check_payment_active", user.lang),
                    reply_markup=menu_markup
                )
            except TelegramBadRequest:
                pass
        else:
            try:
                await callback.message.edit_text(
                    t("check_payment_status", user.lang, status=status),
                    reply_markup=menu_markup
                )
            except TelegramBadRequest:
                pass
    else:
        await callback.message.answer_sticker("CAACAgIAAxkBAAEOi95oMFEAAcgO-YbH4g76A2cfNt3zXzUAAgIBAAJWnb0KTuJsgctA5P82BA")
        await callback.message.answer(
            t("check_payment_not_found", user.lang),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_{invoice_id}")],
                [InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main")]
            ])
        )

# Запуск бота
async def main():
    await db.init()
    
    # Устанавливаем команды бота
    await set_bot_commands()
    
    # Запускаем планировщик автоматической рассылки
    asyncio.create_task(weekly_winner_scheduler())
    
    await dp.start_polling(bot)

async def set_bot_commands():
    """Установка команд бота"""
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="play", description="Играть"),
        BotCommand(command="rules", description="Правила"),
        BotCommand(command="referral", description="Рефералы"),
    ]
    await bot.set_my_commands(commands)

async def weekly_winner_scheduler():
    """Планировщик для автоматической рассылки еженедельного выигрыша"""
    while True:
        now = datetime.now(timezone.utc)
        
        # Проверяем, воскресенье ли сегодня и 18:00 UTC
        if now.weekday() == 6 and now.hour == 18 and now.minute == 0:
            await send_weekly_winner_broadcast()
            # Ждём 1 час, чтобы не отправлять повторно
            await asyncio.sleep(3600)
        else:
            # Проверяем каждую минуту
            await asyncio.sleep(60)

async def send_weekly_winner_broadcast():
    """Отправка автоматической рассылки о еженедельном выигрыше"""
    try:
        # Генерируем случайный ID победителя
        fake_id = str(random.randint(100000000, 999999999))
        winner_id_masked = fake_id[:-3] + "***"
        
        # Получаем всех пользователей
        async with db.async_session() as session:
            from sqlalchemy import select
            result = await session.execute(select(User))
            users = result.scalars().all()
        
        count = 0
        for user in users:
            lang = getattr(user, "lang", "ru")
            try:
                # Кнопка "Испытать удачу" для перехода в главное меню
                builder = InlineKeyboardBuilder()
                builder.row(InlineKeyboardButton(text=t("try_luck", lang), callback_data="back_to_main"))
                
                await bot.send_message(
                    user.user_id,
                    t("second_chance_winner", lang, winner_id=winner_id_masked),
                    reply_markup=builder.as_markup()
                )
                count += 1
            except Exception as e:
                logger.error(f"Error sending weekly winner broadcast to user {user.user_id}: {e}")
                continue
        
        logger.info(f"Weekly winner broadcast sent to {count} users")
        
    except Exception as e:
        logger.error(f"Error in weekly winner broadcast: {e}")

# Обработчики команд
@dp.message(Command("help"))
async def help_command(message: types.Message):
    user = await db.get_user(message.from_user.id)
    await message.answer(
        t("help_text", user.lang),
        reply_markup=main_menu(message.from_user.id, lang=user.lang)
    )

@dp.message(Command("balance"))
async def balance_command(message: types.Message):
    user = await db.get_user(message.from_user.id)
    history = db.get_history(user)
    history_text = t("history", user.lang)
    if history:
        for h in history[-5:]:  # Показываем последние 5 операций
            if h.get("type") == "deposit":
                desc = t("history_deposit", user.lang, amount=h.get("amount"))
            elif h.get("type") == "withdraw":
                desc = t("history_withdraw", user.lang, amount=h.get("amount"))
            elif h.get("type") == "lottery":
                desc = t("history_lottery", user.lang, tickets=h.get("tickets", 0), win=h.get("win", 0))
            else:
                desc = h.get("desc", "")
            history_text += f"• {desc}\n"
    else:
        history_text += t("no_history", user.lang)
    
    await message.answer(
        t("balance_text", user.lang, balance=user.balance) + history_text,
        reply_markup=main_menu(message.from_user.id, lang=user.lang)
    )

@dp.message(Command("deposit"))
async def deposit_command(message: types.Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    await state.set_state(UserStates.waiting_for_deposit_amount)
    await message.answer(
        t("deposit_menu", user.lang),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main")
        ]])
    )

@dp.message(Command("withdraw"))
async def withdraw_command(message: types.Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    await state.set_state(UserStates.waiting_for_withdraw_amount)
    menu_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main")
    ]])
    if user.balance < 1:
        await message.answer(t("withdraw_min", user.lang), reply_markup=menu_markup)
        await state.clear()
        return

    await message.answer(
        t("withdraw_menu", user.lang, balance=user.balance),
        reply_markup=menu_markup
    )

@dp.message(Command("play"))
async def play_command(message: types.Message):
    user = await db.get_user(message.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=t("agree_button", user.lang), callback_data="agree_lottery"))
    builder.add(InlineKeyboardButton(text=t("back", user.lang), callback_data="back_to_main"))
    await message.answer(
        t("agree_lottery", user.lang),
        reply_markup=builder.as_markup()
    )

@dp.message(Command("rules"))
async def rules_command(message: types.Message):
    user = await db.get_user(message.from_user.id)
    lang = user.lang
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t("next", lang), callback_data="rules_next"))
    builder.row(InlineKeyboardButton(text=t("back", lang), callback_data="back_to_main"))
    await message.answer(
        t("rules_page1", lang),
        reply_markup=builder.as_markup(),
        disable_web_page_preview=True
    )

@dp.message(Command("referral"))
async def referral_command(message: types.Message):
    user_id = message.from_user.id
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
    ref_percent = int(get_ref_percent(total_referrals) * 100)
    next_level, next_percent = get_next_ref_level(total_referrals)
    max_percent = 25
    # Таблица уровней
    ref_table = (
        "<b>Уровни реферальной программы:</b>\n"
        "1-2 приглашённых — 10%\n"
        "3-4 — 12%\n"
        "5-9 — 15%\n"
        "10-19 — 18%\n"
        "20-29 — 20%\n"
        "30-49 — 22%\n"
        "50+ — 25%\n"
        if lang == 'ru' else
        "<b>Referral program levels:</b>\n"
        "1-2 invited — 10%\n"
        "3-4 — 12%\n"
        "5-9 — 15%\n"
        "10-19 — 18%\n"
        "20-29 — 20%\n"
        "30-49 — 22%\n"
        "50+ — 25%\n"
    )
    # Прогресс-бар
    bar_total = next_level if next_level else total_referrals
    bar_filled = min(total_referrals, bar_total)
    bar_length = 10
    filled = int(bar_length * bar_filled / bar_total) if bar_total else bar_length
    empty = bar_length - filled
    bar = "[" + "■" * filled + "□" * empty + "]"
    if next_level:
        progress_text = (
            f"\n<b>Ваш бонус:</b> {ref_percent}%  <b>({total_referrals} приглашённых)</b>\n"
            f"{bar} {total_referrals}/{next_level} до {int(next_percent*100)}%\n"
            f"Максимальный бонус: {max_percent}%"
        ) if lang == 'ru' else (
            f"\n<b>Your bonus:</b> {ref_percent}%  <b>({total_referrals} invited)</b>\n"
            f"{bar} {total_referrals}/{next_level} to {int(next_percent*100)}%\n"
            f"Maximum bonus: {max_percent}%"
        )
    else:
        progress_text = (
            f"\n<b>Ваш бонус:</b> {ref_percent}%  <b>({total_referrals} приглашённых)</b>\n"
            f"{bar} {total_referrals}/{total_referrals}\n"
            f"Вы достигли максимального бонуса!"
        ) if lang == 'ru' else (
            f"\n<b>Your bonus:</b> {ref_percent}%  <b>({total_referrals} invited)</b>\n"
            f"{bar} {total_referrals}/{total_referrals}\n"
            f"You have reached the maximum bonus!"
        )
    text = t("referral_menu", lang, ref_link=ref_link, total_referrals=total_referrals, total_active=total_active, earned=earned, total_purchases=total_purchases)
    text += ref_table + progress_text
    if last_active:
        text += "\n" + t("referral_last_active", lang)
        for rid in last_active:
            text += f"- {rid}\n"
    text += t("referral_bonus_info", lang, percent=ref_percent)
    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[ 
            InlineKeyboardButton(text=t("back", lang), callback_data="back_to_main")
        ]])
    )

# Прогрессивная реферальная система
REF_LEVELS = [
    (1, 2, 0.10),
    (3, 4, 0.12),
    (5, 9, 0.15),
    (10, 19, 0.18),
    (20, 29, 0.20),
    (30, 49, 0.22),
    (50, 9999, 0.25),
]

def get_ref_percent(ref_count):
    for min_n, max_n, percent in REF_LEVELS:
        if min_n <= ref_count <= max_n:
            return percent
    return 0.10  # по умолчанию

def get_next_ref_level(ref_count):
    for min_n, max_n, percent in REF_LEVELS:
        if ref_count < min_n:
            return min_n, percent
    return None, None

if __name__ == '__main__':
    asyncio.run(main())
