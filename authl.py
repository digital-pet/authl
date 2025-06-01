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
import traceback
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

bot = interactions.Client(token=bottoken, intents=interactions.Intents.ALL)

###
# Setup logging
###

loglevelDict = {
    'debug' : logging.DEBUG,
    'info' : logging.INFO,
    'warning' : logging.WARNING,
    'error' : logging.ERROR,
    'critical' : logging.CRITICAL}

logging.basicConfig(
    format="%(asctime)s %(levelname)-10s %(message)s",
    filename=config['Logging']['file'], 
    encoding='utf-8', 
    level=loglevelDict[config['Logging']['level']], 
    datefmt='%Y-%m-%d %H:%M:%S')

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
    err_query = '''UPDATE goons SET is_sus=1 WHERE userID=:userid LIMIT 1'''

    await asyncio.sleep(10)

    botspamchannel = interactions.Channel(**await bot._http.get_channel(bschan), _client=bot._http)

    while True:
        await asyncio.sleep(10)
        logging.info("auth worker running")
        results = query(dbfile, get_query, get_params)
        if results:
            success = ""
            displaymessage = False
            for r in results:
                userid = r[0]
                try:
                    user = interactions.Member(**await bot._http.get_member(guildid,r[1]), _client=bot._http)
                except Exception:
                    user = None
                    logging.error("Error encountered finding user", exc_info=True)
                if user is None:
                    logging.info(f"User with discord id {r[1]} is not in the server, skipping.")
                    err_params = {"userid":userid}
                    query(dbfile, err_query, err_params)
                    await botspamchannel.send(f"User https://forums.somethingawful.com/member.php?action=getinfo&userid={userid} left discord, please unsus if they rejoin.")
                    continue

                
                result = await profile.fetch_profile_by_id(userid)
                fulltext = result.biography
                
                position = fulltext.find(r[2])
                if position > -1:
                    auth_params = {"userid":userid}
                    try:
                        
                        await user.add_role(goonrole,int(guildid))
 
                        success = success + "\n" + user.mention
                        
                        displaymessage = True
                        
                        query(dbfile, auth_query, auth_params)
                    
                    except Exception:
                        logging.error("Could not auth user", exc_info=True)
                        await botspamchannel.send(f"Authenticating user {user.mention} failed.")
                        await asyncio.sleep(10)
                        continue
                await asyncio.sleep(10)
                
            if displaymessage:
                await botspamchannel.send(f"Gave goon role to the following users {success}")
                    
        logging.info("auth worker waiting")
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

async def get_profile(userid = None, username = None):
    if userid:
        return await profile.fetch_profile_by_id(userid)
    elif username:
        return await profile.fetch_profile(username)
    else:
        raise ArgumentError("get_profile called without userid or username")


async def get_userid(username):
    user_profile = await get_profile(username=username)
    return user_profile.userid

async def get_username(userid):
    user_profile = await get_profile(userid=userid)
    return user_profile.username
    
async def calculate_suspicion(userid):
    user_profile = await get_profile(userid=userid)

    sus = 0
    
    #sub 300 postcount is sus

    postcount = user_profile.posts
    
    if abs(postcount) < 300:
        sus = 1
     
    #regdate less than 3 months is sus

    regdate = datetime.utcfromtimestamp(user_profile.joindate)
    
    threshhold = datetime.timestamp(datetime.now()) - (2629800*3)
 
    if datetime.timestamp(regdate) > threshhold:
        sus = 1
    
    return sus
    
