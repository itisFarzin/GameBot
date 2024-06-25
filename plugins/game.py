import asyncio
import random

from betbot import BetBot, filters
from betbot.types import Message, CallbackQuery
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BLACKJACK_CARDS = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10,
                   'A': 11}


def calculate_hand_value(hand: list):
    value = sum(BLACKJACK_CARDS[card] for card in hand)
    num_aces = hand.count('A')
    while value > 21 and num_aces:
        value -= 10
        num_aces -= 1
    return value


@BetBot.on_message(filters.command(BetBot.GAME_COMMANDS) & filters.group)
async def game_commands(app: BetBot, message: Message):
    chat = message.chat
    action = message.command[0]
    amount = message.amount

    if amount is None:
        await message.reply(f"/{action} [amount]")
        return
    if amount == 0:
        await message.reply("The amount can't be zero.")
        return
    if not message.has_enough_money(amount):
        await message.reply("You dont have this amount of money.")
        return
    win = False

    match action:
        case "roulette" | "rl":
            message.remove_from_user_balance(amount)
            message.update_user_value("in_game", True)
            await message.reply("Choose", reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Even", f"roulette-even-{amount}"),
                  InlineKeyboardButton("Odd", f"roulette-odd-{amount}")],
                 [InlineKeyboardButton("Red", f"roulette-red-{amount}"),
                  InlineKeyboardButton("Black", f"roulette-black-{amount}")],
                 [InlineKeyboardButton("Cancel", f"cancel-{amount}")]]
            ))
        case "blackjack" | "bj":
            message.remove_from_user_balance(amount)
            message.update_user_value("in_game", True)
            deck = list(BLACKJACK_CARDS.keys()) * 4
            random.shuffle(deck)
            player_hand = [deck.pop(), deck.pop()]
            dealer_hand = [deck.pop(), deck.pop()]
            message.update_user_value("hand", f"{' '.join(player_hand)}|{' '.join(dealer_hand)}")
            await message.reply(
                f"Player's hand: {', '.join(player_hand)} (Value: {calculate_hand_value(player_hand)})" +
                f"\nDealer's hand: {dealer_hand[0]}, '?'", reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("Hit", f"blackjack-hit-{amount}"),
                      InlineKeyboardButton("Stand", f"blackjack-stand-{amount}")],
                     [InlineKeyboardButton("Cancel", f"cancel-{amount}")]]
                ))
        case "slot":
            text = f"You Lost ${amount:,}"
            double_emoji = False
            message.remove_from_user_balance(amount)
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
                message.add_to_user_balance(amount, False)
            elif win:
                multiplier = {1: 2.5, 22: 2.5, 43: 3, 64: 3.5}[slot.dice.value]
                new_amount, res = message.add_to_user_balance(amount + (amount * multiplier))
                text = f"You Win ${new_amount:,}{res}"
            await slot.reply(text + f"\nYour current balance: ${message.user_balance:,}")
        case "dice":
            message.remove_from_user_balance(amount)
            message.update_user_value("in_game", True)
            buttons = []
            keyboard = [[InlineKeyboardButton("Even", f"dice-even-{amount}"),
                         InlineKeyboardButton("Odd", f"dice-odd-{amount}")],
                        [InlineKeyboardButton("3 and below", f"dice-1to3-{amount}"),
                         InlineKeyboardButton("4 and above", f"dice-4to6-{amount}")]]
            for i in range(1, 7):
                buttons.append(InlineKeyboardButton(str(i), f"dice-{i}-{amount}"))
            keyboard.append(buttons)
            keyboard.append([InlineKeyboardButton("Cancel", f"cancel-{amount}")])
            await message.reply("Choose", reply_markup=InlineKeyboardMarkup(keyboard))
        case "basketball" | "bb":
            message.remove_from_user_balance(amount)
            basketball = await app.send_dice(chat.id, "🏀")
            value = basketball.dice.value
            await asyncio.sleep(4.5)
            if value in [4, 5]:
                multiplier = 1 if value == 4 else 2
                new_amount, res = message.add_to_user_balance(amount + (amount * multiplier))
                text = f"\nYou Win ${new_amount:,}{res}"
            else:
                text = f"\nYou Lost ${amount:,}"
            await message.reply(text + f"\nYour current balance: ${message.user_balance:,}")
            await asyncio.sleep(5)
            await basketball.delete()
        case "football" | "fb":
            message.remove_from_user_balance(amount)
            football = await app.send_dice(chat.id, "⚽")
            value = football.dice.value
            await asyncio.sleep(4.5)
            if value in [3, 4, 5]:
                multiplier = 1 if value in [4, 3] else 2
                new_amount, res = message.add_to_user_balance(amount + (amount * multiplier))
                text = f"\nYou Win ${new_amount:,}{res}"
            else:
                text = f"\nYou Lost ${amount:,}"
            await message.reply(text + f"\nYour current balance: ${message.user_balance:,}")
            await asyncio.sleep(5)
            await football.delete()
        case "dart":
            message.remove_from_user_balance(amount)
            message.update_user_value("in_game", True)
            keyboard = [[InlineKeyboardButton("White", f"dart-white-{amount}"),
                         InlineKeyboardButton("Center", f"dart-center-{amount}"),
                         InlineKeyboardButton("Red", f"dart-red-{amount}")],
                        [InlineKeyboardButton("Cancel", f"cancel-{amount}")]]
            await message.reply("Choose", reply_markup=InlineKeyboardMarkup(keyboard))


