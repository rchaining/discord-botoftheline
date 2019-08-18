import discord
import sqlite3

class DiscordClient(discord.Client):
    def __init__(self, *args, **kwargs):
        self.sql = SQLAccess('spells_sqlite.db')
        super().__init__(*args, **kwargs)

    async def on_ready(self):
        print('We have logged in as {0.user}'.format(client))

    async def on_message(self, message):
        if message.author == client.user:
            return
        
        if message.content.startswith('$spell contains'):
            output = ''
            m = message.content.split()
            results = None
            if m[0] == '-a':
                # message must contain all the following
                results = self.sql.spellSearchNameContainsAll(m[1:])
            else:
                # message contains any of the following
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
        for result in results:
            name = result[0]
            school = result[1]
            subschool = result[2]
            descriptor = result[3]
            spellLevel = result[4]
            castingTime = result[5]
            components = result[6]
            spellRange = result[8]
            area = result[9]
            targets = result[10]
            duration = result[11]
            savingThrow = result[15]
            spellResistance = result[16]
            description = result[17]
            shortDesc = result[44]

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
            print('Found: '+spell)
            spellStrings.append(spell)
            
        return spellStrings


client = DiscordClient()
client.run('NjAyOTkyNzQ1MDg2MTg5NTY5.XVjPeQ.CPfqEJQnds38JvzIyi1k7xbaiEE')
