from raider import RaidParticipant

class Raid:
    def __init__(self, raidId, pokemon, gym, end, embed):
        self.id = raidId
        self.pokemon = pokemon
        self.gym = gym
        self.end = end
        self.embed = embed
        self.raiders = set()
        self.messages = []

    def add_raider(self, raiderName, partySize=1, startTime=None):
        raider = RaidParticipant(raiderName, int(partySize), startTime)
        if raider in self.raiders:
            self.raiders.remove(raider)
        self.raiders.add(raider)
        self.update_embed_participants()

    def remove_raider(self, raiderName):
        self.raiders.discard(RaidParticipant(raiderName))
        self.update_embed_participants()

    def get_participant_number(self):
        result = 0
        for raider in self.raiders:
            result += raider.party_size
        return result

    def update_embed_participants(self):
        self.embed.set_footer(text='Participants: ' + str(self.get_participant_number()))

    def get_raiders(self):
        result = 'Here are the ' + str(self.get_participant_number()) + ' participants for raid #' + str(self.id) + ':'
        for raider in self.raiders:
            result += '\n\t' + str(raider)
        return result

    def add_message(self, message):
        self.messages.append(message)

class RaidMap:
    def __init__(self):
        self.raids = dict()
        self.raidIdSeed = 0

    def generate_raid_id(self):
        self.raidIdSeed += 1
        return self.raidIdSeed

    def store_raid(self, raidId, pokemon, gym, end, raidMessageEmbed):
        raid = Raid(raidId, pokemon, gym, end, raidMessageEmbed)
        self.raids[str(raidId)] = raid
        return raid

    def get_raid(self, raidId):
        return self.raids[str(raidId)]

    def get_raiders_gh(self, raidId):
        result = 'Here are the ' + str(self.get_participant_number(raidId)) + ' participants for raid #' + str(raidId) + ':'
        for raider in self.raiders[raidId]:
            result += '\n\t' + str(raider)
        return result

    def clear_raids(self):
        self.raids.clear()
        self.raiders.clear()