@BetBot.on_callback_query(filters.regex("(cancel|roulette|blackjack|dice|dart)\-(\w+)?-?(\w+)?"))
async def game_callback(app: BetBot, query: CallbackQuery):
    if not query.message:
        return
    chat = query.message.chat
    user = query.from_user
    if query.matches[0].group(3):
        game, choose, amount = query.matches[0].groups()
    else:
        choose, amount, _ = query.matches[0].groups()
        game = ""
    amount = int(amount)
    win = False

    if not query.message.reply_to_message:
        return
    if not query.message.reply_to_message.from_user.id == user.id:
        return

    if query.get_user_value("in_game") == 1 and choose == "cancel":
        text = f"You canceled this game and you lost 25% of the money putted in the game."
        query.update_user_value("hand", "")
        query.add_to_user_balance(amount * 0.75, False)
        query.update_user_value("in_game", False)
        await query.answer(text)
        await query.edit_message_text(text)
        return

    if query.get_user_value("in_game") == 0:
        await query.edit_message_reply_markup()
        return
    query.update_user_value("in_game", False)

    if game == "roulette":
        number = random.randrange(1, 36)
        text = f"\nYou Lost ${amount:,}"

        if number % 2 == 0:
            if choose in ["even", "black"]:
                win = True
        else:
            if choose in ["odd", "red"]:
                win = True
        if win:
            new_amount, res = query.add_to_user_balance(amount * 2)
            text = f"\nYou Win ${new_amount:,}{res}"
        query.change_user_game_status(win)

        await query.answer(text)
        await query.edit_message_text(
            f"The wheel spins... and lands on {number} ({'even, black' if number % 2 == 0 else 'odd, red'}).{text}" +
            f"\nYour current balance: ${query.user_balance:,}")

    elif game == "blackjack":
        deck = list(BLACKJACK_CARDS.keys()) * 4
        random.shuffle(deck)
        hand = str(query.get_user_value("hand"))
        if len(hand) == 0:
            await query.answer("Game ended.")
            await query.edit_message_text("Game ended.")
            return
        player_hand, dealer_hand = hand.split("|")
        player_hand = player_hand.split()
        dealer_hand = dealer_hand.split()
        for card in player_hand + dealer_hand:
            deck.pop(deck.index(card))
        if choose == "hit":
            player_hand.append(deck.pop())
            text = f"Your hand: {', '.join(player_hand)} (Value: {calculate_hand_value(player_hand)})"
            if calculate_hand_value(player_hand) > 21:
                await query.answer("You busted! Dealer wins.")
                await query.edit_message_text(
                    text + f"\nDealer's hand: {', '.join(dealer_hand)} (Value: {calculate_hand_value(dealer_hand)})" +
                    f"\n\nYou busted! Dealer wins.\nYour current balance: ${query.user_balance:,}")
                query.change_user_game_status(False)
                query.update_user_value("hand", "")
                return
            query.update_user_value("hand", f"{' '.join(player_hand)}|{' '.join(dealer_hand)}")
            query.update_user_value("in_game", True)
            await query.edit_message_text(text + f"\nDealer's hand: {dealer_hand[0]}, '?'",
                                          reply_markup=InlineKeyboardMarkup(
                                              [[InlineKeyboardButton("Hit", f"blackjack-hit-{amount}"),
                                                InlineKeyboardButton("Stand", f"blackjack-stand-{amount}")]]
                                          ))
        else:
            tie = False
            player_hand_value = calculate_hand_value(player_hand)
            dealer_hand_value = calculate_hand_value(dealer_hand)
            while dealer_hand_value < 17:
                dealer_hand.append(deck.pop())
                dealer_hand_value = calculate_hand_value(dealer_hand)
            message_text = (f"Player's hand: {', '.join(player_hand)} (Value: {calculate_hand_value(player_hand)})" +
                            f"\nDealer's hand: {', '.join(dealer_hand)} (Value: {calculate_hand_value(dealer_hand)})")
            if player_hand_value > 21:
                text = "You busted! Dealer wins."
            elif dealer_hand_value > 21:
                text = "Dealer busted! You win"
                win = True
            elif player_hand_value > dealer_hand_value:
                text = "You win"
                win = True
            elif player_hand_value < dealer_hand_value:
                text = "Dealer wins!"
            else:
                text = "It's a tie!"
                tie = True
            if text:
                message_text += f"\n\n{text}"
            if win:
                new_amount, res = query.add_to_user_balance(amount * 2)
                message_text += f" ${new_amount:,}{res}"
            if tie:
                query.add_to_user_balance(amount, False)
            else:
                query.change_user_game_status(win)
            query.update_user_value("hand", "")
            await query.answer(text)
            await query.edit_message_text(
                message_text + f"\nYour current balance: ${query.user_balance:,}")

    elif game == "dice":
        dice = await app.send_dice(chat.id, reply_to_message_id=query.message.id)
        await query.edit_message_text("Wait...")
        value = dice.dice.value
        text = f"Dice value: {value}"
        await asyncio.sleep(2.5)
        match choose:
            case "even" if value % 2 == 0:
                win = True
            case "odd" if value % 2 != 0:
                win = True
            case "1to3" if value <= 3:
                win = True
            case "4to6" if value >= 4:
                win = True
        if choose.isdigit() and int(choose) == value:
            win = True
        if win:
            multiplier = 1 if choose in ["even", "odd", "1to3", "4to6"] else 2.5
            new_amount, res = query.add_to_user_balance(amount + (amount * multiplier))
            text += f"\nYou Win ${new_amount:,}{res}"
        else:
            text += f"\nYou Lost ${amount:,}"
        query.change_user_game_status(win)
        await query.edit_message_text(text + f"\nYour current balance: ${query.user_balance:,}")
        await asyncio.sleep(5)
        await dice.delete()

    elif game == "dart":
        dart = await app.send_dice(chat.id, "🎯", reply_to_message_id=query.message.id)
        await query.edit_message_text("Wait...")
        value = dart.dice.value
        text = f"You missed"
        match value:
            case 2 | 3 | 4 | 5:
                text = "You hit the {} row ({})".format({2: "first", 3: "second", 4: "third", 5: "fourth"}[value],
                                                        "Red" if value in [2, 4] else "White")
            case 6:
                text = f"You hit the center"
        await asyncio.sleep(3)
        match choose:
            case "red" if value in [2, 4]:
                win = True
            case "white" if value in [3, 5]:
                win = True
            case "center" if value == 6:
                win = True
        if win:
            multiplier = 1 if choose in ["red", "white"] else 2.5
            new_amount, res = query.add_to_user_balance(amount + (amount * multiplier))
            text += f"\nYou Win ${new_amount:,}{res}"
        else:
            text += f"\nYou Lost ${amount:,}"
            if choose == "red" and value == 6:
                text += " (for the game being fair, the red center dont count as red)"
        query.change_user_game_status(win)
        await query.edit_message_text(text + f"\nYour current balance: ${query.user_balance:,}")
        await asyncio.sleep(5)
        await dart.delete()
