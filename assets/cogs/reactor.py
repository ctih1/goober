import discord
from discord.ext import commands
from discord import app_commands

import discord.ext
import discord.ext.commands

import random

from modules.permission import requires_admin
from modules.sentenceprocessing import send_message
from modules.settings import instance as settings_manager
from typing import TypedDict, List

class Reaction(TypedDict):
    search: str
    text_content: str


class Reactor(commands.Cog): 
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot: discord.ext.commands.Bot = bot


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if "true" not in message.content.lower(): return
        if message.author.bot: return

        await message.delete()
        await message.channel.send("https://c.tenor.com/wez5Uu1KN0AAAAAC/tenor.gif")


async def setup(bot):
    await bot.add_cog(Reactor(bot))
