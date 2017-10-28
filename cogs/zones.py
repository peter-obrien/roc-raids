from decimal import Decimal, InvalidOperation

import discord
from discord.ext import commands

from cogs.utils.converters import ChannelOrMember
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
                msg += f'\n\t{index + 1}) {listed_zones[index].name}'
            await ctx.send(msg)

    @commands.group(pass_context=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def config(self, ctx, destination: ChannelOrMember, number: int):
        """Allow for configuration of a specified raid zone.

        Allows for multiple zones to be setup for a channel or setting up a zone for a member."""
        if ctx.invoked_subcommand is None:
            await ctx.send(f'Incorrect config subcommand passed. Try {ctx.prefix}help config')
        else:
            if destination.id in ctx.zones.zones and number <= len(ctx.zones.zones[destination.id]):
                ctx.rz = ctx.zones.zones[destination.id][number - 1]
            elif ctx.subcommand_passed == 'setup':
                ctx.rz = destination
            else:
                raise commands.BadArgument(
                    f'The raid zone specified does not exist: `{destination} {number}`')

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def setup(self, ctx, latitude: str, longitude: str):
        """Creates a new raid zone or changes the coordinates of an existing one."""
        try:
            lat = Decimal(latitude)
            lon = Decimal(longitude)

            if ctx.channel.id in ctx.zones.zones:
                rz = ctx.zones.zones[ctx.channel.id][0]
                rz.latitude = lat
                rz.longitude = lon
                rz.save()
                await ctx.send(f'Raid zone coordinates updated: {lat}, {lon}')
            else:
                rz = ctx.zones.create_zone(ctx.guild.id, ctx.channel.id, lat, lon)
                rz.discord_destination = ctx.channel
                await ctx.send(f'Raid zone created: {lat}, {lon}')
        except Exception as e:
            print(e)
            await ctx.send(f'There was an error handling your request.\n\n`{ctx.message.content}`')

    @config.command(name='setup')
    async def setup_sub(self, ctx, latitude: str, longitude: str):
        """Creates a new raid zone or changes the coordinates of an existing one."""
        try:
            lat = Decimal(latitude)
            lon = Decimal(longitude)

            if isinstance(ctx.rz, RaidZone):
                ctx.rz.latitude = lat
                ctx.rz.longitude = lon
                ctx.rz.save()
                await ctx.rz.discord_destination.send(f'Raid zone coordinates updated: {lat}, {lon}')
                await ctx.send(f'Raid zone coordinates updated: {lat}, {lon}')
            else:
                rz = ctx.zones.create_zone(ctx.guild.id, ctx.rz.id, lat, lon)
                rz.discord_destination = ctx.rz
                await ctx.rz.send(f'Raid zone created: {lat}, {lon}')
                await ctx.send(f'Raid zone created: {lat}, {lon}')
        except Exception as e:
            print(e)
            await ctx.send(f'There was an error handling your request.\n\n`{ctx.message.content}`')

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def rename(self, ctx, new_name: str):
        """Changes the name of a zone."""
        if ctx.message.channel.id in ctx.zones.zones:
            rz = ctx.zones.zones[ctx.channel.id][0]
            rz.name = new_name
            rz.save()
            await ctx.send(f'Zone renamed to {new_name}')
        else:
            await ctx.send('Setup has not been run for this channel.')

    @config.command(name='rename')
    async def rename_sub(self, ctx, new_name: str):
        """Changes the name of a zone."""
        ctx.rz.name = new_name
        ctx.rz.save()
        await ctx.rz.discord_destination.send(f'Zone renamed to {new_name}')
        await ctx.send(f'Zone renamed to {new_name}')

    @commands.command(hidden=True, usage='xxx.x')
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def radius(self, ctx, value: str):
        """Sets the radius for a zone."""
        try:
            radius = Decimal(value)
            if radius >= 1000.0:
                await ctx.send('Radius is too large.')
            else:
                if ctx.message.channel.id in ctx.zones.zones:
                    rz = ctx.zones.zones[ctx.channel.id][0]
                    rz.radius = radius
                    rz.save()
                    await ctx.send(f'Radius updated to {radius}')
                else:
                    await ctx.send('Setup has not been run for this channel.')
        except InvalidOperation:
            raise commands.BadArgument(f'Invalid radius: {value}')

    @config.command(name='radius', hidden=True, usage='xxx.x')
    async def radius_sub(self, ctx, value: str):
        """Sets the radius for a zone."""
        try:
            radius = Decimal(value)
            if radius >= 1000.0:
                await ctx.send('Radius is too large.')
            else:
                ctx.rz.radius = radius
                ctx.rz.save()
                await ctx.rz.discord_destination.send(f'Radius updated to {radius}')
                await ctx.send(f'Radius updated to {radius}')
        except InvalidOperation:
            raise commands.BadArgument(f'Invalid radius: {value}')

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
                raise commands.BadArgument(f'Unable to process argument `{value}` for `{ctx.command}`')

        else:
            await ctx.send('Setup has not been run for this channel.')

    @config.command(name='zone', hidden=True)
    async def zone_sub(self, ctx, value: str):
        """Toggles if this raid zone is active or not."""
        if value == 'on':
            ctx.rz.active = True
            ctx.rz.save()
            await ctx.rz.discord_destination.send('Raid messages enabled.')
            await ctx.send('Raid messages enabled.')
        elif value == 'off':
            ctx.rz.active = False
            ctx.rz.save()
            await ctx.rz.discord_destination.send('Raid messages disabled.')
            await ctx.send('Raid messages disabled.')
        else:
            raise commands.BadArgument(f'Unable to process argument `{value}` for `{ctx.command}`')

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
                raise commands.BadArgument(f'Unable to process argument `{value}` for `{ctx.command}`')
        else:
            await ctx.send('Setup has not been run for this channel.')

    @config.command(name='eggs', hidden=True, usage='on/off')
    async def eggs_sub(self, ctx, value: str):
        """Toggles whether this zone will receive raid eggs."""
        if value.lower() == 'on':
            ctx.rz.filter_eggs = True
            ctx.rz.save()
            await ctx.rz.discord_destination.send('Egg notifications enabled.')
            await ctx.send('Egg notifications enabled.')
        elif value.lower() == 'off':
            ctx.rz.filter_eggs = False
            ctx.rz.save()
            await ctx.rz.discord_destination.send('Egg notifications disabled.')
            await ctx.send('Egg notifications disabled.')
        else:
            raise commands.BadArgument(f'Unable to process argument `{value}` for `{ctx.command}`')

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def info(self, ctx):
        """Displays the raid zones configuration for a channel."""
        if ctx.channel.id in ctx.zones.zones:
            rz = ctx.zones.zones[ctx.channel.id][0]
            output = f'''Here is the raid zone configuration for this channel:
Name: `{rz.name}`
Status: `{rz.status}`
Coordinates: `{rz.latitude}, {rz.longitude}`
Radius: `{rz.radius}`
Egg Notifications: `{rz.egg_status}`
Pokemon Filtering By Raid Level: `{rz.pokemon_by_raid_level_status}`
Levels: `{rz.filters['raid_levels']}`
Pokemon: `{rz.filters['pokemon']}`'''
            await ctx.send(output)
        else:
            await ctx.send('This channel is not configured as a raid zone.')

    @config.command(name='info', hidden=True)
    async def info_sub(self, ctx):
        """Displays the raid zones configuration for a channel."""
        output = f'''Here is the raid zone configuration for this channel:
Name: `{ctx.rz.name}`
Status: `{ctx.rz.status}`
Coordinates: `{ctx.rz.latitude}, {ctx.rz.longitude}`
Radius: `{ctx.rz.radius}`
Egg Notifications: `{ctx.rz.egg_status}`
Pokemon Filtering By Raid Level: `{ctx.rz.pokemon_by_raid_level_status}`
Levels: `{ctx.rz.filters['raid_levels']}`
Pokemon: `{ctx.rz.filters['pokemon']}`'''
        await ctx.send(output)

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def filter(self, ctx, *pokemon_numbers: str):
        """Allows for a list of pokemon numbers to enable filtering. Use `0` to clear the filter."""
        if len(pokemon_numbers) == 0:
            await ctx.author(f'Please provide at least one pokemon number for command `{ctx.command}`')
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
                await ctx.send(f"Updated pokemon filter list: `{rz.filters['pokemon']}`")
            else:
                await ctx.send('Setup has not been run for this channel.')
        except ValueError:
            await ctx.send(f'Unable to process filter. Please verify your input: `{ctx.message.content}`')
            pass

    @config.command(name='filter', hidden=True)
    async def filter_sub(self, ctx, *pokemon_numbers: str):
        """Allows for a list of pokemon numbers to enable filtering. Use `0` to clear the filter."""
        if len(pokemon_numbers) == 0:
            await ctx.author(f'Please provide at least one pokemon number for command `{ctx.command}`')
            return
        try:
            new_filter = []
            if pokemon_numbers[0] != '0':
                for raid_level in pokemon_numbers:
                    new_filter.append(int(raid_level))
            ctx.rz.filters['pokemon'].clear()
            ctx.rz.filters['pokemon'] = sorted(new_filter)
            ctx.rz.save()
            await ctx.rz.discord_destination.send(f"Updated pokemon filter list: `{ctx.rz.filters['pokemon']}`")
            await ctx.send(f"Updated pokemon filter list: `{ctx.rz.filters['pokemon']}`")
        except ValueError:
            await ctx.send(f'Unable to process filter. Please verify your input: `{ctx.message.content}`')
            pass

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def level(self, ctx, *raid_levels: str):
        """Allows for a list of raid levels to accept. Use `0` to clear the filter."""
        if len(raid_levels) == 0:
            await ctx.author(f'Please provide at least one raid level for command `{ctx.command}`')
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
                await ctx.send(f"Updated raid level filter list: `{ctx.rz.filters['raid_levels']}`")
            else:
                await ctx.send('Setup has not been run for this channel.')
        except ValueError:
            await ctx.send(f'Unable to process filter. Please verify your input: `{ctx.message.content}`')
            pass

    @config.command(name='level', hidden=True)
    async def level_sub(self, ctx, *raid_levels: str):
        """Allows for a list of raid levels to accept. Use `0` to clear the filter."""
        if len(raid_levels) == 0:
            await ctx.author(f'Please provide at least one raid level for command `{ctx.command}`')
            return
        try:
            new_filter = []
            if '0' != raid_levels[0]:
                for raid_level in raid_levels:
                    new_filter.append(int(raid_level))
            ctx.rz.filters['raid_levels'].clear()
            ctx.rz.filters['raid_levels'] = new_filter
            ctx.rz.save()
            await ctx.rz.discord_destination.send(f"Updated raid level filter list: `{ctx.rz.filters['raid_levels']}`")
            await ctx.send(f"Updated raid level filter list: `{ctx.rz.filters['raid_levels']}`")
        except ValueError:
            await ctx.send(f'Unable to process filter. Please verify your input: `{ctx.message.content}`')
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
                raise commands.BadArgument(f'Unable to process argument `{value}` for `{ctx.command}`')
        else:
            await ctx.send('Setup has not been run for this channel.')

    @config.command(name='monlevels', hidden=True, usage='on/off')
    async def monlevels_sub(self, ctx, value: str):
        """Toggles whether this zone will have pokemon filtered by raid level. Use this if you only want to filter by pokemon number for non eggs."""
        if value.lower() == 'on':
            ctx.rz.filter_pokemon_by_raid_level = True
            ctx.rz.save()
            await ctx.rz.discord_destination.send('Pokemon filtering by raid level enabled.')
            await ctx.send('Pokemon filtering by raid level enabled.')
        elif value.lower() == 'off':
            ctx.rz.filter_pokemon_by_raid_level = False
            ctx.rz.save()
            await ctx.rz.discord_destination.send('Pokemon filtering by raid level disabled.')
            await ctx.send('Pokemon filtering by raid level disabled.')
        else:
            raise commands.BadArgument(f'Unable to process argument `{value}` for `{ctx.command}`')

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def delete_zone(self, ctx):
        """Deletes a raid zone"""
        if ctx.channel.id in ctx.zones.zones:
            rz = ctx.zones.zones[ctx.channel.id][0]
            author = ctx.author
            channel = ctx.channel
            await ctx.send(f'Are you sure you want to delete `{rz.name}`? Enter `yes` to confirm.')

            def check(m):
                return m.channel == channel and m.author == author

            response = await ctx.bot.wait_for('message', check=check)

            if response.content.lower() == 'yes':
                await ctx.send(f'Zone `{rz.name}` deleted')
                ctx.zones.zones[ctx.channel.id].remove(rz)
                if len(ctx.zones.zones[ctx.channel.id]) == 0:
                    ctx.zones.zones.pop(ctx.channel.id, None)
                rz.delete()
            else:
                await ctx.send('Zone not deleted')
        else:
            await ctx.send('There is no raid zone to delete.')

    @config.command(name='delete_zone', hidden=True)
    async def delete_zone_sub(self, ctx):
        """Deletes a raid zone"""
        rz = ctx.rz
        author = ctx.author
        channel = ctx.channel
        await ctx.send(f'Are you sure you want to delete `{rz.name}`? Enter `yes` to confirm.')

        def check(m):
            return m.channel == channel and m.author == author

        response = await ctx.bot.wait_for('message', check=check)

        if response.content.lower() == 'yes':
            await ctx.send(f'Zone `{rz.name}` deleted')
            ctx.zones.zones[ctx.channel.id].remove(rz)
            if len(ctx.zones.zones[ctx.channel.id]) == 0:
                ctx.zones.zones.pop(ctx.channel.id, None)
            rz.delete()
        else:
            await ctx.send('Zone not deleted')

    @commands.command(name="myzones")
    async def my_zones(self, ctx):
        """Lists your private raid zones"""
        if ctx.author.id in ctx.zones.zones:
            listed_zones = ctx.zones.zones[ctx.author.id]
            msg = 'Here are your available raid zones:'
            for index in range(0, len(listed_zones)):
                msg += f'\n\t{index + 1}) {listed_zones[index].name}'
            await ctx.author.send(msg)
        else:
            await ctx.author.send('You do not have any private zones setup.')

    @my_zones.after_invoke
    async def after_my_zones(self, ctx):
        if isinstance(ctx.channel, discord.TextChannel):
            await ctx.message.delete()

def setup(bot):
    bot.add_cog(Zones(bot))
