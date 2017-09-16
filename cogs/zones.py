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

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def info(self, ctx):
        try:
            if ctx.channel.id in ctx.zones.zones:
                rz = ctx.zones.zones[ctx.channel.id]
                output = '''Here is the raid zone configuration for this channel:
Status: `{}`
Coordinates: `{}, {}`
Radius: `{}`
Egg Notifications: `{}`
Pokemon Filtering By Raid Level: `{}`
Levels: `{}`
Pokemon: `{}`'''.format(rz.status, rz.latitude, rz.longitude, rz.radius, rz.egg_status,
                                        rz.pokemon_by_raid_level_status,
                                        rz.filters['raid_levels'], rz.filters['pokemon'])
                await ctx.send(output)
            else:
                await ctx.send('This channel is not configured as a raid zone.')
        finally:
            if isinstance(ctx.channel, discord.TextChannel):
                await ctx.message.delete()

def setup(bot):
    bot.add_cog(Zones(bot))
