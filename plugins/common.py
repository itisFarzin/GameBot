from pyrogram import enums
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from betbot import BetBot, filters
from betbot.database import Config, UserDatabase
from betbot.types import Message
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery


@BetBot.on_message(filters.command(Config.COMMON_COMMANDS))
async def common_commands(_: BetBot, message: Message):
    action = message.command[0]

    match action:
        case "start":
            await message.reply("""
Hi, welcome to bet bot
if you want to play games, use /help to see what games we have and how to play them in your group
""")
        case "help":
            await message.reply(f"""
**Game Commands**:
/roulette ║ /rl [amount] | play roulette
/blackjack ║ /bj [amount] | play blackjack
/slot [amount] | play slot machine
/dice [amount] | play dice
/basketball ║ /bb [amount] | play basketball
/football ║ /fb [amount] | play football
/dart [amount] | play dart

**Common Commands**:
/info | Shows information of a user
/balance | Shows the balance of a user
/gift [amount] * | gift some money to a user
/leaderboard ║ /lb | Shows the leaderboard of the group
/loan [amount] | maximum loan is ${Config.LOAN_LIMIT:,}
/repay [amount] | repay your loan
/daily | check back everyday to get some cash

""" + ("""
**Admin Only Commands**:
/setbalance [amount] * | set the balance of a user
/addbalance [amount] * | add some money to a user's balance
/rmbalance [amount] * | remove some money from a user's balance
/reset * | reset users data

""" if message.user_is_admin else "") + "* must reply to a user")
        case "leaderboard" | "lb" if message.chat.type in {enums.ChatType.GROUP, enums.ChatType.SUPERGROUP}:
            text = "Leaderboard (Trophies):\n"
            with Session(Config.engine) as session:
                results = session.execute(
                    select(UserDatabase)
                    .order_by(UserDatabase.trophies.desc())
                    .limit(10)
                ).all()
                for i, result in enumerate(results, start=1):
                    result = result[0]
                    text += f"{i}. {result.name}: {round(result.trophies):,}\n"
                await message.reply(text, reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("• Trophies", "leaderboard-trophies")],
                     [InlineKeyboardButton("◦ Balance", "leaderboard-balance"),
                      InlineKeyboardButton("◦ Wins", "leaderboard-wins"),
                      InlineKeyboardButton("◦ Losses", "leaderboard-losses")],
                     [InlineKeyboardButton("◦ Highest Win Streaks", "leaderboard-highest_win_streaks"),
                      InlineKeyboardButton("◦ Highest Loss Streaks", "leaderboard-highest_loss_streaks")]]
                ))


@BetBot.on_callback_query(filters.regex(r"leaderboard-(\w+)"))
async def common_callback(_: BetBot, query: CallbackQuery):
    if not query.message:
        return
    user = query.from_user
    lb_type = str(query.matches[0].group(1)).lower()

    if not query.message.reply_to_message:
        return
    if not query.message.reply_to_message.from_user.id == user.id:
        return

    text = f"Leaderboard ({lb_type.replace('_', ' ').title()}):\n"
    column_mapping = {
        "trophies": UserDatabase.trophies,
        "balance": UserDatabase.balance,
        "wins": UserDatabase.wins,
        "losses": UserDatabase.losses,
        "highest_win_streaks": UserDatabase.highest_win_streaks,
        "highest_loss_streaks": UserDatabase.highest_loss_streaks,
    }
    with Session(Config.engine) as session:
        results = session.execute(
            select(UserDatabase)
            .order_by(desc(column_mapping.get(lb_type, UserDatabase.trophies)))
            .limit(10)
        ).all()
        for i, result in enumerate(results, start=1):
            result = result[0]
            if lb_type == "balance":
                data = f"${int(result.balance):,}"
            else:
                data = f"{int(getattr(result, lb_type)):,}"
            text += f"{i}. {result.name}: {data}\n"
        buttons = []
        for key in column_mapping.keys():
            buttons.append(InlineKeyboardButton(f"{'•' if key == lb_type else '◦'} {key.replace('_', ' ').title()}",
                                                f"leaderboard-{key}"))
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(
            [buttons[0:1]] + [buttons[1:4]] + [buttons[4:6]]
        ))
