import discord
from discord.ext import commands

from orm.models import BotOnlyChannel


class Admin:
    """Commands for the owner, admins, and mods."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    async def clear(self, ctx, *msg_count_to_delete: str):
        if ctx.author == ctx.guild.owner:
            if len(msg_count_to_delete) != 1 or not msg_count_to_delete[0].isdigit() or int(
                    msg_count_to_delete[0]) > 100 or not isinstance(ctx.channel,
                                                                    discord.TextChannel):
                await ctx.send(content='Please only provide a number of messages to delete less than 100.')
            else:
                try:
                    message_to_delete = []
                    async for message in ctx.message.channel.history(limit=int(msg_count_to_delete[0])):
                        message_to_delete.append(message)
                    await ctx.channel.delete_messages(message_to_delete)
                except discord.HTTPException:
                    # Assume that messages older than 14 days were found and delete one at a time.
                    async for message in ctx.message.channel.history(limit=int(msg_count_to_delete[0])):
                        await message.delete()
        else:
            raise commands.CommandInvokeError('User cannot run this command.')

    @commands.command()
    async def logout(self, ctx, *msg_count_to_delete: str):
        if ctx.bot.is_owner(ctx.author):
            print('Logout command invoked. Shutting down.')
            await ctx.message.delete()
            await ctx.bot.logout()
        else:
            raise commands.CommandInvokeError('User cannot run this command.')

    @commands.command()
    @commands.guild_only()
    async def botonly(self, ctx, *value: str):
        toggle_value = value[0]
        if toggle_value == 'on':
            if ctx.channel not in ctx.bot.bot_only_channels:
                boc = BotOnlyChannel(channel=ctx.channel.id)
                boc.save()
                ctx.bot.bot_only_channels.append(ctx.channel)
            await ctx.send('Bot only commands enabled.')
        elif toggle_value == 'off':
            if ctx.channel in ctx.bot.bot_only_channels:
                boc = BotOnlyChannel.objects.get(channel=ctx.channel.id)
                boc.delete()
                ctx.bot.bot_only_channels.remove(ctx.channel)
            await ctx.send('Bot only commands disabled.')
        else:
            await ctx.send('Command to change bot only status:\n\n`{}[on/off]`'.format(ctx.command))


def setup(bot):
    bot.add_cog(Admin(bot))
