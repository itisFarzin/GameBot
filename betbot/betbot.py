import os
import re
import asyncio
from threading import Thread
from typing import Optional, Union

from pyromod import Client

from betbot import types
from betbot.database import Config, Base
from betbot.dispatcher import Dispatcher


class BetBot(Client):
    def __init__(self,
                 api_id: Optional[Union[int, str]] = None,
                 api_hash: Optional[str] = None,
                 bot_token: Optional[str] = None,
                 plugins_folder: str = "plugins"):
        self.plugins_folder = plugins_folder
        super().__init__(self.__class__.__name__,
                         api_id=os.getenv("APP_ID", api_id),
                         api_hash=os.getenv("API_HASH", api_hash),
                         bot_token=os.getenv("BOT_TOKEN", bot_token),
                         plugins=dict(root=self.plugins_folder),
                         proxy=self._proxy_parser(os.getenv("PROXY", "")))

        self.dispatcher = Dispatcher(self)

        Base.metadata.create_all(Config.engine)

    def _proxy_parser(self, proxy: str):
        keys = ["scheme", "username", "password", "hostname", "port"]
        pattern = re.compile(r'^(?P<scheme>[a-zA-Z0-9]+)://(?:(?P<username>[^:]+)(?::(?P<password>[^@]+))?@)?(?P<hostname>[^:]+)(?::(?P<port>\d+))?$') # noqa
        result = pattern.match(proxy)

        if not result:
            return {}

        result = {key: int(value) if str(value).isdigit() else value
                  for key, value in result.groupdict().items()}
        return {key: result.get(key) for key in keys}

    async def deletable_dice(
        self,
        chat_id: int | str,
        emoji: str = "🎲",
        reply_to_message_id: int = None,
        seconds: int = 0
    ) -> Optional["types.Message"]:
        msg = await self.send_dice(
            chat_id,
            emoji,
            reply_to_message_id=reply_to_message_id
        )
        msg.__class__ = types.Message

        async def _delete(msg: Optional["types.Message"], second: int):
            if msg and second > 0:
                await asyncio.sleep(second)
                await msg.delete()
        Thread(target=asyncio.run, args=(_delete(msg, seconds),)).start()
        return msg
