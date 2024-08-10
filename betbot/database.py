import os
import yaml
import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

load_dotenv()


class League:
    name: str
    bonus: int
    trophies: int

    def __init__(self, name: str, bonus: int, trophies: int) -> None:
        self.name = name
        self.bonus = bonus
        self.trophies = trophies


class Language:
    name: str
    language: dict

    def __init__(self, name: str):
        self.name = name
        self.load()

    def get_translation(self, key: str) -> str:
        return self.language.get(key, "Missing translation")

    def load(self):
        path = f"languages/{self.name}.yml"
        if os.path.exists(path):
            with open(path, "r") as file:
                self.language = yaml.load(file, Loader=yaml.SafeLoader)
        else:
            raise Exception(f"There is no language file for {self.name}")


class Config:
    engine = create_engine(os.getenv("DB_URI", "sqlite:///database.db"))

    OWNER_ID = int(os.getenv("OWNER_ID", 0))
    LOAN_LIMIT = int(os.getenv("LOAN_LIMIT", 10000))
    GAME_AMOUNT_LIMIT = int(os.getenv("GAME_AMOUNT_LIMIT", 500000))
    TAX = os.getenv("TAX", "true").lower() in ["true", "1"]

    SUDO_COMMANDS = ["addadmin", "rmadmin", "admins"]
    ADMIN_COMMANDS = ["user"]
    COMMON_COMMANDS = ["start", "help", "leaderboard", "lb"]
    EASY_GAMES = ["basketball", "bb", "football", "fb", "dart", "dice"]
    NORMAL_GAMES = ["slot", "roulette", "rl"]
    HARD_GAMES = ["blackjack", "bj"]
    GAME_COMMANDS = EASY_GAMES + NORMAL_GAMES + HARD_GAMES
    USER_COMMANDS = ["info", "balance", "gift", "loan", "repay", "daily"]

    LEAGUES = [
        League("newbie", 0, 0),
        League("bronze", 5, 600),
        League("silver", 10, 1200),
        League("gold", 15, 2000),
        League("platinum", 20, 3000),
    ]

    LANGUAGES = [
        Language("en"),
    ]

    DEFAULT_LANGUAGE = next(filter(
        lambda language: language.name == os.getenv("DEFAULT_LANGUAGE", "en"), LANGUAGES), LANGUAGES[0])
    # TODO: Add ability to have per user language

    @staticmethod
    def get_translation(key: str):
        return Config.DEFAULT_LANGUAGE.get_translation(key)


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
    league: Mapped[str] = mapped_column(String(20), default="newbie")


class AdminDatabase(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40))
