from discord.ext import commands


class Context(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.raids = self.bot.raids
        self.zones = self.bot.zones
        self.bot_guild = self.bot.bot_guild
        self.rsvp_channel = self.bot.rsvp_channel

    async def show_help(self, command=None):
        """Shows the help command for the specified command if given.
        If no command is given, then it'll show help for the current
        command.
        """
        cmd = self.bot.get_command('help')
        command = command or self.command.qualified_name
        await self.invoke(cmd, str(command))
