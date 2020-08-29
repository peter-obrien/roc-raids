from datetime import timedelta

import discord
from decimal import Decimal
from discord.ext import commands
from django.db import transaction
from django.utils import timezone

from orm.models import RaidMessage


class Rsvp(commands.Cog):
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
    async def add_user_to_raid(raid, bot, origin_channel, user, party_size: str = '1', notes: str = None):
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
                await private_raid_card.add_reaction('1⃣')
                await private_raid_card.add_reaction('2⃣')
                await private_raid_card.add_reaction('3⃣')
                await private_raid_card.add_reaction('4⃣')
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

    @commands.command(aliases=['reportegg'])
    @commands.has_role('Raid Reporter')
    async def report_egg(self, ctx, gym_name: str, level: str, latitude: Decimal, longitude: Decimal,
                         minutes_remaining: int):
        """Creates an raid that user can join via the RSVP commands.

        If a gym name is multiple words wrap the gym name with double quotes.
        """

        hatch_time = timezone.localtime(timezone.now()) + timedelta(minutes=minutes_remaining)

        raid = await ctx.raids.create_manual_raid(ctx.author.id, gym_name=gym_name, raid_level=level,
                                                  latitude=latitude, longitude=longitude,
                                                  expiration=hatch_time,
                                                  is_egg=True)

        await self.finish_reporting_manual_raid(ctx, raid)

    @commands.command(aliases=['reportraid'])
    @commands.has_role('Raid Reporter')
    async def report_raid(self, ctx, gym_name: str, level: str, pokemon_name: str, latitude: Decimal,
                          longitude: Decimal,
                          minutes_remaining: int):
        """Creates an raid that user can join via the RSVP commands.

        If a gym name is multiple words wrap the gym name with double quotes.
        """

        expiration = timezone.localtime(timezone.now()) + timedelta(minutes=minutes_remaining)

        raid = await ctx.raids.create_manual_raid(ctx.author.id,  gym_name=gym_name,
                                                  raid_level=level, pokemon_name=pokemon_name,
                                                  latitude=latitude, longitude=longitude,
                                                  expiration=expiration, is_egg=False)

        await self.finish_reporting_manual_raid(ctx, raid)

    # Handles duplicate management as well as communicating the raid to the appropriate channels.
    async def finish_reporting_manual_raid(self, ctx, raid):
        hash_val = hash(raid)
        if hash_val in ctx.raids.hashed_active_raids:
            raid = ctx.raids.hashed_active_raids[hash_val]
            await ctx.author.send(f"This raid was already reported. It's number is {raid.display_id}")
        else:
            ctx.raids.track_raid(raid)
            raid.embed = ctx.raids.build_manual_raid_embed(raid)

            objects_to_save = await ctx.zones.send_to_raid_zones(raid, ctx.bot)
            RaidMessage.objects.bulk_create(objects_to_save)

            await ctx.send(f'Created raid #{raid.display_id}')

    @commands.command(aliases=['hatch'])
    @commands.has_role('Raid Reporter')
    async def hatched(self, ctx, raid_id: str, pokemon_name: str):
        """Reports what pokemon hatched from a raid egg. Existing cards for the raid will be deleted and new ones sent out.

        If a pokemon name is multiple words wrap it with double quotes.
        """
        raid = ctx.raids.get_raid(raid_id)
        if raid.is_exclusive:
            await ctx.author.send(f"This operation cannot be performed on EX raids")
        elif not raid.is_egg:
            await ctx.author.send(f"This raid has already hatched.")
        else:

            raid.is_egg = False
            raid.pokemon_name = pokemon_name
            raid.save()

            raid.embed = ctx.raids.build_manual_raid_embed(raid)

            for m in raid.messages:
                try:
                    if not ctx.bot.raids.logging_out:
                        if m.id in ctx.bot.raids.message_to_raid:
                            del ctx.bot.raids.message_to_raid[m.id]
                        elif m.id in ctx.bot.raids.private_channel_raids:
                            del ctx.bot.raids.private_channel_raids[m.id]
                    await m.delete()
                except discord.NotFound:
                    pass
            raid.messages = []

            if len(raid.participants) > 0:
                ctx.bot.raids.update_embed_participants(raid)

            # Send the new embed to the private channel
            if raid.private_channel is not None:
                private_raid_card = await raid.private_discord_channel.send(embed=raid.embed)
                # Add reaction to allow for easy leaving the raid.
                if not ctx.bot.raids.logging_out:
                    await private_raid_card.add_reaction('❌')
                    await private_raid_card.add_reaction('1⃣')
                    await private_raid_card.add_reaction('2⃣')
                    await private_raid_card.add_reaction('3⃣')
                    await private_raid_card.add_reaction('4⃣')
                    ctx.bot.raids.private_channel_raids[private_raid_card.id] = raid
                raid.messages.append(private_raid_card)

            objects_to_save = await ctx.zones.send_to_raid_zones(raid, ctx.bot)
            RaidMessage.objects.bulk_create(objects_to_save)

            await ctx.send(f'Hatched raid #{raid.display_id}')

def setup(bot):
    bot.add_cog(Rsvp(bot))
