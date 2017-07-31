class RaidParticipant:
    def __init__(self, username, party_size=1, start_time=None):
        self.username = username
        self.party_size = party_size
        self.start_time = start_time

    def __eq__(self, other):
        return self.username == other.username

    def __hash__(self):
        return hash(self.username)

    def __str__(self):
        result = self.username
        if self.party_size > 1:
            result += ' +' + str(self.party_size-1)
        if self.start_time is not None:
            result += ' at ' + self.start_time
        return result
