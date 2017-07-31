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
        self.raiders[str(raidId)] = set()

    def add_raider_gh(self, raidId, raiderName, party_size=1, start_time=None):
        raider = Participant(raiderName, int(party_size), start_time)
        participants = self.raiders[raidId]
        if raider in participants:
            participants.remove(raider)
        participants.add(raider)
        raidMessageEmbed = self.raidMessages[raidId][1]
        raidMessageEmbed.set_footer(text='Participants: ' + str(self.get_participant_number(raidId)))
        return (self.raidMessages[raidId][0], raidMessageEmbed)

    def remove_raider_gh(self, raidId, raiderName):
        self.raiders[raidId].discard(Participant(raiderName))
        raidMessageEmbed = self.raidMessages[raidId][1]
        raidMessageEmbed.set_footer(text='Participants: ' + str(self.get_participant_number(raidId)))
        return (self.raidMessages[raidId][0], raidMessageEmbed)

    def get_participant_number(self, raidId):
        result = 0
        for raider in self.raiders[raidId]:
            result += raider.party_size
        return result

    def get_raiders_gh(self, raidId):
        result = 'Here are the ' + str(self.get_participant_number(raidId)) + ' participants for raid #' + str(raidId) + ':'
        for raider in self.raiders[raidId]:
            result += '\n\t' + str(raider)
        return result

    #start_raid will be used when gymhuntr integration is down
    def start_raid(self, raidDetails):
        raidId = self.raidIdSeed + 1
        self.raidIdSeed += 1
        self.raids.add(str(raidId))
        self.raiders[str(raidId)] = set()
        self.details[str(raidId)] = raidDetails
        return str(raidId)

    def add_raider(self, raidId, raiderName):
        self.raiders[raidId].add(raiderName)

    def get_raiders(self, raidId):
        return self.raiders[raidId]

    def get_details(self, raidId):
        return self.raidMessages[raidId][1]

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

    def clear_raids(self):
        self.raids.clear()
        self.raiders.clear()
#
# End RaidMap class
#

class Participant:
    def __init__(self, username, party_size=1, start_time=None):
        self.username = username
        self.party_size = party_size
        self.start_time = start_time

    def __eq__(self, other):
        return self.username == other.username

    def __hash__(self):
        return hash(self.username)

    def __str__(self):
        result = self.username
        if self.party_size > 1:
            result += ' +' + str(self.party_size-1)
        if self.start_time is not None:
            result += ' at ' + self.start_time
        return result
#
# End Participant class
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
                if message.id != '341294312749006849':
                    await client.delete_message(message)
        else:
            if message.content.startswith('!rocraids') or message.content.startswith('!roc-raids'):
                em=discord.Embed(title="Commands", description="Here are the commands that the roc-raids bot recognizes.", color=0xf0040b)
                em.add_field(name="!join [raid-id] (party-size) (start-time)", value="Use this command to signal to others that you wish to attend the raid. The message with the specified raid-id will be updated to reflect your party's size. Can be used again to overwrite your previous party for raid.", inline=False)
                em.add_field(name="!leave [raid-id]", value="Can't make the raid you intended to join? Use this to take your party off the list.", inline=False)
                em.add_field(name="!raid [raid-id]", value="Receive a PM from the bot with the raid summary. Can also use !details [raid-id]", inline=False)
                em.add_field(name="!who [raid-id]", value="Receive a PM from the bot with the details of those that used the !join command.", inline=False)
                await client.send_message(message.channel, embed=em)

            elif message.content.startswith('!start '):
                raidDetails = message.content[7:]
                raidId = raids.start_raid(raidDetails)
                raids.add_raider(raidId, message.author.display_name)
                em = raids.get_detail_embed(raidId)
                await client.send_message(message.channel, embed=em)
                await client.delete_message(message)

            elif message.content.startswith('!who '):
                raidId = message.content[5:]
                msg = raids.get_raiders_gh(raidId)
                await client.send_message(message.author, msg)

            elif message.content.startswith('!join '):
                commandDetails = message.content[6:].split(' ')
                raidId = commandDetails[0]
                party_size = 1
                start_time = None
                if len(commandDetails) > 1:
                    party_size = commandDetails[1]
                if len(commandDetails) > 2:
                    start_time = ' '.join(str(x) for x in commandDetails[2:])
                msgData = raids.add_raider_gh(raidId, message.author.display_name, party_size, start_time)
                await client.edit_message(msgData[0], embed=msgData[1])

            elif message.content.startswith('!leave '):
                raidId = message.content[7:]
                msgData = raids.remove_raider_gh(raidId, message.author.display_name)
                await client.edit_message(msgData[0], embed=msgData[1])

            elif message.content.startswith('!details '):
                raidId = message.content[9:]
                em = raids.get_details(raidId)
                await client.send_message(message.author, embed=em)

            elif message.content.startswith('!raid '): # alias for !details
                raidId = message.content[6:]
                em = raids.get_details(raidId)
                await client.send_message(message.author, embed=em)

client.run(sys.argv[1])