async def get_user(userid,discordid):
    
    get_query = '''SELECT * FROM goons WHERE userID=:userid OR discordID=:discordid'''
    get_params = {"userid": userid, "discordid":discordid}
    
    kos_check_query = '''SELECT * FROM kos WHERE userID=:userid LIMIT 1'''
    kos_params = {"userid":userid}
    
    results = query(dbfile, get_query, get_params)
    if len(results) > 1:
        raise DuplicateEntry(f"Expected 1 result, got {len(results)}")
    
    if not results:
    
        #If there isn't an existing user, add it.
        sus = await calculate_suspicion(userid)

        # TODO: log in botspam if sus

        secret = crypt.crypt(f"{discordid}{userid}")
        minsecret = "HONK!" + secret[20:32]
        
        ban = 1 if len(query(dbfile,kos_check_query,kos_params)) else 0
        
        ins_query = '''INSERT INTO goons values (:userid,:discordid,:secret,:ban,0,:sus)'''
        ins_params = {"userid": userid,"discordid": discordid,"secret":minsecret,"ban":ban,"sus":sus}
        
        query(dbfile, ins_query,ins_params)
        results = query(dbfile, get_query, get_params)
    
    if results[0][0] != str(userid):
        logging.error("UserMismatch - " + str(results))
        raise UserMismatch(f"User provided {userid}, db contained {results[0][0]}")
    
    if results[0][1] != discordid:
        logging.error("DiscordMismatch - " + str(results))
        raise DiscordMismatch(f"User provided {discordid}, db contained {results[0][1]}")
    
    if results[0][3]:
        logging.error("BannedUser - " + str(results))
        raise BannedUser("User is banned!")
    
    return results


###
# Bot events
###

@bot.event(name="on_guild_member_add")
async def on_guild_member_add(user: interactions.GuildMember):

    logging.info("User joined")
    
    get_query = '''SELECT is_banned, is_authed FROM goons WHERE discordID=:discordid'''
    get_params = {"discordid":str(user.id)}

    try:
        results = query(dbfile, get_query, get_params)
    except Exception:
        logging.error("Error encountered finding user", exc_info=True)
        return

    if not results:
        logging.info("User not registered as goon")
        return


    if results[0][0]:
    #    try:
    #        await user.ban(guildid,reason="You're banned!")
    #    except Exception:
    #        #log error
    #        pass
        logging.info("User is banned, not granting role")
        return

    if results[0][1]:
        try:
            await user.add_role(goonrole)
        except Exception:
            logging.error("Error encountered giving user role", exc_info=True)
            pass
        return



###
# Bot commands
###

