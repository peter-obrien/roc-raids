import configparser

from discord.ext import commands
import logging
import traceback
import aiohttp
import sys

description = """
I'm a Pokemon Go raid coordinator
"""

log = logging.getLogger(__name__)

initial_extensions = (
    'cogs.rsvp',
    'cogs.admin'
)

propFilename = 'properties.ini'
config = configparser.ConfigParser()
config.read(propFilename)
botToken = config['DEFAULT']['bot_token']

if not botToken:
    print('bot_token is not set. Please update ' + propFilename)
    quit()

def _prefix_callable(bot, msg):
    return '!'

class RaidCoordinator(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(command_prefix=_prefix_callable, description=description,
                         pm_help=None, help_attrs=dict(hidden=True))

        self.session = aiohttp.ClientSession(loop=self.loop)

        for extension in initial_extensions:
            try:
                self.load_extension(extension)
            except Exception:
                print(f'Failed to load extension {extension}.', file=sys.stderr)
                traceback.print_exc()

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send('This command cannot be used in private messages.')
        elif isinstance(error, commands.DisabledCommand):
            await ctx.author.send('Sorry. This command is disabled and cannot be used.')
        elif isinstance(error, commands.CommandInvokeError):
            print(f'In {ctx.command.qualified_name}:', file=sys.stderr)
            traceback.print_tb(error.original.__traceback__)
            print(f'{error.original.__class__.__name__}: {error.original}', file=sys.stderr)

    async def on_ready(self):
        print(f'Ready: {self.user} (ID: {self.user.id})')

    async def on_resumed(self):
        print('resumed...')

    async def on_message(self, message):
        if message.author.bot:
            return
        await self.process_commands(message)

    async def close(self):
        await super().close()
        await self.session.close()

    def run(self):
        super().run(botToken, reconnect=True)

bot = RaidCoordinator()
bot.run()