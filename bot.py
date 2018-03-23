import os, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

import configparser
import logging
import traceback
import aiohttp
import asyncio
import sys
import discord
import alarm_handler
import gymhuntr_handler

from discord.ext import commands
from orm.models import BotOnlyChannel, Raid, GuildConfig
from cogs.rsvp import Rsvp
from cogs.utils import context
from raids import RaidManager, RaidZoneManager
from datetime import timedelta
from django.db import transaction
from django.utils import timezone

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
    command_char = config['DEFAULT']['command_character']
except KeyError:
    command_char = '!'
try:
    test_message_id = config['DEFAULT']['test_message_id']
except Exception as e:
    test_message_id = None


def _prefix_callable(bot, msg):
    return bot.config.command


class RaidCoordinator(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(command_prefix=_prefix_callable, description=description,
                         pm_help=True, help_attrs=dict(hidden=True))

        self.session = aiohttp.ClientSession(loop=self.loop)
        self.raids = RaidManager()
        self.zones = RaidZoneManager()
        self.bot_guild = None
        self.rsvp_channel = None
        self.bot_only_channels = []
        self.reset_date = timezone.localdate(timezone.now()) + timedelta(hours=24)
        self.private_channel_no_access = discord.PermissionOverwrite(read_messages=False)
        self.private_channel_access = discord.PermissionOverwrite(read_messages=True, mention_everyone=True)

        config_results = GuildConfig.objects.filter(guild=guild_id)
        if len(config_results) == 0:
            gc = GuildConfig(guild=guild_id)
            gc.save()
            self.config: GuildConfig = gc
        else:
            self.config: GuildConfig = config_results[0]

        # create the background task and run it in the background
        self.bg_task = self.loop.create_task(self.background_cleanup())

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
        elif isinstance(error, commands.BadArgument):
            await ctx.author.send(str(error))
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.author.send(f'Missing required argument for: {ctx.command}')
            await ctx.show_help(command=ctx.command)
            await ctx.message.delete()

    async def on_ready(self):
        self.bot_guild = self.get_guild(guild_id)
        self.rsvp_channel = self.bot_guild.get_channel(rsvp_channel_id)
        self.config.discord_rsvp_channel = self.rsvp_channel
        self.config.discord_ex_raid_channel = self.bot_guild.get_channel(self.config.ex_raid_channel)

        for cat in self.bot_guild.categories:
            if self.config.raid_category == cat.id:
                self.config.discord_raid_category = cat
                break

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

        # Used for testing purposes
        if message.content.startswith(command_char + 'go') and test_message_id is not None:
            await message.delete()
            message = await message.channel.get_message(test_message_id)

        if message.channel.id == raid_src_id and message.author.bot:
            await alarm_handler.process_raid(self, message)
        elif message.author.id == 329412230481444886:
            await gymhuntr_handler.process_raid(self, message)
        else:
            if message.author.bot:
                return

            await self.process_commands(message)

    async def on_reaction_add(self, reaction, user):

        if user.bot:
            return

        # Reactions to the raid card in the private lobby
        if reaction.message.id in self.raids.private_channel_raids:
            raid = self.raids.private_channel_raids[reaction.message.id]
            if reaction.emoji == '❌':
                await Rsvp.remove_user_from_raid(raid, self, reaction.message.channel, user)
                await reaction.message.remove_reaction(reaction.emoji, user)
            elif reaction.emoji == '1⃣':
                await Rsvp.add_user_to_raid(raid, self, reaction.message.channel, user, '1')
                await reaction.message.remove_reaction(reaction.emoji, user)
            elif reaction.emoji == '2⃣':
                await Rsvp.add_user_to_raid(raid, self, reaction.message.channel, user, '2')
                await reaction.message.remove_reaction(reaction.emoji, user)
            elif reaction.emoji == '3⃣':
                await Rsvp.add_user_to_raid(raid, self, reaction.message.channel, user, '3')
                await reaction.message.remove_reaction(reaction.emoji, user)
            elif reaction.emoji == '4⃣':
                await Rsvp.add_user_to_raid(raid, self, reaction.message.channel, user, '4')
                await reaction.message.remove_reaction(reaction.emoji, user)
        # Reactions to the public raid cards
        elif reaction.message.id in self.raids.message_to_raid:
            raid = self.raids.message_to_raid[reaction.message.id]
            if reaction.emoji == '✅':
                await Rsvp.add_user_to_raid(raid, self, reaction.message.channel, user)
                await reaction.message.remove_reaction(reaction.emoji, user)

    async def on_guild_channel_delete(self, channel):
        # If the channel was a raid zone, delete it.
        if channel.id in self.zones.zones:
            self.zones.zones[channel.id].delete()

    async def close(self):
        await super().close()
        await self.session.close()

    def run(self):
        super().run(bot_token, reconnect=True)

    async def background_cleanup(self):
        await self.wait_until_ready()

        while not self.is_closed():
            expired_raids = []
            current_time = timezone.localtime(timezone.now())
            current_date = timezone.localdate(current_time)

            # Find expired raids
            with transaction.atomic():
                for raid in self.raids.raid_map.values():
                    if current_time > raid.expiration:
                        raid.active = False
                        raid.save()
                        expired_raids.append(raid)
                for raid in self.raids.exclusive_raid_map.values():
                    if current_time > raid.expiration:
                        raid.active = False
                        raid.save()
                        expired_raids.append(raid)

            # Process expired raids
            for raid in expired_raids:
                for message in raid.messages:
                    try:
                        if not self.raids.logging_out:
                            if message.id in self.raids.message_to_raid:
                                del self.raids.message_to_raid[message.id]
                            elif message.id in self.raids.private_channel_raids:
                                del self.raids.private_channel_raids[message.id]
                        await message.delete()
                    except discord.errors.NotFound:
                        pass
                if raid.private_discord_channel is not None:
                    try:
                        await raid.private_discord_channel.delete()
                    except discord.errors.NotFound:
                        pass
                self.raids.remove_raid(raid)

            # Check to see if the raid manager needs to be reset
            if current_date == self.reset_date:
                # Get the next reset time.
                self.reset_date = self.reset_date + timedelta(hours=24)
                self.raids.reset()
                # Clean up any non exclusive raids that may still be active in the database
                for raid in Raid.objects.filter(active=True, is_exclusive=False):
                    raid.active = False
                    raid.save()

            await asyncio.sleep(60)  # task runs every 60 seconds


bot = RaidCoordinator()
bot.run()
