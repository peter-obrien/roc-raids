import discord
from discord.ext import commands


class Rsvp:
    """Reservation system"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx, *raid_id: str):
        try:
            print('join called')
        finally:
            if isinstance(ctx.channel, discord.TextChannel):
                await ctx.message.delete()

    @commands.command()
    async def leave(self, ctx, *raid_id: str):
        try:
            print('leave called')
        finally:
            if isinstance(ctx.channel, discord.TextChannel):
                await ctx.message.delete()


def setup(bot):
    bot.add_cog(Rsvp(bot))
