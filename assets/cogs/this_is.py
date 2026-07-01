import discord
from discord.ext import commands
from discord import app_commands
import discord.ext
import discord.ext.commands
import random
from modules.permission import requires_admin
from modules.sentenceprocessing import send_message
from modules.settings import instance as settings_manager
from typing import TypedDict

from PIL import Image, ImageFont, ImageDraw

class ThisIs(commands.Cog): 
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot: discord.ext.commands.Bot = bot

    @commands.command()
    async def this_is(self, ctx: commands.Context, who: str):
        pass


async def setup(bot):
    await bot.add_cog(ThisIs(bot))
