from decimal import Decimal, InvalidOperation

from discord.ext import commands

from orm.models import RaidZone


class ChannelOrMember(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            return await commands.TextChannelConverter().convert(ctx, argument)
        except commands.BadArgument:
            return await commands.MemberConverter().convert(ctx, argument)


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
    async def zones(self, ctx, destination: ChannelOrMember = None):
        """List the named zones for a channel or member."""
        if destination is None:
            zone_id = ctx.channel.id
        else:
            zone_id = destination.id
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
    async def config(self, ctx, destination: ChannelOrMember, number: int):
        """Displays a random thing you request."""
        if ctx.invoked_subcommand is None:
            await ctx.send(f'Incorrect config subcommand passed. Try {ctx.prefix}help config')
        else:
            if destination.id in ctx.zones.zones and number <= len(ctx.zones.zones[destination.id]):
                ctx.rz = ctx.zones.zones[destination.id][number - 1]
            elif ctx.subcommand_passed == 'setup':
                ctx.rz = destination
            else:
                raise commands.BadArgument(
                    'The raid zone specified does not exist: `{} {}`'.format(destination, number))

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

    @config.command(name='radius', hidden=True, usage='xxx.x')
    async def radius_sub(self, ctx, value: str):
        try:
            radius = Decimal(value)
            if radius >= 1000.0:
                await ctx.send('Radius is too large.')
            else:
                ctx.rz.radius = radius
                ctx.rz.save()
                await ctx.send('Radius updated')
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

    @config.command(name='zone', hidden=True)
    async def zone_sub(self, ctx, value: str):
        """Toggles if this raid zone is active or not."""
        if value == 'on':
            ctx.rz.active = True
            ctx.rz.save()
            await ctx.send('Raid messages enabled.')
        elif value == 'off':
            ctx.rz.active = False
            ctx.rz.save()
            await ctx.send('Raid messages disabled.')
        else:
            raise commands.BadArgument('Unable to process argument `{}` for `{}`'.format(value, ctx.command))

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

    @config.command(name='eggs', hidden=True, usage='on/off')
    async def eggs_sub(self, ctx, value: str):
        """Toggles whether this zone will receive raid eggs."""
        if value.lower() == 'on':
            ctx.rz.filter_eggs = True
            ctx.rz.save()
            await ctx.send('Egg notifications enabled.')
        elif value.lower() == 'off':
            ctx.rz.filter_eggs = False
            ctx.rz.save()
            await ctx.send('Egg notifications disabled.')
        else:
            raise commands.BadArgument('Unable to process argument `{}` for `{}`'.format(value, ctx.command))

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def info(self, ctx):
        """Displays the raid zones configuration for a channel."""
        if ctx.channel.id in ctx.zones.zones:
            rz = ctx.zones.zones[ctx.channel.id][0]
            output = '''Here is the raid zone configuration for this channel:
Name: `{}`
Status: `{}`
Coordinates: `{}, {}`
Radius: `{}`
Egg Notifications: `{}`
Pokemon Filtering By Raid Level: `{}`
Levels: `{}`
Pokemon: `{}`'''.format(rz.name, rz.status, rz.latitude, rz.longitude, rz.radius, rz.egg_status,
                        rz.pokemon_by_raid_level_status,
                        rz.filters['raid_levels'], rz.filters['pokemon'])
            await ctx.send(output)
        else:
            await ctx.send('This channel is not configured as a raid zone.')

    @config.command(name='info', hidden=True)
    async def info_sub(self, ctx):
        """Displays the raid zones configuration for a channel."""
        output = '''Here is the raid zone configuration for this channel:
Name: `{}`
Status: `{}`
Coordinates: `{}, {}`
Radius: `{}`
Egg Notifications: `{}`
Pokemon Filtering By Raid Level: `{}`
Levels: `{}`
Pokemon: `{}`'''.format(ctx.rz.name, ctx.rz.status, ctx.rz.latitude, ctx.rz.longitude, ctx.rz.radius, ctx.rz.egg_status,
                        ctx.rz.pokemon_by_raid_level_status,
                        ctx.rz.filters['raid_levels'], ctx.rz.filters['pokemon'])
        await ctx.send(output)

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

    @config.command(name='filter', hidden=True)
    async def filter_sub(self, ctx, *pokemon_numbers: str):
        """Allows for a list of pokemon numbers to enable filtering. Use `0` to clear the filter."""
        if len(pokemon_numbers) == 0:
            await ctx.author('Please provide at least one pokemon number for command `{}`'.format(ctx.command))
            return
        try:
            new_filter = []
            if pokemon_numbers[0] != '0':
                for raid_level in pokemon_numbers:
                    new_filter.append(int(raid_level))
            ctx.rz.filters['pokemon'].clear()
            ctx.rz.filters['pokemon'] = sorted(new_filter)
            ctx.rz.save()
            await ctx.send('Updated pokemon filter list: `{}`'.format(rz.filters['pokemon']))
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

    @config.command(name='level', hidden=True)
    async def level_sub(self, ctx, *raid_levels: str):
        """Allows for a list of raid levels to accept. Use `0` to clear the filter."""
        if len(raid_levels) == 0:
            await ctx.author('Please provide at least one raid level for command `{}`'.format(ctx.command))
            return
        try:
            new_filter = []
            if '0' != raid_levels[0]:
                for raid_level in raid_levels:
                    new_filter.append(int(raid_level))
            ctx.rz.filters['raid_levels'].clear()
            ctx.rz.filters['raid_levels'] = new_filter
            ctx.rz.save()
            await ctx.send('Updated raid level filter list')
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

    @config.command(name='monlevels', hidden=True, usage='on/off')
    async def monlevels_sub(self, ctx, value: str):
        """Toggles whether this zone will have pokemon filtered by raid level. Use this if you only want to filter by pokemon number for non eggs."""
        if value.lower() == 'on':
            ctx.rz.filter_pokemon_by_raid_level = True
            ctx.rz.save()
            await ctx.send('Pokemon filtering by raid level enabled.')
        elif value.lower() == 'off':
            ctx.rz.filter_pokemon_by_raid_level = False
            ctx.rz.save()
            await ctx.send('Pokemon filtering by raid level disabled.')
        else:
            raise commands.BadArgument('Unable to process argument `{}` for `{}`'.format(value, ctx.command))


def setup(bot):
    bot.add_cog(Zones(bot))
