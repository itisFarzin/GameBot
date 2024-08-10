from pyrogram import enums
from betbot import BetBot, filters, types
from betbot.database import Config, AdminDatabase, UserDatabase
from sqlalchemy.orm import Session
from sqlalchemy import select, delete, update
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message as PyroMessage

get_translation = Config.get_translation


@BetBot.on_message(filters.command(Config.SUDO_COMMANDS) & filters.is_owner)
async def sudo_commands(_: BetBot, message: types.Message):
    action = message.command[0]

    match action:
        case "addadmin":
            if not message.reply_to_message:
                await message.reply(get_translation("reply"))
                return
            user = message.reply_to_message.from_user

            with Session(Config.engine) as session:
                result = session.execute(select(AdminDatabase).where(AdminDatabase.id == user.id)).one_or_none()
                if result is None:
                    session.add(
                        AdminDatabase(
                            id=user.id,
                            name=user.first_name
                        )
                    )
                    session.commit()
                    await message.reply(get_translation("add_admin").format(user.first_name))
                    return
                await message.reply(get_translation("already_is_admin").format(user.first_name))
        case "rmadmin":
            if not message.reply_to_message:
                await message.reply(get_translation("reply"))
                return
            user = message.reply_to_message.from_user

            with Session(Config.engine) as session:
                result = session.execute(select(AdminDatabase).where(AdminDatabase.id == user.id)).one_or_none()
                if result:
                    session.execute(delete(AdminDatabase).where(AdminDatabase.id == user.id))
                    session.commit()
                    await message.reply(get_translation("remove_admin").format(user.first_name))
                    return
            await message.reply(get_translation("is_not_admin").format(user.first_name))
        case "admins":
            text = [get_translation("admins") + ":"]
            with Session(Config.engine) as session:
                result = session.execute(select(AdminDatabase.name)).all()
                if result:
                    for i, admin in enumerate(result, start=1):
                        text.append(f"{i}: **{admin[0]}**")
                else:
                    text.append("Theres no admin")
                await message.reply("\n".join(text))


@BetBot.on_message(filters.command(Config.ADMIN_COMMANDS) & filters.is_admin)
async def admin_commands(_: BetBot, message: types.Message):
    action = message.command[0]
    amount = message.amount

    if amount and amount == 0:
        await message.reply(get_translation("no_zero_amount"))
        return

    match action:
        case "user":
            user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
            await message.reply(get_translation("user_panel").format(user.first_name), reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(get_translation("set_balance"), f"setbalance-{user.id}"),
                      InlineKeyboardButton(get_translation("add_balance"), f"addbalance-{user.id}"),
                      InlineKeyboardButton(get_translation("remove_balance"), f"removebalance-{user.id}")],
                    [InlineKeyboardButton(get_translation("reset_data"), f"reset-{user.id}")]]
                ))


@BetBot.on_callback_query(filters.regex(r"(setbalance|addbalance|removebalance|reset)-(\d+)") & filters.is_admin)
async def admin_callback(client: BetBot, query: CallbackQuery):
    if not query.message:
        return
    user = query.from_user

    if query.message.chat.type != enums.ChatType.PRIVATE:
        if not query.message.reply_to_message:
            return
        if not query.message.reply_to_message.from_user.id == user.id:
            return

    action, user_id = query.matches[0].groups()

    with Session(Config.engine) as session:
        _user = await client.get_users(user_id)
        if action in ["setbalance", "addbalance", "removebalance"]:
            sent_message: types.Message = await client.ask(query.message.chat.id, get_translation("enter_amount"), timeout=20,
                                                        user_id=user.id)
            amount = sent_message.amount

            if amount is None:
                await query.edit_message_text(get_translation("enter_valid_number"))
                return
            if amount == 0:
                await query.edit_message_text(get_translation("no_zero_amount"))
                return

            balance = int(session.execute(
                select(UserDatabase.balance)
                .where(UserDatabase.id == user_id)
                .select()
            ).fetchone()[0])

            text = "impossible"
            if action == "setbalance":
                session.execute(
                    update(UserDatabase)
                    .where(UserDatabase.id == user_id)
                    .values({"balance": amount})
                )
                text = get_translation("set_user_balance").format(_user.first_name, amount)
            elif action == "addbalance":
                session.execute(
                    update(UserDatabase)
                    .where(UserDatabase.id == user_id)
                    .values({"balance": balance + amount})
                )
                text = get_translation("add_to_user_balance").format(amount, _user.first_name)
            elif action == "removebalance":
                session.execute(
                    update(UserDatabase)
                    .where(UserDatabase.id == user_id)
                    .values({"balance": balance - amount})
                )
                text = get_translation("remove_from_user_balance").format(amount, _user.first_name)
            if isinstance(sent_message.sent_message, (types.Message, PyroMessage)):
                await sent_message.sent_message.delete()
            await query.edit_message_text(text)
        else:
            result = session.execute(
                select(UserDatabase).where(UserDatabase.id == user_id)
            ).one_or_none()
            if result:
                session.execute(delete(UserDatabase).where(UserDatabase.id == user_id))
                await query.edit_message_text(get_translation("remove_user_data").format(_user.first_name))
            else:
                await query.edit_message_text(get_translation("failed_to_remove_user_data").format(_user.first_name))
        session.commit()
