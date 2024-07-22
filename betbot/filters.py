from sqlalchemy import select
from sqlalchemy.orm import Session

from betbot import BetBot
from pyrogram.filters import *

from betbot.database import Config, AdminDatabase

is_owner = user(Config.OWNER_ID)


class Admin(Filter, set):
    def __init__(self):
        super().__init__()

    async def __call__(self, _: BetBot, message: Message):
        with Session(Config.engine) as session:
            return (message.from_user
                    and (message.from_user.id == Config.OWNER_ID or
                         bool(session.execute(select(AdminDatabase).where(AdminDatabase.id == message.from_user.id))
                              .one_or_none())))


is_admin = Admin()
