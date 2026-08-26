import logging
import sys
import traceback

import discord
import discord.ext.commands.errors
from discord.ext.commands import Context

import modules.keys as k
from modules.sentenceprocessing import send_message
from modules.settings import instance as settings_manager

settings = settings_manager.settings
logger = logging.getLogger("goober")


def handle_exception(exc_type, exc_value, exc_traceback, *, context: str | None = None):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.error("=====BEGINNING OF TRACEBACK=====")
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    logger.error("========END OF TRACEBACK========")
    logger.error(k.unhandled_exception())

    if context:
        logger.error(f"Context: {context}")


async def handle_exception_with_context(
    ctx: Context,
    exc_type: type[Exception],
    exc_value,
    exc_traceback,
    *,
    context: str | None = None,
):
    if exc_type == discord.ext.commands.errors.ArgumentParsingError:
        embed = discord.Embed(color=0xFC1C03)
        embed.title = "Invalid input"
        embed.description = f"{exc_value}"

        await send_message(ctx, embed=embed)
        return

    if (
        exc_type == discord.ext.commands.errors.UserNotFound
        or exc_type == discord.ext.commands.errors.MemberNotFound
    ):
        embed = discord.Embed(color=0xFC1C03)
        embed.title = "User not found"
        embed.description = f"{exc_value}"

        await send_message(ctx, embed=embed)
        return

    handle_exception(exc_type, exc_value, exc_traceback, context=context)

    embed = discord.Embed(color=0xFC1C03)
    embed.title = "Command failed with exception"
    embed.description = (
        "```"
        + "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))[-4000:]
        + "```"
    )

    await send_message(ctx, embed=embed)
