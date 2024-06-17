import os
import random
import sqlite3
import asyncio
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, Chat, User, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

load_dotenv()

conn = sqlite3.connect('main.db')
cursor = conn.cursor()

OWNER_ID = int(os.getenv("OWNER_ID"))
START_MONEY = int(os.getenv("START_MONEY", 1000))
LOAN_LIMIT = int(os.getenv("LOAN_LIMIT", 1000))
TAX = os.getenv("TAX", "true").lower() in ["true", "1"]
BLUE = '\033[34m'
RESET = '\033[0m'

BLACKJACK_CARDS = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11}

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

def add_to_user_balance(chat: Chat, user: User, amount: int, tax: bool = TAX):
    if tax:
        update_user_value(chat, app.me, "balance", get_user_value(chat, app.me, "balance") + (amount * 0.1))
    new_value = amount * 0.9 if tax else amount
    update_user_value(chat, user, "balance", get_user_value(chat, user, "balance") + new_value)
    return int(new_value), "\nYou paid 10% in taxes." if tax else ""

def pay_loan(chat: Chat, user: User, amount: int):
    user_balance = get_user_value(chat, user, "balance")
    loan = get_user_value(chat, user, "loan")

    if amount > user_balance:
        return "You dont have the money to pay the loan.", False

    update_user_value(chat, user, "loan", loan - amount if not amount == loan else 0)
    update_user_value(chat, user, "balance", user_balance - amount)
    if not amount == loan:
        return f"You paid ${amount} of the loan.\nYou have ${loan - amount} left to pay.", True
    return f"You paid the ${loan} loan.", True

def pay_loan_from_game(chat: Chat, user: User, win_amount: int):
    pay_amount = 0
    loan = get_user_value(chat, user, "loan")
    text = ""

    if not loan == 0:
        pay_amount = win_amount // 10
        if pay_amount > loan:
            pay_amount = loan
        res, status = pay_loan(chat, user, pay_amount)
        if status:
            text = "\n\n" + res
    return pay_amount, text

def change_user_game_status(chat: Chat, user: User, win: bool):
    res = get_user_value(chat, user, "wins" if win else "losses")
    update_user_value(chat, user, "wins" if win else "losses", int(res) + 1)

    res = get_user_value(chat, user, "win_streak" if win else "loss_streak")
    update_user_value(chat, user, "win_streak" if win else "loss_streak", int(res) + 1)
    update_user_value(chat, user, "win_streak" if not win else "loss_streak", 0)

def calculate_hand_value(hand: list):
    value = sum(BLACKJACK_CARDS[card] for card in hand)
    num_aces = hand.count('A')
    while value > 21 and num_aces:
        value -= 10
        num_aces -= 1
    return value

app = Client("BetBot",
            api_id=os.getenv("APP_ID"),
            api_hash=os.getenv("API_HASH"),
            bot_token=os.getenv("BOT_TOKEN"))

COMMON_COMMANDS = ["info", "balance", "gift", "loan", "repay", "daily", "leaderboard"]
ADMIN_COMMANDS = ["reset", "setbalance", "addbalance", "rmbalance"]
GAME_COMMANDS = ["roulette", "blackjack", "slot", "dice"]

