import gamebot
from gamebot import types


class CustomUpdate:
    def __init__(self, client: "gamebot.GameBot" = None, reply_to_message: "types.Message" = None):
        self._client = client
        self.reply_to_message = reply_to_message
