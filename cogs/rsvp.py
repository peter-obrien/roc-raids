from discord.ext import commands

class Rsvp:
    """Reservation system"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx):
       print('join called')

    @commands.command()
    async def leave(self, ctx):
        print('leave called')

def setup(bot):
    bot.add_cog(Rsvp(bot))