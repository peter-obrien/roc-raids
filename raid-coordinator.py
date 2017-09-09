import os, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

import discord
import asyncio
import configparser
from django.utils.timezone import make_aware, localtime
from datetime import datetime, timedelta
from decimal import *
from pytz import timezone
from django.db import transaction
from orm.models import RaidMessage, BotOnlyChannel
from raids import RaidManager, RaidZoneManager
from errors import InputError

propFilename = 'properties.ini'
config = configparser.ConfigParser()
config.read(propFilename)
serverId = config['DEFAULT']['server_id']
rsvpChannelId = config['DEFAULT']['rsvp_channel_id']
botToken = config['DEFAULT']['bot_token']
raidSourceChannelId = config['DEFAULT']['raid_src_channel_id']
raidDestChannelId = config['DEFAULT']['raid_dest_channel_id']
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
raids = RaidManager()
raid_zones = RaidZoneManager()
easternTz = timezone('US/Eastern')
utcTz = timezone('UTC')
reset_date_time = datetime.now(easternTz).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=24)
googleDirectionsUrlBase = 'https://www.google.com/maps/?daddr='
private_channel_no_access = discord.PermissionOverwrite(read_messages=False)
private_channel_access = discord.PermissionOverwrite(read_messages=True, mention_everyone=True)

helpMessage = discord.Embed(title="Commands", description="Here are the commands that the roc-raids bot recognizes.",
                            color=0xf0040b)
helpMessage.add_field(name="!join [raid id] (party size) (notes/start time)",
                      value="Use this command to signal to others that you wish to attend the raid. The message with the specified raid id will be updated to reflect your party's size. Can be used again to overwrite your previous party for the raid.",
                      inline=False)
helpMessage.add_field(name="!leave [raid id]",
                      value="Can't make the raid you intended to join? Use this to take your party off the list.",
                      inline=False)
helpMessage.add_field(name="!raid [raid id]",
                      value="Receive a PM from the bot with the raid summary. This contains the gym name, pokemon, raid end time and Google Maps location. Can also use !details [raid id]",
                      inline=False)
helpMessage.add_field(name="!who [raid id]",
                      value="Receive a PM from the bot with the details of who is attending the raid along with their party size and notes.",
                      inline=False)

channelConfigMessage = discord.Embed(title="Channel Config Commands",
                                     description="Here are the available commands to configure channels.",
                                     color=0xf0040b)
channelConfigMessage.add_field(name="!setup latitude, longitude",
                               value="Creates a raid zone with radius 5km. If used again replaces the coordinates.",
                               inline=False)
channelConfigMessage.add_field(name="!radius xxx.x",
                               value="Changes the raid zone radius.",
                               inline=False)
channelConfigMessage.add_field(name="!filter pokemon_numbers",
                               value="Allows for a comma separated list of pokemon numbers to enable filtering. E.g. `!filter 144,145,146`. Use `0` to clear the filter.",
                               inline=False)
channelConfigMessage.add_field(name="!raids [on/off]",
                               value="Toggles if this raid zone is active or not.",
                               inline=False)
channelConfigMessage.add_field(name="!info",
                               value="Displays the configuration for the channel.",
                               inline=False)
channelConfigMessage.add_field(name="!botonly [on/off]",
                               value="Toggles if this channel can only allow bot commands.",
                               inline=False)


@client.event
async def on_ready():
    global discordServer
    global rsvpChannel
    global botOnlyChannels
    global raidInputChannel
    global raidDestChannel
    global reset_date_time

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
        print('Could not locate Raid source channel: [{}]'.format(raidSourceChannelId))
        quit(1)

    raidDestChannel = discordServer.get_channel(raidDestChannelId)
    if raidDestChannel is None:
        print('Could not locate Raid destination channel: [{}]'.format(raidDestChannelId))
        quit(1)

    await raid_zones.load_from_database(discordServer)

    botOnlyChannels = []
    for boc in BotOnlyChannel.objects.all():
        channel = discordServer.get_channel(boc.channel)
        if channel is not None:
            botOnlyChannels.append(channel)

    await raids.load_from_database(client, discordServer)

    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')


