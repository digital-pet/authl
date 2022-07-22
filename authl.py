#######################################################
#                     digital_pet                     #
#                   p r e s e n t s                   #
#   A fucking something awful authbot fucking shit.   #
#######################################################

###
# Imports
###
import logging
import asyncio
import os
import re
import interactions
import sqlite3
import crypt
from configparser import ConfigParser
from awfulpy import *
from contextlib import closing
from datetime import datetime

###
# Config
###
secrets = ConfigParser()
secrets.read('secrets.ini')
config = ConfigParser()
config.read('config.ini')

bbuserid = secrets['SAForums']['bbuserid']
bbpassword = secrets['SAForums']['bbpassword']
sessionid = secrets['SAForums']['sessionid']
sessionhash = secrets['SAForums']['sessionhash']
bottoken = secrets['Discord']['token']

dbfile=config['Database']['file']

goonrole=config['Discord']['roleID']
guildid=config['Discord']['guildID']
bschan=config['Discord']['botspamID']

###
# instantiate awful scraper and bot
###

profile = AwfulProfile(bbuserid, bbpassword, sessionid, sessionhash)

bot = interactions.Client(token=bottoken)

#db_cursor.execute('''CREATE TABLE goons (userID TEXT NOT NULL, discordID TEXT NOT NULL, secret TEXT NOT NULL, is_banned INTEGER NOT NULL CHECK (is_banned IN (0, 1)), is_authed INTEGER NOT NULL CHECK (is_authed IN (0, 1)), is_sus INTEGER NOT NULL CHECK (is_sus IN (0, 1))) ''')

###
# Setup logging
###

loglevelDict = {
    'debug' : logging.DEBUG,
    'info' : logging.INFO,
    'warning' : logging.WARNING,
    'error' : logging.ERROR,
    'critical' : logging.CRITICAL}

logging.basicConfig(filename=config['Logging']['file'], encoding='utf-8', level=loglevelDict[config['Logging']['level']])


###
# db wrapper for parameterized queries
###

def query(db_name, querystring, params):
    with closing(sqlite3.connect(db_name)) as con, con, closing(con.cursor()) as cur:
        cur.execute(querystring, params)
        return cur.fetchall()    

###
# Auth worker loop
###

async def auth_processor():

    get_query = '''SELECT * FROM goons WHERE is_banned=0 AND is_authed=0 AND is_sus=0'''
    get_params = {}
    
    auth_query = '''UPDATE goons SET is_authed=1 WHERE userID=:userid LIMIT 1'''
    await asyncio.sleep(10)

    botspamchannel = interactions.Channel(**await bot._http.get_channel(bschan), _client=bot._http)

    while True:
        await asyncio.sleep(10)
        print("auth thread running")
        results = query(dbfile, get_query, get_params)
        if results:
            success = ""
            displaymessage = False
        
            for r in results:
                userid = r[0]
                result = await profile.fetch_profile_by_id(userid)
                fulltext = result.raw_profile_text
                
                position = fulltext.find(r[2])
                if position > -1:
                    auth_params = {"userid":userid}
                    try:
                        user = interactions.Member(**await bot._http.get_member(guildid,r[1]), _client=bot._http)
                    
                        #await get(bot, interactions.Member, parent_id=guildid, object_id=r[1])
                        
                        await user.add_role(goonrole,guildid)
                        
                        success = success + "\n" + user.mention
                        
                        displaymessage = True
                        
                        query(dbfile, auth_query, auth_params)
                    
                    except Exception:
                        logging.error("Could not auth user", exc_info=True)
                        await botspamchannel.send("Authenticating user " + user.mention + " failed. Blame corgski.")
                        await asyncio.sleep(10)
                        continue
                await asyncio.sleep(10)
                
            if displaymessage:
                await botspamchannel.send("Gave goon role to the following users " + success)
                    
        print("auth thread waiting")
        await asyncio.sleep(890)



