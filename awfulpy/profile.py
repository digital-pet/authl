from . import awful
import aiohttp
import asyncio
import logging
import unicodedata

class AwfulProfile:
    def __init__(self, bbuserid, bbpassword, sessionid, sessionhash):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cookies = {
            'bbuserid' : bbuserid,
            'bbpassword' : bbpassword,
            'sessionid' : sessionid,
            'sessionhash' : sessionhash}
        self.logger.debug('Scraper started.')
    
    async def fetch_profile(self, username):
        base_url = "https://forums.somethingawful.com/member.php?action=getinfo&username={0}"

        self.logger.debug('Retreiving profile for user: {0}'.format(username))

        async with aiohttp.ClientSession(cookies=self.cookies) as session:
            async with session.get(base_url.format(username)) as response:
                raw_data = await response.read()
            
            text = unicodedata.normalize('NFC',raw_data.decode('utf-8', 'ignore'))

        return awful.ProfilePage(text)

    async def fetch_profile_by_id(self, username):
        base_url = "https://forums.somethingawful.com/member.php?action=getinfo&userid={0}"

        self.logger.debug('Retreiving profile for user: {0}'.format(username))

        async with aiohttp.ClientSession(cookies=self.cookies) as session:
            async with session.get(base_url.format(username)) as response:
                raw_data = await response.read()
            
            text = unicodedata.normalize('NFC',raw_data.decode('utf-8', 'ignore'))

        return awful.ProfilePage(text)