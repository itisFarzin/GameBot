# BetBot
> A Game Bot for Telegram using Pyrogram

## Dependencies
- Listed in `requirements.txt`

## Environment Configuration
To get started, rename `.env.example` to `.env` and set the following variables:

| Key                   | Description                             |
|-----------------------|-----------------------------------------|
| **DB_URI**            | Database URI                            |
| **OWNER_ID**          | User ID of the bot owner                |
| **API_ID**            | API ID <sup>*</sup>                     |
| **API_HASH**          | API Hash <sup>*</sup>                   |
| **BOT_TOKEN**         | Telegram Bot Token                      |
| **START_MONEY**       | Initial amount of money for new players |
| **LOAN_LIMIT**        | Maximum loan limit for a player         |
| **GAME_AMOUNT_LIMIT** | Maximum bet amount                      |
| **TAX**               | Enable or disable tax feature           |
| **PROXY**             | Proxy                                   |

---

<sup>*</sup> Get your API ID and API Hash from https://my.telegram.org/apps.

## Credits
- [Rodstor](https://github.com/Rodstor) For QOL and daily reward system
- [delivrance](https://github.com/delivrance) For Pyrogram
- [KurimuzonAkuma](https://github.com/KurimuzonAkuma) For keeping Pyrogram alive