###
#   Exceptions that may be encountered during authentication
###

class DuplicateEntry(Exception):
    pass
class UserMismatch(Exception):
    pass
class DiscordMismatch(Exception):
    pass
class BannedUser(Exception):
    pass

###
#   Authentication functions
###

async def get_userid(username):
    result = await profile.fetch_profile(username)
    return result.userid

    
async def calculate_suspicion(userid):
    result = await profile.fetch_profile_by_id(userid)
    fulltext = result.raw_profile_text

    sus = 0
    
    
    #sub 300 postcount is sus
    re_res = re.search(r"en \<b\>-?([0-9]*)\<\/b\> po", fulltext)

    postcount = int(re_res.group(1))
    
    if postcount < 300:
        sus = 1
     
    #regdate less than 3 months is sus
    result = re.search(r"registering on \<b\>(.*)\<\/b\>", fulltext)
    regdate = datetime.strptime(result.group(1), "%b %d, %Y")
    
    threshhold = datetime.timestamp(datetime.now()) - (2629800*3)
 
    if datetime.timestamp(regdate) > threshhold:
        sus = 1
    
    return sus
    
async def get_user(userid,discordid):
    
    get_query = '''SELECT * FROM goons WHERE userID=:userid OR discordID=:discordid'''
    get_params = {"userid": userid, "discordid":discordid}
    
    results = query(dbfile, get_query, get_params)
    if len(results) > 1:
        raise DuplicateEntry("Expected 1 result, got " + len(results))
    
    if not results:
    
        #If there isn't an existing user, add it.
        sus = await calculate_suspicion(userid)

        secret = crypt.crypt(f"{discordid}{userid}")
        minsecret = "HONK!" + secret[20:32]
        
        ins_query = '''INSERT INTO goons values (:userid,:discordid,:secret,0,0,:sus)'''
        ins_params = {"userid": userid,"discordid": discordid,"secret":minsecret,"sus":sus}
        
        query(dbfile, ins_query,ins_params)
        results = query(dbfile, get_query, get_params)
    
    if results[0][0] != userid:
        logging.error("UserMismatch - " + str(results))
        raise UserMismatch("User provided " + userid + ", db contained " + results[0][0])
    
    if results[0][1] != discordid:
        logging.error("DiscordMismatch - " + str(results))
        raise DiscordMismatch("User provided " + discordid + ", db contained " + results[0][1])
    
    if results[0][3]:
        logging.error("BannedUser - " + str(results))
        raise BannedUser("User is banned!")
    
    return results



###
# Bot commands
###

'''

'''

@bot.command(
    name="authme",
    description="Get authorized in this discord",
    dm_permission=False,
    options = [
        interactions.Option(
            name = "username",
            description = "Your username on the Something Awful Forums",
            type=interactions.OptionType.STRING,
            required=True),],)

async def authme(ctx: interactions.CommandContext, username: str):

    botspamchannel = interactions.Channel(**await bot._http.get_channel(bschan), _client=bot._http)

    response = ""
    userid = await get_userid(username)
    if userid is None:
        response = f"{username} is not registered on SA."
        await ctx.send(response)
        return
    
    response = f"Found {username} with ID {userid}"
    
    try:
        results = await get_user(userid,str(ctx.author.id))
    except BannedUser:
        response = "You are banned! Contact leadership if you wish to appeal your ban."
        await ctx.send(response)
        return
    
    except UserMismatch:
        response = "An error occured. Please ping leadership."
        await ctx.send(response)
        return

    except DiscordMismatch:
        response = "An error occured. Please ping leadership."
        await ctx.send(response)
        return
    except DuplicateEntry:
        response = "A duplicate entry was encountered. This should never happen. The database is corrupted."
        await ctx.send(response)
        return
    
    response = response + "\n" + f"Put the following key in your SA profile: {results[0][2]}"
    
    if results[0][5]:
        await botspamchannel.send("User " + ctx.author.mention + " needs attention to complete authentication.")
        response = response + "\n\nA member of leadership may contact you to complete your authentication."
    else:
        response = response + "\n\nYou will be automatically authenticated within 24 hours."
    
    await ctx.send(response)


