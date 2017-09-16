import discord
import pytz
from datetime import timedelta
from decimal import Decimal
from django.utils.timezone import make_aware

from orm.models import RaidMessage


async def process_raid(bot, message):
    # Only attempt to process messages with an embed
    if len(message.embeds) == 0:
        return

    the_embed = message.embeds[0]

    body = the_embed['description'].split('}{')
    attributes = dict()
    for token in body:
        key_and_value = token.split('::')
        attributes[key_and_value[0].upper()] = key_and_value[1]

    # Determine if this is a raid egg or hatched raid
    message_is_egg = attributes['ISEGG'] == 'true'
    raid_level = attributes['RAIDLEVEL']
    if raid_level.isdigit():
        raid_level = int(raid_level)
    gym_name = attributes['GYMNAME']

    # Determine when the raid expires
    time_remaining_tokens = attributes['TIMELEFT'].split(' ')
    seconds_to_end = 0
    for token in time_remaining_tokens:
        if token.endswith('h'):
            seconds_to_end += int(token.rstrip('h')) * 60 * 60
        elif token.endswith('m'):
            seconds_to_end += int(token.rstrip('m')) * 60
        elif token.endswith('s'):
            seconds_to_end += int(token.rstrip('s'))
    end_time = make_aware(message.timestamp, timezone=pytz.utc) + timedelta(seconds=seconds_to_end)
    end_time = end_time.replace(microsecond=0)

    if message_is_egg:
        pokemon = None
        pokemon_number = None
        quick_move = None
        charge_move = None
        # Get the time when the raid egg hatches
        hatch_time_tokens = attributes['EGGTIMELEFT'].split(' ')
        seconds_to_end = 0
        for token in hatch_time_tokens:
            if token.endswith('h'):
                seconds_to_end += int(token.rstrip('h')) * 60 * 60
            elif token.endswith('m'):
                seconds_to_end += int(token.rstrip('m')) * 60
            elif token.endswith('s'):
                seconds_to_end += int(token.rstrip('s'))
        hatch_time = make_aware(message.timestamp, timezone=pytz.utc) + timedelta(seconds=seconds_to_end)
        hatch_time = hatch_time.replace(microsecond=0)
    else:
        pokemon = attributes['POKEMON']
        pokemon_number = attributes['POKEMON#']
        quick_move = attributes['QUICKMOVE']
        charge_move = attributes['CHARGEMOVE']
        hatch_time = None

    # Get the coordinate of the gym so we can determine which zone(s) it belongs to
    coord_tokens = the_embed['url'].split('=')[1].split(',')
    latitude = Decimal(coord_tokens[0])
    longitude = Decimal(coord_tokens[1])

    raid = bot.raids.create_raid(pokemon, pokemon_number, raid_level, gym_name, end_time, latitude, longitude,
                                 hatch_time)

    if raid.id is None or (raid.is_egg and not message_is_egg):

        # Build the jsonb field contents
        data = dict()

        if charge_move is not None:
            data['charge_move'] = charge_move
        if quick_move is not None:
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
            bot.raids.track_raid(raid)
        else:
            raid.pokemon_name = pokemon
            raid.pokemon_number = pokemon_number
            raid.expiration = end_time
            raid.save()

        if raid.is_egg:
            result = await bot.raids.build_egg_embed(raid)
        else:
            result = await bot.raids.build_raid_embed(raid)

        raid.embed = result

        if raid_was_egg:
            # If transitioning from a raid egg to a raid pokemon, delete all the previous egg messages.
            for m in raid.messages:
                try:
                    await m.delete()
                except discord.NotFound:
                    pass
            raid.messages = []

            if len(raid.participants) > 0:
                bot.raids.update_embed_participants(raid)

            # Send the new embed to the private channel
            if raid.private_channel is not None:
                private_raid_card = await raid.private_discord_channel.send(embed=raid.embed)
                raid.messages.append(private_raid_card)

    # Send the raids to any compatible raid zones.
    objects_to_save = await bot.zones.send_to_raid_zones(raid)

    RaidMessage.objects.bulk_create(objects_to_save)
