import discord
import asyncio
import sys
from datetime import datetime, timedelta
from pytz import timezone
import pytz

class RaidMap:
    def __init__(self):
        self.raids = set()
        self.raiders = dict()
        self.details = dict()
        self.raidMessages = dict()
        self.raidIdSeed = 0

    def generate_raid_id(self):
        self.raidIdSeed += 1
        return self.raidIdSeed

    def store_raid(self, raidId, raidMessage, raidMessageEmbed):
        self.raidMessages[str(raidId)] = (raidMessage, raidMessageEmbed)
        self.raiders[str(raidId)] = []

    def add_raider_gh(self, raidId, raiderName):
        self.raiders[raidId].append(raiderName)
        raidMessageEmbed = self.raidMessages[raidId][1]
        raidMessageEmbed.set_footer(text='Participants: ' + str(len(self.raiders[raidId])))
        return (self.raidMessages[raidId][0], raidMessageEmbed)

    #start_raid will be used when gymhuntr integration is down
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
        result = discord.Embed(title='Raid ' + str(raidId), description=self.details[str(raidId)], colour=embedColor)
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
        result = discord.Embed(title='Raid ' + str(raidId), description=self.details[str(raidId)] + '\n' + raiderOutput, colour=embedColor)
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
easternTz = timezone('US/Eastern')
utcTz = timezone('UTC')
timeFmt = '%m/%d %I:%M %p'
googleDirectionsUrlBase='https://www.google.com/maps/dir/Current+Location/'
embedColor = 0x408fd0

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

@client.event
async def on_message(message):

    if message.channel.name != 'general':
        if message.content.startswith('!go'):
            message = await client.get_message(message.channel, '341294312749006849')

        if message.author.name == 'GymHuntrBot':
            if len(message.embeds) > 0:
                gmapUrl = googleDirectionsUrlBase + message.embeds[0]['url'].split('#')[1]

                descTokens = message.embeds[0]['description'].split('\n')
                gymName = descTokens[0]
                pokemon = descTokens[1]

                timeTokens = descTokens[3].split(' ')
                secondsToEnd = int(timeTokens[6]) + (60 * int(timeTokens[4])) + (60 * 60 * int(timeTokens[2]))
                endTime = message.timestamp + timedelta(seconds=secondsToEnd)
                easternEndTime = endTime.replace(tzinfo=utcTz).astimezone(easternTz)

                desc = gymName + '\n' + '*Ends: ' + easternEndTime.strftime(timeFmt) + '*'

                raidId = raids.generate_raid_id()
                result = discord.Embed(title=pokemon + ': Raid #' + str(raidId), url=gmapUrl, description=desc, colour=embedColor)

                thumbnailContent = message.embeds[0]['thumbnail']
                result.set_thumbnail(url=thumbnailContent['url'])
                result.thumbnail.height=thumbnailContent['height']
                result.thumbnail.width=thumbnailContent['width']
                result.thumbnail.proxy_url=thumbnailContent['proxy_url']

                raidMessage = await client.send_message(message.channel, embed=result)
                raids.store_raid(raidId, raidMessage, result)
        else:
            if message.content.startswith('!how'):
                output = 'Valid commands:\n' + '\n\t!start <raid-details>' + '\n\t!join <raid-id>' + '\n\t!who <raid-id>' + '\n\t!details <raid-id>'
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
                msgData = raids.add_raider_gh(raidId, message.author.display_name)
                await client.edit_message(msgData[0], embed=msgData[1])

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