'''

'''

@bot.command(
    name="authem",
    description="Auth someone else on this discord",
    dm_permission=False,
    default_member_permissions=interactions.Permissions.MANAGE_ROLES,
    options = [
        interactions.Option(
            name = "user",
            description = "The discord user who should be authed",
            type=interactions.OptionType.USER,
            required=True),
        interactions.Option(
            name = "username",
            description = "Your username on the Something Awful Forums",
            type=interactions.OptionType.STRING,
            required=True),],)

async def authem(ctx: interactions.CommandContext, user: interactions.User, username: str):

    botspamchannel = interactions.Channel(**await bot._http.get_channel(bschan), _client=bot._http)

    response = ""
    userid = await get_userid(username)
    if userid is None:
        response = f"{username} is not registered on SA."
        await ctx.send(response)
        return
    
    response = f"Found {username} with ID {userid}"
    
    try:
        results = await get_user(userid,str(user.id))
    except BannedUser:
        response = "They are banned!"
        await ctx.send(response)
        return
    
    except UserMismatch:
        response = "An error occured: This discord account is registered to another SA user."
        await ctx.send(response)
        return

    except DiscordMismatch:
        response = "An error occured. This SA account is registered to another discord user."
        await ctx.send(response)
        return
    
    response = response + "\n" + user.mention + f" Put the following key in your SA profile: {results[0][2]}"
    
    if results[0][5]:
        await botspamchannel.send("User " + user.mention + " needs attention to complete authentication.")
        response = response + "\n\nA member of leadership may contact you to complete your authentication."
    else:
        response = response + "\n\nYou will be automatically authenticated within 24 hours."
    
    await ctx.send(response)


'''

'''

@bot.command(
    name="listsus",
    description="List all sus goons",
    dm_permission=False,
    default_member_permissions=interactions.Permissions.MANAGE_ROLES,)



async def listsus(ctx: interactions.CommandContext):

    querystr = '''SELECT * FROM goons WHERE is_sus = 1 AND is_banned = 0'''

    params = {}

    result = query(dbfile, querystr, params)
    
    if result:
        response = str(len(result)) + " goons are sus:"
        for r in result:
            user = interactions.Member(**await bot._http.get_member(guildid,r[1]), _client=bot._http)
            response = response + "\n" + user.mention + "(ID: " + r[0] + ")"

    else:
        response = "No goons are currently being sus."
    
    await ctx.send(response)

'''

'''

@bot.command(
    name="listunauth",
    description="List all unauthed goons",
    dm_permission=False,
    default_member_permissions=interactions.Permissions.MANAGE_ROLES,)



async def listunauth(ctx: interactions.CommandContext):

    querystr = '''SELECT * FROM goons WHERE is_authed = 0 AND is_sus = 0 AND is_banned = 0'''

    params = {}

    result = query(dbfile, querystr, params)
    
    if result:
        response = str(len(result)) + " goons haven't put the code in:"
        for r in result:
            user = interactions.Member(**await bot._http.get_member(guildid,r[1]), _client=bot._http)
            response = response + "\n" + user.mention

    else:
        response = "All the goons have followed instructions."
    
    await ctx.send(response)

'''

'''

@bot.command(
    name="listban",
    description="List all banned goons",
    dm_permission=False,
    default_member_permissions=interactions.Permissions.MANAGE_ROLES,)



async def listban(ctx: interactions.CommandContext):

    querystr = '''SELECT * FROM goons WHERE is_banned = 1'''

    params = {}

    result = query(dbfile, querystr, params)
    
    if result:
        response = str(len(result)) + " goons are banned:"
        for r in result:
            user = interactions.Member(**await bot._http.get_member(guildid,r[1]), _client=bot._http)
            response = response + "\n" + user.mention + "(ID: " + r[0] + ")"

    else:
        response = "Nobody's banned!"
    
    await ctx.send(response)

