import os
from typing import Dict, List
import discord
from discord.ext import commands
import discord.ext
import discord.ext.commands
import modules.keys as k
from modules.permission import requires_admin
from modules.sentenceprocessing import send_message
from modules.settings import instance as settings_manager
import requests
import psutil
import cpuinfo
import sys
import subprocess
import updater
import platform
import logging
from modules.sync_connector import instance as sync_connector

settings = settings_manager.settings

OS_STRING = f"{platform.system() if platform.system() != 'Darwin' else 'macOS'} {platform.release() if platform.system() != 'Darwin' else platform.mac_ver()[0]}"

logger = logging.getLogger("goober")

class BaseCommands(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.ext.commands.Bot = bot

    @commands.command()
    async def help(self, ctx: commands.Context, layout: str = "h") -> None:
        embed: discord.Embed = discord.Embed(
            title=f"{k.command_help_embed_title()}",
            description=f"{k.command_help_embed_desc()}. Do `{settings['bot']['prefix']}help v` to use a vertical layout",
            color=discord.Colour(0x000000),
        )

        command_categories = {
            "General": [
                "mem",
                "talk",
                "about",
                "ping",
                "impact",
                "demotivator",
                "help",
            ],
            "Administration": ["stats", "retrain", "setlanguage", "add_owner", "remove_owner", "blacklist_user", "unblacklist_user", "restart", "force_update"],
            "Cog management": ["enable", "load", "unload", "disable", "reload", "listcogs"],
            "Synchub": ["synchub_test", "synchub_connect", "synchub_stats"]
        }

        cog_commands: Dict[str, List[str]] = {}
        category_descriptions: Dict[str, str] = {
            "Administration": "🛠️|Commands meant for stuff like stuff",
            "Cog management": "💼|Commands for managing cogs",
            "Synchub": "📨|Commands for managing Sync hub",
            "General": "🌐|General commands for stuff"
        }

        for cog_name, cog in self.bot.cogs.items():
            for command in cog.get_commands():
                if any([command.name in commands for commands in list(command_categories.values())]): continue

                if cog_commands.get(cog_name) is None:
                    cog_commands[cog_name] = []
                
                cog_commands[cog_name].append(command.name)
            category_descriptions[cog_name] = cog.description


        for category, commands_list in (command_categories | cog_commands).items():
            commands_in_category: str = "\n".join(
                [f"{settings['bot']['prefix']}**{command}**" for command in commands_list]
            )
            description = category_descriptions.get(category, 'No description')
            emoji = ""
            if "|" in description:
                emoji, description = description.split("|", 1)

            embed_value = f"\n\n{commands_in_category}\n‌" # don't remove zero width non joiner since it adds spacing
            embed.add_field(name=f"{emoji} {category}", value=embed_value, inline=(False if layout == "v" else True))
        await send_message(ctx, embed=embed)

    @requires_admin()
    @commands.command()
    async def setlanguage(self, ctx: commands.Context, locale: str) -> None:
        await ctx.defer()
        k.change_language(locale)

        settings["locale"] = locale  # type: ignore
        settings_manager.commit()

        await ctx.send(":thumbsup:")

    @commands.command()
    async def ping(self, ctx: commands.Context) -> None:
        await ctx.defer()
        latency: int = round(self.bot.latency * 1000)

        embed: discord.Embed = discord.Embed(
            title="Pong!!",
            description=f'{settings["bot"]["misc"]["ping_line"]}\n`{k.command_ping_embed_desc()}: {latency}ms`',
            color=discord.Colour(0x000000),
        )
        embed.set_footer(
            text=f"{k.command_ping_footer()} {ctx.author.name}",
            icon_url=ctx.author.display_avatar.url,
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def about(self, ctx: commands.Context) -> None:
        embed: discord.Embed = discord.Embed(
            title=k.command_about_embed_title(),
            description="",
            color=discord.Colour(0x000000),
        )

        embed.add_field(
            name=k.system_info(),
            value=k.os_info(OS_STRING)
        )

        embed.add_field(
            name=k.command_about_embed_field1(),
            value=settings['name'],
            inline=False,
        )

        embed.add_field(name="Github", value=f"https://github.com/gooberinc/goober")
        await send_message(ctx, embed=embed)

    @commands.command()
    async def stats(self, ctx: commands.Context) -> None:
        memory_file: str = settings["bot"]["active_memory"]
        file_size: int = os.path.getsize(memory_file)

        memory_info = psutil.virtual_memory()  # type: ignore
        total_memory = memory_info.total / (1024**3)
        used_memory = memory_info.used / (1024**3)


        cpu_name = cpuinfo.get_cpu_info()["brand_raw"]


        with open(memory_file, "r") as file:
            line_count: int = sum(1 for _ in file)

        embed: discord.Embed = discord.Embed(
            title=f"{k.command_stats_embed_title()}",
            description=f"{k.command_stats_embed_desc()}",
            color=discord.Colour(0x000000),
        )
        embed.add_field(
            name=f"{k.command_stats_embed_field1name()}",
            value=f"{k.command_stats_embed_field1value(file_size=file_size, line_count=line_count)}",
            inline=False,
        )

        mem_used_by_process = psutil.Process().memory_info().rss / 1024 **2

        embed.add_field(name="Instance", value=f"Memory usage: {round(mem_used_by_process)}mb")

        embed.add_field(
            name=k.system_info(),
            value=f"""
                    {k.memory_usage(used=round(used_memory,2), total=round(total_memory,2), percent=round(used_memory/total_memory * 100))}
                    {k.cpu_info(cpu_name)}
                """
        )

        embed.add_field(
            name=k.sync_hub_info(),
            value=k.sync_hub_description(sync_connector.connected, sync_connector.url),
            inline=False,
        )

        with open(settings["splash_text_loc"], "r") as f:
            splash_text = "".join(f.readlines())

        embed.add_field(
            name=f"{k.command_stats_embed_field3name()}",
            value=f"""{k.command_stats_embed_field3value(
                NAME=settings["name"], PREFIX=settings["bot"]["prefix"], ownerid=settings["bot"]["owner_ids"][0],
                PING_LINE=settings["bot"]["misc"]["ping_line"], showmemenabled=settings["bot"]["allow_show_mem_command"],
                USERTRAIN_ENABLED=settings["bot"]["user_training"], song=settings["bot"]["misc"]["activity"]["content"],
                splashtext=splash_text
            )}""",
            inline=False,
        )


        await send_message(ctx, embed=embed)

    @requires_admin()
    @commands.command()
    async def restart(self, ctx: commands.Context):
        await ctx.send("Restarting...")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    @requires_admin()
    @commands.command()
    async def force_update(self, ctx: commands.Context):
        await ctx.send("Forcefully updating...")
        updater.force_update()
        os.execv(sys.executable, [sys.executable] + sys.argv)
        

    @requires_admin()
    @commands.command()
    async def mem(self, ctx: commands.Context) -> None:
        if not settings["bot"]["allow_show_mem_command"]:
            return

        with open(settings["bot"]["active_memory"], "rb") as f:
            data: bytes = f.read()

        response = requests.post(
            "https://litterbox.catbox.moe/resources/internals/api.php",
            data={"reqtype": "fileupload", "time": "1h"},
            files={"fileToUpload": data},
        )

        if response.status_code != 200:
            with open(settings["bot"]["active_memory"], "rb") as f:
                await send_message(ctx, file=discord.File(f))
                return

        await send_message(ctx, response.text)

    @requires_admin()
    @commands.command()
    async def synchub_test(self, ctx: commands.Context, message_id: str | None) -> None:
        message_id = message_id or "0"
        status = sync_connector.can_react(int(message_id), 0)

        await send_message(ctx, f"Allowed to react to message {message_id}? {'yes' if status else 'no'} (connection to {settings['bot']['sync_hub']['url']} active? {'yes' if sync_connector.connected else 'no'})")


    @requires_admin()
    @commands.command()
    async def synchub_connect(self, ctx: commands.Context) -> None:
        await send_message(ctx, "Trying to connect...")
        
        connected = sync_connector.try_to_connect()
        if connected:
            await send_message(ctx, "Succesfully connected to sync hub!")
        else:
            await send_message(ctx, "Failed to connect to sync hub")

    
    @requires_admin()
    @commands.command()
    async def synchub_stats(self, ctx: commands.Context) -> None:
        connected = sync_connector.get_connected()
        await ctx.send(connected)

async def setup(bot: discord.ext.commands.Bot):
    print("Setting up base_commands")
    bot.remove_command("help")
    await bot.add_cog(BaseCommands(bot))