'''
AUTHME
AUTHME
AUTHME
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
        response = f"{username} is not registered on SA.\n\nIf you want to be registered on SA you can spend :10bux: at https://forums.somethingawful.com. Otherwise, please honk in \#spambot-prison until we give you a role."
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
    
    response = f"{response}\nPut the following key in your SA profile \"about me\" section: {results[0][2]}\nDo not put it in ICQ number or homepage or any other field."
    
    if results[0][5]:
        await botspamchannel.send("User " + ctx.author.mention + " needs attention to complete authentication.")
        response = response + "\n\nA member of leadership may contact you to complete your authentication."
    else:
        response = response + "\n\nYou will be automatically authenticated within 24 hours."
    
    await ctx.send(response)


'''
AUTHEM
AUTHEM
AUTHEM
'''

@bot.command(
    name="authem",
    description="Auth someone else on this discord",
    dm_permission=False,
    default_member_permissions=interactions.Permissions.KICK_MEMBERS,
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
        response = f"{username} is not registered on SA. Verify that they're actually a Something Awful poster."
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
    
    response = response + "\n" + user.mention + f" Put the following key in your SA profile \"about me\" section: {results[0][2]}\nDo not put it in ICQ number or homepage or any other field."
    
    if results[0][5]:
        await botspamchannel.send("User " + user.mention + " needs attention to complete authentication.")
        response = response + "\n\nA member of leadership may contact you to complete your authentication."
    else:
        response = response + "\n\nYou will be automatically authenticated within 24 hours."
    
    await ctx.send(response)


'''
WHOIS
WHOIS
WHOIS
'''

@bot.command(
    name="whois",
    description="Find a user on this server",
    dm_permission=False,
    default_member_permissions=interactions.Permissions.KICK_MEMBERS,
    options = [
        interactions.Option(
            name = "discord",
            description = "Their discord username",
            type=interactions.OptionType.USER,
            required=False),
        interactions.Option(
            name = "username",
            description = "Their forums username",
            type=interactions.OptionType.STRING,
            required=False),],)

async def whois(ctx: interactions.CommandContext, discord=None, username=None):

    user = discord

    userid_query = '''SELECT * FROM goons WHERE userID=:userid'''
    discordid_query = '''SELECT * FROM goons WHERE discordID=:discordid'''


    #botspamchannel = interactions.Channel(**await bot._http.get_channel(bschan), _client=bot._http)
    response = ""

    if user:
        try:
            discordid = int(user.id)
        except Exception:
            response = "User is not on this discord"
            await ctx.send(response, ephemeral=True)
            return
        
        params = {"discordid": discordid}
        result = query(dbfile, discordid_query, params)
        
        if result:
            for r in result:
                try:
                    username = await get_username(r[0])
                    response = f"{response}\n{user.mention} - {username}"
                except Exception:
                    response = f"{response}\nUser not in discord - {username}"            
        
 
    elif username:
        userid = await get_userid(username)
        if userid is None:
            response = f"{username} is not registered on SA."
            await ctx.send(response, ephemeral=True)
            return
            
        params = {"userid": userid}
        
        result = query(dbfile, userid_query, params)
        
        if result:
            for r in result:
                try:
                    user = interactions.Member(**await bot._http.get_member(guildid,r[1]), _client=bot._http)
                    response = f"{response}\n{user.mention} - {username}"
                except Exception:
                    response = f"{response}\nUser not in discord - {username}"
                
        else:
            response = f"User {username} is not registered on this discord"            
        
    
    else:
        response = "You must provide at least one option."
    
    await ctx.send(response, ephemeral=True)

'''
LISTSUS
LISTSUS
LISTSUS
'''

@bot.command(
    name="listsus",
    description="List all sus goons",
    dm_permission=False,
    default_member_permissions=interactions.Permissions.KICK_MEMBERS,)



async def listsus(ctx: interactions.CommandContext):
    
    await ctx.defer()

    querystr = '''SELECT * FROM goons WHERE is_sus = 1 AND is_banned = 0'''

    params = {}

    result = query(dbfile, querystr, params)
    
    if result:
        response = str(len(result)) + " goons are sus:"
        for r in result:
            try: 
                user = interactions.Member(**await bot._http.get_member(guildid,r[1]), _client=bot._http)
            except Exception:
                user = False
            userid = r[0]
            username = await get_username(r[0])
            try:
                response = f"{response}\n{user.mention} (ID: {userid}, Handle: {username})"
            except Exception:
                response = f"{response}\nUser not in discord (ID: {userid}, Handle: {username})"

    else:
        response = "No goons are currently being sus."
    
    await ctx.send(response)

'''
LISTUNAUTH
LISTUNAUTH
LISTUNAUTH
'''

@bot.command(
    name="listunauth",
    description="List all unauthed goons",
    dm_permission=False,
    default_member_permissions=interactions.Permissions.KICK_MEMBERS,)



async def listunauth(ctx: interactions.CommandContext):

    await ctx.defer()

    querystr = '''SELECT * FROM goons WHERE is_authed = 0 AND is_sus = 0 AND is_banned = 0'''

    params = {}

    result = query(dbfile, querystr, params)
    
    if result:
        response = str(len(result)) + " goons haven't put the code in:"
        for r in result:
            try: 
                user = interactions.Member(**await bot._http.get_member(guildid,r[1]), _client=bot._http)
            except Exception:
                user = False
            userid = r[0]
            username = await get_username(r[0])
            try:
                response = f"{response}\n{user.mention} (ID: {userid}, Handle: {username})"
            except Exception:
                response = f"{response}\nUser not in discord (ID: {userid}, Handle: {username})"

    else:
        response = "All the goons have followed instructions."
    
    await ctx.send(response)

'''
LISTBAN
LISTBAN
LISTBAN
'''

@bot.command(
    name="listban",
    description="List all banned goons",
    dm_permission=False,
    default_member_permissions=interactions.Permissions.KICK_MEMBERS,)



async def listban(ctx: interactions.CommandContext):

    await ctx.defer()

    querystr = '''SELECT * FROM goons WHERE is_banned = 1'''

    params = {}
    result = query(dbfile, querystr, params)
    if result:
        response = str(len(result)) + " goons are banned:"
        for r in result:
            try: 
                user = interactions.Member(**await bot._http.get_member(guildid,r[1]), _client=bot._http)
            except Exception:
                user = False
            userid = r[0]
            username = await get_username(r[0])
            try:
                response = f"{response}\n{user.mention} (ID: {userid}, Handle: {username})"
            except Exception:
                response = f"{response}\nUser not in discord (ID: {userid}, Handle: {username})"
    
    else:

        response = "Nobody's banned!"
    
    await ctx.send(response)

'''
LISTKLINE
LISTKLINE
LISTKLINE
'''

@bot.command(
    name="listkline",
    description="List all banned goons",
    dm_permission=False,
    default_member_permissions=interactions.Permissions.KICK_MEMBERS,)



async def listkline(ctx: interactions.CommandContext):

    await ctx.defer()

    querystr = '''SELECT * FROM kos'''

    params = {}
    result = query(dbfile, querystr, params)
    if result:
        response = str(len(result)) + " goons are banned:"
        for r in result:
            #user = interactions.Member(**await bot._http.get_member(guildid,r[1]), _client=bot._http)
            
            userid = r[0]
            username = await get_username(r[0])
            response = f"{response}\nID: {userid}, Handle: {username}"
    
    else:

        response = "Nobody's banned!"
    
    await ctx.send(response)


'''
UNSUS
UNSUS
UNSUS
'''

@bot.command(
    name="unsus",
    description="Remove the sus hold on a goon",
    dm_permission=False,
    default_member_permissions=interactions.Permissions.KICK_MEMBERS,
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
ROLEUPALL
'''
@bot.command(
    name="roleupall",
    description="Re-assign goon role on all goons",
    dm_permission=False,
    default_member_permissions=interactions.Permissions.KICK_MEMBERS,
    options = [
        interactions.Option(
            name = "verification",
            description = "Are you very, very sure you want to do this?",
            type = interactions.OptionType.STRING,
            required=True),],)

