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
        raid_level = int(the_embed.title.split(' ')[1])
        gym_location = the_embed.url.split('#')[1]
        google_maps_url = google_dir_url_base + gym_location
        coord_tokens = gym_location.split(',')
        latitude = Decimal(coord_tokens[0])
        longitude = Decimal(coord_tokens[1])

        desc_tokens = the_embed.description.split('\n')
        gym_name = desc_tokens[0].strip('*').rstrip('.')
        pokemon_name = desc_tokens[1]

        time_tokens = desc_tokens[3].split(' ')
        seconds_to_end = int(time_tokens[6]) + (60 * int(time_tokens[4])) + (60 * 60 * int(time_tokens[2]))
        end_time = make_aware(message.created_at, timezone=pytz.utc) + timedelta(seconds=seconds_to_end)
        end_time = end_time.replace(microsecond=0)

        raid = bot.raids.create_raid(pokemon_name, 0, raid_level, gym_name, end_time, latitude, longitude,
                                     hatch_time=None)

        if raid.id is None:
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

            bot.raids.track_raid(raid)

            result = await bot.raids.build_raid_embed(raid)

            raid.embed = result

        raid_message = await message.channel.send(embed=raid.embed)
        objects_to_save = [RaidMessage(raid=raid, channel=raid_message.channel.id, message=raid_message.id)]
        raid.messages.append(raid_message)

        # Send the raids to any compatible raid zones.
        zone_messages = await bot.zones.send_to_raid_zones(raid)
        objects_to_save.extend(zone_messages)

        RaidMessage.objects.bulk_create(objects_to_save)