@client.event
async def on_message(message):
    if message.content.startswith('!go') and test_message_id is not None:
        message = await client.get_message(message.channel, test_message_id)

    if message.author.name == 'GymHuntrBot':
        if len(message.embeds) > 0:
            the_embed = message.embeds[0]
            raid_level = int(the_embed['title'].split(' ')[1])
            gym_location = the_embed['url'].split('#')[1]
            google_maps_url = googleDirectionsUrlBase + gym_location
            coord_tokens = gym_location.split(',')
            latitude = Decimal(coord_tokens[0])
            longitude = Decimal(coord_tokens[1])

            desc_tokens = the_embed['description'].split('\n')
            gym_name = desc_tokens[0].strip('*').rstrip('.')
            pokemon_name = desc_tokens[1]

            time_tokens = desc_tokens[3].split(' ')
            seconds_to_end = int(time_tokens[6]) + (60 * int(time_tokens[4])) + (60 * 60 * int(time_tokens[2]))
            end_time = message.timestamp + timedelta(seconds=seconds_to_end)
            end_time = end_time.replace(second=0, microsecond=0, tzinfo=utcTz)

            raid = raids.create_raid(pokemon_name, 0, raid_level, gym_name, end_time, latitude, longitude)

            if raid.id is None:
                data = dict()

                data['url'] = google_maps_url

                thumbnail = dict()
                thumbnail_content = the_embed['thumbnail']
                thumbnail['url'] = thumbnail_content['url']
                thumbnail['height'] = thumbnail_content['height']
                thumbnail['width'] = thumbnail_content['width']
                thumbnail['proxy_url'] = thumbnail_content['proxy_url']
                data['thumbnail'] = thumbnail

                raid.data = data

                raids.track_raid(raid)

                result = await raids.build_raid_embed(raid)

                raids.embed_map[raid.display_id] = result

            raid_embed = raids.embed_map[raid.display_id]
            raid_message = await client.send_message(raidDestChannel, embed=raid_embed)
            objects_to_save = []
            objects_to_save.append(RaidMessage(raid=raid, channel=raid_message.channel.id, message=raid_message.id))
            raids.message_map[raid.display_id].append(raid_message)

            # Send the raids to any compatible raid zones.
            zone_messages = await send_to_raid_zones(raid, raid_embed)
            objects_to_save.extend(zone_messages)

            RaidMessage.objects.bulk_create(objects_to_save)

            if message.id != test_message_id:
                try:
                    await client.delete_message(message)
                except discord.errors.NotFound as e:
                    pass
    elif message.channel == raidInputChannel:
        if len(message.embeds) > 0:
            the_embed = message.embeds[0]

            body = the_embed['description'].split('}{')
            attributes = dict()
            for token in body:
                keyAndValue = token.split('::')
                attributes[keyAndValue[0].upper()] = keyAndValue[1]

            # Determine if this is a raid egg or hatched raid
            message_is_egg = attributes['ISEGG'] == 'true'
            raid_level = attributes['RAIDLEVEL']
            if raid_level.isdigit():
                raid_level = int(raid_level)
            gym_name = attributes['GYMNAME']

            if message_is_egg:
                pokemon = None
                pokemon_number = None
                quick_move = None
                charge_move = None
                end_time_tokens = attributes['BEGINTIMERAID'].split(':')
            else:
                pokemon = attributes['POKEMON']
                pokemon_number = attributes['POKEMON#']
                quick_move = attributes['QUICKMOVE']
                charge_move = attributes['CHARGEMOVE']
                end_time_tokens = attributes['TIME'].split(':')

            end_time = make_aware(message.timestamp).replace(hour=int(end_time_tokens[0]),
                                                             minute=int(end_time_tokens[1]),
                                                             second=0,
                                                             microsecond=0)

            # Get the coordinate of the gym so we can determine which zone(s) it belongs to
            coord_tokens = the_embed['url'].split('=')[1].split(',')
            latitude = Decimal(coord_tokens[0])
            longitude = Decimal(coord_tokens[1])

            raid = raids.create_raid(pokemon, pokemon_number, raid_level, gym_name, end_time, latitude, longitude)

            if raid.id is None or (raid.is_egg and not message_is_egg):

                # Build the jsonb field contents
                data = dict()

                if not charge_move is None:
                    data['charge_move'] = charge_move
                if not quick_move is None:
                    data['quick_move'] = quick_move
                data['url'] = the_embed['url']

                image = dict()
                image_content = the_embed['image']
                image['url'] = image_content['url']
                image['height'] = image_content['height']
                image['width'] = image_content['width']
                image['proxy_url'] = image_content['proxy_url']
                data['image'] = image

                thumbnail = dict()
                thumbnail_content = the_embed['thumbnail']
                thumbnail['url'] = thumbnail_content['url']
                thumbnail['height'] = thumbnail_content['height']
                thumbnail['width'] = thumbnail_content['width']
                thumbnail['proxy_url'] = thumbnail_content['proxy_url']
                data['thumbnail'] = thumbnail

                raid.data = data

                raid_was_egg = raid.id is not None and raid.is_egg and not message_is_egg
                raid.is_egg = message_is_egg

                if raid.id is None:
                    raids.track_raid(raid)
                else:
                    raid.pokemon_name = pokemon
                    raid.pokemon_number = pokemon_number
                    raid.expiration = end_time
                    raid.save()

                if raid.is_egg:
                    result = await raids.build_egg_embed(raid)
                else:
                    result = await raids.build_raid_embed(raid)


                raids.embed_map[raid.display_id] = result

                if raid_was_egg:
                    # If transitioning from a raid egg to a raid pokemon, delete all the previous egg messages.
                    for m in raids.message_map[raid.display_id]:
                        try:
                            await client.delete_message(m)
                        except Exception:
                            pass
                    raids.message_map[raid.display_id] = []

                    raids.update_embed_participants(raid)

                    # Send the new embed to the private channel
                    if raid.private_channel is not None:
                        private_raid_card = await client.send_message(raids.channel_map[raid.display_id], embed=raids.embed_map[raid.display_id])
                        raids.message_map[raid.display_id].append(private_raid_card)

            raid_embed = raids.embed_map[raid.display_id]
            raid_message = await client.send_message(raidDestChannel, embed=raid_embed)
            objects_to_save = []
            objects_to_save.append(RaidMessage(raid=raid, channel=raid_message.channel.id, message=raid_message.id))
            raids.message_map[raid.display_id].append(raid_message)

            # Send the raids to any compatible raid zones.
            zone_messages = await send_to_raid_zones(raid, raid_embed)
            objects_to_save.extend(zone_messages)

            RaidMessage.objects.bulk_create(objects_to_save)
    else:
        # Covert the message to lowercase to make the commands case-insensitive.
        lowercase_message = message.content.lower()

        # Ignore bots (including self)
        if message.author.bot:
            return

        # Used for channel configuration commands
        if isinstance(message.author, discord.member.Member):
            can_manage_channels = message.channel.permissions_for(message.author).manage_channels
        else:
            can_manage_channels = False

        if lowercase_message.startswith('!who '):
            user_raid_id = message.content[5:]
            try:
                raid = raids.get_raid(user_raid_id)
                msg = raids.get_participant_printout(raid)
                await client.send_message(message.author, msg)
            except InputError as err:
                await client.send_message(message.author, err.message)
            finally:
                if not message.channel.is_private:
                    try:
                        await client.delete_message(message)
                    except discord.errors.NotFound:
                        pass
        elif lowercase_message.startswith('!join '):
            command_details = message.content[6:].split(' ')
            user_raid_id = command_details[0]
            party_size = '1'
            notes = None
            author = message.author
            if len(command_details) > 1:
                party_size = command_details[1]
            if len(command_details) > 2:
                notes = ' '.join(str(x) for x in command_details[2:])
            try:
                # If the message is coming from PM we want to use the server's version of the user.
                if message.channel.is_private:
                    author = discordServer.get_member(message.author.id)

                raid = raids.get_raid(user_raid_id)

                private_raid_channel = raids.channel_map.get(raid.display_id, None)
                if private_raid_channel is None:
                    private_raid_channel = await client.create_channel(discordServer,
                                                                       'raid-{}-chat'.format(raid.display_id),
                                                                       (discordServer.default_role, private_channel_no_access),
                                                                       (discordServer.me, private_channel_access))
                    raids.channel_map[raid.display_id] = private_raid_channel

                    # Send the raid card to the top of the channel.
                    private_raid_card = await client.send_message(private_raid_channel,
                                                                  embed=raids.embed_map[raid.display_id])
                    raids.message_map[raid.display_id].append(private_raid_card)

                    with transaction.atomic():
                        raid.private_channel = private_raid_channel.id
                        raid.save()
                        RaidMessage(raid=raid, channel=private_raid_channel.id, message=private_raid_card.id).save()

                # Add this user to the raid and update all the embeds for the raid.
                resultTuple = raids.add_participant(raid, author.id, author.display_name, party_size, notes)
                for msg in raids.message_map[raid.display_id]:
                    await client.edit_message(msg, embed=raids.embed_map[raid.display_id])

                # Add the user to the private channel for the raid
                await client.edit_channel_permissions(raids.channel_map[raid.display_id], author, private_channel_access)
                await client.send_message(raids.channel_map[raid.display_id],
                                          '{}{}'.format(author.mention, resultTuple[0].details()))

                # Send message to the RSVP channel
                if not message.channel.is_private:
                    await client.send_message(rsvpChannel, resultTuple[1])
                    try:
                        await client.delete_message(message)
                    except discord.errors.NotFound:
                        pass
            except InputError as err:
                await client.send_message(author, err.message)
                if not message.channel.is_private:
                    try:
                        await client.delete_message(message)
                    except discord.errors.NotFound:
                        pass
        elif lowercase_message.startswith('!leave '):
            user_raid_id = message.content[7:]
            author = message.author
            try:
                # If the message is coming from PM we want to use the server's version of the user.
                if message.channel.is_private:
                    author = discordServer.get_member(message.author.id)

                raid = raids.get_raid(user_raid_id)
                displayMsg = raids.remove_participant(raid, author.id, author.display_name)

                if displayMsg is not None:
                    # Remove the user to the private channel for the raid
                    await client.edit_channel_permissions(raids.channel_map[raid.display_id], author, private_channel_no_access)
                    await client.send_message(raids.channel_map[raid.display_id],
                                              '**{}** is no longer attending'.format(author.display_name))

                    for msg in raids.message_map[raid.display_id]:
                        await client.edit_message(msg, embed=raids.embed_map[raid.display_id])
                    if not message.channel.is_private:
                        await client.send_message(rsvpChannel, displayMsg)
                if not message.channel.is_private:
                    try:
                        await client.delete_message(message)
                    except discord.errors.NotFound:
                        pass
            except InputError as err:
                await client.send_message(author, err.message)
                if not message.channel.is_private:
                    try:
                        await client.delete_message(message)
                    except discord.errors.NotFound:
                        pass
        elif lowercase_message.startswith('!details '):
            user_raid_id = message.content[9:]
            try:
                raid = raids.get_raid(user_raid_id)
                await client.send_message(message.author, embed=raids.embed_map[raid.display_id])
            except InputError as err:
                await client.send_message(message.author, err.message)
            finally:
                if not message.channel.is_private:
                    try:
                        await client.delete_message(message)
                    except discord.errors.NotFound as e:
                        pass
        elif lowercase_message.startswith('!raid '):  # alias for !details
            user_raid_id = message.content[6:]
            try:
                raid = raids.get_raid(user_raid_id)
                await client.send_message(message.author, embed=raids.embed_map[raid.display_id])
            except InputError as err:
                await client.send_message(message.author, err.message)
            finally:
                if not message.channel.is_private:
                    try:
                        await client.delete_message(message)
                    except discord.errors.NotFound as e:
                        pass
        elif can_manage_channels and lowercase_message.startswith('!botonly ') and not message.channel.is_private:
            toggle_value = lowercase_message[9:]
            if toggle_value == 'on':
                if message.channel not in botOnlyChannels:
                    boc = BotOnlyChannel(channel=message.channel.id)
                    boc.save()
                    botOnlyChannels.append(message.channel)
                    await client.send_message(message.channel, 'Bot only commands enabled.')
            elif toggle_value == 'off':
                if message.channel in botOnlyChannels:
                    boc = BotOnlyChannel.objects.get(channel=message.channel.id)
                    boc.delete()
                    botOnlyChannels.remove(message.channel)
                    await client.send_message(message.channel, 'Bot only commands disabled.')
            else:
                await client.send_message(message.channel,
                                          'Command to change bot only status:\n\n`!botonly [on/off]`')
            await client.delete_message(message)
        elif can_manage_channels and lowercase_message.startswith('!setup '):
            coordinates = message.content[7:]
            if coordinates.find(',') != -1:
                try:
                    coord_tokens = coordinates.split(',')
                    latitude = Decimal(coord_tokens[0].strip())
                    longitude = Decimal(coord_tokens[1].strip())

                    if message.channel.id in raid_zones.zones:
                        rz = raid_zones.zones[message.channel.id]
                        rz.latitude = latitude
                        rz.longitude = longitude
                        rz.save()
                        await client.send_message(message.channel, 'Raid zone coordinates updated')
                    else:
                        rz = raid_zones.create_zone(message.channel.id, latitude, longitude)
                        rz.discord_destination = message.channel
                        await client.send_message(message.channel, 'Raid zone created')
                except Exception as e:
                    print(e)
                    await client.send_message(message.channel, embed=channelConfigMessage,
                                              content='There was an error handling your request.\n\n`{}`'.format(
                                                  message.content))
            else:
                await client.send_message(message.channel, content='Invalid command: `{}`'.format(message.content),
                                          embed=channelConfigMessage)
            await client.delete_message(message)
        elif can_manage_channels and lowercase_message.startswith('!radius '):
            user_radius = message.content[8:]
            try:
                radius = Decimal(user_radius)
                if message.channel.id in raid_zones.zones:
                    rz = raid_zones.zones[message.channel.id]
                    rz.radius = radius
                    rz.save()
                    await client.send_message(message.channel, 'Radius updated')
                else:
                    await client.send_message(message.channel,
                                              content='Setup has not been run for this channel.',
                                              embed=channelConfigMessage)
            except InvalidOperation:
                await client.send_message(message.channel, 'Invalid radius: {}'.format(user_radius))
                pass
            finally:
                await client.delete_message(message)
        elif can_manage_channels and lowercase_message.startswith('!filter '):
            user_pokemon_list = message.content[8:]
            try:
                if message.channel.id in raid_zones.zones:
                    rz = raid_zones.zones[message.channel.id]
                    new_pokemon_filter = []
                    if user_pokemon_list.find(',') == -1:
                        if '0' != user_pokemon_list:
                            new_pokemon_filter.append(int(user_pokemon_list))
                    else:
                        for pokemon_number in user_pokemon_list.split(','):
                            new_pokemon_filter.append(int(pokemon_number))
                    rz.filters['pokemon'].clear()
                    rz.filters['pokemon'] = new_pokemon_filter
                    rz.save()
                    await client.send_message(message.channel, 'Updated filter list')
                else:
                    await client.send_message(message.channel, embed=channelConfigMessage,
                                              content='Setup has not been run for this channel.')
            except Exception as e:
                print('Unable to process: {}'.format(message.content))
                print(e)
                await client.send_message(message.channel,
                                          'Unable to process filter. Please verify your input: {}'.format(
                                              user_pokemon_list))
                pass
            await client.delete_message(message)
        elif can_manage_channels and lowercase_message.startswith('!raids '):
            if message.channel.id in raid_zones.zones:
                rz = raid_zones.zones[message.channel.id]
                token = lowercase_message[7:]
                try:
                    if token == 'on':
                        rz.active = True
                        rz.save()
                        await client.send_message(message.channel, 'Raid messages enabled.')
                    elif token == 'off':
                        rz.active = False
                        rz.save()
                        await client.send_message(message.channel, 'Raid messages disabled.')
                    else:
                        await client.send_message(message.channel, embed=channelConfigMessage,
                                                  content='Unknown command: `{}`'.format(message.content))
                finally:
                    await client.delete_message(message)
            else:
                await client.send_message(message.channel, embed=channelConfigMessage,
                                          content='Setup has not been run for this channel.')
        elif can_manage_channels and lowercase_message == '!info':
            if message.channel.id in raid_zones.zones:
                rz = raid_zones.zones[message.channel.id]
                output = 'Here is the raid zone configuration for this channel:\n\nStatus: `{}`\nCoordinates: `{}, {}`\nRadius: `{}`\nPokemon: `{}`'.format(
                    rz.status, rz.latitude, rz.longitude, rz.radius, rz.filters['pokemon'])
                await client.send_message(message.channel, output)
            else:
                await client.send_message(message.channel, 'This channel is not configured as a raid zone.')
            await client.delete_message(message)
        elif lowercase_message.startswith('!'):
            await client.send_message(message.author, embed=helpMessage)
            if not message.channel.is_private:
                try:
                    await client.delete_message(message)
                except discord.errors.NotFound:
                    pass
        elif message.channel in botOnlyChannels:
            if not message.author.bot:
                await client.send_message(message.author, 'Only bot commands may be used in this channel.')
                try:
                    await client.delete_message(message)
                except discord.errors.NotFound as e:
                    pass


