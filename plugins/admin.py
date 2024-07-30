from pyrogram import enums
from betbot import BetBot, filters, types
from betbot.database import Config, AdminDatabase, UserDatabase
from sqlalchemy.orm import Session
from sqlalchemy import select, delete, update
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message as PyroMessage


@BetBot.on_message(filters.command(Config.SUDO_COMMANDS) & filters.is_owner)
async def sudo_commands(_: BetBot, message: types.Message):
    action = message.command[0]

    match action:
        case "addadmin":
            if not message.reply_to_message:
                await message.reply("You should reply to the user that you want to add as an admin.")
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
                    await message.reply(f"Successfully added {user.first_name} as an admin")
                    return
                await message.reply(f"{user.first_name} is already an admin.")
        case "rmadmin":
            if not message.reply_to_message:
                await message.reply("You should reply to the user that you want to add as an admin.")
                return
            user = message.reply_to_message.from_user

            with Session(Config.engine) as session:
                result = session.execute(select(AdminDatabase).where(AdminDatabase.id == user.id)).one_or_none()
                if result:
                    session.execute(delete(AdminDatabase).where(AdminDatabase.id == user.id))
                    session.commit()
                    await message.reply(f"Successfully removed {user.first_name} from admin list")
                    return
            await message.reply(f"{user.first_name} is not an admin.")
        case "admins":
            text = "Admins:\n"
            with Session(Config.engine) as session:
                result = session.execute(select(AdminDatabase)).all()
                for i, admin in enumerate(result, start=1):
                    text += f"{i}: {admin[0].name}\n"
                await message.reply(text)


@BetBot.on_message(filters.command(Config.ADMIN_COMMANDS) & filters.is_admin)
async def admin_commands(_: BetBot, message: types.Message):
    action = message.command[0]
    amount = message.amount

    if amount and amount == 0:
        await message.reply("The amount can't be zero.")
        return

    match action:
        case "user":
            user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
            await message.reply(f"Panel for user {user.first_name}", reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("Set balance", f"setbalance-{user.id}"),
                      InlineKeyboardButton("Add balance", f"addbalance-{user.id}"),
                      InlineKeyboardButton("Remove balance", f"removebalance-{user.id}")],
                    [InlineKeyboardButton("Reset user data", f"reset-{user.id}")]]
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
            sent_message: types.Message = await client.ask(query.message.chat.id, "Enter the amount", timeout=20,
                                                        user_id=user.id)
            amount = sent_message.amount

            if amount is None:
                await query.edit_message_text("Enter a valid number")
                return
            if amount == 0:
                await query.edit_message_text("The amount can't be zero.")
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
                text = f"Set {_user.first_name} balance to ${amount:,}"
            elif action == "addbalance":
                session.execute(
                    update(UserDatabase)
                    .where(UserDatabase.id == user_id)
                    .values({"balance": balance + amount})
                )
                text = f"Added ${amount:,} to {_user.first_name}."
            elif action == "removebalance":
                session.execute(
                    update(UserDatabase)
                    .where(UserDatabase.id == user_id)
                    .values({"balance": balance - amount})
                )
                text = f"Removed ${amount:,} from {_user.first_name}."
            if isinstance(sent_message.sent_message, (types.Message, PyroMessage)):
                await sent_message.sent_message.delete()
            await query.edit_message_text(text)
        else:
            result = session.execute(
                select(UserDatabase).where(UserDatabase.id == user_id)
            ).one_or_none()
            if result:
                session.execute(delete(UserDatabase).where(UserDatabase.id == user_id))
                await query.edit_message_text(f"Removed {_user.first_name} data successfully.")
            else:
                await query.edit_message_text(f"Failed to delete {_user.first_name} data.")
        session.commit()
