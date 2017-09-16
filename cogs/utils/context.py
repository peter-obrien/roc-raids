from discord.ext import commands


class Context(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.raids = self.bot.raids
        self.zones = self.bot.zones
        self.bot_guild = self.bot.bot_guild
        self.rsvp_channel = self.bot.rsvp_channel
