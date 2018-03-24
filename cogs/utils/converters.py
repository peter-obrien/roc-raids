from datetime import datetime

from discord.ext import commands
from django.utils import timezone


class ChannelOrMember(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            return await commands.TextChannelConverter().convert(ctx, argument)
        except commands.BadArgument:
            return await commands.MemberConverter().convert(ctx, argument)


class UserRaidEndTimeAndDate(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            return datetime.strptime(argument, '%m/%d/%y %H:%M')
        except ValueError:
            raise commands.BadArgument(f'Unable to parse end time `{argument}` expected "mm/dd/yy 24H:MM"')


class UserRaidEndTime(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            current_date = timezone.localdate(timezone.now())
            user_time = datetime.strptime(argument, '%H:%M')
            return datetime(year=current_date.year, month=current_date.month, day=current_date.day, hour=user_time.hour,
                            minute=user_time.minute)
        except ValueError:
            raise commands.BadArgument(f'Unable to parse end time `{argument}` expected "24H:MM"')
