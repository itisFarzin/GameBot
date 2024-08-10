import random
from betbot import BetBot, filters
from betbot.types import Message
from betbot.database import Config
from datetime import datetime, timezone, timedelta

get_translation = Config.get_translation


@BetBot.on_message(filters.command(Config.USER_COMMANDS))
async def user_commands(_: BetBot, message: Message):
    action = message.command[0]
    amount = message.amount

    match action:
        case "info":
            _message = message.reply_to_message if message.reply_to_message else message
            info = _message.get_user_values(["name", "balance", "wins", "losses", "loan",
                                                   "claim_streak", "highest_win_streaks", "highest_loss_streaks",
                                                   "trophies", "league"])
            await message.reply(get_translation("user_info").format(*info))
        case "balance":
            _message = message.reply_to_message if message.reply_to_message else message
            await message.reply(get_translation("user_balance").format(_message.user_balance))
        case "gift":
            if not message.reply_to_message:
                await message.reply(get_translation("reply"))
                return
            if amount is None:
                await message.reply(get_translation("common_use").format("gift"))
                return
            if amount == 0:
                await message.reply(get_translation("no_zero_amount"))
                return
            if not message.has_enough_money(amount):
                await message.reply(get_translation("dont_have_money"))
                return
            message.remove_from_user_balance(amount)
            amount, text = message.reply_to_message.add_to_user_balance(amount, should_pay_loan=False)
            await message.reply(get_translation("gift")
                                .format(message.reply_to_message.from_user.first_name, amount, text))

        case "loan":
            if amount is None:
                amount = Config.LOAN_LIMIT
            if amount == 0:
                await message.reply(get_translation("no_zero_loan"))
                return
            if amount > Config.LOAN_LIMIT:
                await message.reply(get_translation("loan_limit").format(Config.LOAN_LIMIT))
                return
            loan = int(message.get_user_value("loan"))
            if loan != 0:
                await message.reply(get_translation("have_debt"))
                return
            message.update_user_value("loan", amount)
            message.add_to_user_balance(amount, False, False)
            await message.reply(get_translation("granted_loan").format("amount") +
                                "\n" + get_translation("user_balance").format(message.user_balance))
        case "repay":
            loan = int(message.get_user_value("loan"))
            if loan == 0:
                await message.reply(get_translation("dont_have_debt"))
                return
            if amount is None:
                amount = loan
            if amount == 0:
                await message.reply(get_translation("no_zero_amount"))
                return
            if amount > loan:
                amount = loan
            loan_info = message.pay_loan(amount)[1]
            await message.reply(loan_info +
                                "\n" + get_translation("user_balance").format(message.user_balance))
        case "daily":
            today = datetime.now(timezone.utc).date()
            last_claim, streak = message.get_user_values(["last_claim", "claim_streak"])
            if not last_claim:
                streak = 1
            else:
                last_claim_date = last_claim.date()
                if last_claim_date == today:
                    await message.reply(get_translation("already_claimed_daily"))
                    return

                if last_claim_date == today - timedelta(days=1):
                    streak += 1

                    if streak == 15:
                        streak = 1
                else:
                    streak = 1

            reward = random.randrange(100 * streak, 250 * streak)

            reward *= 1 + (message.league.bonus // 100)
            reward, text = message.add_to_user_balance(reward, False)
            message.update_user_value("last_claim", today)
            message.update_user_value("claim_streak", streak)

            await message.reply(get_translation("daily_reward").format(reward, text, streak) +
                                "\n" + get_translation("user_balance").format(message.user_balance))
