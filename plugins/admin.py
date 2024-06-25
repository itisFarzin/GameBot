from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from betbot import BetBot, filters, types
from betbot.database import AdminDatabase, UserDatabase


def fix_id(chat_id: int):
    return int(str(chat_id).replace("-", ""))


@BetBot.on_message(filters.command(BetBot.SUDO_COMMANDS) & filters.is_owner)
async def sudo_commands(client: BetBot, message: types.Message):
    action = message.command[0]

    match action:
        case "addadmin":
            if not message.reply_to_message:
                await message.reply("You should reply to the user that you want to add as an admin.")
                return
            user = message.reply_to_message.from_user

            with Session(client.engine) as session:
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

            with Session(client.engine) as session:
                result = session.execute(select(AdminDatabase).where(AdminDatabase.id == user.id)).one_or_none()
                if result:
                    session.execute(delete(AdminDatabase).where(AdminDatabase.id == user.id))
                    session.commit()
                    await message.reply(f"Successfully removed {user.first_name} from admin list")
                    return
            await message.reply(f"{user.first_name} is not an admin.")
        case "admins":
            text = "Admins:\n"
            with Session(client.engine) as session:
                result = session.execute(select(AdminDatabase)).all()
                for i, admin in enumerate(result, start=1):
                    text += f"{i}: {admin[0].name}\n"
                await message.reply(text)


@BetBot.on_message(filters.command(BetBot.ADMIN_COMMANDS) & filters.is_admin)
async def admin_commands(client: BetBot, message: types.Message):
    action = message.command[0]
    amount = message.amount

    if amount and amount == 0:
        await message.reply("The amount can't be zero.")
        return

    match action:
        case "reset":
            if not message.reply_to_message:
                await message.reply("You should reply to user that you want to delete their data.")
                return
            user = message.reply_to_message.from_user
            with Session(client.engine) as session:
                result = session.execute(
                    select(UserDatabase).where(UserDatabase.id == user.id)
                ).one_or_none()
                if result:
                    session.execute(delete(UserDatabase).where(UserDatabase.id == user.id))
                    session.commit()
                    await message.reply(f"Removed {user.first_name} data successfully.")
                else:
                    await message.reply(f"Failed to delete {user.first_name} data.")
        case "setbalance":
            if amount is None:
                await message.reply("/setbalance [amount]")
                return
            that_message = message.reply_to_message if message.reply_to_message else message
            that_message.update_user_value("balance", amount)
            await message.reply(f"Set {that_message.from_user.first_name} balance to ${amount:,}")
        case "addbalance" | "rmbalance":
            if amount is None:
                await message.reply(f"/{action} [amount]")
                return
            that_message = message.reply_to_message if message.reply_to_message else message
            that_user = that_message.from_user
            if action == "addbalance":
                that_message.add_to_user_balance(amount, False)
                text = f"Added ${amount:,} to {that_user.first_name}."
            else:
                that_message.remove_from_user_balance(amount)
                text = f"Removed ${amount:,} from {that_user.first_name}."
            await message.reply(text + f"\nNew balance: ${that_message.user_balance:,}")
