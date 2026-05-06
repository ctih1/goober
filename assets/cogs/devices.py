import discord
from discord.ext import commands
from discord import app_commands

import discord.ext
import discord.ext.commands

import random

from modules.permission import requires_admin
from modules.sentenceprocessing import send_message
from modules.settings import instance as settings_manager
from typing import TypedDict, Dict
import os

class SettingsType(TypedDict):
    devices: Dict[str, str]

default_settings: SettingsType = {
    "devices": {}
}

class Example(commands.Cog): 
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot: discord.ext.commands.Bot = bot


    @commands.command()
    async def devices(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Devices",
            description=f"List of devices and if they are connected to my local network",
            color=discord.Color.blue(),
        )

        settings: SettingsType = settings_manager.get_plugin_settings("devices", default_settings) # type: ignore

        for device, ip in settings["devices"].items():
            is_up = os.system(f"ping -c 1 -t 10 {ip}") == 0
            stauts_emoji: str = "✅" if is_up else "❌"

            embed.add_field(name=f"{device} {stauts_emoji} ", value=f"`{ip}` **{'UP' if is_up else 'DOWN'}**", inline=True) 

        await send_message(ctx, embed=embed)

    @requires_admin()
    @commands.command()
    async def add_device(self, ctx: commands.Context, *args):
        ip = args[-1]
        device_name = " ".join(args[:-1])

        settings: SettingsType = settings_manager.get_plugin_settings("devices", default_settings) # type: ignore
        settings["devices"][str(device_name)] = ip
        settings_manager.set_plugin_setting("devices", settings)

        await send_message(ctx, f"Added device **{device_name}** with IP `{ip}`")

    @requires_admin()
    @commands.command()
    async def remove_device(self, ctx: commands.Context, *args):
        device_name = " ".join(args)

        settings: SettingsType = settings_manager.get_plugin_settings("devices", default_settings) # type: ignore
        del settings["devices"][str(device_name)]
        settings_manager.set_plugin_setting("devices", settings)

        await send_message(ctx, f"Removed device {device_name}")


async def setup(bot):
    await bot.add_cog(Example(bot))
