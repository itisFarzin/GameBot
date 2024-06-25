import betbot
import pyrogram
from .UserMethods import UserMethods
from .CustomUpdate import CustomUpdate


class Message(CustomUpdate, UserMethods, pyrogram.types.Message):
    def __init__(self, client: "betbot.BetBot" = None, **kwargs):
        super().__init__(client=client, **kwargs)

    @property
    def amount(self):
        if len(self.command) == 1:
            return None

        amount = self.command[1].lower()
        match amount:
            case "all":
                return self.user_balance
            case "half":
                return self.user_balance // 2
            case "quarter":
                return self.user_balance // 4
        human_readable_number = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000, "t": 1_000_000_000_000,
                                 "q": 1_000_000_000_000_000}
        try:
            for key, value in human_readable_number.items():
                if key in str(amount):
                    amount = float(amount.replace(key, "")) * value
            amount = round(float(amount))
        except ValueError:
            return
        return abs(amount)
