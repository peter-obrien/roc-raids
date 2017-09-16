import discord
from discord.ext import commands
from django.db import transaction

from orm.models import RaidMessage


class Rsvp:
    """Reservation system"""

    def __init__(self, bot):
        self.bot = bot
        self.private_channel_no_access = discord.PermissionOverwrite(read_messages=False)
        self.private_channel_access = discord.PermissionOverwrite(read_messages=True, mention_everyone=True)

    async def __after_invoke(self, ctx):
        if isinstance(ctx.channel, discord.TextChannel):
            await ctx.message.delete()

    @commands.command()
    async def join(self, ctx, *join_details: str):
        if len(join_details) == 0:
            raise commands.BadArgument('Please provide the number for the raid that you wish to attend.')

        user_raid_id = join_details[0]
        party_size = '1'
        notes = None
        author = ctx.author
        if len(join_details) > 1:
            party_size = join_details[1]
        if len(join_details) > 2:
            notes = ' '.join(str(x) for x in join_details[2:])

        # If the message is coming from PM we want to use the server's version of the user.
        if isinstance(ctx.channel, discord.abc.PrivateChannel):
            author = ctx.bot_guild.get_member(author.id)

        raid = ctx.raids.get_raid(user_raid_id)

        private_raid_channel = raid.private_discord_channel
        if private_raid_channel is None:
            overwrites = {
                ctx.bot_guild.default_role: self.private_channel_no_access,
                ctx.bot_guild.me: self.private_channel_access
            }
            private_raid_channel = await ctx.bot_guild.create_text_channel('raid-{}-chat'.format(raid.display_id),
                                                                           overwrites=overwrites)
            raid.private_discord_channel = private_raid_channel

            # Send the raid card to the top of the channel.
            private_raid_card = await raid.private_discord_channel.send(embed=raid.embed)
            raid.messages.append(private_raid_card)

            with transaction.atomic():
                raid.private_channel = private_raid_channel.id
                raid.save()
                RaidMessage(raid=raid, channel=private_raid_channel.id, message=private_raid_card.id).save()

        # Add this user to the raid and update all the embeds for the raid.
        result_tuple = ctx.raids.add_participant(raid, author.id, author.display_name, party_size, notes)
        for msg in raid.messages:
            try:
                await msg.edit(embed=raid.embed)
            except discord.errors.NotFound:
                raid.messages.remove(msg)
                pass

        # Add the user to the private channel for the raid
        await raid.private_discord_channel.set_permissions(author, overwrite=self.private_channel_access)
        await raid.private_discord_channel.send('{}{}'.format(author.mention, result_tuple[0].details()))

        # Send message to the RSVP channel if the command was invoked publicly
        if isinstance(ctx.channel, discord.abc.GuildChannel):
            await ctx.rsvp_channel.send(result_tuple[1])

    @commands.command()
    async def leave(self, ctx, *raid_id: str):
        if len(raid_id) == 0:
            raise commands.BadArgument('Please provide the number for the raid that you wish to leave.')
        elif len(raid_id) > 1:
            raise commands.TooManyArguments('Please only provide a raid id to this command.')

        user_raid_id = raid_id[0]
        author = ctx.author
        # If the message is coming from PM we want to use the server's version of the user.
        if isinstance(ctx.channel, discord.abc.PrivateChannel):
            author = ctx.bot_guild.get_member(author.id)

        raid = ctx.raids.get_raid(user_raid_id)
        display_msg = ctx.raids.remove_participant(raid, author.id, author.display_name)

        if display_msg is not None:
            # Remove the user to the private channel for the raid
            await raid.private_discord_channel.set_permissions(author, overwrite=None)
            await raid.private_discord_channel.send('**{}** is no longer attending'.format(author.display_name))

            for msg in raid.messages:
                await msg.edit(embed=raid.embed)
            if isinstance(ctx.channel, discord.abc.GuildChannel):
                await ctx.rsvp_channel.send(display_msg)

    @commands.command()
    async def who(self, ctx, *raid_id: str):
        if len(raid_id) == 0:
            raise commands.BadArgument('Raid id not provided to who command.')

        user_raid_id = raid_id[0]
        raid = ctx.raids.get_raid(user_raid_id)
        msg = ctx.raids.get_participant_printout(raid)
        await ctx.author.send(msg)

    @commands.command(aliases=['raid'])
    async def details(self, ctx, *raid_id: str):
        if len(raid_id) == 0:
            raise commands.BadArgument('Please specify what raid you want.')

        user_raid_id = raid_id[0]
        raid = ctx.raids.get_raid(user_raid_id)
        await ctx.author.send(embed=raid.embed)


def setup(bot):
    bot.add_cog(Rsvp(bot))
