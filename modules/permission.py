from functools import wraps
import discord

import discord.ext
import discord.ext.commands

from modules.settings import instance as settings_manager
import logging

logger = logging.getLogger("goober")

settings = settings_manager.settings


class PermissionError(Exception):
    pass


def requires_admin():
    async def wrapper(ctx: discord.ext.commands.Context):
        if ctx.author.id not in settings["bot"]["owner_ids"]:
            await ctx.send(
                "You don't have the necessary permissions to run this command!"
            )
            return False

        command = ctx.command
        if not command:
            logger.info(f"Unknown command ran {ctx.message}")
        else:
            logger.info(
                f'Command {settings["bot"]["prefix"]}{command.name} @{ctx.author.name}'
            )
        return True

    return discord.ext.commands.check(wrapper)
