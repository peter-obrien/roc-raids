import os, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

import configparser
import logging
import traceback
import aiohttp
import sys

from discord.ext import commands
from orm.models import BotOnlyChannel
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
elif not config['DEFAULT']['server_id']:
    print('server_id is not set. Please update ' + propFilename)
    quit()
elif not config['DEFAULT']['rsvp_channel_id']:
    print('rsvp_channel_id is not set. Please update ' + propFilename)
    quit()
bot_token = config['DEFAULT']['bot_token']
try:
    raid_src_id = int(config['DEFAULT']['raid_src_channel_id'])
except ValueError:
    print('raid_src_channel_id is not a number.')
    quit()
try:
    guild_id = int(config['DEFAULT']['server_id'])
except ValueError:
    print('server_id is not a number.')
    quit()
try:
    rsvp_channel_id = int(config['DEFAULT']['rsvp_channel_id'])
except ValueError:
    print('rsvp_channel_id is not a number.')
    quit()
try:
    test_message_id = config['DEFAULT']['test_message_id']
except Exception as e:
    test_message_id = None


def _prefix_callable(bot, msg):
    return '!'


class RaidCoordinator(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(command_prefix=_prefix_callable, description=description,
                         pm_help=None, help_attrs=dict(hidden=True))

        self.session = aiohttp.ClientSession(loop=self.loop)
        self.raids = RaidManager()
        self.zones = RaidZoneManager()
        self.bot_guild = None
        self.rsvp_channel = None
        self.bot_only_channels = []

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
        self.bot_guild = self.get_guild(guild_id)
        self.rsvp_channel = self.bot_guild.get_channel(rsvp_channel_id)

        for boc in BotOnlyChannel.objects.all():
            channel = self.bot_guild.get_channel(boc.channel)
            if channel is not None:
                self.bot_only_channels.append(channel)

        await self.raids.load_from_database(self)
        await self.zones.load_from_database(self)
        print(f'Ready: {self.user} (ID: {self.user.id})')

    async def on_resumed(self):
        print('resumed...')

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=context.Context)

        # Make base commands case insensitive
        if ctx.prefix is not None:
            command = ctx.invoked_with
            if command:
                ctx.command = self.get_command(command.lower())

        if ctx.prefix is None and ctx.channel in self.bot_only_channels:
            await ctx.author.send('Only bot commands may be used in this channel.')
            await ctx.message.delete()
            return

        if ctx.command is None:
            return

        await self.invoke(ctx)

    async def on_message(self, message):
        if message.author.bot:
            return

        # Used for testing purposes
        if message.content.startswith('!go') and test_message_id is not None:
            await message.delete()
            message = await message.channel.get_message(test_message_id)

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
