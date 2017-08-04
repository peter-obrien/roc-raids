import discord
import asyncio
import sys
import configparser
from datetime import datetime, timedelta
from pytz import timezone
import pytz
from raids import RaidMap, Raid
from errors import InputError

propFilename = 'properties.ini'
config = configparser.ConfigParser()
config.read(propFilename)
serverId = config['DEFAULT']['server_id']
rsvpChannelId = config['DEFAULT']['rsvp_channel_id']
botToken = config['DEFAULT']['bot_token']
if not serverId:
    print('server_id is not set. Please update ' + propFilename)
    quit()
if not rsvpChannelId:
    print('rsvp_channel_id is not set. Please update ' + propFilename)
    quit()
if not botToken:
    print('bot_token is not set. Please update ' + propFilename)
    quit()


client = discord.Client()
raids = RaidMap()
easternTz = timezone('US/Eastern')
utcTz = timezone('UTC')
timeFmt = '%m/%d %I:%M %p'
googleDirectionsUrlBase='https://www.google.com/maps/dir/Current+Location/'
embedColor = 0x408fd0

helpMessage=discord.Embed(title="Commands", description="Here are the commands that the roc-raids bot recognizes.", color=0xf0040b)
helpMessage.add_field(name="!join [raid-id] (party-size) (start-time)", value="Use this command to signal to others that you wish to attend the raid. The message with the specified raid-id will be updated to reflect your party's size. Can be used again to overwrite your previous party for the raid.", inline=False)
helpMessage.add_field(name="!leave [raid-id]", value="Can't make the raid you intended to join? Use this to take your party off the list.", inline=False)
helpMessage.add_field(name="!raid [raid-id]", value="Receive a PM from the bot with the raid summary. This contains the gym name, pokemon, raid end time and Google Maps location. Can also use !details [raid-id]", inline=False)
helpMessage.add_field(name="!who [raid-id]", value="Receive a PM from the bot with the details of who is attending the raid.", inline=False)

@client.event
async def on_ready():
    global discordServer
    global rsvpChannel
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

    discordServer = client.get_server(serverId)
    if discordServer is None:
        print('Could not obtain server: [{}]'.format(serverId))
        quit()

    rsvpChannel = discordServer.get_channel(rsvpChannelId)
    if rsvpChannel is None:
        print('Could not location RSVP channel: [{}]'.format(rsvpChannelId))
        quit(1)

@client.event
async def on_message(message):

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

            raid = raids.create_raid(pokemon, gymName, easternEndTime)

            if raid.id is None:
                raid.id = raids.generate_raid_id()
                raids.store_raid(raid)

                desc = gymName + '\n' + '*Ends: ' + easternEndTime.strftime(timeFmt) + '*'

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
        # Covert the message to lowercase to make the commands case-insensitive.
        lowercaseMessge = message.content.lower()

        if lowercaseMessge.startswith('!who '):
            raidId = message.content[5:]
            try:
                raid = raids.get_raid(raidId)
                msg = raid.get_raiders()
                await client.send_message(message.author, msg)
            except InputError as err:
                await client.send_message(message.author, err.message)
            finally:
                if not message.channel.is_private:
                    await client.delete_message(message)

        elif lowercaseMessge.startswith('!join '):
            commandDetails = message.content[6:].split(' ')
            raidId = commandDetails[0]
            party_size = '1'
            start_time = None
            if len(commandDetails) > 1:
                party_size = commandDetails[1]
            if len(commandDetails) > 2:
                start_time = ' '.join(str(x) for x in commandDetails[2:])
            try:
                raid = raids.get_raid(raidId)
                displayMsg = raid.add_raider(message.author.display_name, party_size, start_time)
                for msg in raid.messages:
                    await client.edit_message(msg, embed=raid.embed)
                if not message.channel.is_private:
                    await client.send_message(rsvpChannel, displayMsg)
                    await client.delete_message(message)
            except InputError as err:
                await client.send_message(message.author, err.message)
                if not message.channel.is_private:
                    await client.delete_message(message)

        elif lowercaseMessge.startswith('!leave '):
            raidId = message.content[7:]
            try:
                raid = raids.get_raid(raidId)
                displayMsg = raid.remove_raider(message.author.display_name)
                if displayMsg is not None:
                    for msg in raid.messages:
                        await client.edit_message(msg, embed=raid.embed)
                if not message.channel.is_private:
                    await client.send_message(rsvpChannel, displayMsg)
                    await client.delete_message(message)
            except InputError as err:
                await client.send_message(message.author, err.message)
                if not message.channel.is_private:
                    await client.delete_message(message)

        elif lowercaseMessge.startswith('!details '):
            raidId = message.content[9:]
            try:
                raid = raids.get_raid(raidId)
                await client.send_message(message.author, embed=raid.embed)
            except InputError as err:
                await client.send_message(message.author, err.message)
            finally:
                if not message.channel.is_private:
                    await client.delete_message(message)

        elif lowercaseMessge.startswith('!raid '): # alias for !details
            raidId = message.content[6:]
            try:
                raid = raids.get_raid(raidId)
                await client.send_message(message.author, embed=raid.embed)
            except InputError as err:
                await client.send_message(message.author, err.message)
            finally:
                if not message.channel.is_private:
                    await client.delete_message(message)
        elif lowercaseMessge.startswith('!'):
            await client.send_message(message.author, embed=helpMessage)
            if not message.channel.is_private:
                await client.delete_message(message)
        elif message.channel == rsvpChannel:
            # Only bot commands can be used in the RSVP channel.
            if not message.author.bot:
                await client.send_message(message.author, 'Only bot commands may be used in the RSVP channel.')
                await client.delete_message(message)

async def background_cleanup():
    await client.wait_until_ready()
    while not client.is_closed:
        # Delete expired raids
        expiredRaids = []
        currentTime = datetime.now(easternTz)
        for raid in raids.raids.values():
            if currentTime > raid.end:
                expiredRaids.append(raid)
        for raid in expiredRaids:
            for message in raid.messages:
                await client.delete_message(message)
            raids.remove_raid(raid)

        await asyncio.sleep(60) # task runs every 60 seconds

client.loop.create_task(background_cleanup())

client.run(botToken)
