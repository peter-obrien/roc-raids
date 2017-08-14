from raider import RaidParticipant
from datetime import datetime
from errors import InputError

class Raid:
    def __init__(self, pokemon, gym, end, latitude, longitude):
        self.pokemon = pokemon
        self.gym = gym
        self.end = end
        self.latitude = latitude
        self.longitude = longitude
        self.id = None
        self.embed = None
        self.raiders = set()
        self.messages = []
        self.channel = None

    def add_raider(self, raiderName, partySize=1, notes=None):
        if not partySize.isdigit() :
            raise InputError("The party size entered [" + partySize + "] is not a number. If you're attending alone, please use 1." )
        raider = RaidParticipant(raiderName, int(partySize), notes)
        alreadyInRaid = raider in self.raiders
        if alreadyInRaid:
            self.raiders.remove(raider)
        self.raiders.add(raider)
        self.update_embed_participants()
        partyDescriptor = (' +{} '.format(str(int(partySize)-1)) if int(partySize) > 1 else '')
        if alreadyInRaid:
            return (raider, "{} {}has __modified__ their RSVP to {} Raid #{} at {}".format(raiderName, partyDescriptor, self.pokemon, self.id, self.gym))
        else:
            return (raider, "{} {}has RSVP'd to {} Raid #{} at {}".format(raiderName, partyDescriptor, self.pokemon, self.id, self.gym))

    def remove_raider(self, raiderName):
        tempRaider = RaidParticipant(raiderName)
        if tempRaider in self.raiders:
            self.raiders.discard(tempRaider)
            self.update_embed_participants()
            return '{} is no longer attending Raid #{}'.format(raiderName, self.id)
        else:
            return None

    def get_participant_number(self):
        result = 0
        for raider in self.raiders:
            result += raider.party_size
        return result

    def update_embed_participants(self):
        self.embed.set_footer(text='Participants: ' + str(self.get_participant_number()))

    def get_raiders(self):
        result = 'Here are the ' + str(self.get_participant_number()) + ' participants for Raid #' + str(self.id) + ':'
        for raider in self.raiders:
            result += '\n\t' + str(raider)
        return result

    def add_message(self, message):
        self.messages.append(message)

    def __hash__(self):
        return hash((self.pokemon, self.latitude, self.longitude))

    def __eq__(self, other):
        return (self.pokemon == other.pokemon
            and self.latitude == other.latitude
            and self.longitude == other.longitude)

class RaidMap:
    def __init__(self):
        self.raids = dict()
        self.hashedRaids = dict()
        self.raidIdSeed = 0

    def generate_raid_id(self):
        self.raidIdSeed += 1
        return self.raidIdSeed

    def create_raid(self, pokemon, gym, end, latitude, longitude):
        raid = Raid(pokemon, gym, end, latitude, longitude)
        # Check to see if this raid was already generated from a different channel
        raidHash = hash(raid)
        if raidHash in self.hashedRaids:
            return self.hashedRaids[raidHash]
        return raid

    def store_raid(self, raid):
        self.raids[str(raid.id)] = raid
        self.hashedRaids[hash(raid)] = raid

    def get_raid(self, raidId):
        if str(raidId) not in self.raids:
            if raidId.isdigit() and int(raidId) <= self.raidIdSeed:
                raise InputError('Raid #' + str(raidId) + ' has expired.' )
            else:
                raise InputError('Raid #' + str(raidId) + ' does not exist.' )
        return self.raids[str(raidId)]

    def remove_raid(self, raid):
        self.raids.pop(str(raid.id), None)
        self.hashedRaids.pop(hash(raid), None)

    def clear_raids(self):
        self.raids.clear()
        self.hashedRaids.clear()
        self.raidIdSeed = 0

class RaidZone:
    def __init__(self,channel,lat,lon,raidus):
        self.channel = channel
        self.latitude = float(lat)
        self.longitude = float(lon)
        self.raidus = float(raidus)
