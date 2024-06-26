import random

from sqlalchemy import select, update
from sqlalchemy.orm import Session

import betbot
from betbot import types
from pyrogram.types import User

from betbot.database import UserDatabase, AdminDatabase


class UserMethods:
    def __init__(self, client: "betbot.BetBot" = None, from_user: User = None):
        self._client = client
        self.from_user = from_user

    def fix_id(self):
        if isinstance(self, types.CallbackQuery):
            chat_id = self.message.chat.id
        elif isinstance(self, types.Message):
            chat_id = self.chat.id
        else:
            return
        return int(str(chat_id).replace("-", ""))

    def insert_user(self, client: int = False):
        user = self._client.me if client else self.from_user

        with Session(self._client.engine) as session:
            if session.execute(
                    select(UserDatabase).where(UserDatabase.id == user.id)
            ).first() is None:
                session.add(
                    UserDatabase(
                        id=user.id,
                        name=user.first_name
                    )
                )
                session.commit()

    def update_user_value(self, key: str, value: object, client: int = False):
        user = self._client.me if client else self.from_user
        self.insert_user(client)
        with Session(self._client.engine) as session:
            session.execute(
                update(UserDatabase)
                .where(UserDatabase.id == user.id)
                .values({key: value})
            )
            session.commit()

    def get_user_values(self, keys: str | list[str], client: int = False):
        if isinstance(keys, str):
            keys = [keys]
        user = self._client.me if client else self.from_user
        self.insert_user()
        with Session(self._client.engine) as session:
            result = session.execute(
                select(UserDatabase)
                .where(UserDatabase.id == user.id)
            ).fetchone()[0]
            return [getattr(result, key) for key in keys]

    def get_user_value(self, key: str, client: int = False):
        return self.get_user_values(key, client)[0]

    def has_enough_money(self, amount: int):
        return self.user_balance >= amount

    def add_to_user_balance(self, amount: int | float, tax: bool = None, should_pay_loan: bool = True):
        text = ""
        loan = self.get_user_value("loan")

        if tax is None:
            tax = self._client.TAX
        if tax:
            text = " (You paid 5% in taxes)"
            self.insert_user(True)
            self.update_user_value("balance", self.get_user_value("balance", True) + amount * 0.05, True)
        new_value = amount * 0.95 if tax else amount

        self.update_user_value("balance", self.user_balance + new_value)

        if not loan == 0 and should_pay_loan:
            pay_amount = new_value // 10
            if pay_amount > loan:
                pay_amount = loan
            loan_left, res, status = self.pay_loan(pay_amount)
            if status:
                text += "\n\n" + res
                new_value -= pay_amount

        return int(new_value), text

    def remove_from_user_balance(self, amount: int):
        if not self.has_enough_money(amount):
            return False
        self.update_user_value("balance", self.user_balance - amount)
        return True

    def pay_loan(self, amount: int):
        loan = self.get_user_value("loan")

        if not self.has_enough_money(amount):
            return loan, "You dont have the money to pay the loan.", False

        if amount > loan:
            amount = loan

        loan_left = loan - amount if not amount == loan else 0
        self.update_user_value("loan", loan_left)
        self.remove_from_user_balance(amount)
        if not loan_left == 0:
            return loan_left, f"You paid ${int(amount):,} of the loan.\nYou have ${int(loan_left):,} left to pay.", True
        return loan_left, f"You paid the ${loan:,} loan.", True

    def change_user_game_status(self, win: bool):
        res = self.get_user_value("wins" if win else "losses")
        self.update_user_value("wins" if win else "losses", res + 1)
        trophies = self.get_user_value("trophies")

        if win:
            res = self.get_user_value("highest_win_streaks")
            res2 = self.get_user_value("win_streaks")
            if res2 >= res:
                self.update_user_value("highest_win_streaks", res2)
            trophies += random.randrange(10, 15)
            self.update_user_value("trophies", trophies + random.randrange(10, 15))
        else:
            res = self.get_user_value("highest_loss_streaks")
            res2 = self.get_user_value("loss_streaks")
            if res2 >= res:
                self.update_user_value("highest_loss_streaks", res2)
            self.update_user_value("trophies", trophies - random.randrange(5, 10))
        self.on_trophies_change()

        res = self.get_user_value("win_streaks" if win else "loss_streaks")
        self.update_user_value("win_streaks" if win else "loss_streaks", res + 1)
        self.update_user_value("win_streaks" if not win else "loss_streaks", 0)

    @property
    def user_balance(self):
        return int(self.get_user_value("balance"))

    @property
    def user_is_owner(self):
        if not self.from_user:
            return False
        return self.from_user.id == self._client.OWNER_ID

    @property
    def user_is_admin(self):
        if not self.from_user:
            return False
        if self.user_is_owner:
            return True
        with Session(self._client.engine) as session:
            return bool(session.execute(select(AdminDatabase).where(AdminDatabase.id == self.from_user.id))
                        .one_or_none())

    def on_trophies_change(self):
        pass
