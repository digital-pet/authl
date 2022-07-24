#######################################################
#                     digital_pet                     #
#                   p r e s e n t s                   #
#   A fucking something awful authbot fucking shit.   #
#######################################################

import sqlite3
from configparser import ConfigParser
from contextlib import closing


config = ConfigParser()
config.read('config.ini')

dbfile=config['Database']['file']

###
# db wrapper for parameterized queries
###

def query(db_name, querystring, params):
    with closing(sqlite3.connect(db_name)) as con, con, closing(con.cursor()) as cur:
        cur.execute(querystring, params)
        return cur.fetchall()
        

querystring = '''CREATE TABLE goons (userID TEXT NOT NULL, discordID TEXT NOT NULL, secret TEXT NOT NULL, is_banned INTEGER NOT NULL CHECK (is_banned IN (0, 1)), is_authed INTEGER NOT NULL CHECK (is_authed IN (0, 1)), is_sus INTEGER NOT NULL CHECK (is_sus IN (0, 1))) '''

querystring2 = '''CREATE TABLE kos (userID TEXT NOT NULL) '''


params = {}

query(dbfile,querystring,params)
query(dbfile,querystring2,params)