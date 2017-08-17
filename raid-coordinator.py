import discord
import asyncio
import sys
import configparser
from datetime import datetime, timedelta
from pytz import timezone
import pytz
from raids import RaidMap, Raid, RaidZone
from errors import InputError

propFilename = 'properties.ini'
config = configparser.ConfigParser()
config.read(propFilename)
serverId = config['DEFAULT']['server_id']
rsvpChannelId = config['DEFAULT']['rsvp_channel_id']
botToken = config['DEFAULT']['bot_token']
botOnlyChannelIds = config['DEFAULT']['bot_only_channels']
raidSourceChannelId = config['DEFAULT']['raid_src_channel_id']
raidDestChannelId = config['DEFAULT']['raid_dest_channel_id']
zonesRaw = config['DEFAULT']['zones'].split(',')
if not serverId:
    print('server_id is not set. Please update ' + propFilename)
    quit()
if not rsvpChannelId:
    print('rsvp_channel_id is not set. Please update ' + propFilename)
    quit()
if not botToken:
    print('bot_token is not set. Please update ' + propFilename)
    quit()
if not raidSourceChannelId:
    print('raid_src_channel_id is not set. Please update ' + propFilename)
    quit()
if not raidDestChannelId:
    print('raid_dest_channel_id is not set. Please update ' + propFilename)
    quit()

try:
    test_message_id = config['DEFAULT']['test_message_id']
except Exception as e:
    test_message_id = None

client = discord.Client()
raids = RaidMap()
easternTz = timezone('US/Eastern')
utcTz = timezone('UTC')
timeFmt = '%m/%d %I:%M %p'
resetDateTime = datetime.now(easternTz).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=24)
print('next reset time = {}'.format(str(resetDateTime)))
googleDirectionsUrlBase='https://www.google.com/maps/dir/Current+Location/'
embedColor = 0x408fd0
not_read = discord.PermissionOverwrite(read_messages=False)
read = discord.PermissionOverwrite(read_messages=True)

helpMessage=discord.Embed(title="Commands", description="Here are the commands that the roc-raids bot recognizes.", color=0xf0040b)
helpMessage.add_field(name="!join [raid id] (party size) (notes/start time)", value="Use this command to signal to others that you wish to attend the raid. The message with the specified raid id will be updated to reflect your party's size. Can be used again to overwrite your previous party for the raid.", inline=False)
helpMessage.add_field(name="!leave [raid id]", value="Can't make the raid you intended to join? Use this to take your party off the list.", inline=False)
helpMessage.add_field(name="!raid [raid id]", value="Receive a PM from the bot with the raid summary. This contains the gym name, pokemon, raid end time and Google Maps location. Can also use !details [raid id]", inline=False)
helpMessage.add_field(name="!who [raid id]", value="Receive a PM from the bot with the details of who is attending the raid along with their party size and notes.", inline=False)

@client.event
async def on_ready():
    global discordServer
    global rsvpChannel
    global botOnlyChannels
    global raidInputChannel
    global raidDestChannel
    global raidZones
    global resetDateTime
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

    discordServer = client.get_server(serverId)
    if discordServer is None:
        print('Could not obtain server: [{}]'.format(serverId))
        quit(1)

    rsvpChannel = discordServer.get_channel(rsvpChannelId)
    if rsvpChannel is None:
        print('Could not locate RSVP channel: [{}]'.format(rsvpChannelId))
        quit(1)

    raidInputChannel = discordServer.get_channel(raidSourceChannelId)
    if raidInputChannel is None:
        print('Could not locate Raid srouce channel: [{}]'.format(raidSourceChannelId))
        quit(1)

    raidDestChannel = discordServer.get_channel(raidDestChannelId)
    if raidDestChannel is None:
        print('Could not locate Raid destination channel: [{}]'.format(raidDestChannelId))
        quit(1)

    try:
        raidZones = []
        for zoneData in zonesRaw:
            zoneTokens = zoneData.split('|')
            rz = RaidZone(discordServer.get_channel(zoneTokens[0].strip()), zoneTokens[1].strip(), zoneTokens[2].strip(), zoneTokens[3].strip())
            raidZones.append(rz)
            i = 4
            while i < len(zoneTokens):
                rz.targetPokemon.append(int(zoneTokens[i]))
                i += 1
    except Exception as e:
        print('Could not initialize raid zones. Please check the config.')
        quit(1)

    botOnlyChannels = []
    tokens = botOnlyChannelIds.split(',')
    for token in tokens:
        channel = discordServer.get_channel(token.strip())
        if channel is not None:
            botOnlyChannels.append(channel)

