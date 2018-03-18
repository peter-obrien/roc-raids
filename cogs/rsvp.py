import discord
from discord.ext import commands
from django.db import transaction

from orm.models import RaidMessage


class Rsvp:
    """Reservation system"""

    def __init__(self, bot):
        self.bot = bot

    async def __after_invoke(self, ctx):
        if isinstance(ctx.channel, discord.TextChannel):
            await ctx.message.delete()

    @commands.command()
    async def join(self, ctx, raid_id: str, party_size: str = '1', *notes: str):
        """Used to indicate that you wish to attend a raid. Can also provide the size of your party (including you) and any notes."""

        author = ctx.author
        if len(notes) == 0:
            notes = None
        else:
            notes = ' '.join(str(x) for x in notes)

        # If the message is coming from PM we want to use the server's version of the user.
        if isinstance(ctx.channel, discord.abc.PrivateChannel):
            author = ctx.bot_guild.get_member(author.id)

        raid = ctx.raids.get_raid(raid_id)

        await self.add_user_to_raid(raid, self.bot, ctx.channel, author, party_size, notes)

    @staticmethod
    async def add_user_to_raid(raid, bot, origin_channel, user, party_size: str='1', notes: str = None):
        private_raid_channel = raid.private_discord_channel
        if private_raid_channel is None:
            overwrites = {
                bot.bot_guild.default_role: bot.private_channel_no_access,
                bot.bot_guild.me: bot.private_channel_access
            }
            if raid.is_exclusive:
                private_raid_channel = await bot.bot_guild.create_text_channel(f'ex-raid-{raid.display_id}-chat',
                                                                               overwrites=overwrites)
            else:
                private_raid_channel = await bot.bot_guild.create_text_channel(f'raid-{raid.display_id}-chat',
                                                                               overwrites=overwrites)
            if bot.config.discord_raid_category is not None:
                await private_raid_channel.edit(category=bot.config.discord_raid_category)

            raid.private_discord_channel = private_raid_channel

            # Send the raid card to the top of the channel.
            private_raid_card = await raid.private_discord_channel.send(embed=raid.embed)
            # Add reaction to allow for easy leaving the raid.
            if not bot.raids.logging_out:
                await private_raid_card.add_reaction('❌')
                bot.raids.private_channel_raids[private_raid_card.id] = raid
            raid.messages.append(private_raid_card)

            with transaction.atomic():
                raid.private_channel = private_raid_channel.id
                raid.save()
                RaidMessage(raid=raid, channel=private_raid_channel.id, message=private_raid_card.id).save()

        # Add this user to the raid and update all the embeds for the raid.
        result_tuple = bot.raids.add_participant(raid, user.id, user.display_name, party_size, notes)
        for msg in raid.messages:
            try:
                await msg.edit(embed=raid.embed)
            except discord.errors.NotFound:
                raid.messages.remove(msg)
                pass

        # Add the user to the private channel for the raid
        await raid.private_discord_channel.set_permissions(user, overwrite=bot.private_channel_access)
        await raid.private_discord_channel.send(f'{user.mention}{result_tuple[0].details()}')

        # Send message to the RSVP channel if the command was invoked publicly
        if bot.rsvp_channel is not None and isinstance(origin_channel, discord.abc.GuildChannel):
            await bot.rsvp_channel.send(result_tuple[1])

    @commands.command()
    async def leave(self, ctx, raid_id: str):
        """Used to indicate to others that you are no longer attending the indicated raid."""

        author = ctx.author
        # If the message is coming from PM we want to use the server's version of the user.
        if isinstance(ctx.channel, discord.abc.PrivateChannel):
            author = ctx.bot_guild.get_member(author.id)

        raid = ctx.raids.get_raid(raid_id)

        await self.remove_user_from_raid(raid, self.bot, ctx.channel, author)

    @staticmethod
    async def remove_user_from_raid(raid, bot, origin_channel, user):
        display_msg = bot.raids.remove_participant(raid, user.id, user.display_name)

        if display_msg is not None:
            # Remove the user to the private channel for the raid
            await raid.private_discord_channel.set_permissions(user, overwrite=None)
            await raid.private_discord_channel.send(f'**{user.display_name}** is no longer attending')

            for msg in raid.messages:
                await msg.edit(embed=raid.embed)
            if bot.rsvp_channel is not None and isinstance(origin_channel, discord.abc.GuildChannel):
                await bot.rsvp_channel.send(display_msg)

    @commands.command()
    async def who(self, ctx, raid_id: str):
        """Used to get a listing of who is attend the provided raid."""
        raid = ctx.raids.get_raid(raid_id)
        msg = ctx.raids.get_participant_printout(raid)
        await ctx.author.send(msg)

    @commands.command(aliases=['raid'])
    async def details(self, ctx, raid_id: str):
        """Used to get the raid card PM to you by the bot. Useful for quickly learning the location of a particular raid."""
        raid = ctx.raids.get_raid(raid_id)
        await ctx.author.send(embed=raid.embed)


def setup(bot):
    bot.add_cog(Rsvp(bot))
