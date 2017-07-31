from raider import RaidParticipant

class RaidMap:
    def __init__(self):
        self.raids = set()
        self.raiders = dict()
        self.details = dict()
        self.raidMessages = dict()
        self.raidIdSeed = 0

    def generate_raid_id(self):
        self.raidIdSeed += 1
        return self.raidIdSeed

    def store_raid(self, raidId, raidMessage, raidMessageEmbed):
        self.raidMessages[str(raidId)] = (raidMessage, raidMessageEmbed)
        self.raiders[str(raidId)] = set()

    def add_raider_gh(self, raidId, raiderName, party_size=1, start_time=None):
        raider = RaidParticipant(raiderName, int(party_size), start_time)
        participants = self.raiders[raidId]
        if raider in participants:
            participants.remove(raider)
        participants.add(raider)
        raidMessageEmbed = self.raidMessages[raidId][1]
        raidMessageEmbed.set_footer(text='Participants: ' + str(self.get_participant_number(raidId)))
        return (self.raidMessages[raidId][0], raidMessageEmbed)

    def remove_raider_gh(self, raidId, raiderName):
        self.raiders[raidId].discard(RaidParticipant(raiderName))
        raidMessageEmbed = self.raidMessages[raidId][1]
        raidMessageEmbed.set_footer(text='Participants: ' + str(self.get_participant_number(raidId)))
        return (self.raidMessages[raidId][0], raidMessageEmbed)

    def get_participant_number(self, raidId):
        result = 0
        for raider in self.raiders[raidId]:
            result += raider.party_size
        return result

    def get_raiders_gh(self, raidId):
        result = 'Here are the ' + str(self.get_participant_number(raidId)) + ' participants for raid #' + str(raidId) + ':'
        for raider in self.raiders[raidId]:
            result += '\n\t' + str(raider)
        return result

    #start_raid will be used when gymhuntr integration is down
    def start_raid(self, raidDetails):
        raidId = self.raidIdSeed + 1
        self.raidIdSeed += 1
        self.raids.add(str(raidId))
        self.raiders[str(raidId)] = set()
        self.details[str(raidId)] = raidDetails
        return str(raidId)

    def add_raider(self, raidId, raiderName):
        self.raiders[raidId].add(raiderName)

    def get_raiders(self, raidId):
        return self.raiders[raidId]

    def get_details(self, raidId):
        return self.raidMessages[raidId][1]

    def get_detail_embed(self, raidId):
        result = discord.Embed(title='Raid ' + str(raidId), description=self.details[str(raidId)], colour=embedColor)
        result.set_footer(text='Participants: ' + str(len(self.raiders[raidId])))
        return result

    def get_raiders_embed(self, raidId):
        raiderOutput = ''
        counter = 0
        for raider in self.raiders[raidId]:
            if counter == 0 :
                raiderOutput += raider
            else:
                raiderOutput += ', ' + raider
            counter += 1
            if counter == 3:
                raiderOutput += '\n'
                counter = 0
        result = discord.Embed(title='Raid ' + str(raidId), description=self.details[str(raidId)] + '\n' + raiderOutput, colour=embedColor)
        result.set_footer(text='Participants: ' + str(len(self.raiders[raidId])))
        return result

    def clear_raids(self):
        self.raids.clear()
        self.raiders.clear()