@client.event
async def on_message(message):

    if message.content.startswith('!go') and test_message_id is not None:
        message = await client.get_message(message.channel, test_message_id)

    if message.author.name == 'GymHuntrBot':
        if len(message.embeds) > 0:
            gymLocation = message.embeds[0]['url'].split('#')[1]
            gmapUrl = googleDirectionsUrlBase + gymLocation
            coordTokens = gymLocation.split(',')
            latitude = float(coordTokens[0])
            longitude = float(coordTokens[1])

            descTokens = message.embeds[0]['description'].split('\n')
            gymName = descTokens[0]
            pokemon = descTokens[1]

            timeTokens = descTokens[3].split(' ')
            secondsToEnd = int(timeTokens[6]) + (60 * int(timeTokens[4])) + (60 * 60 * int(timeTokens[2]))
            endTime = message.timestamp + timedelta(seconds=secondsToEnd)
            easternEndTime = endTime.replace(tzinfo=utcTz).astimezone(easternTz)

            raid = raids.create_raid(pokemon, gymName, easternEndTime, latitude, longitude)

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
                try:
                    await client.delete_message(message)
                except discord.errors.NotFound as e:
                    pass
    elif message.channel == raidInputChannel:
        if len(message.embeds) > 0:
            theEmbed = message.embeds[0]

            body = theEmbed['description'].split('}{')
            attributes = dict()
            for token in body:
                keyAndValue = token.split('::')
                attributes[keyAndValue[0].upper()] = keyAndValue[1]

            pokemon = attributes['POKEMON']
            pokemonNumber = attributes['POKEMON#']
            raidLevel = attributes['RAIDLEVEL']
            gymName = attributes['GYMNAME']
            endTimeTokens = attributes['TIME'].split(':')

            now = datetime.now(easternTz)
            endTime = now.replace(hour=int(endTimeTokens[0]), minute=int(endTimeTokens[1]), second=0)

            # Get the coordinate of the gym so we can determine which zone(s) it belongs to
            coordTokens = theEmbed['url'].split('=')[1].split(',')
            latitude = float(coordTokens[0])
            longitude = float(coordTokens[1])

            raid = raids.create_raid(pokemon, pokemonNumber, raidLevel, gymName, endTime, latitude, longitude)

            if raid.id is None:
                raid.id = raids.generate_raid_id()
                raids.store_raid(raid)

                desc = gymName + '\n' + '*Ends: ' + endTime.strftime(timeFmt) + '*'

                result = discord.Embed(title=pokemon + ': Raid #' + str(raid.id), url=theEmbed['url'], description=desc, colour=embedColor)

                imageContent = theEmbed['image']
                result.set_image(url=imageContent['url'])
                result.image.height=imageContent['height']
                result.image.width=imageContent['width']
                result.image.proxy_url=imageContent['proxy_url']

                thumbnailContent = theEmbed['thumbnail']
                result.set_thumbnail(url=thumbnailContent['url'])
                result.thumbnail.height=thumbnailContent['height']
                result.thumbnail.width=thumbnailContent['width']
                result.thumbnail.proxy_url=thumbnailContent['proxy_url']

                raid.embed = result

            raidMessage = await client.send_message(raidDestChannel, embed=raid.embed)
            raid.add_message(raidMessage)

            # Send the raids to any compatible raid zones.
            for rz in raidZones:
                if rz.isInRaidZone(raid) and rz.filterPokemon(raid.pokemonNumber):
                    raidMessage = await client.send_message(rz.channel, embed=raid.embed)
                    raid.add_message(raidMessage)
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
                    try:
                        await client.delete_message(message)
                    except discord.errors.NotFound as e:
                        pass

        elif lowercaseMessge.startswith('!join '):
            commandDetails = message.content[6:].split(' ')
            raidId = commandDetails[0]
            party_size = '1'
            notes = None
            if len(commandDetails) > 1:
                party_size = commandDetails[1]
            if len(commandDetails) > 2:
                notes = ' '.join(str(x) for x in commandDetails[2:])
            try:
                author = message.author
                # If the message is coming from PM we want to use the server's version of the user.
                if message.channel.is_private:
                    author = discordServer.get_member(message.author.id)

                raid = raids.get_raid(raidId)

                if raid.channel is None:
                    privateRaidChannel = await client.create_channel(discordServer, 'raid-{}-chat'.format(raid.id), (discordServer.default_role, not_read), (discordServer.me, read))
                    raid.channel = privateRaidChannel
                    # Send the raid card to the top of the channel.
                    privateChannelRaidMessage = await client.send_message(raid.channel, embed=raid.embed)
                    raid.add_message(privateChannelRaidMessage)

                # Add this user to the raid and update all the embeds for the raid.
                resultTuple = raid.add_raider(author.display_name, party_size, notes)
                for msg in raid.messages:
                    await client.edit_message(msg, embed=raid.embed)

                # Add the user to the private channel for the raid
                await client.edit_channel_permissions(raid.channel, author, read)
                await client.send_message(raid.channel, '{}{}'.format(author.mention, resultTuple[0].details()))

                # Send message to the RSVP channel
                if not message.channel.is_private:
                    await client.send_message(rsvpChannel, resultTuple[1])
                    try:
                        await client.delete_message(message)
                    except discord.errors.NotFound as e:
                        pass
            except InputError as err:
                await client.send_message(author, err.message)
                if not message.channel.is_private:
                    try:
                        await client.delete_message(message)
                    except discord.errors.NotFound as e:
                        pass

        elif lowercaseMessge.startswith('!leave '):
            raidId = message.content[7:]
            try:
                author = message.author
                # If the message is coming from PM we want to use the server's version of the user.
                if message.channel.is_private:
                    author = discordServer.get_member(message.author.id)

                raid = raids.get_raid(raidId)
                displayMsg = raid.remove_raider(author.display_name)


                if displayMsg is not None:
                    # Remove the user to the private channel for the raid
                    await client.edit_channel_permissions(raid.channel, author, not_read)
                    await client.send_message(raid.channel, '**{}** is no longer attending'.format(author.display_name))

                    for msg in raid.messages:
                        await client.edit_message(msg, embed=raid.embed)
                    if not message.channel.is_private:
                        await client.send_message(rsvpChannel, displayMsg)
                if not message.channel.is_private:
                    try:
                        await client.delete_message(message)
                    except discord.errors.NotFound as e:
                        pass
            except InputError as err:
                await client.send_message(author, err.message)
                if not message.channel.is_private:
                    try:
                        await client.delete_message(message)
                    except discord.errors.NotFound as e:
                        pass

        elif lowercaseMessge.startswith('!details '):
            raidId = message.content[9:]
            try:
                raid = raids.get_raid(raidId)
                await client.send_message(message.author, embed=raid.embed)
            except InputError as err:
                await client.send_message(message.author, err.message)
            finally:
                if not message.channel.is_private:
                    try:
                        await client.delete_message(message)
                    except discord.errors.NotFound as e:
                        pass

        elif lowercaseMessge.startswith('!raid '): # alias for !details
            raidId = message.content[6:]
            try:
                raid = raids.get_raid(raidId)
                await client.send_message(message.author, embed=raid.embed)
            except InputError as err:
                await client.send_message(message.author, err.message)
            finally:
                if not message.channel.is_private:
                    try:
                        await client.delete_message(message)
                    except discord.errors.NotFound as e:
                        pass
        elif lowercaseMessge.startswith('!'):
            await client.send_message(message.author, embed=helpMessage)
            if not message.channel.is_private:
                try:
                    await client.delete_message(message)
                except discord.errors.NotFound as e:
                    pass
        elif message.channel in botOnlyChannels:
            if not message.author.bot:
                await client.send_message(message.author, 'Only bot commands may be used in this channel.')
                try:
                    await client.delete_message(message)
                except discord.errors.NotFound as e:
                    pass

async def background_cleanup():
    global resetDateTime
    await client.wait_until_ready()
    while not client.is_closed:
        # Delete expired raids
        expiredRaids = []
        currentTime = datetime.now(easternTz)
        # Find expired raids
        for raid in raids.raids.values():
            if currentTime > raid.end:
                expiredRaids.append(raid)
        # Process expired raids
        for raid in expiredRaids:
            for message in raid.messages:
                try:
                    await client.delete_message(message)
                except discord.errors.NotFound as e:
                    pass
            if raid.channel is not None:
                try:
                    await client.delete_channel(raid.channel)
                except discord.errors.NotFound as e:
                    pass
            raids.remove_raid(raid)

        # Check to see if the raid counter needs to be reset
        if datetime.now(easternTz) > resetDateTime:
            # Get the next reset time.
            resetDateTime = datetime.now(easternTz).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=24)
            raids.clear_raids()

        await asyncio.sleep(60) # task runs every 60 seconds

client.loop.create_task(background_cleanup())

client.run(botToken)
