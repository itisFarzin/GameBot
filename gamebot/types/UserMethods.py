import random
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

import gamebot
from pyrogram.types import User

from gamebot.database import Config, UserDatabase, AdminDatabase

get_translation = Config.get_translation


class UserMethods:
    def __init__(self, client: "gamebot.GameBot", from_user: User):
        self._client = client
        self.from_user = from_user

    def insert_user(self, client: bool = False):
        user = self._client.me if client else self.from_user

        with Session(Config.engine) as session:
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

    def update_user_value(self, key: str, value: Any, client: bool = False):
        user = self._client.me if client else self.from_user
        self.insert_user(client)
        with Session(Config.engine) as session:
            session.execute(
                update(UserDatabase)
                .where(UserDatabase.id == user.id)
                .values({key: value})
            )
            session.commit()

    def get_user_values(self, keys: str | list[str], client: bool = False):
        if isinstance(keys, str):
            keys = [keys]
        user = self._client.me if client else self.from_user
        self.insert_user()
        with Session(Config.engine) as session:
            result = session.execute(
                select(UserDatabase)
                .where(UserDatabase.id == user.id)
            ).fetchone()
            if result:
                return [getattr(result[0], key) for key in keys]
        return []

    def get_user_value(self, key: str, client: bool = False):
        return self.get_user_values(key, client)[0]

    def has_enough_money(self, amount: int | float):
        return self.user_balance >= amount

    def add_to_user_balance(self, amount: int | float, tax: bool = Config.TAX, should_pay_loan: bool = True):
        text = ""
        loan = int(self.get_user_value("loan"))
        new_value = amount

        if tax:
            text = f"({get_translation('fee')})"
            self.insert_user(True)
            self.update_user_value("balance", self.get_user_value("balance", True) + amount * 0.05, True)
            new_value = amount * 0.95

        self.update_user_value("balance", self.user_balance + new_value)

        if should_pay_loan and loan != 0:
            pay_amount = new_value // 10
            if pay_amount > loan:
                pay_amount = loan
            _, res, status = self.pay_loan(pay_amount)
            if status:
                text += "\n\n" + res
                new_value -= pay_amount

        return int(new_value), text

    def remove_from_user_balance(self, amount: int | float):
        if not self.has_enough_money(amount):
            return False
        self.update_user_value("balance", self.user_balance - amount)
        return True

    def pay_loan(self, amount: int | float, new_line: bool = False):
        loan = int(self.get_user_value("loan"))

        if not self.has_enough_money(amount):
            return loan, get_translation("dont_have_money_to_pay_debt") + "\n", False

        if amount > loan:
            amount = loan
        amount = int(amount)

        loan_left = loan - amount if not amount == loan else 0
        self.update_user_value("loan", loan_left)
        self.remove_from_user_balance(amount)
        if not loan_left == 0:
            return loan_left, get_translation("paid_x_of_debt", new_line).format(amount, int(loan_left)), True
        return loan_left, get_translation("paid_full_debt", new_line).format(loan), True

    def change_user_game_status(self, win: bool, tie: bool = False):
        res = int(self.get_user_value("wins" if win else "losses"))
        self.update_user_value("wins" if win else "losses", res + 1)

        if tie:
            self.update_user_value("win_streaks", 0)
            self.update_user_value("loss_streaks", 0)
            return

        if win:
            highest_win_streaks = int(self.get_user_value("highest_win_streaks"))
            win_streaks = int(self.get_user_value("win_streaks"))
            self.update_user_value("win_streaks", win_streaks + 1)
            self.update_user_value("loss_streaks", 0)
            if win_streaks >= highest_win_streaks:
                self.update_user_value("highest_win_streaks", win_streaks)
            self.update_user_value("trophies", self.trophies + random.randrange(10, 15))
        else:
            highest_loss_streaks = int(self.get_user_value("highest_loss_streaks"))
            loss_streaks = int(self.get_user_value("loss_streaks"))
            self.update_user_value("loss_streaks", loss_streaks + 1)
            self.update_user_value("win_streaks", 0)
            if loss_streaks >= highest_loss_streaks:
                self.update_user_value("highest_loss_streaks", loss_streaks)
            self.update_user_value("trophies", self.trophies - random.randrange(5, 10))
        self.on_trophies_change()

    def can_play(self, game: str):
        if self.league.name not in Config.NEW_PLAYER:
            if game in Config.EASY_GAMES:
                return False, (get_translation("cant_play_game")
                               .format(", ".join(Config.NEW_PLAYER)))
        return True, ""

    def on_trophies_change(self):
        for league in reversed(Config.LEAGUES):
            if self.trophies > league.trophies and self.get_user_value("league") != league.name:
                self.update_user_value("league", league.name)
                break

    @property
    def user_balance(self):
        return int(self.get_user_value("balance"))

    @property
    def trophies(self):
        return int(self.get_user_value("trophies"))

    @property
    def league(self):
        user_league = self.get_user_value("league")
        return next(filter(
            lambda league: league.name == user_league, Config.LEAGUES), Config.LEAGUES[0])

    @property
    def user_is_owner(self):
        if not self.from_user:
            return False
        return self.from_user.id == Config.OWNER_ID

    @property
    def user_is_admin(self):
        if not self.from_user:
            return False
        if self.user_is_owner:
            return True
        with Session(Config.engine) as session:
            return bool(session.execute(
                select(AdminDatabase)
                .where(AdminDatabase.id == self.from_user.id)
            ).one_or_none())
