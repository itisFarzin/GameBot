import os
import random
import sqlite3
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, Chat, User, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

load_dotenv()

conn = sqlite3.connect('main.db')
cursor = conn.cursor()

OWNER_ID = int(os.getenv("OWNER_ID"))
START_MONEY = int(os.getenv("START_MONEY") or 1000)
LOAN_LIMIT = int(os.getenv("LOAN_LIMIT") or 1000)
BLUE = '\033[34m'
RESET = '\033[0m'

def fix_id(id: int):
    return int(str(id).replace("-", ""))

def insert_user(chat: Chat, user: User, balance: int = START_MONEY):
    chat_id = fix_id(chat.id)
    cursor.execute(f'''
        INSERT OR IGNORE INTO group_{chat_id} (user_id, name, balance)
        VALUES (?, ?, ?)
    ''', (user.id, user.first_name, balance))
    conn.commit()

def update_user_value(chat: Chat, user: User, key: str, value: str | int):
    chat_id = fix_id(chat.id)
    insert_user(chat, user)
    cursor.execute(f'''
        UPDATE group_{chat_id}
        SET {key} = ?
        WHERE user_id = ?
    ''', (value, user.id))
    conn.commit()

def get_user_values(chat: Chat, user: User, key: str):
    chat_id = fix_id(chat.id)
    insert_user(chat, user)
    cursor.execute(f'''
        SELECT {key}
        FROM group_{chat_id}
        WHERE user_id = ?
    ''', (user.id,))
    return cursor.fetchone()

def get_user_value(chat: Chat, user: User, key: str):
    return get_user_values(chat, user, key)[0]

def pay_loan(chat: Chat, user: User, amount: int):
    user_balance = get_user_value(chat, user, "balance")
    loan = get_user_value(chat, user, "loan")

    if amount > user_balance:
        return "You dont have the money to pay the loan."

    update_user_value(chat, user, "loan", loan - amount if not amount == loan else 0)
    update_user_value(chat, user, "balance", user_balance - amount)
    if not amount == loan:
        return f"You paid ${amount} of the loan.\nYou have ${loan - amount} left to pay."
    return f"You paid the ${loan} loan."

app = Client("BetBot",
            api_id=os.getenv("APP_ID"),
            api_hash=os.getenv("API_HASH"),
            bot_token=os.getenv("BOT_TOKEN"))

