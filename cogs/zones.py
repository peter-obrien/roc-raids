import discord
from decimal import Decimal, InvalidOperation
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
            if len(value) == 1:
                try:
                    radius = Decimal(value[0])
                    if ctx.message.channel.id in ctx.zones.zones:
                        rz = ctx.zones.zones[ctx.channel.id]
                        rz.radius = radius
                        rz.save()
                        await ctx.send('Radius updated')
                    else:
                        await ctx.send('Setup has not been run for this channel.')
                except InvalidOperation:
                    await ctx.send('Invalid radius: {}'.format(value[0]))
            else:
                await ctx.send('Tried `{}` expected `!radius xxx.x`'.format(ctx.message.content))
        finally:
            if isinstance(ctx.channel, discord.TextChannel):
                await ctx.message.delete()

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def zone(self, ctx, *value: str):
        try:
            if len(value) == 1:
                if ctx.channel.id in ctx.zones.zones:
                    rz = ctx.zones.zones[ctx.channel.id]
                    if value[0] == 'on':
                        rz.active = True
                        rz.save()
                        await ctx.send('Raid messages enabled.')
                    elif value[0] == 'off':
                        rz.active = False
                        rz.save()
                        await ctx.send('Raid messages disabled.')
                    else:
                        await ctx.send('Unknown command: `{}`'.format(ctx.message.content))

                else:
                    await ctx.send('Setup has not been run for this channel.')
            else:
                await ctx.send(
                    'Tried `{}` expected `!zone on/off`'.format(ctx.message.content))
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
