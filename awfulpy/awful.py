from bs4 import BeautifulSoup
from bs4 import Comment
import re
import json


class ForumPost:
    def __init__(self, post):
        soup = BeautifulSoup(post, 'lxml')
        self.author = ForumPoster(str(soup.find_all("dl", class_="userinfo")))
        self.postid = int(soup.table['id'][4:])
        #self.timestamp = None
        body = soup.find("td", class_="postbody")
        for child in body.find_all("div", class_="bbc-block"):
            child.decompose()
        self.body = body.text.strip()

class ForumPoster:
    def __init__(self, sidebar):
        soup = BeautifulSoup(sidebar, 'lxml')
        self.name = soup.find("dt", class_="author").string
        #self.userid = None
        #self.avatar = None
        #self.signature = None
        #self.regdate = None

class ForumThreadPage:
    def __init__(self, text):
        soup = BeautifulSoup(text, 'lxml')
        posts = soup.find_all("table", class_="post")
        self.posts = []
        for p in posts:
            pobj = ForumPost(str(p))
            self.posts.append(pobj)
        breadcrumbs = soup.find("div", class_="breadcrumbs").find("select")
        if breadcrumbs:
            self.pagenum = int(breadcrumbs.find("option", selected=True).text)
            self.maxpagenum = int(breadcrumbs.find_all("option")[-1].text)
        else:
            self.pagenum = 1
            self.maxpagenum = 1
        self.replyURL= str(soup.find("div", class_="threadbar bottom").find("ul", class_="postbuttons").find_all("li")[1].a["href"])

class ProfilePage:
    def __init__(self,text):
        try:
            profile = json.loads(text)
            self.userid = profile['userid']
            self.username = profile['username']
            self.homepage = profile['homepage']
            self.icq = profile['icq']
            self.aim = profile['aim']
            self.yahoo = profile['yahoo']
            self.gender = profile['gender']
            self.usertitle = profile['usertitle']
            self.lastpost = profile['lastpost']
            self.posts = profile['posts']
            self.biography = profile['biography']
            self.location = profile['location']
            self.interests = profile['interests']
            self.occupation = profile['occupation']
            self.picture = profile['picture']
            self.joindate = profile['joindate']
            self.raw_text = text

        
        except Exception:
            self.userid = None
            self.username = None
            self.raw_text = None
            self.biography = None
            self.joindate = 0
            self.posts = 0
        
        ## TODO: capture all the separate sections instead of just all of it as a blob.
        
        
        
class ReplyPage:
    def __init__(self, text):
        soup = BeautifulSoup(text, 'lxml')
        self.message = None
        self.action = "postreply"
        self.threadid = soup.find("input", attrs={"name": "threadid"})['value']
        self.formkey = soup.find("input", attrs={"name": "formkey"})['value']
        self.form_cookie = soup.find("input", attrs={"name": "form_cookie"})['value']