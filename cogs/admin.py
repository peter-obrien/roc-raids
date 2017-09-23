import discord
from discord.ext import commands
from django.utils.timezone import activate

from orm.models import BotOnlyChannel


class Admin:
    """Commands for the owner, admins, and mods."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.guild_only()
    async def clear(self, ctx, msg_count_to_delete: int = 5):
        """Deletes groups of messages. Cannot delete messages older than 14 days."""
        if ctx.author == ctx.guild.owner:
            try:
                message_to_delete = []
                async for message in ctx.message.channel.history(limit=msg_count_to_delete):
                    message_to_delete.append(message)
                await ctx.channel.delete_messages(message_to_delete)
            except discord.HTTPException:
                # Assume that messages older than 14 days were found and delete one at a time.
                async for message in ctx.message.channel.history(limit=msg_count_to_delete):
                    await message.delete()
        else:
            raise commands.CommandInvokeError('User cannot run this command.')

    @commands.command(hidden=True)
    @commands.is_owner()
    async def logout(self, ctx):
        """Logs the bot out of Discord."""
        print('Logout command invoked. Shutting down.')
        await ctx.message.delete()
        await ctx.bot.logout()

    @commands.command(hidden=True, usage='on/off')
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def botonly(self, ctx, value: str):
        """Allows user to toggle if a channel only accepts bot commands.
        """
        if value.lower() == 'on':
            if ctx.channel not in ctx.bot.bot_only_channels:
                boc = BotOnlyChannel(channel=ctx.channel.id)
                boc.save()
                ctx.bot.bot_only_channels.append(ctx.channel)
            await ctx.send('Bot only commands enabled.')
        elif value.lower() == 'off':
            if ctx.channel in ctx.bot.bot_only_channels:
                boc = BotOnlyChannel.objects.get(channel=ctx.channel.id)
                boc.delete()
                ctx.bot.bot_only_channels.remove(ctx.channel)
            await ctx.send('Bot only commands disabled.')
        else:
            await ctx.send('Command to change bot only status:\n\n`{}[on/off]`'.format(ctx.command))

    @botonly.after_invoke
    async def after_botonly_command(self, ctx):
        await ctx.message.delete()

    @commands.command(hidden=True)
    @commands.guild_only()
    async def set_rsvp(self, ctx):
        """Make the channel where the command is run the guild RSVP output channel."""
        if ctx.author == ctx.guild.owner:
            ctx.bot.config.rsvp_channel = ctx.channel.id
            ctx.bot.config.save()
            await ctx.send('This channel is now the RSVP destination channel.')
        else:
            raise commands.CommandInvokeError('User cannot run this command.')

    @commands.command(hidden=True)
    @commands.guild_only()
    async def set_alarm_source(self, ctx):
        """Make the channel where the command is run the source channel of Pokemon Alarm notification."""
        if ctx.author == ctx.guild.owner:
            ctx.bot.config.alarm_source = ctx.channel.id
            ctx.bot.config.save()
            await ctx.send('This channel is now the alarm source channel.')
        else:
            raise commands.CommandInvokeError('User cannot run this command.')

    @commands.command(hidden=True)
    @commands.guild_only()
    async def set_time_zone(self, ctx, time_zone):
        """Change the time zone in which the raid end times display."""
        if ctx.author == ctx.guild.owner:
            # Activate the time zone first to verify it's a valid time zone
            try:
                activate(time_zone)
            except ValueError as e:
                raise commands.BadArgument(str(e))

            ctx.bot.config.time_zone = time_zone
            ctx.bot.config.save()
            await ctx.send('Changed time zone to {}'.format(time_zone))
        else:
            raise commands.CommandInvokeError('User cannot run this command.')

    @commands.command(hidden=True)
    @commands.guild_only()
    async def set_command(self, ctx, char):
        """Changes the character to invoke commands."""
        if ctx.author == ctx.guild.owner:
            ctx.bot.config.command = char
            ctx.bot.config.save()
            await ctx.send('Changed command character to `{}`'.format(char))
        else:
            raise commands.CommandInvokeError('User cannot run this command.')

    @commands.command(hidden=True)
    @commands.guild_only()
    async def set_raid_category(self, ctx, category: discord.CategoryChannel):
        """Sets the category for private raid channels"""
        if ctx.author == ctx.guild.owner:
            ctx.bot.config.raid_category = category.id
            ctx.bot.config.save()
            await ctx.send('Private raid channels will now be assigned to `{}`'.format(category.name))
        else:
            raise commands.CommandInvokeError('User cannot run this command.')

    @commands.command(hidden=True)
    async def debug(self, ctx):
        """Prints out diagnostic information regarding this bot's configuration."""
        if ctx.author == ctx.guild.owner:
            if ctx.rsvp_channel is None:
                message_text = '**RSVP Channel not setup**'
            else:
                message_text = 'RSVP Channel Name: {}'.format(ctx.rsvp_channel.name)
            for rz in ctx.zones.zones.values():
                if isinstance(rz.discord_destination, discord.Member):
                    message_text += '\nRaid Zone User: {} (*{}*)'.format(rz.discord_destination.name, rz.status)
                else:
                    message_text += '\nRaid Zone Channel: {} (*{}*)'.format(rz.discord_destination.name, rz.status)
            await ctx.send(message_text)
        else:
            raise commands.CommandInvokeError('User cannot run this command.')


def setup(bot):
    bot.add_cog(Admin(bot))
