import discord
import sqlite3

import logging
logger = logging.getLogger(__name__)

class DiscordClient(discord.Client):
    def __init__(self, *args, **kwargs):
        self.sql = SQLAccess('spells_sqlite.db')
        super().__init__(*args, **kwargs)

    async def on_ready(self):
        logger.info(('We have logged in as {0.user}'.format(client))

    async def on_message(self, message):
        logger.info("Message received! %s"%message.content)
        if message.author == client.user:
            return
        
        if message.content.startswith('$spell contains'):
            m = message.content.split()
            results = None
            if m[0] == '-a':
                # message must contain all the results
                results = self.sql.spellSearchNameContainsAll(m[1:])
            else:
                # message contains any of the results
                results = self.sql.spellSearchNameContainsAny(m)
            
            if results:
                for result in results:
                    await message.channel.send(result)
            else:
                await message.channel.send('No results found :(')

        

class SQLAccess():
    def __init__(self, db):
         self.connection = sqlite3.connect(db)
         self.cur = self.connection.cursor()

    def spellSearchNameContainsAll(self, names):
        # query = '%'+name+'%'
        # self.cur.execute('SELECT * FROM spells WHERE name LIKE ?', (query,))
        parameters = []
        query = 'SELECT * FROM spells WHERE name LIKE '
        for name in names:
            parameters.append('%{}%'.format(name))
            query = query+'? AND name LIKE '
        self.cur.execute(query, tuple(parameters))
        return self.formatSpellList()

    def spellSearchNameContainsAny(self, names):
        parameters = []
        query = 'SELECT * FROM spells WHERE name LIKE ?'
        for name in names:
            parameters.append('%{}%'.format(name))
            query = query+'OR name LIKE ?'
        query = query[:-14]
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
                    '**Saving Throw** {}; **Spell Resistance** {}\n'+ \
                    '__DESCPRIPTION__\n\n'+ \
                    '{}').format(
                        name, school, subschool, descriptor, spellLevel, 
                        castingTime, components, spellRange, area, targets, 
                        duration, savingThrow, spellResistance, description,
                    )
            logger.info('Found: '+spell)
            spellStrings.append(spell)
            
        logger.info('Found %s spells for query'%len(spellStrings))
        return spellStrings


client = DiscordClient()
client.run('NjAyOTkyNzQ1MDg2MTg5NTY5.XVjPeQ.CPfqEJQnds38JvzIyi1k7xbaiEE')
