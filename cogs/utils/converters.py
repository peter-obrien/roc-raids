from datetime import datetime

from discord.ext import commands


class ChannelOrMember(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            return await commands.TextChannelConverter().convert(ctx, argument)
        except commands.BadArgument:
            return await commands.MemberConverter().convert(ctx, argument)


class UserRaidEndTime(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            return datetime.strptime(argument, '%m/%d/%y %H')
        except ValueError:
            raise commands.BadArgument(f'Unable to parse end time `{argument}` expected "MM/DD/YY 24H"')