async def roleupall(ctx: interactions.CommandContext, verification: str):
    if verification != "abracadabra":
        response = "You didn't say the magic word."
        await ctx.send(response)
        return

    querystr = '''SELECT * FROM goons WHERE is_authed = 1 and is_banned = 0'''
    params = {}

    botspamchannel = interactions.Channel(**await bot._http.get_channel(bschan), _client=bot._http)

    results = query(dbfile, querystr, params)
    if not results:
        response = "No goons are authed."
        await ctx.send(response)

    response = "Beginning bulk role re-assignment."
    await ctx.send(response)

    i = 0

    response = "Gooned up:\n"


    for r in results:
        userid = r[0]
        try:
            user = interactions.Member(**await bot._http.get_member(guildid,r[1]), _client=bot._http)
        except Exception:
            user = None
            logging.error("Error encountered finding user", exc_info=True)
        if user is None:
            logging.info(f"User with discord id {r[1]} is not in the server, skipping.")
#            err_params = {"userid":userid}
#            query(dbfile, err_query, err_params)
#            await botspamchannel.send(f"User https://forums.somethingawful.com/member.php?action=getinfo&userid={userid} left discord, please unsus if they rejoin.")
            continue

        try: 
            await user.add_role(goonrole,int(guildid))
        except Exception:
            continue

        i += 1
        response += f"{user.mention}\n"

        if i % 15 == 0:
            await botspamchannel.send(response)
            response = "Gooned up:\n"
            await asyncio.sleep(5)

    if response != "Gooned up:\n":
        await botspamchannel.send(response)

    response = "It is done."
    await botspamchannel.send(response)

'''
UNAUTH
'''

@bot.command(
    name="unauth",
    description="Deauthorize a goon",
    dm_permission=False,
    default_member_permissions=interactions.Permissions.KICK_MEMBERS,
    options = [
        interactions.Option(
            name = "username",
            description = "Their username on the Something Awful Forums",
            type=interactions.OptionType.STRING,
            required=True),],)



async def unauth(ctx: interactions.CommandContext, username: str):

    querystr = '''UPDATE goons SET is_authed = 0 WHERE userID=:userid LIMIT 1'''

    response = ""
    userid = await get_userid(username)

    if userid is None:
        response = f"{username} is not registered on SA."
        await ctx.send(response)
        return
        
    params = {"userid": userid}
    
    query(dbfile, querystr, params)

    response  = f"{str(username)} with id {userid} will be reauthenticated."
    
    await ctx.send(response)

