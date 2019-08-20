import discord
import sqlite3
import yaml
import dropbox
from tempfile import gettempdir
import os

import logging
logging.basicConfig(format = '%(levelname)s:%(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class DiscordClient(discord.Client):
    def __init__(self, *args, **kwargs):
        self.sql = SQLAccess('spells_sqlite.db')
        super().__init__(*args, **kwargs)

    async def on_ready(self):
        logger.info(('We have logged in as {0.user}'.format(client)))

    async def on_message(self, message):
        if message.author == client.user:
            return
        
        logger.info("Message received! %s"%message.content)
        if 'file a bug report' in message.content:
            await message.channel.send('Please direct all bug reports to /dev/null')
            return

        
        m = message.content.split()
        results = None

        if message.content.startswith('$spell named'):
            spellName = message.content.replace('$spell named', '')
            results = self.sql.spellSearchExactName(spellName)

        if message.content.startswith('$spell contains'):
            if m[0] == '--any':
                # spell may contain any of the keywords
                results = self.sql.spellSearchNameContainsAny(m[3:])
            else:
                # spell must contain all of the keywords
                results = self.sql.spellSearchNameContainsAll(m[2:])
            
        if results:
            if len(results) > 10:
                logging.info('Way too many results')
                await message.channel.send('Greater than 10 results. Please refine your search')
                return
            elif len(results) > int(os.environ['condense_after']):
                await message.channel.send('Greater than %s results. Condensing' % int(os.environ['condense_after']))
                for result in results:
                    await message.channel.send(result[1])
            else:
                for result in results:
                    if len(result[0]) < 900: # Discord character limit
                        await message.channel.send(result[0])
                    else:
                        await message.channel.send(result[1])
        else:
            await message.channel.send('No results found :(')

        

class SQLAccess():
    def __init__(self, db):
         self.connection = self.getSqlConn()
         self.cur = self.connection.cursor()

    
    def getSqlConn(self):
        token = os.environ['dbx_token']
        dbx = dropbox.Dropbox(token)
        _, res = dbx.files_download(path='/spells_sqlite.db')
        if res.content:
            logger.info('Found content from dropbox')
        else:
            logger.info('SQLite db not found in dropbox')

        fname = gettempdir()+'/spells_sqlite.db'
        with open(fname, 'wb') as fp:
            logger.info('Writing to tempfile:%s'%fp.write(res.content))

        logger.info('Connecting to sqlite with tempfile: %s'%fname)
        conn = sqlite3.connect(fname)
        return conn

    def spellSearchNameContainsAll(self, names):
        parameters = []
        query = 'SELECT * FROM spells WHERE name LIKE '
        for name in names:
            parameters.append('%{}%'.format(name))
            query = query+'? AND name LIKE '
        query = query[:-15]
        logging.info('Query: %s'%query)
        logging.info('Parameters: %s'%parameters)
        self.cur.execute(query, tuple(parameters))
        return self.formatSpellList()

    def spellSearchNameContainsAny(self, names):
        parameters = []
        query = 'SELECT * FROM spells WHERE name LIKE '
        for name in names:
            parameters.append('%{}%'.format(name))
            query = query+'? OR name LIKE '
        query = query[:-14]
        logging.info('Query: %s'%query)
        logging.info('Parameters: %s'%parameters)
        self.cur.execute(query, tuple(parameters))
        return self.formatSpellList()

    def spellSearchExactName(self, spellName):
        query = 'SELECT * FROM spells WHERE name=?'
        logging.info('Searching for a spell with the name: %s'%spellName)
        self.cur.execute(query, (spellName,))
        return self.formatSpellList

    def formatSpellList(self):
        spellStrings = []
        results = self.cur.fetchall()
        noneFilter = lambda val: val if val else None
        for result in results:
            name = noneFilter(result[0])
            school = noneFilter(result[1])
            subschool = noneFilter(result[2])
            descriptor = noneFilter(result[3])
            spellLevel = noneFilter(result[4])
            castingTime = noneFilter(result[5])
            components = noneFilter(result[6])
            spellRange = noneFilter(result[8])
            area = noneFilter(result[9])
            targets = noneFilter(result[10])
            duration = noneFilter(result[11])
            savingThrow = noneFilter(result[15])
            spellResistance = noneFilter(result[16])
            description = noneFilter(result[17])
            shortDesc = noneFilter(result[44])

            spell = ('__**{}**__\n'+ \
                    '**School** {} ({}) [{}]; **Level** {}\n'+ \
                    '__CASTING__\n'+ \
                    '**Casting Time** {}\n'+ \
                    '**Components** {}\n'+ \
                    '__EFFECT__\n'+ \
                    '**Range** {}\n'+ \
                    '**Area** {}\n'+ \
                    '**Target** {}\n'+ \
                    '**Duration** {}\n'+ \
                    '**Saving Throw** {}; **Spell Resistance** {}\n'+ \
                    '__DESCPRIPTION__\n'+ \
                    '{}\n\n').format(
                        name, school, subschool, descriptor, spellLevel, 
                        castingTime, components, spellRange, area, targets, 
                        duration, savingThrow, spellResistance, description,
                    )

            formattedDesc = ('__**{}**__\n{}\n\n').format(name, shortDesc)

            logger.info('Found: '+spell)
            spellStrings.append([spell, formattedDesc])
            
        logger.info('Found %s spells for query'%len(spellStrings))
        return spellStrings


client = DiscordClient()
logger.info('using token: %s'%os.environ['token'])
client.run(os.environ['token'])
