import datetime
import os

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserDatabase(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(40))
    balance: Mapped[int] = mapped_column(BigInteger, default=int(os.getenv("START_MONEY", 10000)))
    wins: Mapped[int] = mapped_column(default=0)
    win_streaks: Mapped[int] = mapped_column(default=0)
    highest_win_streaks: Mapped[int] = mapped_column(default=0)
    losses: Mapped[int] = mapped_column(default=0)
    loss_streaks: Mapped[int] = mapped_column(default=0)
    highest_loss_streaks: Mapped[int] = mapped_column(default=0)
    loan: Mapped[int] = mapped_column(default=0)
    last_claim: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.min)
    claim_streak: Mapped[int] = mapped_column(default=0)
    trophies: Mapped[int] = mapped_column(default=0)
    hand: Mapped[str] = mapped_column(String(50), default="")
    in_game: Mapped[bool] = mapped_column(default=False)


class AdminDatabase(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40))

