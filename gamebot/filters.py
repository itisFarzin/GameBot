from sqlalchemy import select
from sqlalchemy.orm import Session

from gamebot import GameBot
from pyrogram.filters import *

from gamebot.database import Config, AdminDatabase

is_owner = user(Config.OWNER_ID)


class Admin(Filter, set):
    def __init__(self):
        super().__init__()

    async def __call__(self, _: GameBot, update: Message | CallbackQuery):
        with Session(Config.engine) as session:
            return (update.from_user
                    and (update.from_user.id == Config.OWNER_ID or
                         bool(session.execute(select(AdminDatabase).where(AdminDatabase.id == update.from_user.id))
                              .one_or_none())))


is_admin = Admin()
