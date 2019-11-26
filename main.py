import discord
import sqlite3
import yaml
import dropbox
from tempfile import gettempdir
import os
import dice

import logging
logging.basicConfig(format = '%(levelname)s:%(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

KNOWEDGEMAP = {
    'arcana': ['ancient mysteries', 'magic', 'arcane symbols', 'constructs', 'dragons', 'magical beasts'],
    'dungeoneering' : ['aberrations', 'canerns', 'oozes', 'spelunking'],
    'geography': ['lands', 'terrain', 'climate', 'people'],
    'history' : ['wars', 'colonies', 'migrations', 'inhabitants', 'laws', 'customs', 'traditions',],
    'local' : ['legends', 'personalities', 'inhabitants', 'laws', 'customs', 'traditions', 'humanoids'],
    'nature' : ['animals', 'fey', 'monstrous humanoids', 'plants', 'seasons', 'cycles', 'weather', 'vermin'],
    'nobility' : ['lineages', 'heraldry', 'personalities', 'royalty'],
    'planes' : ['inner planes', 'outer planes', 'astral plane', 'ethereal plane', 'outsiders', 'planar magic'],
    'religion' : ['gods', 'mythic', 'mythic history', 'ecclesiastic tradition', 'holy symbols', 'undead'],
}

class DiscordClient(discord.Client):
    def __init__(self, *args, **kwargs):
        self.sql = SQLAccess('spells_sqlite.db')
        self.enablePartyJoke = False
        self.roller = DiceWrapper()
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
        commandEntered = False

        if message.content == '$camelbot toggle party jokes':
            self.enablePartyJoke = not self.enablePartyJoke
            return
        elif 'split the party' in message.content.lower() and self.enablePartyJoke:
            await message.channel.send('It\'s a bad idea to split the party!')
            return
        elif 'keep' in message.content.lower() and 'party together' in message.content.lower() and self.enablePartyJoke:
            await message.channel.send('https://cdn.discordapp.com/attachments/547608064161873930/619739566332575768/uoqvtjpda3w11.jpg')
            return
        elif message.content.lower().startswith('$spell named'):
            commandEntered = True
            spellName = message.content.lower().strip().replace('$spell named ', '')
            results = self.sql.spellSearchExactName(spellName)
        elif message.content.lower().startswith('$spell contains'):
            commandEntered = True
            if m[0] == '--any':
                # spell may contain any of the keywords
                results = self.sql.spellSearchNameContainsAny(m[3:])
            else:
                # spell must contain all of the keywords
                results = self.sql.spellSearchNameContainsAll(m[2:])
        elif message.content.lower().startswith('$identify'):
            toID = message.content.lower().strip().replace('$identify ', '')
            if not toID:
                return
            for skill in KNOWEDGEMAP.keys():
                if toID in KNOWEDGEMAP[skill]:
                    await message.channel.send('Use %s to identify that'%skill)
            return
        elif message.content.lower().startswith('$roll'):
            commandEntered = True
            try:
                roll = message.content.lower().replace('$roll', '').strip()
                tokens = self.roller.tokenizer(roll)
                head = self.roller.buildTree(tokens)
                rollResults = self.roller.getResults(head)

                await message.channel.send(roll + ': ' + str(rollResults))
                if isinstance(rollResults, list):
                    await message.channel.send('Total:' + str(sum(rollResults)))
            except DiceParserException as e:
                logger.info(e)
                await message.channel.send('Parsing error:' + e.message)
            except TokenizerException as e:
                logger.info(e)
                await message.channel.send('Parsing error:' + e.message)
            return

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
                    if len(result[0]) < 1900: # Discord character limit
                        await message.channel.send(result[0])
                    else:
                        await message.channel.send(result[1])
        elif commandEntered and not results:
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
            targets = noneFilter(result[11])
            duration = noneFilter(result[12])
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

            formattedDesc = ('__**{}**__\n'+ \
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
                        duration, savingThrow, spellResistance, shortDesc,
                    )

            logger.info('Found: '+spell)
            spellStrings.append([spell, formattedDesc])
            
        logger.info('Found %s spells for query'%len(spellStrings))
        return spellStrings


class Token: # Binary expression tree
    def __init__(self, token, parent, left=None, right=None):
        self.token = token
        self.parent = parent # Only none if head node
        self.left = left
        self.right = right

    def __repr__(self):
        parent = self.parent.token if self.parent else 'None'
        left = self.left.token if self.left else 'None'
        right = self.right.token if self.right else 'None'
        
        return 'Token(%s, parent=%s, left=%s, right=%s)'%(self.token, parent, left, right)

    def isOperator(self):
        return not self.token.isnumeric() # Only numbers are not operators.

    def assignParent(self, token):
        # Replace self with a new parent token in the tree. Attach this token to the right of the new parent.
        oldParent = self.parent # Parent before operation
        isLeft = oldParent and (oldParent.left == self)
        
        newParent = Token(token, oldParent, None, self)
        self.parent = newParent
        if oldParent:
            if isLeft:
                oldParent.left = newParent
            else:
                oldParent.right = newParent
        return newParent
        # End result:
        # self's parent is the new token
        # new token's parent is self's *original* parent
        # the original parent refers to the new parent in the same location where it has previously referred to self
        #       that is: if self was left, originalParent.left = newParent. Otherwise originalParent.right = newParent
        # new parent's right is self, and new parent's left is null.

class DiceWrapper:
    def __init__(self):
        self.operators = { # Key: operator. Value: Order (0 performed first)
            'd'     : 0,  # dice. Usage: 1d20
            'kh'    : 9, # keep highest. Usage: 2d20kh1 (keep highest of 2 d20 rolls)
            'kl'    : 9, # keep lowest. Usage: 2d20kl1 (keep lowest of 2 d20 rolls)
            '+'     : 8, # Add. Usage: 1d20+1d20+1 (add value or result to other value or result)
            '-'     : 8, # Subtract. Usage: 1d20-1d20-1 (subtract value or result to other value or result)
            '*'     : 7, # Multiply. Usage: 1d20*1d20*2 (multiply value or result to other value or result)
            '/'     : 7, # Divide. Usage: 1d20/1d20/2 (divide value or result to other value or result. Error if value is below 0 when performing op. Does not sanity check before performing op)
            '>'     : 9, # Count above. Usage: 5d6>5 (count all results of a die roll above a given value or result)
            '<'     : 9, # Count below. Usage: 5d6<2 (count all results of a die roll below a given value or result)
        }

        self.incompatible = [ # Operators within the same list cannot occur within the same command
            ['kh', 'kl', '>', '<'],
            ['>', '<', '+',], # TODO: There are certainly use cases that these can share, but for now it's not 
            ['>', '<', '-'],
            ['>', '<', '/'],
            ['>', '<', '*'],
        ]

        self.context = { # Key: operator. Value: context for lexer
            'd'     : 'DICE',
            'kh'    : 'RESULTMODIFIER',
            'kl'    : 'RESULTMODIFIER',
            '+'     : 'MATHOP', 
            '-'     : 'MATHOP', 
            '*'     : 'MATHOP', 
            '/'     : 'MATHOP', 
            '>'     : 'RESULTMODIFIER', 
            '<'     : 'RESULTMODIFIER', 
        }

    def isOperator(self, token):
        # Assumes properly tokenized token
        return token.isnumeric()

    def tokenizer(self, command):
        tokens = []
        num = ''
        kFlag = False

        for i, char in enumerate(command):
            if not char.isnumeric() and num:
                tokens.append(num)
                num = ''

            # Multicharacter tokens
            if char == 'k':
                kFlag = True
            elif char.isnumeric():
                num = num + char
            elif kFlag:
                kFlag = False
                if not char in ['l', 'h']:
                    raise TokenizerException('Invalid token %s at character %s. Expected \'kh\' or \'kl\''%(char, i))
                tokens.append('k'+char)
            # Single character tokens
            elif char in self.operators or char in ['(' ')']:
                tokens.append(char)
            else:
                raise TokenizerException('Invalid token %s at character %s.'%(char, i))
        if num:
            tokens.append(num) # Catch the number at the end of the command

        if not tokens:
            raise TokenizerException('No valid tokens found')
        return tokens

    def buildTree(self, tokens):
        prev = None
        for token in reversed(tokens):
            if token.isnumeric(): # token is operand
                if not prev:
                    # Because all ops are binary, head assignment will always be an operand
                    prev = Token(token, None) # Initialize head
                elif not prev.isOperator():
                    raise DiceParserException('Cannot have two adjacent operands (%s and %s). Do you have an errant space?'%(prev.token, token))
                else:
                    # token is operand, previous is operator
                    cur = Token(token, prev)
                    prev.left = cur
                    prev = cur
            else: # token is operator
                if not prev:
                    raise DiceParserException('The last character must be a number')
                elif prev.isOperator():
                    raise DiceParserException('Cannot have two adjacent operator') # if prev is operator and cur is operator, there are two adjc operator
                else:
                    # token is operator, previous is operand
                    prev = prev.assignParent(token)

        head = prev
        while head.parent: # seek head
            head = head.parent
        return head

    def getResults(self, head):
        # recurse through tree to figure out value
        # Immediately return numbers
        if not head.isOperator():
            return int(head.token)
        # Roll dice
        elif head.token == 'd':
            try:
                num = int(head.left.token)
                sides = int(head.right.token)
                return list(dice.roll('%sd%s'%(num, sides))) # returns a list of results as ints
            except:
                raise DiceParserException('Cannot roll dice %sd%s'%(head.left.token, head.right.token))
        # RESULT MODIFIERS:
        # kh/kl keep highest/lowest dice
        elif head.token in ('kh', 'kl'):
            diceResults = self.getResults(head.left)
            num = 0
            if not isinstance(diceResults, list):
                raise DiceParserException('Left-hand operand of \'%s\' must be a dice result'%head.token)
            try:
                num = self.getResults(head.right)
            except TypeError:
                raise DiceParserException('Right hand operand of \'%s\' must be a number'%head.token)
            except ValueError:
                raise DiceParserException('Right hand operand of \'%s\' must be a number'%head.token)
            if num == 0:
                return []
            elif num > len(diceResults):
                return diceResults
            return sorted(diceResults)[-1*num:]

        # </>: Count over/under a value
        elif head.token in ('<', '>'):
            diceResults = self.getResults(head.left)
            if not isinstance(diceResults, list):
                raise DiceParserException('Left-hand operand of \'%s\' must be a dice result'%head.token)
            try:
                threshold = int(self.getResults(head.right))
            except TypeError:
                raise DiceParserException('Right hand operand of \'%s\' must be a number'%head.token)
            except ValueError:
                raise DiceParserException('Right hand operand of \'%s\' must be a number'%head.token)
            
            filterFunc = None
            if head.token == '<':
                filterFunc = lambda i: i<threshold
            elif head.token == '>':
                filterFunc = lambda i: i>threshold
            filter(filterFunc, diceResults)

        # math ops
        elif head.token in '+-*/':
            left = self.getResults(head.left)
            right = self.getResults(head.right)
            if isinstance(left, list):
                left = sum(left)
            if isinstance(right, list):
                right = sum(right)
            
            if head.token=='+':
                return left+right
            elif head.token=='-':
                return left-right
            elif head.token=='*':
                return left*right
            elif head.token=='/':
                return left/right
            

class TokenizerException(Exception):
    pass
    
class DiceParserException(Exception):
    pass

client = DiscordClient()
logger.info('using token: %s'%os.environ['token'])
client.run(os.environ['token'])
