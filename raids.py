from collections import defaultdict
from datetime import timedelta

from discord.ext import commands
from orm.models import Raid, RaidParticipant, RaidMessage, RaidZone
import discord
from django.utils.timezone import localtime
from django.db.models import Max

time_format = '%m/%d %I:%M %p'
embed_color = 0x408fd0


class RaidManager:
    def __init__(self, raid_duration:45, ex_duration:45):
        self.logging_out = False
        self.hashed_active_raids = dict()
        self.raid_map = dict()
        self.raid_seed = 0
        last_raid_seed = Raid.objects.filter(active=True, is_exclusive=False).aggregate(Max('display_id')).get('display_id__max')
        if last_raid_seed is not None:
            self.raid_seed = last_raid_seed

        self.raid_duration = raid_duration
        self.ex_duration = ex_duration

        self.exclusive_hashed_raids = dict()
        self.exclusive_raid_map = dict()
        self.exclusive_raid_seed = 0

        self.message_to_raid = dict()
        self.private_channel_raids = dict()

        last_raid_seed = Raid.objects.filter(active=True, is_exclusive=True).aggregate(Max('display_id')).get('display_id__max')
        if last_raid_seed is not None:
            self.exclusive_raid_seed = last_raid_seed

    async def load_from_database(self, bot):

        # Ensure the collections are empty before loading data from the database
        self.hashed_active_raids = dict()
        self.raid_map = dict()
        self.exclusive_hashed_raids = dict()
        self.exclusive_raid_map = dict()

        for raid in Raid.objects.filter(active=True):
            if raid.is_exclusive:
                self.exclusive_hashed_raids[hash(raid)] = raid
                self.exclusive_raid_map[raid.display_id] = raid
            else:
                self.hashed_active_raids[hash(raid)] = raid
                self.raid_map[raid.display_id] = raid
            raid.private_discord_channel = bot.get_channel(raid.private_channel)

            if raid.is_egg:
                raid.embed = await self.build_egg_embed(raid)
            else:
                raid.embed = await self.build_raid_embed(raid)

            for participant in RaidParticipant.objects.filter(raid=raid, attending=True):
                raid.participants.add(participant)

            for rm in RaidMessage.objects.filter(raid=raid):
                try:
                    channel = bot.get_channel(rm.channel)
                    if channel is not None:
                        msg = await channel.fetch_message(rm.message)
                        raid.messages.append(msg)
                        self.message_to_raid[msg.id] = raid
                        if raid.private_discord_channel is not None and raid.private_discord_channel.id == channel.id:
                            self.private_channel_raids[msg.id] = raid
                    else:
                        print(f'Could not find channel raid message {rm.id}')
                except discord.errors.NotFound:
                    pass

    async def create_exclusive_raid(self, gym_name, expiration, latitude, longitude):
        self.exclusive_raid_seed += 1
        data = dict()
        data['url'] = f'http://maps.google.com/maps?q={latitude},{longitude}'
        thumbnail = dict()
        thumbnail['url'] = 'https://raw.githubusercontent.com/peter-obrien/organizer/develop/resources/images/ex_raid_pass.png'
        thumbnail['height'] = '128'
        thumbnail['width'] = '128'
        thumbnail['proxy_url'] = ''
        data['thumbnail'] = thumbnail
        raid = Raid(display_id=self.exclusive_raid_seed, gym_name=gym_name, raid_level=0, pokemon_number=0,
                    latitude=latitude, longitude=longitude, expiration=expiration, is_exclusive=True, data=data)
        self.exclusive_raid_map[raid.display_id] = raid
        self.exclusive_hashed_raids[hash(raid)] = raid
        raid.save()
        raid.embed = await self.build_raid_embed(raid)
        return raid

    async def create_manual_raid(self, user_id, is_egg, gym_name, expiration, latitude, longitude, raid_level=0,
                                 pokemon_name=None, is_mega=False):

        data = dict()
        data['url'] = f'http://maps.google.com/maps?q={latitude},{longitude}'

        hatch_time = None
        expiration_time = expiration
        is_mega = str(raid_level).lower() == 'mega'
        raid_level = 0 if is_mega else int(raid_level)
        if is_egg:
            hatch_time = expiration
            expiration_time = hatch_time + timedelta(minutes=self.raid_duration)

        raid = Raid(gym_name=gym_name, is_egg=is_egg, raid_level=raid_level, pokemon_number=0,
                    pokemon_name=pokemon_name, latitude=latitude, longitude=longitude,
                    hatch_time=hatch_time, expiration=expiration_time,
                    is_exclusive=False, data=data, reporting_user=user_id, is_mega=is_mega)

        return raid

    def create_raid(self, pokemon_name, pokemon_number, raid_level, gym_name, expiration, latitude, longitude,
                    hatch_time):
        raid_result = Raid(pokemon_name=pokemon_name, pokemon_number=pokemon_number, raid_level=raid_level,
                           gym_name=gym_name, expiration=expiration, latitude=latitude, longitude=longitude,
                           hatch_time=hatch_time)
        hash_val = hash(raid_result)
        if hash_val in self.hashed_active_raids:
            raid_result = self.hashed_active_raids[hash_val]
        return raid_result

    def track_raid(self, raid):
        self.raid_seed += 1
        raid.display_id = self.raid_seed
        if not self.logging_out:
            self.hashed_active_raids[hash(raid)] = raid
            self.raid_map[raid.display_id] = raid
        raid.save()
        return raid

    def remove_raid(self, raid):
        raid.embed = None
        raid.messages = None
        raid.participants = None
        raid.private_discord_channel = None
        if raid.is_exclusive:
            self.exclusive_hashed_raids.pop(hash(raid), None)
            self.exclusive_raid_map.pop(raid.display_id, None)
        elif not self.logging_out:
            self.hashed_active_raids.pop(hash(raid), None)
            self.raid_map.pop(raid.display_id, None)

    async def delete_raid_from_discord(self, raid):
        for message in raid.messages:
            try:
                if not self.logging_out:
                    if message.id in self.message_to_raid:
                        del self.message_to_raid[message.id]
                    elif message.id in self.private_channel_raids:
                        del self.private_channel_raids[message.id]
                await message.delete()
            except discord.errors.NotFound:
                pass
        if raid.private_discord_channel is not None:
            try:
                await raid.private_discord_channel.delete()
            except discord.errors.NotFound:
                pass
        self.remove_raid(raid)

    def get_raid(self, raid_id_str):
        if raid_id_str.lower().startswith('ex'):
            ex_raid_id_str = raid_id_str[2:]
            if not ex_raid_id_str.isdigit():
                raise commands.BadArgument(f'EX Raid #{ex_raid_id_str} does not exist.')

            raid_id_int = int(ex_raid_id_str)

            if raid_id_int not in self.exclusive_raid_map:
                if raid_id_int <= self.exclusive_raid_seed:
                    raise commands.BadArgument(f'EX Raid #{raid_id_str} has expired.')
                else:
                    raise commands.BadArgument(f'Raid #{raid_id_str} does not exist.')
            return self.exclusive_raid_map[raid_id_int]
        else:
            if not raid_id_str.isdigit():
                raise commands.BadArgument(f'Raid #{raid_id_str} does not exist.')

            raid_id_int = int(raid_id_str)

            if raid_id_int not in self.raid_map:
                if raid_id_int <= self.raid_seed:
                    raise commands.BadArgument(f'Raid #{raid_id_str} has expired.')
                else:
                    raise commands.BadArgument(f'Raid #{raid_id_str} does not exist.')
            return self.raid_map[raid_id_int]

    def add_participant(self, raid, user_id, user_name, party_size='1', notes=None):
        if not party_size.isdigit():
            raise commands.BadArgument(
                f"The party size entered [{party_size}] is not a number. If you're attending alone, please use 1.")
        party_size = int(party_size)
        participant = RaidParticipant(raid=raid, user_id=user_id, user_name=user_name, party_size=party_size,
                                      notes=notes)
        already_in_raid = participant in raid.participants
        if already_in_raid:
            raid.participants.remove(participant)
            participant = RaidParticipant.objects.get(raid=raid, user_id=user_id, attending=True)
            participant.party_size = party_size
            participant.notes = notes
        participant.save()
        raid.participants.add(participant)

        self.update_embed_participants(raid)
        if party_size > 1:
            party_descriptor = f' +{party_size - 1} '
        else:
            party_descriptor = ''

        if raid.is_exclusive:
            pokemon_or_raid_level = 'EX'
        elif raid.is_mega:
            if raid.pokemon_name is not None:
                pokemon_or_raid_level = f'**MEGA** {raid.pokemon_name}'
            else:
                pokemon_or_raid_level = '**MEGA**'
        elif raid.pokemon_name is None:
            pokemon_or_raid_level = f'a Level {raid.raid_level}'
        else:
            pokemon_or_raid_level = raid.pokemon_name
        if already_in_raid:
            return participant, f"{user_name} {party_descriptor}has __modified__ their RSVP to {pokemon_or_raid_level} Raid #{raid.display_id} at {raid.gym_name}"
        else:
            return participant, f"{user_name} {party_descriptor}has RSVP'd to {pokemon_or_raid_level} Raid #{raid.display_id} at {raid.gym_name}"

    def remove_participant(self, raid, user_id, user_name):
        temp_raider = RaidParticipant(raid=raid, user_id=user_id)
        if temp_raider in raid.participants:
            temp_raider = RaidParticipant.objects.get(raid=raid, user_id=user_id, attending=True)
            temp_raider.attending = False
            temp_raider.save()

            raid.participants.remove(temp_raider)
            self.update_embed_participants(raid)
            return f'{user_name} is no longer attending Raid #{raid.display_id}'
        else:
            return None

    def update_embed_participants(self, raid):
        raid.embed.set_footer(text='Participants: ' + str(self.get_participant_number(raid)))

    def get_participant_number(self, raid):
        result = 0
        for participant in raid.participants:
            result += participant.party_size
        return result

    def get_participant_printout(self, raid):
        result = f'Here are the {self.get_participant_number(raid)} participants for Raid #{raid.display_id}:'
        for raider in raid.participants:
            result += '\n\t' + str(raider)
        return result


    async def build_raid_embed(self, raid):
        if 'quick_move' in raid.data:
            desc = f"{raid.gym_name}\n\n**Moves:** {raid.data['quick_move']}/{raid.data['charge_move']}\n**Ends:** *{localtime(raid.expiration).strftime(time_format)}*"
        else:
            if raid.is_exclusive:
                start_time = localtime(raid.expiration) - timedelta(minutes=self.ex_duration)
                desc = f'{raid.gym_name}\n\n**Starts:** *{start_time.strftime(time_format)}*\n**Ends:** *{localtime(raid.expiration).strftime(time_format)}*'
            else:
                desc = f'{raid.gym_name}\n\n**Ends:** *{localtime(raid.expiration).strftime(time_format)}*'

        if raid.is_exclusive:
            title = f'EX Raid #{raid.display_id}'
        elif raid.is_mega:
            title = f'{raid.pokemon_name}: Mega Raid #{raid.display_id}'
        else:
            title = f'{raid.pokemon_name}: Raid #{raid.display_id}'

        result = discord.Embed(title=title, url=raid.data['url'],
                               description=desc, colour=embed_color)

        if 'image' in raid.data:
            result.set_image(url=raid.data['image']['url'])
            result.image.height = raid.data['image']['height']
            result.image.width = raid.data['image']['width']
            result.image.proxy_url = raid.data['image']['proxy_url']

        if 'thumbnail' in raid.data:
            result.set_thumbnail(url=raid.data['thumbnail']['url'])
            result.thumbnail.height = raid.data['thumbnail']['height']
            result.thumbnail.width = raid.data['thumbnail']['width']
            result.thumbnail.proxy_url = raid.data['thumbnail']['proxy_url']

        return result

    async def build_egg_embed(self, raid):
        desc = f'{raid.gym_name}\n\n**Hatches:** *{localtime(raid.hatch_time).strftime(time_format)}*'

        if raid.is_mega:
            title = f'Mega egg: Raid #{raid.display_id}'
        else:
            title = f'Level {raid.raid_level} egg: Raid #{raid.display_id}'

        result = discord.Embed(title=title, url=raid.data['url'],
                               description=desc, colour=embed_color)

        if 'image' in raid.data:
            result.set_image(url=raid.data['image']['url'])
            result.image.height = raid.data['image']['height']
            result.image.width = raid.data['image']['width']
            result.image.proxy_url = raid.data['image']['proxy_url']

        if 'thumbnail' in raid.data:
            result.set_thumbnail(url=raid.data['thumbnail']['url'])
            result.thumbnail.height = raid.data['thumbnail']['height']
            result.thumbnail.width = raid.data['thumbnail']['width']
            result.thumbnail.proxy_url = raid.data['thumbnail']['proxy_url']

        return result

    def build_manual_raid_embed(self, raid):
        if raid.is_egg:
            desc = f'{raid.gym_name}\n\n**Hatches:** *{localtime(raid.hatch_time).strftime(time_format)}*\n**Approx End:** *{localtime(raid.expiration).strftime(time_format)}*'
        else:
            desc = f'{raid.gym_name}\n\n**Ends:** *{localtime(raid.expiration).strftime(time_format)}*'

        details = ''
        if raid.is_mega:
            if raid.is_egg:
                details = 'Mega Egg: '
            elif raid.pokemon_name is not None:
                    details = f'Mega {raid.pokemon_name}: '
        else:
            if raid.pokemon_name is not None:
                details = f'{raid.pokemon_name}: '
            elif raid.raid_level > 0:
                details = f'Level {raid.raid_level}: '

        result = discord.Embed(title=f'{details}User Raid #{raid.display_id}', url=raid.data['url'],
                               description=desc, colour=embed_color)

        return result

    def reset(self):
        self.hashed_active_raids.clear()
        self.raid_map.clear()
        self.raid_seed = 1


