import os
import random
import sqlite3
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message, Chat, User, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

load_dotenv()

conn = sqlite3.connect('main.db')
cursor = conn.cursor()

def fix_id(id: int):
    return int(str(id).replace("-", ""))

cursor.execute('''
    CREATE TABLE IF NOT EXISTS groups (
        group_id INTEGER PRIMARY KEY UNIQUE,
        name TEXT NOT NULL
    )
''')

def insert_user(group: Chat, user: User, balance: int = 100):
    group_id = fix_id(group.id)
    cursor.execute(f'''
        INSERT OR IGNORE INTO group_{group_id} (user_id, name, balance)
        VALUES (?, ?, ?)
    ''', (user.id, user.first_name, balance))
    conn.commit()

def update_user_balance(group: Chat, user: User, new_amount: int):
    group_id = fix_id(group.id)
    insert_user(group, user)
    cursor.execute(f'''
        UPDATE group_{group_id}
        SET balance = ?
        WHERE user_id = ?
    ''', (new_amount, user.id))
    conn.commit()

def get_user_balance(group: Chat, user: User):
    group_id = fix_id(group.id)
    insert_user(group, user)
    cursor.execute(f'''
        SELECT balance
        FROM group_{group_id}
        WHERE user_id = ?
    ''', (user.id,))
    return cursor.fetchone()[0]

OWNER_ID = int(os.getenv("OWNER_ID"))
BLUE = '\033[34m'
RESET = '\033[0m'

app = Client("BetBot",
            api_id=os.getenv("APP_ID"),
            api_hash=os.getenv("API_HASH"),
            bot_token=os.getenv("BOT_TOKEN"))

@app.on_message(filters.command(["info", "balance", "gift", "setbalance", "addbalance", "rmbalance", "leaderboard", "roulette"]) & filters.group)
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

    cursor.execute('''
        INSERT OR IGNORE INTO groups (group_id, name)
        VALUES (?, ?)
    ''', (fixed_chat_id, chat.full_name))
    
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS group_{fixed_chat_id} (
            user_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            balance BIGINT DEFAULT 100,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    insert_user(chat, user)

    match action:
        case "info":
            user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
            insert_user(chat, user)
            cursor.execute(f'''
                SELECT *
                FROM group_{fixed_chat_id}
                WHERE user_id = ?
            ''', (user.id,))
            _, name, balance, wins, losses = cursor.fetchone()
            await message.reply(f"Name: {name}\nBalance: ${balance}\nWins: {wins}\nLosses: {losses}")
        case "balance":
            user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
            await message.reply(f"Balance: ${get_user_balance(chat, user):,}.")
        case "gift":
            if not amount:
                await message.reply("/gift [amount]")
                return
            if not message.reply_to_message:
                await message.reply("You should reply to user you want to gift your money.")
                return
            user_balance = get_user_balance(chat, user)
            if user_balance < amount:
                await message.reply("You dont have this amount of money.")
                return
            that_user = message.reply_to_message.from_user
            that_user_balance = get_user_balance(chat, that_user)
            update_user_balance(chat, user, user_balance - amount)
            update_user_balance(chat, that_user, that_user_balance + amount)
            await message.reply(f"You gifted {that_user.first_name} ${amount}")
        case "setbalance" if user_is_admin:
            if not amount:
                await message.reply("/setbalance [amount]")
                return
            user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
            update_user_balance(chat, user, amount)
            await message.reply(f"Set {user.first_name} balance to ${amount}\nNew balance: ${amount}")
        case "addbalance"|"rmbalance" if user_is_admin:
            if not amount:
                await message.reply("/addbalance|rmbalance [amount]")
                return
            user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
            user_balance = get_user_balance(chat, user)
            if action == "addbalance":
                new_amount = user_balance + amount
                text = f"Added ${amount} to {user.first_name}.\nNew balance: ${new_amount}"
            else:
                new_amount = user_balance - amount
                f"Removed ${amount} from {user.first_name}.\nNew balance: ${new_amount}"
            update_user_balance(chat, user, new_amount)
            await message.reply(text)
        case "leaderboard":
            text = "Leaderboard:\n"
            cursor.execute(f'''
                SELECT name, balance
                FROM group_{fixed_chat_id}
                ORDER BY balance DESC
                LIMIT 10
            ''')
            for data in cursor.fetchall():
                name, balance = data
                text += f"{name}: {int(balance):,}\n"
            await message.reply(text)
        case "roulette":
            if not amount:
                await message.reply("/roulette [amount]")
                return
            if amount == 0:
                await message.reply("The amount can't be zero.")
                return
            if get_user_balance(chat, user) < amount:
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
    fixed_chat_id = fix_id(chat.id)

    if not query.message:
        return
    if not query.message.reply_to_message:
        return
    if not query.message.reply_to_message.from_user.id == user.id:
        return

    if datas[0] in ["even", "odd", "red", "black", "cancel"]:
        chose, amount = datas
        amount = int(amount)
        user_balance = get_user_balance(chat, user)
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
        update_user_balance(chat, user, (user_balance + amount) if won else (user_balance - amount))
        cursor.execute(f'''
            SELECT {"wins" if won else "losses"}
            FROM group_{fixed_chat_id}
            WHERE user_id = ?
        ''', (user.id,))
        cursor.execute(f'''
            UPDATE group_{fixed_chat_id}
            SET {"wins" if won else "losses"} = ?
            WHERE user_id = ?
        ''', (cursor.fetchone()[0] + 1, user.id))
        conn.commit()

        await query.answer(text)
        await query.edit_message_text(f'The wheel spins... and lands on {number} ({"even, black" if number % 2 == 0 else "odd, red"}).\n' + text)

if __name__ == "__main__":
    print(BLUE + "BetBot by itisFarzin" + RESET)
    app.run()
    conn.close()