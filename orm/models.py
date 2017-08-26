from django.contrib.postgres.fields import JSONField
from django.db import models


class Raid(models.Model):
    display_id = models.IntegerField()
    pokemon_name = models.CharField(max_length=100)
    pokemon_number = models.IntegerField()
    raid_level = models.IntegerField()
    gym_name = models.CharField(max_length=255)
    expiration = models.DateTimeField()
    active = models.BooleanField(default=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    data = JSONField()
    private_channel = models.CharField(max_length=64, null=True)

    def __hash__(self):
        return hash((self.pokemon_name, self.latitude, self.longitude))

    def __eq__(self, other):
        return (self.pokemon_name == other.pokemon_name
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
