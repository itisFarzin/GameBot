import os

import pyrogram
from dotenv import load_dotenv
from sqlalchemy import create_engine

from betbot.database import Base
from betbot.dispatcher import Dispatcher

load_dotenv()


class BetBot(pyrogram.Client):
    engine = create_engine(os.getenv("DB_URI", "sqlite:///database.db"))

    OWNER_ID = int(os.getenv("OWNER_ID"))
    LOAN_LIMIT = int(os.getenv("LOAN_LIMIT", 10000))
    GAME_AMOUNT_LIMIT = int(os.getenv("GAME_AMOUNT_LIMIT", 500000))
    TAX = os.getenv("TAX", "true").lower() in ["true", "1"]

    SUDO_COMMANDS = ["addadmin", "rmadmin", "admins"]
    ADMIN_COMMANDS = ["reset", "setbalance", "addbalance", "rmbalance"]
    COMMON_COMMANDS = ["start", "help", "leaderboard", "lb"]
    GAME_COMMANDS = ["roulette", "rl", "blackjack", "bj", "slot", "dice", "basketball", "bb", "football", "fb", "dart"]
    USER_COMMANDS = ["info", "balance", "gift", "loan", "repay", "daily"]

    def __init__(self, plugins_folder: str = "plugins"):
        self.plugins_folder = plugins_folder
        super().__init__(self.__class__.__name__, api_id=os.getenv("APP_ID"), api_hash=os.getenv("API_HASH"),
                         bot_token=os.getenv("BOT_TOKEN"),
                         plugins=dict(root=self.plugins_folder))

        self.dispatcher = Dispatcher(self)

        Base.metadata.create_all(self.engine)
