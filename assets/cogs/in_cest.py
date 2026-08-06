import discord
from discord.ext import commands
import re
from collections.abc import Callable, Iterator
from typing import Dict, TypedDict, Any, List
from modules.settings import instance as settings_manager
from modules.permission import requires_admin
from modules.sentenceprocessing import send_message
import random
from copy import copy
import logging
from modules.sync_connector import instance as synchub
import datetime
from zoneinfo import ZoneInfo
from zoneinfo._common import ZoneInfoNotFoundError

logger = logging.getLogger("goober")
settings = settings_manager.settings


class SettingsType(TypedDict):
    timezones: Dict[
        str, str
    ]  # int being a discord ID and str being like "Europe/Helsinki"


DEFAULT_SETTINGS: SettingsType = {"timezones": {}}  # type: ignore


def convert_time(match: tuple[str, ...], tz: ZoneInfo) -> int | None:
    hour = int(match[0].strip())
    minutes = 0 if not match[3] else int(match[3].strip())
    meridiem = "" if not match[4] else match[4].lower().strip()

    if not match[1] and not match[4]:
        return None

    hour += 12 if meridiem == "pm" else 0

    logger.info((hour, minutes, meridiem))

    return round(
        datetime.datetime(1984, 6, 8, hour=hour, minute=minutes, tzinfo=tz).timestamp()
    )


class Timezones(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = (
            "⏱|Automatically convert between units (Metric/Imperial) found in chats"
        )

        self.regexes = {
            re.compile(
                r"(?:\s|^)([0-9]{1,2})((\:|\.)([0-9]{1,2}))?\s?(am|pm)?(\s|$)",
                re.IGNORECASE,
            ): convert_time
        }

    def __format_response(self, timestamps: List[int]) -> str:
        logger.debug(f"Values: {timestamps}")
        message: str = "-# That's "

        for i, tramp_stamp in enumerate(timestamps):
            temp_line: str = (
                ", and "
                if (i == len(timestamps) - 1 and i != 0)
                else ", " if i != 0 else ""
            )

            message += temp_line + f"<t:{tramp_stamp}:t>"

        message += " in your time"

        return message

    @commands.command()
    async def set_timezone(self, ctx: commands.Context, timezone: str) -> None:
        settings: SettingsType = settings_manager.get_plugin_settings(
            "times", DEFAULT_SETTINGS
        )  # type: ignore
        try:
            tz = ZoneInfo(timezone)
        except ZoneInfoNotFoundError:
            await ctx.reply("Not a valid timezone digga")
            return

        settings["timezones"][str(ctx.author.id)] = timezone
        settings_manager.set_plugin_setting("times", settings)
        await ctx.reply("Updated timezone!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        settings: SettingsType = settings_manager.get_plugin_settings(
            "times", DEFAULT_SETTINGS
        )  # type: ignore

        logger.debug(f"Received message {message.content}")

        timestamps: List[int] = []

        for regex, conversion_func in self.regexes.items():
            matches: Iterator[re.Match] | None = regex.finditer(message.content)

            if not matches:
                logger.debug("No matches found")
                continue

            for match in matches:
                if str(message.author.id) not in settings["timezones"]:
                    await message.reply("Please specify your time zone dude")
                    break

                logger.info(f"Match groups: {match.groups()}")

                try:
                    val = conversion_func(
                        match.groups(),
                        ZoneInfo(
                            settings["timezones"].get(
                                str(message.author.id), "Europe/Helsinki"
                            )
                        ),
                    )
                    if val:
                        timestamps.append(val)
                except Exception as e:
                    logger.warn(e)

        if not timestamps:
            return

        if synchub.can_timezone(message.id, message.channel.id):
            logger.debug("Synchub accepted")
            await message.reply(self.__format_response(timestamps))
        else:
            logger.info("Synchub denied")


async def setup(bot):
    await bot.add_cog(Timezones(bot))
