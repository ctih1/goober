import os
import subprocess
import platform
from typing import Dict, TypedDict

import discord
import discord.ext
import discord.ext.commands
from discord.ext import commands

from modules.permission import requires_admin
from modules.sentenceprocessing import send_message
from modules.settings import instance as settings_manager


class SettingsType(TypedDict):
    devices: Dict[str, str]


default_settings: SettingsType = {"devices": {}}


class Devices(commands.Cog):
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot: discord.ext.commands.Bot = bot
        self.description = (
            "📱|Cog that shows which devices are currently connected to your network"
        )

    @commands.command()
    async def devices(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Devices",
            description="List of devices and if they are connected to my local network",
            color=discord.Color.blue(),
        )

        settings: SettingsType = settings_manager.get_plugin_settings("devices", default_settings)  # type: ignore

        for device, ip in settings["devices"].items():
            is_up = os.system(f"ping -c 1 -i 0.2 {ip}") == 0
            stauts_emoji: str = "✅" if is_up else "❌"

            embed.add_field(
                name=f"{device} {stauts_emoji} ",
                value=f"`{ip}` **{'UP' if is_up else 'DOWN'}**",
                inline=True,
            )

        await send_message(ctx, embed=embed)

    @requires_admin()
    @commands.command()
    async def add_device(self, ctx: commands.Context, *args):
        ip = args[-1]
        device_name = " ".join(args[:-1])

        settings: SettingsType = settings_manager.get_plugin_settings("devices", default_settings)  # type: ignore
        settings["devices"][str(device_name)] = ip
        settings_manager.set_plugin_setting("devices", settings)

        await send_message(ctx, f"Added device **{device_name}** with IP `{ip}`")

    @requires_admin()
    @commands.command()
    async def remove_device(self, ctx: commands.Context, *args):
        device_name = " ".join(args)

        settings: SettingsType = settings_manager.get_plugin_settings("devices", default_settings)  # type: ignore
        del settings["devices"][str(device_name)]
        settings_manager.set_plugin_setting("devices", settings)

        await send_message(ctx, f"Removed device {device_name}")

    @requires_admin()
    @commands.command()
    async def ping_device(self, ctx: commands.Context, ip: str):

        res = subprocess.run(f"ping {'-n 4' if platform.system() == 'Windows' else '-c 4'} {ip}", shell=True, encoding="utf-8", stdout=subprocess.PIPE)
        await send_message(ctx, f"```bash\n{res.stdout or ''}\n{res.stderr or ''}\n```")

async def setup(bot):
    await bot.add_cog(Devices(bot))
