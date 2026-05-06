import discord
from discord.ext import commands
from discord import app_commands
from zoneinfo import ZoneInfo
import discord.ext
import discord.ext.commands

import random

from modules.permission import requires_admin
from modules.sentenceprocessing import send_message
from modules.settings import instance as settings_manager
from typing import TypedDict, Dict

import icalendar
from icalendar import Calendar
import recurring_ical_events
import datetime
import requests
import logging

logger = logging.getLogger("goober")

TRANSLATED_CLASSES: Dict[str, str] = {
    "ÄI": "Finnish",
    "FY": "Physics",
    "KU": "Arts",
    "MAA": "Advanced maths",
    "MAB": "General maths",
    "OP": "Student councelling",
    "ICT": "IT-Studies",
    "RUB": "Swedish",
    "TE": "Health information",
    "MU": "Music",
    "HI": "History",
    "BI": "Biology",
    "ENA": "English",
    "KE": "Chemistry",
    "UE": "Religious studies",
    "LI": "PE",
    "GE": "Geography",
    "FI": "Philosophy",
    "PS": "Psychology",
    "YH": "Social studies"
}

class SettingsType(TypedDict):
    cached_calendar: str

default_settings: SettingsType = {
    "cached_calendar": ""
}

class ActiveCalendar(commands.Cog): 
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot: discord.ext.commands.Bot = bot
        self.description = "📅|Calendar cog with support for iCals"

    @commands.command()
    async def calendar(self, ctx: commands.Context, day_offset: int = 0):
        time_now = datetime.datetime.now(ZoneInfo("Europe/Helsinki"))

        target_time = datetime.date.today()
        offset = datetime.timedelta(days=abs(day_offset))
        target_time = target_time - offset if day_offset < 0 else target_time + offset
        
        embed = discord.Embed(title=f"Calendar for {target_time.strftime('%d.%m.')}", description=f"Calendar (currently: {time_now.strftime('%d/%m/%Y %H:%M')})")
        settings: SettingsType = settings_manager.get_plugin_settings("calendar", default_settings) # type: ignore
        
        last_building_index: int = 0
        last_level: int = 0

        stairs_climbed = 0

        for event in recurring_ical_events.of(Calendar.from_ical(settings["cached_calendar"])).at(target_time):
            start: icalendar.vDDDTypes  = event.get("DTSTART")
            end: icalendar.vDDDTypes  = event.get("DTEND")
            class_name = event.get("SUMMARY").split(" ")[0]
            place = str(event.get("RESOURCES").split(",")[1]).removeprefix("HA.")

            try:
                building_index = int(place[1])
            except:
                logger.warning("Failed to get building index")
                building_index = last_building_index

            try:
                level = int(place[3])
            except:
                logger.warning("Failed to get building level")
                level = last_level

            if building_index != last_building_index:
                stairs_climbed += abs(1 - last_level)
                stairs_climbed += abs(1 - level)
            else:
                stairs_climbed += abs(last_level - level) 

            last_level = level
            last_building_index = building_index

            class_tag = ""
            for char in class_name:
                try:
                    _ = int(char)
                    break
                except ValueError:
                    class_tag += char
            
            translated_class = TRANSLATED_CLASSES.get(class_tag.upper(), "")
            latter_text = f"**{translated_class}**" if translated_class else ""

            now =  start.dt <= time_now <= end.dt # type: ignore
            passed = end.dt <= time_now # type: ignore

            styling = "~~" if passed else ""

            embed.add_field(name=f"{styling}{latter_text} ({class_name or 'No data'}) {'📍' if now else ''}{styling}", value=f"{start.dt.strftime('%H:%M')} - {end.dt.strftime('%H:%M')}, *{place}*", inline=False) # pyright: ignore[reportAttributeAccessIssue]

        embed.set_footer(text=f"Floors climbed during the day: {stairs_climbed}")
        
        await send_message(ctx, embed=embed)

    @requires_admin()
    @commands.command()
    async def update_calendar_cache(self, ctx: commands.Context, link: str) -> None:
        settings: SettingsType = settings_manager.get_plugin_settings("calendar", default_settings) # type: ignore

        res = requests.get(link)
        settings["cached_calendar"] = res.text

        settings_manager.set_plugin_setting("calendar", default_settings)
        await send_message(ctx, "Updated calendar cache")


async def setup(bot):
    await bot.add_cog(ActiveCalendar(bot))
