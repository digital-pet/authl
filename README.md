# authl
 An Awful Authbot for Discord, from Goosefleet with love.

## Prerequisites

- interactions.py
- configparser
- aiohttp
- BS4
- unicodedata

## Installation

Fill in secrets.ini based on the example file in the repo. The SA info can be pulled from observing a request in the Developer Console or by exporting your cookies. The bot token you will get when creating the bot application in Discord Developer Portal. The only permission the bot needs is "Manage Roles" and I cannot emphasize enough that you should never be lazy and just give all bots Administrator on your server.

Fill in config.ini. I highly recommend using the [Ripcord](https://cancel.fm/ripcord/) client to get the role/channel/guild IDs.

Run init.py to create the SQLite DB.

Run authl.py

If you want to get fancy, you can set it up to run as a daemon but that is outside the scope of this readme.