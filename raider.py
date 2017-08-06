class RaidParticipant:
    def __init__(self, username, party_size=1, notes=None):
        self.username = username
        self.party_size = party_size
        self.notes = notes

    def __eq__(self, other):
        return self.username == other.username

    def __hash__(self):
        return hash(self.username)

    def __str__(self):
        result = self.username
        result += details()
        return result

    def details(self):
        result = ''
        if self.party_size > 1:
            result += ' +' + str(self.party_size-1)
        if self.notes is not None:
            result += ': ' + self.notes
        return result
