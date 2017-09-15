import discord
from discord.ext import commands


class Zones:
    """Reservation system"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def setup(self, ctx, *coordinates: str):
        try:
            print('setup called')
        finally:
            if isinstance(ctx.channel, discord.TextChannel):
                await ctx.message.delete()

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def radius(self, ctx, *value: str):
        try:
            print('radius called')
        finally:
            if isinstance(ctx.channel, discord.TextChannel):
                await ctx.message.delete()

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def zone(self, ctx, *value: str):
        try:
            if len(value) == 1:
                await ctx.send('zone command called with `{}`'.format(value[0]))
            else:
                await ctx.send('Incorrect number of arguments to call `zone`')
        finally:
            if isinstance(ctx.channel, discord.TextChannel):
                await ctx.message.delete()


def setup(bot):
    bot.add_cog(Zones(bot))
