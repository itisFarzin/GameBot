import random

from betbot import BetBot, filters
from betbot.types import Message
from betbot.database import Config
from datetime import datetime, timezone, timedelta


@BetBot.on_message(filters.command(Config.USER_COMMANDS))
async def user_commands(_: BetBot, message: Message):
    action = message.command[0]
    amount = message.amount

    match action:
        case "info":
            _message = message.reply_to_message if message.reply_to_message else message
            (name, balance, wins, losses, loan,
             claim_streak, highest_win_streaks, highest_loss_streaks,
             trophies, league) = _message.get_user_values(["name", "balance", "wins", "losses", "loan",
                                                   "claim_streak", "highest_win_streaks", "highest_loss_streaks",
                                                   "trophies", "league"])
            await message.reply(
                f"Name: {name}\nBalance: ${int(balance):,}\nWins: {wins}\nLosses: {losses}" +
                f"\nLoan: ${loan:,}\nClaim Streak: {claim_streak}" +
                f"\nHighest Win Streaks: {highest_win_streaks}\nHighest Loss Streaks: {highest_loss_streaks}"
                f"\nTrophies: {trophies}\nLeague: {league}")
        case "balance":
            _message = message.reply_to_message if message.reply_to_message else message
            await message.reply(f"Balance: ${_message.user_balance:,}")
        case "gift":
            if not message.reply_to_message:
                await message.reply("You should reply to user that you want to gift your money.")
                return
            if amount is None:
                await message.reply("/gift [amount]")
                return
            if amount == 0:
                await message.reply("The amount can't be zero.")
                return
            if not message.has_enough_money(amount):
                await message.reply("You dont have this amount of money.")
                return
            message.remove_from_user_balance(amount)
            amount, text = message.reply_to_message.add_to_user_balance(amount, should_pay_loan=False)
            await message.reply(f"You gifted {message.reply_to_message.from_user.first_name} ${amount:,}{text}")

        case "loan":
            if amount is None:
                amount = Config.LOAN_LIMIT
            if amount == 0:
                await message.reply("Loan amount can't be zero.")
                return
            if amount > Config.LOAN_LIMIT:
                await message.reply(f"Loan amount can't exceed ${Config.LOAN_LIMIT:,}")
                return
            loan = int(message.get_user_value("loan"))
            if loan != 0:
                await message.reply("You have loan to repay.\nUse /repay to pay it now.")
                return
            message.update_user_value("loan", amount)
            message.add_to_user_balance(amount, False, False)
            await message.reply(f"You have been granted a loan of ${amount:,}\nIt has been added to your balance."
                                f"\nYour current balance: ${message.user_balance:,}")
        case "repay":
            loan = int(message.get_user_value("loan"))
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
            loan_info = message.pay_loan(amount)[1]
            await message.reply(
                loan_info + f"\nYour current balance: ${message.user_balance:,}")
        case "daily":
            today = datetime.now(timezone.utc).date()
            last_claim, streak = message.get_user_values(["last_claim", "claim_streak"])
            if not last_claim:
                streak = 1
            else:
                last_claim_date = last_claim.date()
                if last_claim_date == today:
                    await message.reply("You've already claimed your daily reward today.")
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

            await message.reply(f"You've received ${reward:,} as your daily reward! {text}" +
                                f"\nYour current streak is {streak} days."
                                f"\nYour new balance is ${message.user_balance:,}")
