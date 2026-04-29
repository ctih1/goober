import discord
from discord.ext import commands


class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def crash(self, ctx):
        a = 0 / 0
        await ctx.reply(None)


async def setup(bot):
    await bot.add_cog(Test(bot))
