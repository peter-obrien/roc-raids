from django.contrib.postgres.fields import JSONField
from django.db import models
from math import sin, cos, sqrt, atan2, radians


class Raid(models.Model):
    display_id = models.IntegerField()
    pokemon_name = models.CharField(max_length=100, null=True)
    pokemon_number = models.IntegerField(null=True)
    raid_level = models.IntegerField()
    gym_name = models.CharField(max_length=255)
    expiration = models.DateTimeField()
    active = models.BooleanField(default=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    data = JSONField()
    private_channel = models.CharField(max_length=64, null=True)
    is_egg = models.BooleanField(default=False)
    hatch_time = models.DateTimeField(null=True)

    def __hash__(self):
        return hash((self.raid_level, self.latitude, self.longitude))

    def __eq__(self, other):
        return (self.raid_level == other.raid_level
                and self.latitude == other.latitude
                and self.longitude == other.longitude)


class RaidMessage(models.Model):
    raid = models.ForeignKey(Raid, on_delete=models.CASCADE)
    channel = models.CharField(max_length=64)
    message = models.CharField(max_length=64)


class RaidParticipant(models.Model):
    raid = models.ForeignKey(Raid, on_delete=models.CASCADE)
    user_id = models.CharField(max_length=64)
    user_name = models.CharField(max_length=255)
    party_size = models.IntegerField(default=1)
    notes = models.CharField(max_length=255, null=True)
    attending = models.BooleanField(default=True)

    def __eq__(self, other):
        return self.raid == other.raid and self.user_id == other.user_id

    def __hash__(self):
        return hash((self.raid, self.user_id))

    def __str__(self):
        result = self.user_name
        result += self.details()
        return result

    def details(self):
        result = ''
        if self.party_size > 1:
            result += ' +' + str(self.party_size - 1)
        if self.notes is not None:
            result += ': ' + self.notes
        return result


class BotOnlyChannel(models.Model):
    channel = models.CharField(max_length=64)


def filter_default():
    return {'pokemon': [], 'raid_levels': []}


class RaidZone(models.Model):
    destination = models.CharField(max_length=64)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    radius = models.DecimalField(max_digits=3, decimal_places=1, default=5.0)
    active = models.BooleanField(default=True)
    filters = JSONField(default=filter_default)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Since the destination field is the ID of the discord channel/user, this attribute will hold the full object.
        self.discord_destination = None

    @property
    def status(self):
        if self.active:
            return 'on'
        else:
            return 'off'

    def filter(self, raid):
        if self.active:
            if self._isInRaidZone(raid):
                # TODO Filter by raid level
                if raid.is_egg:
                    return True
                else:
                    return self._filter_pokemon(raid)
        else:
            return False

    def _isInRaidZone(self, raid):
        earth_radius = 6373.0

        center_lat = radians(self.latitude)
        center_lon = radians(self.longitude)
        gym_lat = radians(raid.latitude)
        gym_lon = radians(raid.longitude)

        lon_diff = gym_lon - center_lon
        lat_diff = gym_lat - center_lat

        a = sin(lat_diff / 2) ** 2 + cos(center_lat) * cos(gym_lat) * sin(lon_diff / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = earth_radius * c

        return distance <= self.radius

    def _filter_pokemon(self, raid):
        if len(self.filters['pokemon']) > 0:
            return int(raid.pokemon_number) in self.filters['pokemon']
        else:
            return True

    def _filter_raid_level(self, raid):
        if len(self.filters['raid_levels']) > 0:
            return int(raid.raid_level) in self.filters['raid_levels']
        else:
            return False