'''

'''

@bot.command(
    name="unsus",
    description="Remove the sus hold on a goon",
    dm_permission=False,
    default_member_permissions=interactions.Permissions.MANAGE_ROLES,
    options = [
        interactions.Option(
            name = "username",
            description = "Their username on the Something Awful Forums",
            type=interactions.OptionType.STRING,
            required=True),],)



async def unsus(ctx: interactions.CommandContext, username: str):

    querystr = '''UPDATE goons SET is_sus = 0 WHERE userID=:userid LIMIT 1'''

    response = ""
    userid = await get_userid(username)

    if userid is None:
        response = f"{username} is not registered on SA."
        await ctx.send(response)
        return
        
    params = {"userid": userid}
    
    query(dbfile, querystr, params)

    response  = f"{str(username)} with id {userid} has been cleared to authenticate."
    
    await ctx.send(response)

'''

'''

@bot.command(
    name="bangoon",
    description="Ban a goon from getting the goon role",
    dm_permission=False,
    default_member_permissions=interactions.Permissions.MANAGE_ROLES,
    options = [
        interactions.Option(
            name = "username",
            description = "Their username on the Something Awful Forums",
            type=interactions.OptionType.STRING,
            required=True),],)
    
async def bangoon(ctx: interactions.CommandContext, username: str):

    querystr = '''UPDATE goons SET is_banned = 1, is_authed=0 WHERE userID=:userid LIMIT 1'''

    response = ""
    userid = await get_userid(username)
    if userid is None:
        response = f"{username} is not registered on SA."
        await ctx.send(response)
        return

    params = {"userid": userid}
    
    query(dbfile, querystr, params)

    response  = f"{username} with id {userid} is banned. Be sure to strip their roles."
    
    await ctx.send(response)
    
    
'''

'''

@bot.command(
    name="unbangoon",
    description="Allow a banned goon to get the goon role",
    dm_permission=False,
    default_member_permissions=interactions.Permissions.MANAGE_ROLES,
    options = [
        interactions.Option(
            name = "username",
            description = "Their username on the Something Awful Forums",
            type=interactions.OptionType.STRING,
            required=True),],)
 
async def unbangoon(ctx: interactions.CommandContext, username: str):

    querystr = '''UPDATE goons SET is_banned = 0 WHERE userID=:userid LIMIT 1'''

    response = ""
    userid = await get_userid(username)
    if userid is None:
        response = f"{username} is not registered on SA."
        await ctx.send(response)
        return
        
    params = {"userid": userid}

    query(dbfile, querystr, params)
    
    response  = f"{username} with id {userid} is unbanned."
    
    await ctx.send(response) 

## TODO: Purge command

###
# Exception handler, crash fast for unhandled exceptions inside async functions
###

def handle_exception(loop, context):
    # context["message"] will always be there; but context["exception"] may not
    msg = context.get("exception", context["message"])
    print("Please wait, crashing...")
    logging.critical(f"Caught exception: {msg}", exc_info=True)
    logging.info("Shutting down...")
    os._exit(2)



###
# Main program starts here
###

logging.info('===Startup===')
loop = asyncio.get_event_loop()
loop.set_exception_handler(handle_exception)

# Backend Init

asyncio.ensure_future(auth_processor())


# Discord init
logging.info('Initializing Discord')
asyncio.ensure_future(bot._ready())

try:
    loop.run_forever()
except KeyboardInterrupt:
    print('\nCtrl-C received, quitting immediately')
    logging.critical('Ctrl-C received, quitting immediately')
    os._exit(1)
except Exception:
    logging.error("Fatal error in main loop", exc_info=True)
    os._exit(2)