class RaidZoneManager:
    def __init__(self):
        self.zones = defaultdict(list)

    def create_zone(self, guild, destination, latitude, longitude):
        rz = RaidZone(guild=guild, destination=destination, latitude=latitude, longitude=longitude)
        rz.save()
        self.zones[destination].append(rz)
        return rz

    async def load_from_database(self, bot):

        # Ensure the collections are empty before loading data from the database
        self.zones = defaultdict(list)

        for rz in RaidZone.objects.all().order_by('name'):
            channel = bot.get_channel(int(rz.destination))
            if channel is None:
                channel = bot.get_guild(rz.guild).get_member(int(rz.destination))
            if channel is not None:
                rz.discord_destination = channel
                self.zones[rz.destination].append(rz)
            else:
                print(f'Unable to load raid zone for id rz.id destination {rz.destination}')

    async def send_to_raid_zones(self, raid, bot):
        objects_to_save = []
        for zone_list in self.zones.values():
            for rz in zone_list:
                if rz.filter(raid):
                    try:
                        raid_message = await rz.discord_destination.send(embed=raid.embed)
                        if not isinstance(rz.discord_destination, discord.member.Member):
                            objects_to_save.append(
                                RaidMessage(raid=raid, channel=raid_message.channel.id, message=raid_message.id))
                            raid.messages.append(raid_message)
                            bot.raids.message_to_raid[raid_message.id] = raid
                            # Add a reaction to the raid messages so it's easier to others to react
                            if not bot.raids.logging_out:
                                await raid_message.add_reaction('✅')
                    except discord.errors.Forbidden:
                        print(
                            f'Unable to send raid to channel {rz.discord_destination.name}. The bot does not have permission.')
                        pass
        return objects_to_save
