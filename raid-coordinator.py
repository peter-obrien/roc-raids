import discord
import asyncio
import sys

class RaidMap:
    def __init__(self):
        self.raids = set()
        self.raiders = dict()
        self.details = dict()
        self.raidIdSeed = 0

    def start_raid(self, raidDetails):
        raidId = self.raidIdSeed + 1
        self.raidIdSeed += 1
        self.raids.add(str(raidId))
        self.raiders[str(raidId)] = []
        self.details[str(raidId)] = raidDetails
        return str(raidId)

    def add_raider(self, raidId, raiderName):
        self.raiders[raidId].append(raiderName)

    def get_raiders(self, raidId):
        return self.raiders[raidId]

    def get_details(self, raidId):
        return self.details[raidId]

    def get_detail_embed(self, raidId):
        result = discord.Embed(title='Raid ' + str(raidId), description=self.details[str(raidId)], colour=0x408fd0)
        result.set_footer(text='Participants: ' + str(len(self.raiders[raidId])))
        return result

    def get_raiders_embed(self, raidId):
        raiderOutput = ''
        counter = 0
        for raider in self.raiders[raidId]:
            if counter == 0 :
                raiderOutput += raider
            else:
                raiderOutput += ', ' + raider
            counter += 1
            if counter == 3:
                raiderOutput += '\n'
                counter = 0
        result = discord.Embed(title='Raid ' + str(raidId), description=self.details[str(raidId)] + '\n' + raiderOutput, colour=0x408fd0)
        result.set_footer(text='Participants: ' + str(len(self.raiders[raidId])))
        return result

    def get_raids(self):
        raidList = sorted(self.raids)
        result = ''
        for raid in raidList:
            result += raid + '\n'
        result.rstrip()
        return result

    def clear_raids(self):
        self.raids.clear()
        self.raiders.clear()
#
# End RaidMap class
#

if len(sys.argv) < 2:
    print("Please provide the bot's token.")
    quit()

client = discord.Client()
raids = RaidMap()

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

@client.event
async def on_message(message):

    if message.channel.name != 'general':
        if message.content.startswith('!how'):
            output = 'Valid commands:\n' + '\n\t!start <raid-name>' + '\n\t!join <raid-name>' + '\n\t!who <raid-name>' + '\n\t!raids'
            await client.send_message(message.channel, output)

        elif message.content.startswith('!start '):
            raidDetails = message.content[7:]
            raidId = raids.start_raid(raidDetails)
            raids.add_raider(raidId, message.author.display_name)
            em = raids.get_detail_embed(raidId)
            await client.send_message(message.channel, embed=em)
            await client.delete_message(message)

        elif message.content.startswith('!who '):
            raidId = message.content[5:]
            em = raids.get_raiders_embed(raidId)
            await client.send_message(message.channel, embed=em)

        elif message.content.startswith('!join '):
            raidId = message.content[6:]
            raids.add_raider(raidId, message.author.display_name)
            em = raids.get_detail_embed(raidId)
            await client.send_message(message.channel, embed=em)

        elif message.content.startswith('!leave '):
            raidId = message.content[7:]
            await client.send_message(message.channel, 'Not yet implemented')

        elif message.content.startswith('!details '):
            raidId = message.content[9:]
            em = raids.get_detail_embed(raidId)
            await client.send_message(message.channel, embed=em)

        elif message.content.startswith('!raids'):
            await client.send_message(message.channel, raids.get_raids())

client.run(sys.argv[1])
