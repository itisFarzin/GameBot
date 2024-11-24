import asyncio
import random
from pyrogram import enums
from gamebot import GameBot, filters
from gamebot.database import Config
from gamebot.types import Message, CallbackQuery
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BLACKJACK_CARDS = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10,
                   'A': 11}
get_translation = Config.get_translation


def calculate_hand_value(hand: list):
    value = sum(BLACKJACK_CARDS[card] for card in hand)
    num_aces = hand.count('A')
    while value > 21 and num_aces:
        value -= 10
        num_aces -= 1
    return value


@GameBot.on_message(filters.command(Config.GAME_COMMANDS))
async def game_commands(client: GameBot, message: Message):
    chat = message.chat
    action = message.command[0]
    amount = message.amount

    if amount is None:
        await message.reply(get_translation("common_use").format(action))
        return
    if amount == 0:
        await message.reply(get_translation("no_zero_amount"))
        return
    if not message.has_enough_money(amount):
        await message.reply(get_translation("dont_have_money"))
        return
    if amount > Config.GAME_AMOUNT_LIMIT:
        await message.reply(get_translation("game_amount_limit").format(Config.GAME_AMOUNT_LIMIT))
        return
    if bool(message.get_user_value("in_game")):
        await message.reply(get_translation("already_in_game"))
        return
    win = False

    match action:
        case "roulette" | "rl":
            result = message.can_play("roulette")
            if not result[0]:
                return await message.reply(result[1])
            message.remove_from_user_balance(amount)
            message.update_user_value("in_game", True)
            await message.reply(get_translation("choose"), reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(get_translation("even"), f"roulette-even-{amount}"),
                  InlineKeyboardButton(get_translation("odd"), f"roulette-odd-{amount}")],
                 [InlineKeyboardButton(get_translation("red"), f"roulette-red-{amount}"),
                  InlineKeyboardButton(get_translation("black"), f"roulette-black-{amount}")],
                 [InlineKeyboardButton(get_translation("cancel"), f"cancel-{amount}")]]
            ))
        case "blackjack" | "bj":
            result = message.can_play("blackjack")
            if not result[0]:
                return await message.reply(result[1])
            message.remove_from_user_balance(amount)
            message.update_user_value("in_game", True)
            deck = list(BLACKJACK_CARDS.keys()) * 4
            random.shuffle(deck)
            player_hand = [deck.pop(), deck.pop()]
            dealer_hand = [deck.pop(), deck.pop()]
            message.update_user_value("hand", " ".join(player_hand) + "|" + " ".join(dealer_hand))
            await message.reply(
                get_translation("blackjack_player_hand", True).format(", ".join(player_hand),
                                                                      calculate_hand_value(player_hand)) +
                get_translation("blackjack_dealer_hand").format(dealer_hand[0]), reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(get_translation("blackjack_hit"), f"blackjack-hit-{amount}"),
                      InlineKeyboardButton(get_translation("blackjack_stand"), f"blackjack-stand-{amount}")],
                     [InlineKeyboardButton(get_translation("cancel"), f"cancel-{amount}")]]
                ))
        case "slot":
            result = message.can_play("slot")
            if not result[0]:
                return await message.reply(result[1])
            text = get_translation("lost", True).format(amount)
            double_emoji = False
            slot = await client.deletable_dice(chat.id, "🎰", reply_to_message_id=message.id, seconds=15)
            if not slot:
                await message.reply(get_translation("failed_to_start_game", True) +
                                    get_translation("money_refunded"))
                return
            message.remove_from_user_balance(amount)
            value = slot.dice.value
            await asyncio.sleep(2)
            if value in [1, 22, 43, 64]:
                win = True
            elif value in [2, 3, 4, 6, 11, 16, 17, 21, 23, 24, 27, 32, 33, 38, 41, 42, 44, 48, 49, 54, 59, 61, 62, 63]:
                double_emoji = True
            elif value in [5, 9, 13, 18, 26, 30, 35, 39, 47, 52, 56, 60]:
                double_emoji = True
            if double_emoji:
                text = get_translation("slot_money_refunded", True)
                message.add_to_user_balance(amount, False)
            elif win:
                multiplier = {1: 1, 22: 1, 43: 1.5, 64: 2.5}[slot.dice.value]
                new_amount = int(amount * (1 + multiplier))
                _, res = message.add_to_user_balance(new_amount)
                text = get_translation("win", True).format(new_amount, res)
            await slot.deletable_reply(text + get_translation("player_balance").format(message.user_balance), 60)
        case "dice":
            result = message.can_play("dice")
            if not result[0]:
                return await message.reply(result[1])
            message.remove_from_user_balance(amount)
            message.update_user_value("in_game", True)
            buttons = []
            keyboard = [[InlineKeyboardButton(get_translation("even"), f"dice-even-{amount}"),
                         InlineKeyboardButton(get_translation("odd"), f"dice-odd-{amount}")],
                        [InlineKeyboardButton(get_translation("dice_three_and_below"), f"dice-1to3-{amount}"),
                         InlineKeyboardButton(get_translation("dice_four_and_above"), f"dice-4to6-{amount}")]]
            for i in range(1, 7):
                buttons.append(InlineKeyboardButton(str(i), f"dice-{i}-{amount}"))
            keyboard.append(buttons)
            keyboard.append([InlineKeyboardButton(get_translation("cancel"), f"cancel-{amount}")])
            await message.reply(get_translation("choose"), reply_markup=InlineKeyboardMarkup(keyboard))
        case "basketball" | "bb":
            result = message.can_play("basketball")
            if not result[0]:
                return await message.reply(result[1])
            message.remove_from_user_balance(amount)
            message.update_user_value("in_game", True)
            await message.reply(get_translation("choose"), reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(get_translation("basketball_inside_nest"), f"basketball-inside-{amount}"),
                  InlineKeyboardButton(get_translation("basketball_outside_nest"), f"basketball-outside-{amount}")],
                 [InlineKeyboardButton(get_translation("cancel"), f"cancel-{amount}")]]
            ))
        case "football" | "fb":
            result = message.can_play("football")
            if not result[0]:
                return await message.reply(result[1])
            message.remove_from_user_balance(amount)
            message.update_user_value("in_game", True)
            await message.reply(get_translation("choose"), reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(get_translation("football_inside_goal"), f"football-inside-{amount}"),
                  InlineKeyboardButton(get_translation("football_outside_goal"), f"football-outside-{amount}")],
                 [InlineKeyboardButton(get_translation("cancel"), f"cancel-{amount}")]]
            ))
        case "dart":
            result = message.can_play("dart")
            if not result[0]:
                return await message.reply(result[1])
            message.remove_from_user_balance(amount)
            message.update_user_value("in_game", True)
            keyboard = [[InlineKeyboardButton(get_translation("white"), f"dart-white-{amount}"),
                         InlineKeyboardButton(get_translation("center"), f"dart-center-{amount}"),
                         InlineKeyboardButton(get_translation("red"), f"dart-red-{amount}")],
                        [InlineKeyboardButton(get_translation("cancel"), f"cancel-{amount}")]]
            await message.reply(get_translation("choose"), reply_markup=InlineKeyboardMarkup(keyboard))
        case "rps":
            message.remove_from_user_balance(amount)
            message.update_user_value("in_game", True)
            keyboard = [[InlineKeyboardButton(get_translation("rps_rock"), f"rps-rock-{amount}"),
                         InlineKeyboardButton(get_translation("rps_paper"), f"rps-paper-{amount}"),
                         InlineKeyboardButton(get_translation("rps_scissors"), f"rps-scissors-{amount}")],
                        [InlineKeyboardButton(get_translation("cancel"), f"cancel-{amount}")]]
            await message.reply(get_translation("choose"), reply_markup=InlineKeyboardMarkup(keyboard))


