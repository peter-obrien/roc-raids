import discord
from decimal import Decimal, InvalidOperation
from discord.ext import commands

from orm.models import RaidZone


class Zones:
    """Raid zone setup and configuration. To invoke user must have Manage Channels permission."""

    def __init__(self, bot):
        self.bot = bot

    # async def __after_invoke(self, ctx):
    #     if isinstance(ctx.channel, discord.TextChannel):
    #         await ctx.message.delete()

    @commands.command(hidden=True, usage='channel_id/user_id')
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def zones(self, ctx, destination: int = None):
        """List the named zones for a channel or member."""
        zone_id = destination
        if destination is None:
            zone_id = ctx.channel.id
        listed_zones = ctx.zones.zones[zone_id]
        if len(listed_zones) == 0:
            await ctx.send('There are no available zones.')
        else:
            msg = 'Here are the available raid zones:'
            for index in range(0, len(listed_zones)):
                msg += '\n\t{}) {}'.format(index + 1, listed_zones[index].name)
            await ctx.send(msg)

    @commands.group(pass_context=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def config(self, ctx, zone_number: int, zone_id: int):
        """Displays a random thing you request."""
        if ctx.invoked_subcommand is None:
            await ctx.send(f'Incorrect config subcommand passed. Try {ctx.prefix}help config')
        else:
            # Lookup the channel or user
            destination = ctx.guild.get_channel(zone_id)
            if destination is None:
                destination = ctx.guild.get_member(zone_id)
            if destination is None:
                raise commands.BadArgument('`zone_id` could not be resolved to a valid user or channel.')

            if zone_id in ctx.zones.zones and zone_number <= len(ctx.zones.zones[zone_id]):
                ctx.rz = ctx.zones.zones[zone_id][zone_number - 1]
            elif ctx.subcommand_passed == 'setup':
                ctx.rz = destination
            else:
                raise commands.BadArgument(
                    'The raid zone specified does not exist: `{} {}`'.format(zone_number, zone_id))

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def setup(self, ctx, latitude: str, longitude: str):
        try:
            lat = Decimal(latitude)
            lon = Decimal(longitude)

            if ctx.channel.id in ctx.zones.zones:
                rz = ctx.zones.zones[ctx.channel.id][0]
                rz.latitude = lat
                rz.longitude = lon
                rz.save()
                await ctx.send('Raid zone coordinates updated')
            else:
                rz = ctx.zones.create_zone(ctx.guild.id, ctx.channel.id, lat, lon)
                rz.discord_destination = ctx.channel
                await ctx.send('Raid zone created')
        except Exception as e:
            print(e)
            await ctx.send('There was an error handling your request.\n\n`{}`'.format(ctx.message.content))

    @config.command(name='setup')
    async def setup_sub(self, ctx, latitude: str, longitude: str):
        try:
            lat = Decimal(latitude)
            lon = Decimal(longitude)

            if isinstance(ctx.rz, RaidZone):
                ctx.rz.latitude = lat
                ctx.rz.longitude = lon
                ctx.rz.save()
                await ctx.send('Raid zone coordinates updated')
            else:
                rz = ctx.zones.create_zone(ctx.guild.id, ctx.rz.id, lat, lon)
                rz.discord_destination = ctx.rz
                await ctx.send('Raid zone created')
        except Exception as e:
            print(e)
            await ctx.send('There was an error handling your request.\n\n`{}`'.format(ctx.message.content))

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def rename(self, ctx, new_name: str):
        if ctx.message.channel.id in ctx.zones.zones:
            rz = ctx.zones.zones[ctx.channel.id][0]
            rz.name = new_name
            rz.save()
            await ctx.send('Zone renamed')
        else:
            await ctx.send('Setup has not been run for this channel.')

    @config.command(name='rename')
    async def rename_sub(self, ctx, new_name: str):
        ctx.rz.name = new_name
        ctx.rz.save()
        await ctx.send('Zone renamed')

    @commands.command(hidden=True, usage='xxx.x')
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def radius(self, ctx, value: str):
        try:
            radius = Decimal(value)
            if radius >= 1000.0:
                await ctx.send('Radius is too large.')
            else:
                if ctx.message.channel.id in ctx.zones.zones:
                    rz = ctx.zones.zones[ctx.channel.id][0]
                    rz.radius = radius
                    rz.save()
                    await ctx.send('Radius updated')
                else:
                    await ctx.send('Setup has not been run for this channel.')
        except InvalidOperation:
            raise commands.BadArgument('Invalid radius: {}'.format(value))

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def zone(self, ctx, value: str):
        """Toggles if this raid zone is active or not."""
        if ctx.channel.id in ctx.zones.zones:
            rz = ctx.zones.zones[ctx.channel.id][0]
            if value == 'on':
                rz.active = True
                rz.save()
                await ctx.send('Raid messages enabled.')
            elif value == 'off':
                rz.active = False
                rz.save()
                await ctx.send('Raid messages disabled.')
            else:
                raise commands.BadArgument('Unable to process argument `{}` for `{}`'.format(value, ctx.command))

        else:
            await ctx.send('Setup has not been run for this channel.')

    @commands.command(hidden=True, usage='on/off')
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def eggs(self, ctx, value: str):
        """Toggles whether this zone will receive raid eggs."""
        if ctx.channel.id in ctx.zones.zones:
            rz = ctx.zones.zones[ctx.channel.id][0]
            if value.lower() == 'on':
                rz.filter_eggs = True
                rz.save()
                await ctx.send('Egg notifications enabled.')
            elif value.lower() == 'off':
                rz.filter_eggs = False
                rz.save()
                await ctx.send('Egg notifications disabled.')
            else:
                raise commands.BadArgument('Unable to process argument `{}` for `{}`'.format(value, ctx.command))
        else:
            await ctx.send('Setup has not been run for this channel.')

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def info(self, ctx):
        """Displays the raid zones configuration for a channel."""
        if ctx.channel.id in ctx.zones.zones:
            rz = ctx.zones.zones[ctx.channel.id][0]
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

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def filter(self, ctx, *pokemon_numbers: str):
        """Allows for a list of pokemon numbers to enable filtering. Use `0` to clear the filter."""
        if len(pokemon_numbers) == 0:
            await ctx.author('Please provide at least one pokemon number for command `{}`'.format(ctx.command))
            return
        try:
            if ctx.channel.id in ctx.zones.zones:
                rz = ctx.zones.zones[ctx.channel.id][0]
                new_filter = []
                if pokemon_numbers[0] != '0':
                    for raid_level in pokemon_numbers:
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

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def level(self, ctx, *raid_levels: str):
        """Allows for a list of raid levels to accept. Use `0` to clear the filter."""
        if len(raid_levels) == 0:
            await ctx.author('Please provide at least one raid level for command `{}`'.format(ctx.command))
            return
        try:
            if ctx.channel.id in ctx.zones.zones:
                rz = ctx.zones.zones[ctx.channel.id][0]
                new_filter = []
                if '0' != raid_levels[0]:
                    for raid_level in raid_levels:
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

    @commands.command(hidden=True, usage='on/off')
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def monlevels(self, ctx, value: str):
        """Toggles whether this zone will have pokemon filtered by raid level. Use this if you only want to filter by pokemon number for non eggs."""
        if ctx.channel.id in ctx.zones.zones:
            rz = ctx.zones.zones[ctx.channel.id][0]
            if value.lower() == 'on':
                rz.filter_pokemon_by_raid_level = True
                rz.save()
                await ctx.send('Pokemon filtering by raid level enabled.')
            elif value.lower() == 'off':
                rz.filter_pokemon_by_raid_level = False
                rz.save()
                await ctx.send('Pokemon filtering by raid level disabled.')
            else:
                raise commands.BadArgument('Unable to process argument `{}` for `{}`'.format(value, ctx.command))
        else:
            await ctx.send('Setup has not been run for this channel.')


def setup(bot):
    bot.add_cog(Zones(bot))
