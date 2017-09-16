import discord
from discord.ext import commands


class Rsvp:
    """Reservation system"""

    def __init__(self, bot):
        self.bot = bot

    async def __after_invoke(self, ctx):
        if isinstance(ctx.channel, discord.TextChannel):
            await ctx.message.delete()

    @commands.command()
    async def join(self, ctx, *raid_id: str):
        print('join called')

    @commands.command()
    async def leave(self, ctx, *raid_id: str):
        print('leave called')


def setup(bot):
    bot.add_cog(Rsvp(bot))
