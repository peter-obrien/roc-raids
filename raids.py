from math import sin, cos, sqrt, atan2, radians

from orm.models import Raid, RaidParticipant, RaidMessage, RaidZone
from errors import InputError
import discord
from django.utils.timezone import localtime
from django.db.models import Max

time_format = '%m/%d %I:%M %p'
embed_color = 0x408fd0


class RaidManager:
    def __init__(self):
        self.hashed_active_raids = dict()
        self.raid_map = dict()
        self.message_map = dict()
        self.participant_map = dict()
        self.channel_map = dict()
        self.embed_map = dict()
        self.raid_seed = 0

    async def load_from_database(self, discordClient, discordServer):

        last_raid_seed = Raid.objects.filter(active=True).aggregate(Max('display_id')).get('display_id__max')
        if last_raid_seed is not None:
            self.raid_seed = last_raid_seed

        for raid in Raid.objects.filter(active=True):
            self.hashed_active_raids[hash(raid)] = raid
            self.raid_map[raid.display_id] = raid
            self.channel_map[raid.display_id] = discordServer.get_channel(raid.private_channel)
            self.message_map[raid.display_id] = []
            self.participant_map[raid.display_id] = set()
            self.embed_map[raid.display_id] = await self.build_raid_embed(raid)
            for participant in RaidParticipant.objects.filter(raid=raid, attending=True):
                self.participant_map[raid.display_id].add(participant)
            for rm in RaidMessage.objects.filter(raid=raid):
                try:
                    msg = await discordClient.get_message(discordServer.get_channel(rm.channel), rm.message)
                    self.message_map[raid.display_id].append(msg)
                except discord.errors.NotFound:
                    pass

    def create_raid(self, pokemon_name, pokemon_number, raid_level, gym_name, expiration, latitude, longitude):
        raid_result = Raid(pokemon_name=pokemon_name, pokemon_number=pokemon_number, raid_level=raid_level,
                           gym_name=gym_name, expiration=expiration, latitude=latitude, longitude=longitude)
        hash_val = hash(raid_result)
        if hash_val in self.hashed_active_raids:
            raid_result = self.hashed_active_raids[hash_val]
        return raid_result

    def track_raid(self, raid):
        self.raid_seed += 1
        raid.display_id = self.raid_seed
        self.hashed_active_raids[hash(raid)] = raid
        self.raid_map[raid.display_id] = raid
        self.message_map[raid.display_id] = []
        self.participant_map[raid.display_id] = set()
        raid.save()
        return raid

    def remove_raid(self, raid):
        self.hashed_active_raids.pop(hash(raid), None)
        self.raid_map.pop(raid.display_id, None)
        self.message_map.pop(raid.display_id, None)
        self.participant_map.pop(raid.display_id, None)
        self.channel_map.pop(raid.display_id, None)
        self.embed_map.pop(raid.display_id, None)

    def get_raid(self, raid_id_str):
        if not raid_id_str.isdigit():
            raise InputError('Raid #{} does not exist.'.format(raid_id_str))

        raid_id_int = int(raid_id_str)

        if raid_id_int not in self.raid_map:
            if raid_id_int <= self.raid_seed:
                raise InputError('Raid #{} has expired.'.format(raid_id_str))
            else:
                raise InputError('Raid #{} does not exist.'.format(raid_id_str))
        return self.raid_map[raid_id_int]

    def add_participant(self, raid, user_id, user_name, party_size='1', notes=None):
        if not party_size.isdigit():
            raise InputError(
                "The party size entered [{}] is not a number. If you're attending alone, please use 1.".format(
                    party_size))
        party_size = int(party_size)
        participant = RaidParticipant(raid=raid, user_id=user_id, user_name=user_name, party_size=party_size,
                                      notes=notes)
        already_in_raid = participant in self.participant_map[raid.display_id]
        if already_in_raid:
            self.participant_map[raid.display_id].remove(participant)
            participant = RaidParticipant.objects.get(raid=raid, user_id=user_id)
            participant.party_size = party_size
            participant.notes = notes
        participant.save()
        self.participant_map[raid.display_id].add(participant)

        self.update_embed_participants(raid)
        party_descriptor = (' +{} '.format(str(party_size - 1)) if party_size > 1 else '')
        if already_in_raid:
            return participant, "{} {}has __modified__ their RSVP to {} Raid #{} at {}".format(user_name,
                                                                                               party_descriptor,
                                                                                               raid.pokemon_name,
                                                                                               raid.display_id,
                                                                                               raid.gym_name)
        else:
            return participant, "{} {}has RSVP'd to {} Raid #{} at {}".format(user_name, party_descriptor,
                                                                              raid.pokemon_name,
                                                                              raid.display_id, raid.gym_name)

    def remove_participant(self, raid, user_id, user_name):
        temp_raider = RaidParticipant(raid=raid, user_id=user_id)
        if temp_raider in self.participant_map[raid.display_id]:
            temp_raider = RaidParticipant.objects.get(raid=raid, user_id=user_id)
            temp_raider.attending = False
            temp_raider.save()

            self.participant_map[raid.display_id].remove(temp_raider)
            self.update_embed_participants(raid)
            return '{} is no longer attending Raid #{}'.format(user_name, raid.display_id)
        else:
            return None

    def update_embed_participants(self, raid):
        self.embed_map[raid.display_id].set_footer(text='Participants: ' + str(self.get_participant_number(raid)))

    def get_participant_number(self, raid):
        result = 0
        for participant in self.participant_map[raid.display_id]:
            result += participant.party_size
        return result

    def get_participant_printout(self, raid):
        result = 'Here are the ' + str(self.get_participant_number(raid)) + ' participants for Raid #' + str(
            raid.display_id) + ':'
        for raider in self.participant_map[raid.display_id]:
            result += '\n\t' + str(raider)
        return result

    async def build_raid_embed(self, raid):
        if 'quick_move' in raid.data:
            desc = '{}\n\n**Moves:** {}/{}\n**Ends:** *{}*'.format(raid.gym_name, raid.data['quick_move'],
                                                                   raid.data['charge_move'],
                                                                   localtime(raid.expiration).strftime(time_format))
        else:
            desc = '{}\n\n**Ends:** *{}*'.format(raid.gym_name, localtime(raid.expiration).strftime(time_format))

        result = discord.Embed(title=raid.pokemon_name + ': Raid #' + str(raid.display_id), url=raid.data['url'],
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

    def reset(self):
        self.hashed_active_raids.clear()
        self.raid_map.clear()
        self.message_map.clear()
        self.participant_map.clear()
        self.channel_map.clear()
        self.embed_map.clear()
        self.raid_seed = 1


class RaidZoneManager:
    def __init__(self):
        self.zones = dict()

    def create_zone(self, destination, latitude, longitude):
        rz = RaidZone(destination=destination, latitude=latitude, longitude=longitude)
        rz.save()
        self.zones[destination] = rz
        return rz

    async def load_from_database(self, discordServer):
        for rz in RaidZone.objects.all():
            channel = discordServer.get_channel(rz.destination)
            if channel is None:
                channel = discordServer.get_member(rz.destination)
            if channel is not None:
                rz.discord_destination = channel
                self.zones[rz.destination] = rz
            else:
                print('Unable to load raid zone for id {} destination {}'.format(rz.id, rz.destination))

