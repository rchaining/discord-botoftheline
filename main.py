import discord
import sqlite3
import yaml
import dropbox
import tempfile
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
        logger.info("Message received! %s"%message.content)
        if message.author == client.user:
            return
        
        if message.content.startswith('$spell contains'):
            m = message.content.split()
            results = None
            if m[0] == '--any':
                # spell may contain any of the keywords
                results = self.sql.spellSearchNameContainsAny(m[3:])
            else:
                # spell must contain all of the keywords
                results = self.sql.spellSearchNameContainsAll(m[2:])
            
            if results:
                if len(results) > int(os.environ['condense_after']):
                    await message.channel.send('Greater than %s results. Condensing' % int(os.environ['condense_after']))
                    for result in results:
                        await message.channel.send(result[1])
                else:
                    for result in results:
                        await message.channel.send(result[0])
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

        fp = tempfile.TemporaryFile()
        fp.write(res.content)
        fp.close()

        logger.info('Connecting to sqlite with tempfile: %s'%fp.name)
        conn = sqlite3.connect(fp.name)
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
                    '**Saving Throw** {}; **Spell Resistance** {}\n\n'+ \
                    '__DESCPRIPTION__\n'+ \
                    '{}').format(
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