@app.on_message(filters.command(COMMON_COMMANDS + ADMIN_COMMANDS + GAME_COMMANDS) & filters.group)
async def message(_, message: Message):
    chat = message.chat
    user = message.from_user
    action = message.command[0]
    amount = message.command[1].lower() if len(message.command) > 1 else None
    fixed_chat_id = fix_id(chat.id)
    user_is_admin = user.id == OWNER_ID
    win = False

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
            claim_streak INTEGER DEFAULT 0,
            hand TEXT DEFAULT ""
        )
    ''')
    conn.commit()

    user_balance = int(get_user_value(chat, user, "balance"))
    if amount:
        human_readable_number = {"k": 1000, "m": 1000000, "b": 1000000000}
        try:
            for key, value in human_readable_number.items():
                if key in str(amount):
                    amount = float(amount.replace(key, "")) * value
            amount = int(float(amount))
        except:
            await message.reply("The amount should be a positive number.")
            return
        if action in GAME_COMMANDS + ["gift"]:
            if amount == 0:
                await message.reply("The amount can't be zero.")
                return
            if user_balance < amount:
                await message.reply("You dont have this amount of money.")
                return

    match action:
        case "info":
            user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
            _, name, balance, wins, losses, win_streak, loss_streak, loan, _, claim_streak, _ = get_user_values(chat, user, "*")
            await message.reply(f"Name: {name}\nBalance: ${int(balance):,}\nWins: {wins}\nLosses: {losses}\nWin Streak: {win_streak}\nLoss Streak: {loss_streak}\nLoan: ${loan}\nClaim Streak: {claim_streak}")
        case "balance":
            user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
            await message.reply(f"Balance: ${get_user_value(chat, user, 'balance'):,}.")
        case "gift":
            if amount is None:
                await message.reply("/gift [amount]")
                return
            if not message.reply_to_message:
                await message.reply("You should reply to user that you want to gift your money.")
                return
            update_user_value(chat, user, "balance", user_balance - amount)
            that_user = message.reply_to_message.from_user
            that_user_balance = get_user_value(chat, that_user, "balance")
            amount, text = add_to_user_balance(chat, that_user, amount)
            await message.reply(f"You gifted {that_user.first_name} ${amount:,}" + text)
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
            if amount is None:
                await message.reply("/setbalance [amount]")
                return
            that_user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
            update_user_value(chat, that_user, "balance", amount)
            await message.reply(f"Set {that_user.first_name} balance to ${amount:,}")
        case "addbalance"|"rmbalance" if user_is_admin:
            if amount is None:
                await message.reply("/addbalance|rmbalance [amount]")
                return
            that_user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
            that_user_balance = get_user_value(chat, that_user, "balance")
            if action == "addbalance":
                new_amount = that_user_balance + amount
                text = f"Added ${amount} to {that_user.first_name}.\nNew balance: ${new_amount}"
            else:
                new_amount = that_user_balance - amount
                text = f"Removed ${amount} from {that_user.first_name}.\nNew balance: ${new_amount}"
            update_user_value(chat, that_user, "balance", new_amount)
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
            if amount is None:
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
            add_to_user_balance(chat, user, amount, False)
            conn.commit()
            await message.reply(f"You have been granted a loan of ${amount}. It has been added to your balance.")
        case "repay":
            loan = get_user_value(chat, user, "loan")
            if loan == 0:
                await message.reply("You dont have loan to pay.")
                return
            if amount is None:
                amount = loan
            if amount == 0:
                await message.reply("Pay amount can't be zero.")
                return
            if amount > loan:
                amount = loan
            await message.reply(pay_loan(chat, user, amount)[0])
        case "daily":
            today = datetime.date()
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
            reward, text = add_to_user_balance(chat, user, reward)
            update_user_value(chat, user, "last_claim", today)
            update_user_value(chat, user, "claim_streak", streak)

            await message.reply(f"You've received ${reward} as your daily reward! Your current streak is {streak} days.\nYour new balance is ${user_balance + reward:,}" + text)
        case "roulette":
            if amount is None:
                await message.reply("/roulette [amount]")
                return
            update_user_value(chat, user, "balance", user_balance - amount)
            await message.reply("Choose", reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Even", f"even-{amount}"), InlineKeyboardButton("Odd", f"odd-{amount}")],
                 [InlineKeyboardButton("Red", f"red-{amount}"), InlineKeyboardButton("Black", f"black-{amount}")],
                 [InlineKeyboardButton("Cancel", f"cancel-{amount}")]]
            ))
        case "blackjack":
            if amount is None:
                await message.reply("/blackjack [amount]")
                return
            update_user_value(chat, user, "balance", user_balance - amount)
            deck = list(BLACKJACK_CARDS.keys()) * 4
            random.shuffle(deck)
            player_hand = [deck.pop(), deck.pop()]
            dealer_hand = [deck.pop(), deck.pop()]
            update_user_value(chat, user, "hand", f"{' '.join(player_hand)}|{' '.join(dealer_hand)}")
            await message.reply(f"Player's hand: {', '.join(player_hand)} (Value: {calculate_hand_value(player_hand)})" +
                                f"\nDealer's hand: {dealer_hand[0]}, '?'", reply_markup=InlineKeyboardMarkup(
                                    [[InlineKeyboardButton("Hit", f"blackjack-hit-{amount}"), InlineKeyboardButton("Stand", f"blackjack-stand-{amount}")],
                                     [InlineKeyboardButton("Cancel", f"cancel-{amount}")]]
                                ))
        case "slot":
            if amount is None:
                await message.reply("/slot [amount]")
                return
            text = "You Lost."
            double_emoji = False
            update_user_value(chat, user, "balance", user_balance - amount)
            slot = await app.send_dice(chat.id, "🎰", reply_to_message_id=message.id)
            value = slot.dice.value
            await asyncio.sleep(2)
            if value in [1, 22, 43, 64]:
                win = True
            elif value in [2, 3, 4, 6, 11, 16, 17, 21, 23, 24, 27, 32, 33, 38, 41, 42, 44, 48, 49, 54, 59, 61, 62, 63]:
                double_emoji = True
            elif value in [5, 9, 13, 18, 26, 30, 35, 39, 47, 52, 56, 60]:
                double_emoji = True
            if double_emoji:
                text = "Double Emoji, money refunded."
                add_to_user_balance(chat, user, amount, False)
            elif win:
                add_to_user_balance(chat, user, amount, False)
                amount = amount * {1: 2.5, 22: 2.5, 43: 3, 64: 3.5}[slot.dice.value]
                pay_amount, res = pay_loan_from_game(chat, user, amount)
                _, res2 = add_to_user_balance(chat, user, amount - pay_amount)
                text = f"You Win ${amount:,}{res}{res2}"
            await slot.reply(text + f"\nYour current balance: ${int(get_user_value(chat, user, 'balance')):,}")
        case "dice":
            if amount is None:
                await message.reply("/dice [amount]")
                return
            update_user_value(chat, user, "balance", user_balance - amount)
            temp_list = []
            keyboard = [[InlineKeyboardButton("Even", f"dice-even-{amount}"), InlineKeyboardButton("Odd", f"dice-odd-{amount}")],
                        [InlineKeyboardButton("3 and below", f"dice-1upto3-{amount}"), InlineKeyboardButton("4 and above", f"dice-4upto6-{amount}")]]
            for i in range(1, 7):
                temp_list.append(InlineKeyboardButton(str(i), f"dice-{i}-{amount}"))
            keyboard.append(temp_list)
            keyboard.append([InlineKeyboardButton("Cancel", f"cancel-{amount}")])
            await message.reply("Choose", reply_markup=InlineKeyboardMarkup(keyboard))

@app.on_callback_query()
async def callback(_, query: CallbackQuery):
    data = query.data
    if not query.message:
        return
    message = query.message
    chat = message.chat
    user = query.from_user
    datas = data.split("-")
    if len(datas) == 2:
        chose, amount = datas
    else:
        chose = None
        game, chose, amount = datas
    amount = int(amount)
    text = None
    win = False
    user_balance = int(get_user_value(chat, user, "balance"))

    if not message.reply_to_message:
        return
    if not message.reply_to_message.from_user.id == user.id:
        return
    
    if chose == "cancel":
        text = f"You canceled this game and you lost 25% of the money putted in the game."
        update_user_value(chat, user, "hand", "")
        add_to_user_balance(chat, user, amount * 0.75, False)
        await query.answer(text)
        await query.edit_message_text(text)
        return

    if game == "roulette":
        number = random.randrange(1, 36)
        text = f"\nYou Lose ${amount:,}."

        if number % 2 == 0:
            if chose in ["even", "black"]:
                win = True
        else:
            if chose in ["odd", "red"]:
                win = True
        if win:
            add_to_user_balance(chat, user, amount, False)
            pay_amount, res = pay_loan_from_game(chat, user, amount)
            _, res2 = add_to_user_balance(chat, user, amount - pay_amount)
            text = f"\nYou Win ${amount:,}{res}{res2}"
        change_user_game_status(chat, user, win)

        await query.answer(text)
        await query.edit_message_text(f'The wheel spins... and lands on {number} ({"even, black" if number % 2 == 0 else "odd, red"}).' + text + f"\nYour current balance: ${int(get_user_value(chat, user, 'balance')):,}")
    
    if game == "blackjack":
        deck = list(BLACKJACK_CARDS.keys()) * 4
        random.shuffle(deck)
        hand = str(get_user_value(chat, user, "hand"))
        if len(hand) == 0:
            await query.answer("Game ended.")
            await query.edit_message_text("Game ended.")
            return
        player_hand, dealer_hand = hand.split("|")
        player_hand = player_hand.split()
        dealer_hand = dealer_hand.split()
        for card in player_hand + dealer_hand:
            deck.pop(deck.index(card))
        if chose == "hit":
            player_hand.append(deck.pop())
            text = f"Your hand: {', '.join(player_hand)} (Value: {calculate_hand_value(player_hand)})"
            if calculate_hand_value(player_hand) > 21:
                await query.answer("You busted! Dealer wins.")
                await query.edit_message_text(text + f"\nDealer's hand: {', '.join(dealer_hand)} (Value: {calculate_hand_value(dealer_hand)})\n\nYou busted! Dealer wins.\nYour current balance: ${user_balance:,}")
                change_user_game_status(chat, user, False)
                update_user_value(chat, user, "hand", "")
                return
            dealer_hand.append(deck.pop())
            if calculate_hand_value(dealer_hand) > 21:
                add_to_user_balance(chat, user, amount, False)
                pay_amount, res = pay_loan_from_game(chat, user, amount)
                _, res2 = add_to_user_balance(chat, user, amount - pay_amount)
                await query.answer("You win!")
                await query.edit_message_text(text + f"\nDealer's hand: {', '.join(dealer_hand)} (Value: {calculate_hand_value(dealer_hand)})\n\nYou win!\nYour current balance: ${int(get_user_value(chat, user, 'balance')):,}" + res + res2)
                change_user_game_status(chat, user, True)
                update_user_value(chat, user, "hand", "")
                return
            update_user_value(chat, user, "hand", f"{' '.join(player_hand)}|{' '.join(dealer_hand)}")
            await query.edit_message_text(text + f"\nDealer's hand: {dealer_hand[0]}, '?'", reply_markup=InlineKeyboardMarkup(
                                    [[InlineKeyboardButton("Hit", f"hit-{amount}"), InlineKeyboardButton("Stand", f"stand-{amount}")]]
                                ))
        else:
            tie = False
            player_hand_value = calculate_hand_value(player_hand)
            dealer_hand_value = calculate_hand_value(dealer_hand)
            while player_hand_value > dealer_hand_value:
                dealer_hand.append(deck.pop())
                dealer_hand_value = calculate_hand_value(dealer_hand)
            message_text = f"Player's hand: {', '.join(player_hand)} (Value: {calculate_hand_value(player_hand)})" + f"\nDealer's hand: {', '.join(dealer_hand)} (Value: {calculate_hand_value(dealer_hand)})"
            if player_hand_value > 21:
                text = "You busted! Dealer wins."
            elif dealer_hand_value > 21:
                text = "Dealer busted! You win!"
                win = True
            elif player_hand_value > dealer_hand_value:
                text = "You win!"
                win = True
            elif player_hand_value < dealer_hand_value:
                text = "Dealer wins!"
            else:
                text = "It's a tie!"
                tie = True
            if text:
                message_text += f"\n\n{text}"
            new_amount = 0
            if win:
                add_to_user_balance(chat, user, amount, False)
                pay_amount, res = pay_loan_from_game(chat, user, amount)
                message_text += res
                new_amount = amount - pay_amount
            if tie:
                new_amount = amount
            else:
                change_user_game_status(chat, user, win)
            update_user_value(chat, user, "hand", "")
            _, res = add_to_user_balance(chat, user, new_amount, win)
            await query.answer(text)
            await query.edit_message_text(message_text + f"\nYour current balance: ${get_user_value(chat, user, 'balance'):,}" + res)

    if game == "dice":
        dice = await app.send_dice(chat.id, reply_to_message_id=message.id)
        value = dice.dice.value
        text = f"Dice value: {value}"
        await asyncio.sleep(2.5)
        match chose:
            case "even" if value % 2 == 0:
                win = True
            case "odd" if value % 2 != 0:
                win = True
            case "1upto3" if value <= 3:
                win = True
            case "4upto6" if value >= 4:
                win = True
        if chose.isdigit() and int(chose) == value:
            win = True
        if win:
            pay_amount, res = pay_loan_from_game(chat, user, amount)
            add_to_user_balance(chat, user, amount, False)
            multiplier = 0.5 if chose in ["even", "odd", "1upto3", "4upto6"] else 2
            amount = int(amount * multiplier)
            _, res2 = add_to_user_balance(chat, user, amount - pay_amount)
            text += f"\nYou Win ${amount:,}{res}{res2}"
        else:
            text += "\nYou Lost."
        await query.edit_message_text(text + f"\nYour current balance: ${int(get_user_value(chat, user, 'balance')):,}")
        await asyncio.sleep(5)
        await dice.delete()

if __name__ == "__main__":
    print(BLUE + "BetBot by itisFarzin" + RESET)
    app.run()
    conn.close()
