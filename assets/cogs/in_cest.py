import datetime
import logging
import re
from collections.abc import Iterator
from typing import Dict, List, TypedDict
from zoneinfo import ZoneInfo
from zoneinfo._common import ZoneInfoNotFoundError

import discord
from discord.ext import commands
from discord.message import Message, MessageReference
from google.genai.tunings import t

from modules.settings import instance as settings_manager
from modules.sync_connector import instance as synchub

logger = logging.getLogger("goober")
settings = settings_manager.settings


class SettingsType(TypedDict):
    timezones: Dict[str, str]  # int being a discord ID and str being like "Europe/Helsinki"


DEFAULT_SETTINGS: SettingsType = {"timezones": {}}  # type: ignore


def convert_time(match: tuple[str, ...], tz: ZoneInfo) -> int | None:
    hour = int(match[0].strip())
    minutes = 0 if not match[3] else int(match[3].strip())
    meridiem = "" if not match[4] else match[4].lower().strip()

    if not match[1] and not match[4]:
        return None

    hour += 12 if meridiem == "pm" else 0

    logger.info((hour, minutes, meridiem))

    now = datetime.datetime.now()
    return round(
        datetime.datetime(
            now.year, now.month, now.day, hour=hour, minute=minutes, tzinfo=tz
        ).timestamp()
    )


class Timezones(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "⏱|Automatically displays the listed time in your own timezone"

        self.regexes = {
            re.compile(
                r"(?:\s|^)([0-9]{1,2})((\:)([0-9]{2}))?\s?(am|pm)?(\s|$)",
                re.IGNORECASE,
            ): convert_time
        }

    def __format_response(self, timestamps: List[int]) -> str:
        logger.debug(f"Values: {timestamps}")
        message: str = "-# That's "

        for i, tramp_stamp in enumerate(timestamps):
            temp_line: str = (
                ", and " if (i == len(timestamps) - 1 and i != 0) else ", " if i != 0 else ""
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
            _tz = ZoneInfo(timezone)
        except ZoneInfoNotFoundError:
            await ctx.reply("Not a valid timezone digga")
            return

        settings["timezones"][str(ctx.author.id)] = timezone
        settings_manager.set_plugin_setting("times", settings)
        await ctx.reply("Updated timezone!")

    def find_matches(self, message_content: str, author: int) -> list[int]:
        timestamps: list[int] = []
        settings: SettingsType = settings_manager.get_plugin_settings(
            "times", DEFAULT_SETTINGS
        )  # type: ignore

        for regex, conversion_func in self.regexes.items():
            matches: Iterator[re.Match] | None = regex.finditer(message_content)

            if not matches:
                logger.debug("No matches found")
                continue

            for match in matches:
                if str(author) not in settings["timezones"]:
                    raise ValueError("Pleaase specify timezone for the user!")

                logger.info(f"Match groups: {match.groups()}")

                try:
                    val = conversion_func(
                        match.groups(),
                        ZoneInfo(settings["timezones"].get(str(author), "Europe/Helsinki")),
                    )
                    if val:
                        timestamps.append(val)
                except Exception as e:
                    logger.warning(e)

        return timestamps

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        try:
            timestamps: list[int] = self.find_matches(message.content, message.author.id)
        except ValueError:
            await message.reply("Please specify your time zone dude")
            return

        if not timestamps:
            return

        if synchub.can_timezone(message.id, message.channel.id):
            logger.debug("Synchub accepted")
            await message.reply(self.__format_response(timestamps))
        else:
            logger.info("Synchub denied")

    @commands.command(aliases=["times", "timezones", "mytime", "astime", "alltimes", "mosttimes", "alltime", "mosttime", "ineveryfuckingtimezone"])
    async def time(self, ctx: commands.Context) -> None:
        reference: MessageReference | None = ctx.message.reference
        if not reference or not reference.message_id:
            await ctx.reply("Digga reply to something first")
            return

        message: Message = await ctx.fetch_message(reference.message_id)

        settings: SettingsType = settings_manager.get_plugin_settings(
            "times", DEFAULT_SETTINGS
        )  # type: ignore

        timestamps = self.find_matches(message.content, message.author.id)

        if not timestamps:
            await ctx.reply("No time found")

        timezone_infos = []
        for timestamp in timestamps:
            for user_id, timezone in settings["timezones"].items():
                timezone_infos.append([timezone, datetime.datetime.fromtimestamp(timestamp, ZoneInfo(timezone))])

        timezone_infos.sort(key=lambda info: info[1].strftime("%j%H%M"), reverse=True)
        formatted_output: str = ""
        for tz, time in timezone_infos:
            formatted_output += f"{tz}: {time.strftime('%H:%M')}\n"
        await ctx.reply(formatted_output)


async def setup(bot):
    await bot.add_cog(Timezones(bot))
