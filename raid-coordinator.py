import discord
import asyncio
import sys

class raidMap:
    def __init__(self):
        self.raids = set()
        self.raiders = dict()
        self.details = dict()
        self.raidIdSeed = 0
    def startRaid(self, raidDetails):
        raidId = self.raidIdSeed + 1
        self.raidIdSeed += 1
        self.raids.add(str(raidId))
        self.raiders[str(raidId)] = []
        self.details[str(raidId)] = raidDetails
        return str(raidId)
    def addRaider(self, raidId, raiderName):
        self.raiders[raidId].append(raiderName)
    def getRaiders(self, raidId):
        return self.raiders[raidId]
    def getDetails(self, raidId):
        return self.details[raidId]
    def getRaids(self):
        raidList = sorted(self.raids)
        result = ''
        for raid in raidList:
            result += raid + '\n'
        result.rstrip()
        return result
    def clearRaids(self):
        self.raids.clear()
        self.raiders.clear()

if len(sys.argv) < 2:
    print("Please provide the bot's token.")
    quit()

client = discord.Client()
raids = raidMap()

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
            raidId = raids.startRaid(raidDetails)
            raids.addRaider(raidId, message.author.display_name)
            output = 'Raid Id:  ' + str(raidId) + '\nDetails:  ' + raids.getDetails(raidId) + '\nParticipants:  ' + str(len(raids.getRaiders(raidId)))
            # output = 'Raid "' + str(raidId) + '" is being organized by ' + message.author.display_name
            await client.send_message(message.channel, output)
            await client.delete_message(message)

        elif message.content.startswith('!who '):
            raidId = message.content[5:]
            await client.send_message(message.channel, raids.getRaiders(raidId))

        elif message.content.startswith('!join '):
            raidId = message.content[6:]
            raids.addRaider(raidId, message.author.display_name)
            output = 'Raid Id:  ' + str(raidId) + '\nDetails:  ' + raids.getDetails(raidId) + '\nParticipants:  ' + str(len(raids.getRaiders(raidId)))
            await client.send_message(message.channel, output)

        elif message.content.startswith('!leave '):
            raidId = message.content[7:]
            await client.send_message(message.channel, 'Not yet implemented')

        elif message.content.startswith('!details '):
            raidId = message.content[9:]
            output = 'Raid Id:  ' + str(raidId) + '\nDetails:  ' + raids.getDetails(raidId) + '\nParticipants:  ' + str(len(raids.getRaiders(raidId)))
            await client.send_message(message.channel, output)

        elif message.content.startswith('!raids'):
            await client.send_message(message.channel, raids.getRaids())

client.run(sys.argv[1])
