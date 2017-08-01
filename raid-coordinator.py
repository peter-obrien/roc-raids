import discord
import asyncio
import sys
from datetime import datetime, timedelta
from pytz import timezone
import pytz
from raids import RaidMap, Raid
from errors import InputError

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

                raid = raids.create_raid(pokemon, gymName, easternEndTime)

                if raid.id is None:
                    raid.id = raids.generate_raid_id()
                    raids.store_raid(raid)

                    result = discord.Embed(title=pokemon + ': Raid #' + str(raid.id), url=gmapUrl, description=desc, colour=embedColor)

                    thumbnailContent = message.embeds[0]['thumbnail']
                    result.set_thumbnail(url=thumbnailContent['url'])
                    result.thumbnail.height=thumbnailContent['height']
                    result.thumbnail.width=thumbnailContent['width']
                    result.thumbnail.proxy_url=thumbnailContent['proxy_url']

                    raid.embed = result

                raidMessage = await client.send_message(message.channel, embed=raid.embed)
                raid.add_message(raidMessage)
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

            elif message.content.startswith('!who '):
                raidId = message.content[5:]
                try:
                    raid = raids.get_raid(raidId)
                    msg = raid.get_raiders()
                    await client.send_message(message.author, msg)
                except InputError as err:
                    await client.send_message(message.author, err.message)
                finally:
                    await client.delete_message(message)

            elif message.content.startswith('!join '):
                commandDetails = message.content[6:].split(' ')
                raidId = commandDetails[0]
                party_size = 1
                start_time = None
                if len(commandDetails) > 1:
                    party_size = commandDetails[1]
                if len(commandDetails) > 2:
                    start_time = ' '.join(str(x) for x in commandDetails[2:])
                try:
                    raid = raids.get_raid(raidId)
                    raid.add_raider(message.author.display_name, party_size, start_time)
                    for msg in raid.messages:
                        await client.edit_message(msg, embed=raid.embed)
                except InputError as err:
                    await client.send_message(message.author, err.message)
                    await client.delete_message(message)

            elif message.content.startswith('!leave '):
                raidId = message.content[7:]
                try:
                    raid = raids.get_raid(raidId)
                    raid.remove_raider(message.author.display_name)
                    for msg in raid.messages:
                        await client.edit_message(msg, embed=raid.embed)
                except InputError as err:
                    await client.send_message(message.author, err.message)
                    await client.delete_message(message)

            elif message.content.startswith('!details '):
                raidId = message.content[9:]
                try:
                    raid = raids.get_raid(raidId)
                    await client.send_message(message.author, embed=raid.embed)
                except InputError as err:
                    await client.send_message(message.author, err.message)
                finally:
                    await client.delete_message(message)

            elif message.content.startswith('!raid '): # alias for !details
                raidId = message.content[6:]
                try:
                    raid = raids.get_raid(raidId)
                    await client.send_message(message.author, embed=raid.embed)
                except InputError as err:
                    await client.send_message(message.author, err.message)
                finally:
                    await client.delete_message(message)

client.run(sys.argv[1])
