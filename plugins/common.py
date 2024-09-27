from pyrogram import enums
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from gamebot import GameBot, filters
from gamebot.database import Config, UserDatabase
from gamebot.types import Message
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

get_translation = Config.get_translation


@GameBot.on_message(filters.command(Config.COMMON_COMMANDS))
async def common_commands(_: GameBot, message: Message):
    action = message.command[0]

    match action:
        case "start":
            await message.reply(get_translation("start"))
        case "help":
            await message.reply(get_translation("help", True).format(Config.LOAN_LIMIT) +
                                (get_translation("admin_help", True) if message.user_is_admin else "") +
                                (get_translation("owner_help", True) if message.user_is_owner else "") +
                                get_translation("help_footer"))
        case "leaderboard" | "lb":
            text = f"{get_translation('leaderboard')} ({get_translation('trophies')}):\n"
            with Session(Config.engine) as session:
                results = session.execute(
                    select(UserDatabase)
                    .order_by(UserDatabase.trophies.desc())
                    .limit(10)
                ).all()
                for i, result in enumerate(results, start=1):
                    result = result[0]
                    text += f"{i}. **{result.name}**: {result.trophies:,}\n"
                await message.reply(text, reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("•" + get_translation("trophies"),
                                           "leaderboard-trophies")],
                     [InlineKeyboardButton("◦" + get_translation("balance"),
                                           "leaderboard-balance"),
                      InlineKeyboardButton("◦" + get_translation("wins"),
                                           "leaderboard-wins"),
                      InlineKeyboardButton("◦" + get_translation("losses"),
                                           "leaderboard-losses")],
                     [InlineKeyboardButton("◦" + get_translation("highest_win_streaks"),
                                           "leaderboard-highest_win_streaks"),
                      InlineKeyboardButton("◦" + get_translation("highest_loss_streaks"),
                                           "leaderboard-highest_loss_streaks")]]
                ))


@GameBot.on_callback_query(filters.regex(r"leaderboard-(\w+)"))
async def common_callback(_: GameBot, query: CallbackQuery):
    if not query.message:
        return
    user = query.from_user
    lb_type = str(query.matches[0].group(1)).lower()

    if query.message.chat.type != enums.ChatType.PRIVATE:
        if not query.message.reply_to_message:
            return
        if not query.message.reply_to_message.from_user.id == user.id:
            return

    text = f"{get_translation('leaderboard')} ({get_translation(lb_type.lower())}):\n"
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
            data = f"{int(getattr(result, lb_type)):,}"
            text += f"{i}. **{result.name}**: {data}\n"
        buttons = []
        for key in column_mapping.keys():
            buttons.append(InlineKeyboardButton(("• " if key == lb_type else "◦ ") +
                                                get_translation(key.lower()), f"leaderboard-{key}"))
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(
            [buttons[0:1]] + [buttons[1:4]] + [buttons[4:6]]
        ))
