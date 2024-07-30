import os
from typing import Optional, Union

from pyromod import Client

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
                         plugins=dict(root=self.plugins_folder))

        self.dispatcher = Dispatcher(self)

        Base.metadata.create_all(Config.engine)
        