@GameBot.on_callback_query(
    filters.regex(r"(cancel|roulette|blackjack|dice|basketball|football|dart|rps)\-(\w+)?-?(\w+)?"))
async def game_callback(client: GameBot, query: CallbackQuery):
    if not query.message:
        return
    chat = query.message.chat
    user = query.from_user

    if query.message.chat.type != enums.ChatType.PRIVATE:
        if not query.message.reply_to_message:
            return
        if not query.message.reply_to_message.from_user.id == user.id:
            return

    if query.matches[0].group(3):
        game, choose, amount = query.matches[0].groups()
    else:
        choose, amount, _ = query.matches[0].groups()
        game = ""
    amount = int(amount)
    win = False
    tie = False

    if choose == "cancel" and bool(query.get_user_value("in_game")):
        text = get_translation("game_canceled")
        query.update_user_value("hand", "")
        query.add_to_user_balance(amount * 0.75, False)
        query.update_user_value("in_game", False)
        await query.edit_message_text(text)
        return

    if not bool(query.get_user_value("in_game")):
        await query.edit_message_reply_markup()
        return
    query.update_user_value("in_game", False)

    match game:
        case "roulette":
            text = get_translation("lost", True).format(amount)
            number = random.randrange(1, 36)

            if number % 2 == 0:
                if choose in ["even", "black"]:
                    win = True
            else:
                if choose in ["odd", "red"]:
                    win = True
            if win:
                new_amount = amount * 2
                _, res = query.add_to_user_balance(new_amount)
                text = get_translation("win", True).format(new_amount, res)
            query.change_user_game_status(win)

            await query.edit_message_text(
                get_translation("roulette", True).format(
                    number, "even, black" if number % 2 == 0 else "odd, red") +
                text + get_translation("player_balance").format(query.user_balance))

        case "blackjack":
            deck = list(BLACKJACK_CARDS.keys()) * 4
            random.shuffle(deck)
            hand = str(query.get_user_value("hand"))
            if len(hand) == 0:
                await query.edit_message_text(get_translation("game_ended"))
                return
            player_hand, dealer_hand = hand.split("|")
            player_hand = player_hand.split()
            dealer_hand = dealer_hand.split()
            for card in player_hand + dealer_hand:
                deck.pop(deck.index(card))
            if choose == "hit":
                player_hand.append(deck.pop())
                text = get_translation("blackjack_player_hand", True).format(
                    ", ".join(player_hand), calculate_hand_value(player_hand))
                if calculate_hand_value(player_hand) > 21:
                    await query.edit_message_text(
                        text + get_translation("blackjack_dealer_hand_full").format(", ".join(dealer_hand),
                                                                                    calculate_hand_value(dealer_hand)) +
                        "\n\n" + get_translation("blackjack_player_busted", True) +
                        get_translation("player_balance").format(query.user_balance))
                    query.change_user_game_status(False)
                    query.update_user_value("hand", "")
                else:
                    query.update_user_value("hand", " ".join(player_hand) + "|" + " ".join(dealer_hand))
                    query.update_user_value("in_game", True)
                    await query.edit_message_text(text +
                                                  get_translation("blackjack_dealer_hand").format(dealer_hand[0]),
                                                  reply_markup=InlineKeyboardMarkup(
                                                      [[InlineKeyboardButton(get_translation("blackjack_hit"),
                                                                             f"blackjack-hit-{amount}"),
                                                        InlineKeyboardButton(get_translation("blackjack_stand"),
                                                                             f"blackjack-stand-{amount}")]]
                                                  ))
            else:
                player_hand_value = calculate_hand_value(player_hand)
                dealer_hand_value = calculate_hand_value(dealer_hand)
                while dealer_hand_value < 17:
                    dealer_hand.append(deck.pop())
                    dealer_hand_value = calculate_hand_value(dealer_hand)
                text = (get_translation("blackjack_player_hand", True).format(", ".join(player_hand),
                                                                              calculate_hand_value(player_hand)) +
                        get_translation("blackjack_dealer_hand_full", True).format(
                            ", ".join(dealer_hand), calculate_hand_value(dealer_hand))) + "\n"
                win_amount = amount * 2.5
                if player_hand_value > 21:
                    text += get_translation("blackjack_player_busted", True)
                elif dealer_hand_value > 21:
                    text += get_translation("blackjack_dealer_busted", True)
                    win = True
                elif player_hand_value > dealer_hand_value:
                    win = True
                elif player_hand_value < dealer_hand_value:
                    text += get_translation("blackjack_dealer_win", True)
                else:
                    tie = True
                if tie:
                    _, res = query.add_to_user_balance(amount, False)
                    text += get_translation("tie", True) + get_translation("money_refunded", True)
                elif win:
                    _, res = query.add_to_user_balance(win_amount)
                    text += get_translation("win", True).format(int(win_amount), res)
                else:
                    text += get_translation("lost", True).format(amount)
                query.change_user_game_status(win, tie)
                query.update_user_value("hand", "")
                await query.edit_message_text(text + get_translation("player_balance").format(query.user_balance))

        case "dice":
            dice = await client.deletable_dice(chat.id, reply_to_message_id=query.message.id, seconds=15)
            if not dice:
                query.add_to_user_balance(amount, False, False)
                await query.edit_message_text(get_translation("failed_to_start_game", True) +
                                              get_translation("money_refunded"))
                return
            await query.edit_message_text(get_translation("wait"))
            value = dice.dice.value
            text = get_translation("dice_value", True).format(value)
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
                new_amount = int(amount * (1 + multiplier))
                _, res = query.add_to_user_balance(new_amount)
                text += get_translation("win", True).format(new_amount, res)
            else:
                text += get_translation("lost", True).format(amount)
            query.change_user_game_status(win)
            await query.edit_message_text(text + get_translation("player_balance").format(query.user_balance))

        case "basketball":
            text = get_translation("lost", True).format(amount)
            basketball = await client.deletable_dice(chat.id, "🏀", reply_to_message_id=query.message.id, seconds=15)
            if not basketball:
                query.add_to_user_balance(amount, False, False)
                await query.edit_message_text(get_translation("failed_to_start_game", True) +
                                              get_translation("money_refunded"))
                return
            value = basketball.dice.value
            await asyncio.sleep(4.5)
            match choose:
                case "inside" if value in [4, 5]:
                    win = True
                case "outside" if value in [1, 2, 3]:
                    win = True
            if win:
                multiplier = 1 if value == 5 else 0.5
                new_amount = int(amount * (1 + multiplier))
                _, res = query.add_to_user_balance(new_amount)
                text = get_translation("win", True).format(new_amount, res)
            query.change_user_game_status(win)
            await query.edit_message_text(text + get_translation("player_balance").format(query.user_balance))

        case "football":
            text = get_translation("lost", True).format(amount)
            football = await client.deletable_dice(chat.id, "⚽", reply_to_message_id=query.message.id, seconds=15)
            if not football:
                query.add_to_user_balance(amount, False, False)
                await query.edit_message_text(get_translation("failed_to_start_game", True) +
                                              get_translation("money_refunded"))
                return
            value = football.dice.value
            await asyncio.sleep(4.5)
            match choose:
                case "inside" if value in [3, 4, 5]:
                    win = True
                case "outside" if value in [1, 2]:
                    win = True
            if win:
                multiplier = 0.5 if value in [4, 3] else 1
                new_amount = int(amount * (1 + multiplier))
                _, res = query.add_to_user_balance(new_amount)
                text = get_translation("win", True).format(new_amount, res)
            query.change_user_game_status(win)
            await query.edit_message_text(text + get_translation("player_balance").format(query.user_balance))

        case "dart":
            dart = await client.deletable_dice(chat.id, "🎯", reply_to_message_id=query.message.id, seconds=15)
            if not dart:
                query.add_to_user_balance(amount, False, False)
                await query.edit_message_text(get_translation("failed_to_start_game", True) +
                                              get_translation("money_refunded"))
                return
            await query.edit_message_text(get_translation("wait"))
            value = dart.dice.value
            text = get_translation("dart_missed", True)
            match value:
                case 2 | 3 | 4 | 5:
                    text = get_translation("dart_normal", True).format(
                        {2: "first", 3: "second", 4: "third", 5: "fourth"}[value],
                        "Red" if value in [2, 4] else "White")
                case 6:
                    text = get_translation("dart_center", True)
            await asyncio.sleep(3)
            match choose:
                case "red" if value in [2, 4]:
                    win = True
                case "white" if value in [3, 5]:
                    win = True
                case "center" if value == 6:
                    win = True
            if win:
                multiplier = 0.5 if choose in ["red", "white"] else 1.5
                new_amount = int(amount * (1 + multiplier))
                _, res = query.add_to_user_balance(new_amount)
                text += get_translation("win", True).format(new_amount, res)
            else:
                text += get_translation("lost", True).format(amount)
                if choose == "red" and value == 6:
                    text += f" ({get_translation('dart_footer')})"
            query.change_user_game_status(win)
            await query.edit_message_text(text + get_translation("player_balance").format(query.user_balance))

        case "rps":
            moves = ["rock", "paper", "scissors"]
            move = random.choice(moves)
            match move:
                case "rock" if choose == "paper":
                    win = True
                case "paper" if choose == "scissors":
                    win = True
                case "scissors" if choose == "rock":
                    win = True
            if move == choose:
                tie = True

            text = get_translation("rps", True).format(choose, move)
            if tie:
                text += get_translation("tie", True) + get_translation("money_refunded", True)
                query.add_to_user_balance(amount, False)
            elif win:
                new_amount = int(amount * 2)
                _, res = query.add_to_user_balance(new_amount)
                text += get_translation("win", True).format(new_amount, res)
            else:
                text += get_translation("lost", True).format(amount)
            query.change_user_game_status(win, tie)
            await query.edit_message_text(text + get_translation("player_balance").format(query.user_balance))

    if not bool(query.get_user_value("in_game")):
        await asyncio.sleep(60)
        await query.message.delete()