@app.on_message(filters.command(["info", "balance", "gift", "reset", "setbalance", "addbalance", "rmbalance", "leaderboard", "loan", "repay", "daily", "roulette"]) & filters.group)
async def message(_, message: Message):
    chat = message.chat
    user = message.from_user
    action = message.command[0]
    amount = message.command[1] if len(message.command) > 1 else None
    if amount:
        if not amount.isnumeric():
            await message.reply("The amount should be a positive number.")
            return
        amount = int(amount)
    fixed_chat_id = fix_id(chat.id)
    user_is_admin = user.id == OWNER_ID

    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS group_{fixed_chat_id} (
            user_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            balance BIGINT DEFAULT {START_MONEY},
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            win_streak INTEGER DEFAULT 0,
            loss_streak INTEGER DEFAULT 0,
            loan BIGINT DEFAULT 0,
            last_claim DATE,
            claim_streak INTEGER DEFAULT 0
        )
    ''')
    conn.commit()

    match action:
        case "info":
            user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
            _, name, balance, wins, losses, win_streak, loss_streak, loan, __, claim_streak = get_user_values(chat, user, "*")
            await message.reply(f"Name: {name}\nBalance: ${balance:,}\nWins: {wins}\nLosses: {losses}\nWin Streak: {win_streak}\nLoss Streak: {loss_streak}\nLoan: ${loan}\nClaim Streak: {claim_streak}")
        case "balance":
            user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
            await message.reply(f"Balance: ${get_user_value(chat, user, 'balance'):,}.")
        case "gift":
            if not amount:
                await message.reply("/gift [amount]")
                return
            if not message.reply_to_message:
                await message.reply("You should reply to user that you want to gift your money.")
                return
            user_balance = get_user_value(chat, user, "balance")
            if user_balance < amount:
                await message.reply("You dont have this amount of money.")
                return
            update_user_value(chat, user, "balance", user_balance - amount)
            that_user = message.reply_to_message.from_user
            that_user_balance = get_user_value(chat, that_user, "balance")
            update_user_value(chat, that_user, "balance", that_user_balance + amount)
            await message.reply(f"You gifted {that_user.first_name} ${amount}.")
        case "reset" if user_is_admin:
            if not message.reply_to_message:
                await message.reply("You should reply to user that you want to delete their data.")
                return
            user = message.reply_to_message.from_user
            cursor.execute(f'''
                DELETE FROM group_{fixed_chat_id}
                WHERE user_id = ?
            ''', (user.id,))
            await message.reply(f"Removed {user.first_name} data successfully.")
        case "setbalance" if user_is_admin:
            if not amount:
                await message.reply("/setbalance [amount]")
                return
            user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
            update_user_value(chat, user, "balance", amount)
            await message.reply(f"Set {user.first_name} balance to ${amount:,}")
        case "addbalance"|"rmbalance" if user_is_admin:
            if not amount:
                await message.reply("/addbalance|rmbalance [amount]")
                return
            user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
            user_balance = get_user_value(chat, user, "balance")
            if action == "addbalance":
                new_amount = user_balance + amount
                text = f"Added ${amount} to {user.first_name}.\nNew balance: ${new_amount}."
            else:
                new_amount = user_balance - amount
                text = f"Removed ${amount} from {user.first_name}.\nNew balance: ${new_amount}."
            update_user_value(chat, user, "balance", new_amount)
            await message.reply(text)
        case "leaderboard":
            text = "Leaderboard:\n"
            cursor.execute(f'''
                SELECT name, balance
                FROM group_{fixed_chat_id}
                ORDER BY balance DESC
                LIMIT 10
            ''')
            for i, data in enumerate(cursor.fetchall(), start=1):
                name, balance = data
                text += f"{i}. {name}: ${int(balance):,}\n"
            await message.reply(text)
        case "loan":
            if not amount:
                await message.reply("/loan [amount]")
                return
            if amount == 0:
                await message.reply("Loan amount can't be zero.")
                return
            if amount > LOAN_LIMIT:
                await message.reply(f"Loan amount can't exceed ${LOAN_LIMIT:,}.")
                return
            loan = get_user_value(chat, user, "loan")
            if not loan == 0:
                await message.reply("You have loan to repay.\nUse /repay to pay it now.")
                return
            update_user_value(chat, user, "loan", amount)
            user_balance = get_user_value(chat, user, "balance")
            update_user_value(chat, user, "balance", user_balance + amount)
            conn.commit()
            await message.reply(f"You have been granted a loan of ${amount}. It has been added to your balance.")
        case "repay":
            loan = get_user_value(chat, user, "loan")
            if loan == 0:
                await message.reply("You dont have loan to pay.")
                return
            if not amount:
                amount = loan
            if amount == 0:
                await message.reply("Pay amount can't be zero.")
                return
            if amount > loan:
                amount = loan
            await message.reply(pay_loan(chat, user, amount))
        case "daily":
            today = datetime.utcnow().date()
            last_claim, streak = get_user_values(chat, user, "last_claim, claim_streak")

            if last_claim:
                last_claim_date = datetime.strptime(last_claim, '%Y-%m-%d').date()
                if last_claim_date == today:
                    await message.reply("You've already claimed your daily reward today.")
                    return

                if last_claim_date == today - timedelta(days=1):
                    streak += 1
                else:
                    streak = 1

                if streak == 8:
                    streak = 1

            streak = streak or 1
            reward = 100 * streak
            user_balance = get_user_value(chat, user, "balance")
            update_user_value(chat, user, "balance", user_balance + reward)
            update_user_value(chat, user, "last_claim", today)
            update_user_value(chat, user, "claim_streak", streak)

            await message.reply(f"You've received ${reward} as your daily reward! Your current streak is {streak} days.\nYour new balance is ${get_user_value(chat, user, 'balance'):,}")
        case "roulette":
            if not amount:
                await message.reply("/roulette [amount]")
                return
            if amount == 0:
                await message.reply("The amount can't be zero.")
                return
            if get_user_value(chat, user, "balance") < amount:
                await message.reply("You dont have this amount of money.")
                return
            await message.reply("Choose", reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Even", f"even-{amount}"), InlineKeyboardButton("Odd", f"odd-{amount}")],
                 [InlineKeyboardButton("Red", f"red-{amount}"), InlineKeyboardButton("Black", f"black-{amount}")],
                 [InlineKeyboardButton("Cancel", f"cancel-{amount}")]]
            ))

@app.on_callback_query()
async def callback(_, query: CallbackQuery):
    data = query.data
    chat = query.message.chat
    user = query.from_user
    datas = data.split("-")

    if not query.message:
        return
    if not query.message.reply_to_message:
        return
    if not query.message.reply_to_message.from_user.id == user.id:
        return

    if datas[0] in ["even", "odd", "red", "black", "cancel"]:
        chose, amount = datas
        amount = int(amount)
        user_balance = get_user_value(chat, user, "balance")
        text = None
        won = False
        number = random.randrange(1, 36)

        if user_balance < amount:
            text = "You dont have this amount of money."
        if chose == "cancel":
            text = f"You canceled this game."
        if text:
            await query.answer(text)
            await query.edit_message_text(text)
            return
        if number % 2 == 0:
            if chose in ["even", "black"]:
                text = f"You Won ${(amount * 2):,}."
                won = True
        else:
            if chose in ["odd", "red"]:
                text = f"You Won ${(amount * 2):,}."  
                won = True
        if not won:
            text = f"You Lose ${amount:,}."
        res = get_user_value(chat, user, "wins" if won else "losses")
        update_user_value(chat, user, "wins" if won else "losses", int(res) + 1)

        res = get_user_value(chat, user, "win_streak" if won else "loss_streak")
        update_user_value(chat, user, "win_streak" if won else "loss_streak", int(res) + 1)
        update_user_value(chat, user, "win_streak" if not won else "loss_streak", 0)
        pay_amount = 0
        if won:
            loan = get_user_value(chat, user, "loan")
            if not loan == 0:
                pay_amount = amount // 10
                if pay_amount > loan:
                    pay_amount = loan
                text += "\n\n" + pay_loan(chat, user, pay_amount)
        update_user_value(chat, user, "balance", (user_balance + amount - pay_amount) if won else (user_balance - amount))

        await query.answer(text)
        await query.edit_message_text(f'The wheel spins... and lands on {number} ({"even, black" if number % 2 == 0 else "odd, red"}).\n' + text)

if __name__ == "__main__":
    print(BLUE + "BetBot by itisFarzin" + RESET)
    app.run()
    conn.close()