async def send_to_raid_zones(raid, embed):
    objects_to_save = []
    for rz in raid_zones.zones.values():
        if rz.filter(raid):
            try:
                raid_message = await client.send_message(rz.discord_destination, embed=embed)
                if not isinstance(rz.discord_destination, discord.member.Member):
                    objects_to_save.append(
                        RaidMessage(raid=raid, channel=raid_message.channel.id, message=raid_message.id))
                    raids.message_map[raid.display_id].append(raid_message)
            except discord.errors.Forbidden:
                print('Unable to send raid to channel {}. The bot does not have permission.'.format(
                    rz.discord_destination.name))
                pass
    return objects_to_save


@client.event
async def on_channel_delete(channel):
    # If the channel was a raid zone, delete it.
    if channel.id in raid_zones.zones:
        raid_zones.zones[channel.id].delete()


async def background_cleanup():
    global reset_date_time
    await client.wait_until_ready()
    while not client.is_closed:
        # Delete expired raids
        expired_raids = []
        currentTime = datetime.now(easternTz)
        # Find expired raids
        with transaction.atomic():
            for raid in raids.raid_map.values():
                if not raid.is_egg and currentTime > raid.expiration:
                    raid.active = False
                    raid.save()
                    expired_raids.append(raid)
        # Process expired raids
        for raid in expired_raids:
            for message in raids.message_map[raid.display_id]:
                try:
                    await client.delete_message(message)
                except discord.errors.NotFound:
                    pass
            if raid.display_id in raids.channel_map and raids.channel_map[raid.display_id] is not None:
                try:
                    await client.delete_channel(raids.channel_map[raid.display_id])
                except discord.errors.NotFound:
                    pass
            raids.remove_raid(raid)

        # Check to see if the raid manager needs to be reset
        if datetime.now(easternTz) > reset_date_time:
            # Get the next reset time.
            reset_date_time = datetime.now(easternTz).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
                hours=24)
            raids.reset()

        await asyncio.sleep(60)  # task runs every 60 seconds


client.loop.create_task(background_cleanup())

client.run(botToken)