'''
PURGE
PURGE
PURGE
'''

@bot.command(
    name="purge",
    description="Purge a goon from the database",
    dm_permission=False,
    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    options = [
        interactions.Option(
            name = "username",
            description = "Their username on the Something Awful Forums",
            type=interactions.OptionType.STRING,
            required=True),],)



async def purge(ctx: interactions.CommandContext, username: str):

    querystr = '''DELETE FROM goons WHERE userID=:userid LIMIT 1'''

    response = ""
    userid = await get_userid(username)

    if userid is None:
        response = f"{username} is not registered on SA."
        await ctx.send(response)
        return
        
    params = {"userid": userid}
    
    query(dbfile, querystr, params)

    response  = f"{str(username)} with id {userid} has been purged from the database."
    
    await ctx.send(response)


'''
KLINE
KLINE
KLINE
'''

@bot.command(
    name="kline",
    description="Ban a goon before they join",
    dm_permission=False,
    default_member_permissions=interactions.Permissions.KICK_MEMBERS,
    options = [
        interactions.Option(
            name = "username",
            description = "Their username on the Something Awful Forums",
            type=interactions.OptionType.STRING,
            required=True),],)



async def kline(ctx: interactions.CommandContext, username: str):

    querystr = '''INSERT INTO kos VALUES (:userid, "")'''
    querystr2 = '''UPDATE goons SET is_banned=1 WHERE userID=:userid LIMIT 1'''

    response = ""
    userid = await get_userid(username)

    if userid is None:
        response = f"{username} is not registered on SA."
        await ctx.send(response)
        return
        
    params = {"userid": userid}
    
    query(dbfile, querystr, params)
    query(dbfile, querystr2, params)

    response  = f"{str(username)} with id {userid} has been k-lined."
    
    await ctx.send(response)

'''
UNKLINE
UNKLINE
UNKLINE
'''

@bot.command(
    name="unkline",
    description="Unban a goon before they join",
    dm_permission=False,
    default_member_permissions=interactions.Permissions.KICK_MEMBERS,
    options = [
        interactions.Option(
            name = "username",
            description = "Their username on the Something Awful Forums",
            type=interactions.OptionType.STRING,
            required=True),],)



async def unkline(ctx: interactions.CommandContext, username: str):

    querystr = '''DELETE FROM kos WHERE userID=:userid LIMIT 1'''

    response = ""
    userid = await get_userid(username)

    if userid is None:
        response = f"{username} is not registered on SA."
        await ctx.send(response)
        return
        
    params = {"userid": userid}
    
    query(dbfile, querystr, params)

    response  = f"{str(username)} with id {userid} has been unk-lined."
    
    await ctx.send(response)

'''
BANGOON
BANGOON
BANGOON
'''

@bot.command(
    name="bangoon",
    description="Ban a goon from getting the goon role",
    dm_permission=False,
    default_member_permissions=interactions.Permissions.KICK_MEMBERS,
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
UNBANGOON
UNBANGOON
UNBANGOON
'''

@bot.command(
    name="unbangoon",
    description="Allow a banned goon to get the goon role",
    dm_permission=False,
    default_member_permissions=interactions.Permissions.KICK_MEMBERS,
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
# Main program starts here
###

async def main():

    #logging.info('===Startup===')

    #loop = asyncio.get_running_loop()
    #loop.set_exception_handler(handle_exception)


    background = asyncio.create_task(auth_processor())
    foreground = asyncio.create_task(bot._ready())
    
    done, pending = await asyncio.wait(
        [background, foreground],
        return_when=asyncio.FIRST_EXCEPTION
    )
    
    for task in pending:
        task.cancel()
    
    for task in done:
        if task.exception():
            logging.error(''.join(traceback.format_exception(task.exception())))
        

try:
    retval = 0
    
    #hacky because interactions weirdness
    bot._loop.run_until_complete(main())
except KeyboardInterrupt:
    print('\nCtrl-C received, quitting immediately')
    logging.critical('Ctrl-C received, quitting immediately')
    retval = 1
except Exception:
    print("Please wait, crashing...")
    logging.critical("Fatal error in main loop", exc_info=True)
    retval = 2
finally:
    os._exit(retval)
