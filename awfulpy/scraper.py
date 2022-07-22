from . import awful
import aiohttp
import asyncio
import logging
import unicodedata

class AwfulScraper:
    def __init__(self, threadid, bbuserid, bbpassword, sessionid, sessionhash, start_page = 1, last_seen = 1):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.threadid = threadid
        self.start_page = start_page
        self.last_seen = last_seen
        self.cookies = {
            'bbuserid' : bbuserid,
            'bbpassword' : bbpassword,
            'sessionid' : sessionid,
            'sessionhash' : sessionhash}
        self.logger.debug('Scraper started.')
    
    async def _fetch_thread_page(self, page):
        base_url = "https://forums.somethingawful.com/showthread.php?noseen=0&threadid={0}&perpage=40&pagenumber={1}"

        self.logger.debug('Retreiving page: {0}'.format(page))

        async with aiohttp.ClientSession(cookies=self.cookies) as session:
            async with session.get(base_url.format(self.threadid,page)) as response:
                raw_data = await response.read()
            
            text = unicodedata.normalize('NFC',raw_data.decode('utf-8', 'ignore'))

        return awful.ForumThreadPage(text)

    async def fetch_posts_since_last_seen(self):
        pagenum = self.start_page
        last_seen = self.last_seen
        self.logger.debug('Old start_page: {0}, Old last_seen: {1}'.format(pagenum, last_seen))
        posts = []
        while True:
            page = await self._fetch_thread_page(pagenum)
            for post in page.posts:
                if post.postid > last_seen:
                    posts.append(post)
                    last_seen = post.postid
            if page.pagenum == page.maxpagenum:
                break
            else:
                pagenum += 1
                await asyncio.sleep(1)
        self.logger.debug('New start_page: {0}, New last_seen: {1}'.format(pagenum, last_seen))
        self.start_page = pagenum
        self.last_seen = last_seen

        return posts

    async def reply_to_thread(self,postbody):
        base_url = "https://forums.somethingawful.com/newreply.php?action=newreply&threadid={0}"
        do_post_url = "https://forums.somethingawful.com/newreply.php"

        async with aiohttp.ClientSession(cookies=self.cookies) as session:
            async with session.get(base_url.format(self.threadid)) as response:
                html = await response.text()
        
        replyobj = awful.ReplyPage(html)
        self.logger.debug("Threadid: {0}, formkey: {1}, form_cookie: {2}".format(replyobj.threadid, replyobj.formkey, replyobj.form_cookie))
        payload = {
            "action" : "postreply",
            "threadid" : int(replyobj.threadid),
            "formkey" : replyobj.formkey,
            "form_cookie" : replyobj.form_cookie,
            "message" : postbody,
            "submit" : "Submit Reply",
            "parseurl" : "yes",
            "bookmark" : "yes",
            "signature" : "yes"
        }

        headers = {'referer' : base_url.format(replyobj.threadid)}

        async with aiohttp.ClientSession(cookies=self.cookies) as session:
            async with session.post(do_post_url, data=payload, headers=headers) as response:
                html = await response.text()
        self.logger.info('Submitted post with status: {0}'.format(response.status))
        self.logger.debug(response.headers)

