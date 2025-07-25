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

settings = settings_manager.settings


class BaseCommands(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.ext.commands.Bot = bot

    @commands.command()
    async def help(self, ctx: commands.Context) -> None:
        embed: discord.Embed = discord.Embed(
            title=f"{k.command_help_embed_title()}",
            description=f"{k.command_help_embed_desc()}",
            color=discord.Colour(0x000000),
        )

        command_categories = {
            f"{k.command_help_categories_general()}": [
                "mem",
                "talk",
                "about",
                "ping",
                "impact",
                "demotivator",
                "help",
            ],
            f"{k.command_help_categories_admin()}": ["stats", "retrain", "setlanguage"],
        }

        custom_commands: List[str] = []
        for cog_name, cog in self.bot.cogs.items():
            for command in cog.get_commands():
                if (
                    command.name
                    not in command_categories[f"{k.command_help_categories_general()}"]
                    and command.name
                    not in command_categories[f"{k.command_help_categories_admin()}"]
                ):
                    custom_commands.append(command.name)

        if custom_commands:
            embed.add_field(
                name=f"{k.command_help_categories_custom()}",
                value="\n".join(
                    [
                        f"{settings['bot']['prefix']}{command}"
                        for command in custom_commands
                    ]
                ),
                inline=False,
            )

        for category, commands_list in command_categories.items():
            commands_in_category: str = "\n".join(
                [f"{settings['bot']['prefix']}{command}" for command in commands_list]
            )
            embed.add_field(name=category, value=commands_in_category, inline=False)

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
            description=(
                settings["bot"]["misc"]["ping_line"],
                f"`{k.command_ping_embed_desc()}: {latency}ms`\n",
            ),
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
            title=f"{k.command_about_embed_title()}",
            description="",
            color=discord.Colour(0x000000),
        )

        embed.add_field(
            name=k.command_about_embed_field1(),
            value=f"{settings['name']}",
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

        embed.add_field(
            name=k.system_info(),
            value=f"""
                    {k.memory_usage(used=round(used_memory,2), total=round(total_memory,2), percent=round(used_memory/total_memory * 100))}
                    {k.cpu_info(cpu_name)}
                """
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

        await send_message(ctx, response.text)


async def setup(bot: discord.ext.commands.Bot):
    print("Setting up base_commands")
    bot.remove_command("help")
    await bot.add_cog(BaseCommands(bot))
