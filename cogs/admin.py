import discord
from discord.ext import commands


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


def setup(bot):
    bot.add_cog(Admin(bot))
