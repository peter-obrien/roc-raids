import discord
import pytz
from datetime import timedelta
from decimal import Decimal
from django.utils.timezone import make_aware

from orm.models import RaidMessage

google_dir_url_base = 'https://www.google.com/maps/?daddr='


async def process_raid(bot, message):
    if len(message.embeds) > 0:
        the_embed = message.embeds[0]

        message_is_egg = the_embed.title.endswith('starting soon!')

        raid_level = int(the_embed.title.split(' ')[1])

        gym_location = the_embed.url.split('#')[1]
        google_maps_url = google_dir_url_base + gym_location
        coord_tokens = gym_location.split(',')
        latitude = Decimal(coord_tokens[0])
        longitude = Decimal(coord_tokens[1])

        desc_tokens = the_embed.description.split('\n')
        gym_name = desc_tokens[0].strip('*').rstrip('.')

        if message_is_egg:
            pokemon = None
            time_tokens = desc_tokens[1].split(' ')
        else:
            pokemon = desc_tokens[1]
            time_tokens = desc_tokens[3].split(' ')

        seconds_to_end = int(time_tokens[6]) + (60 * int(time_tokens[4])) + (60 * 60 * int(time_tokens[2]))
        end_time = make_aware(message.created_at, timezone=pytz.utc) + timedelta(seconds=seconds_to_end)
        end_time = end_time.replace(microsecond=0)

        if message_is_egg:
            hatch_time = end_time
            end_time = end_time + timedelta(seconds=3600)
        else:
            hatch_time = None

        raid = bot.raids.create_raid(pokemon, 0, raid_level, gym_name, end_time, latitude, longitude,
                                     hatch_time=hatch_time)

        if raid.id is None or (raid.is_egg and not message_is_egg):
            data = dict()

            data['url'] = google_maps_url

            thumbnail = dict()
            thumbnail_content = the_embed.thumbnail
            thumbnail['url'] = thumbnail_content.url
            thumbnail['height'] = thumbnail_content.height
            thumbnail['width'] = thumbnail_content.width
            thumbnail['proxy_url'] = thumbnail_content.proxy_url
            data['thumbnail'] = thumbnail

            raid.data = data

            raid_was_egg = raid.id is not None and raid.is_egg and not message_is_egg
            raid.is_egg = message_is_egg

            if raid.id is None:
                bot.raids.track_raid(raid)
            else:
                raid.pokemon_name = pokemon
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

        raid_message = await message.channel.send(embed=raid.embed)
        objects_to_save = [RaidMessage(raid=raid, channel=raid_message.channel.id, message=raid_message.id)]
        raid.messages.append(raid_message)

        # Send the raids to any compatible raid zones.
        zone_messages = await bot.zones.send_to_raid_zones(raid, bot)
        objects_to_save.extend(zone_messages)

        RaidMessage.objects.bulk_create(objects_to_save)
        
        # Delete the source gymhuntr raid message
        await message.delete()

