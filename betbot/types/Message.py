import betbot
import pyromod
import asyncio
from betbot import types
from typing import Optional
from threading import Thread
from .UserMethods import UserMethods
from .CustomUpdate import CustomUpdate


class Message(CustomUpdate, UserMethods, pyromod.Message):
    def __init__(self, client: "betbot.BetBot", **kwargs):
        super().__init__(client=client, **kwargs)

    async def deletable_reply(
        self,
        text: str,
        seconds: int = 0
    ) -> "types.Message":
        msg = await self.reply(text)

        async def _delete(msg: Optional["types.Message"], second: int):
            if msg and second > 0:
                await asyncio.sleep(second)
                await msg.delete()
        Thread(target=asyncio.run, args=(_delete(msg, seconds),)).start()
        return msg

    @property
    def amount(self):
        if self.command:
            if len(self.command) == 1:
                return None

            amount = self.command[1].lower()
        else:
            amount = self.text
        match amount:
            case "all":
                return self.user_balance
            case "half":
                return self.user_balance // 2
            case "quarter":
                return self.user_balance // 4
        human_readable_number = {"k": 1_000,
                                 "m": 1_000_000,
                                 "b": 1_000_000_000,
                                 "t": 1_000_000_000_000,
                                 "q": 1_000_000_000_000_000}
        try:
            for key, value in human_readable_number.items():
                if key in str(amount):
                    amount = float(str(amount).replace(key, "")) * value
            amount = round(float(amount))
        except ValueError:
            return
        return abs(amount)
