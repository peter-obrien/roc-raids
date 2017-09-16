import discord
from decimal import Decimal, InvalidOperation
from discord.ext import commands


class Zones:
    """Reservation system"""

    def __init__(self, bot):
        self.bot = bot

    async def __after_invoke(self, ctx):
        if isinstance(ctx.channel, discord.TextChannel):
            await ctx.message.delete()

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def setup(self, ctx, *coordinates: str):
        if len(coordinates) == 2:
            try:
                latitude = Decimal(coordinates[0])
                longitude = Decimal(coordinates[1])

                if ctx.channel.id in ctx.zones.zones:
                    rz = ctx.zones.zones[ctx.channel.id]
                    rz.latitude = latitude
                    rz.longitude = longitude
                    rz.save()
                    await ctx.send('Raid zone coordinates updated')
                else:
                    rz = ctx.zones.create_zone(ctx.guild.id, ctx.channel.id, latitude, longitude)
                    rz.discord_destination = ctx.channel
                    await ctx.send('Raid zone created')
            except Exception as e:
                print(e)
                await ctx.send('There was an error handling your request.\n\n`{}`'.format(ctx.message.content))
        else:
            await ctx.send('Tried `{}` expected `!setup latitude longitude`'.format(ctx.message.content))

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def radius(self, ctx, *value: str):
        if len(value) == 1:
            try:
                radius = Decimal(value[0])
                if radius >= 1000.0:
                    await ctx.send('Radius is too large.')
                else:
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

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def zone(self, ctx, *value: str):
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

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def eggs(self, ctx, *value: str):
        if ctx.channel.id in ctx.zones.zones:
            rz = ctx.zones.zones[ctx.channel.id]
            if len(value) > 1:
                raise commands.TooManyArguments('`{}{} [on/off]`'.format(ctx.prefix, ctx.command))
            if value[0].lower() == 'on':
                rz.filter_eggs = True
                rz.save()
                await ctx.send('Egg notifications enabled.')
            elif value[0].lower() == 'off':
                rz.filter_eggs = False
                rz.save()
                await ctx.send('Egg notifications disabled.')
            else:
                raise commands.BadArgument('Unable to process argument `{}` for `{}`'.format(value[0], ctx.command))
        else:
            await ctx.send('Setup has not been run for this channel.')

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def info(self, ctx):
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

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def filter(self, ctx, *values: str):
        user_list = values
        try:
            if ctx.channel.id in ctx.zones.zones:
                rz = ctx.zones.zones[ctx.channel.id]
                new_filter = []
                if len(user_list) == 1:
                    if '0' != user_list[0]:
                        new_filter.append(int(user_list[0]))
                else:
                    for raid_level in user_list:
                        new_filter.append(int(raid_level))
                rz.filters['pokemon'].clear()
                rz.filters['pokemon'] = sorted(new_filter)
                rz.save()
                await ctx.send('Updated pokemon filter list: `{}`'.format(rz.filters['pokemon']))
            else:
                await ctx.send('Setup has not been run for this channel.')
        except ValueError:
            await ctx.send('Unable to process filter. Please verify your input: `{}`'.format(ctx.message.content))
            pass

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def level(self, ctx, *values: str):
        try:
            if ctx.channel.id in ctx.zones.zones:
                rz = ctx.zones.zones[ctx.channel.id]
                new_filter = []
                if '0' != values[0]:
                    for raid_level in values:
                        new_filter.append(int(raid_level))
                rz.filters['raid_levels'].clear()
                rz.filters['raid_levels'] = new_filter
                rz.save()
                await ctx.send('Updated raid level filter list')
            else:
                await ctx.send('Setup has not been run for this channel.')
        except ValueError:
            await ctx.send('Unable to process filter. Please verify your input: `{}`'.format(ctx.message.content))
            pass


def setup(bot):
    bot.add_cog(Zones(bot))
