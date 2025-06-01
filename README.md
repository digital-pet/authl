# authl
 An Awful Authbot for Discord, from Goosefleet with love.

## Features

- It works!
- Prevents fresh SA accounts from joining, because we all know :tenbux: does not make a culture fit.
- Allows an admin to override those decisions!
- Also allows you to permanently  (or impermanently) ban goons from getting the goon role.
- No central database of goons that you're beholden to, you alone decide which goons are allowed.
- Probably won't crash!

## Installation

Fill in secrets.ini based on the example file in the repo. The SA info can be pulled from observing a request in the Developer Console or by exporting your cookies. The bot token you will get when creating the bot application in Discord Developer Portal. The bot should get the "bot" and "application commands" roles in the developer portal. The only permission the bot needs on your server itself is "Manage Roles" and I cannot emphasize enough that you should never be lazy and just give all bots Administrator on your server.

Fill in config.ini. I highly recommend using the [Ripcord](https://cancel.fm/ripcord/) client to get the role/channel/guild IDs.

Create a new venv

`pip install -U -r requirements.txt`

Run init.py to create the SQLite DB.

Run authl.py

If you want to get fancy, you can set it up to run as a daemon but that is outside the scope of this readme.

## Commands

### User
- /authme &lt;sa username> - starts the auth process for a user

### Moderator (anyone with Manage Roles)
- /authem &lt;@user> &lt;sa username> - lets a mod start the auth process for a user if they can't use slash commands
- /bangoon &lt;sa username> - bans a goon who has already authed and prevents them from re-authenticating. Does not strip roles.
- /unbangoon &lt;sa username> - unbans a goon
- /unsus &lt;sa username> - clears the j4g block on a goon (currently hardcoded to 300 posts/3 months)
- /kline &lt;sa username> - adds a k-line for a goon who has not joined yet that will ban them when they try to auth
- /unkline &lt;sa username> - removes a k-line for a goon
- /listban - lists all banned users
- /listsus - lists all suspicious users
- /listunauth - lists all users who have started but not completed auth
