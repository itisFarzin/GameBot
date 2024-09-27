import gamebot
import pyrogram
from gamebot import types
from gamebot.database import Config
from pyrogram import enums
from typing import Optional, Union
from pyrogram.types import InlineKeyboardMarkup
from pyrogram.errors import MessageNotModified


class CallbackQuery(types.CustomUpdate, types.UserMethods, pyrogram.types.CallbackQuery):
    def __init__(self, client: "gamebot.GameBot" = None, **kwargs):
        super().__init__(client=client, **kwargs)
        self.is_owner = False

        if self.from_user:
            user_id = self.from_user.id
            self.is_owner = user_id == Config.OWNER_ID

    async def edit_message_reply_markup(self, reply_markup: InlineKeyboardMarkup | None = None):
        try:
            await super().edit_message_reply_markup(reply_markup=reply_markup)
        except MessageNotModified:
            pass

    async def edit_message_text(
            self,
            text: str,
            parse_mode: Optional["enums.ParseMode"] = None,
            disable_web_page_preview: bool = None,
            reply_markup: "InlineKeyboardMarkup" = None
    ) -> Union["types.Message", bool]:
        try:
            return await super().edit_message_text(text=text, parse_mode=parse_mode,
                                                   disable_web_page_preview=disable_web_page_preview,
                                                   reply_markup=reply_markup)
        except MessageNotModified:
            pass
