import os, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

import configparser
from discord.ext import commands
import logging
import traceback
import aiohttp
import sys
from cogs.utils import context
from raids import RaidManager, RaidZoneManager
from alarm_handler import process_raid

description = """
I'm a Pokemon Go raid coordinator
"""

log = logging.getLogger(__name__)

initial_extensions = (
    'cogs.rsvp',
    'cogs.admin',
    'cogs.zones'
)

# Process startup configurations
propFilename = 'properties.ini'
config = configparser.ConfigParser()
config.read(propFilename)
if not config['DEFAULT']['bot_token']:
    print('bot_token is not set. Please update ' + propFilename)
    quit()
elif not config['DEFAULT']['raid_src_channel_id']:
    print('raid_src_channel_id is not set. Please update ' + propFilename)
    quit()
bot_token = config['DEFAULT']['bot_token']
try:
    raid_src_id = int(config['DEFAULT']['raid_src_channel_id'])
except ValueError:
    print('raid_src_channel_id is not a number.')
    quit()


def _prefix_callable(bot, msg):
    return '!'


class RaidCoordinator(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(command_prefix=_prefix_callable, description=description,
                         pm_help=None, help_attrs=dict(hidden=True))

        self.session = aiohttp.ClientSession(loop=self.loop)
        self.raids = RaidManager()
        self.zones = RaidZoneManager()

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
        await self.raids.load_from_database(self)
        await self.zones.load_from_database(self)
        print(f'Ready: {self.user} (ID: {self.user.id})')

    async def on_resumed(self):
        print('resumed...')

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=context.Context)

        if ctx.command is None:
            return

        await self.invoke(ctx)

    async def on_message(self, message):
        if message.author.bot:
            return
        if message.channel.id == raid_src_id:
            await process_raid(self, message)
        else:
            await self.process_commands(message)

    async def close(self):
        await super().close()
        await self.session.close()

    def run(self):
        super().run(bot_token, reconnect=True)


bot = RaidCoordinator()
bot.run()
