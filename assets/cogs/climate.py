import discord
from discord.ext import commands
from discord import app_commands

import discord.ext
import discord.ext.commands
import math
import random
import time
from modules.permission import requires_admin
from modules.sentenceprocessing import send_message
from modules.settings import instance as settings_manager
from typing import TypedDict, Dict, Literal, List, Tuple
import requests_async
import logging
import datetime
import requests_async
import json

ViewType = Literal["outdoors", "indoors"]

class SettingsType(TypedDict):
    latitude: float
    longtitude: float

default_settings: SettingsType = {
    "latitude": 30,
    "longtitude": 0
}

class IndoorData(TypedDict):
    temperature: float
    relative_humidity: float
    air_pressure: float
    air_resistance: float
    sensor_calibrated: bool
    temperature_offset: float
    scd40_temp: float
    scd40_humidity: float
    carbon_dioxide: int
    last_update: float

class TresholdValue(TypedDict):
    label: str
    emoji: str

# for example: 600 would be 600 up until 800
CO2_TRESHOLDS: Dict[int, TresholdValue] = {
    400: {
        "label": "Great",
        "emoji": "🔵"
    },
    600: {
        "label": "Good",
        "emoji": "🟢"
    },
    800: {
        "label": "OK",
        "emoji": "🟢"
    },
    1000: {
        "label": "Suboptimal",
        "emoji": "🟡"
    },
    1300: {
        "label": "Bad",
        "emoji": "🔴"
    },
    1800: {
        "label": "Very bad",
        "emoji": "🟣"
    }
}

TEMP_TRESHOLDS: Dict[int, TresholdValue] = {
    16: {
        "label": "Cold",
        "emoji": "🔵"
    },
    18: {
        "label": "Optimal",
        "emoji": "🟢"
    },
    21: {
        "label": "Warm",
        "emoji": "🟡"
    },
    24: {
        "label": "Hot",
        "emoji": "🔴"
    }
}

HUMIDITY_TRESHOLDS: Dict[int, TresholdValue] = {
    0: {
        "label": "Too dry",
        "emoji": "🟡"
    },
    35: {
        "label": "Optimal",
        "emoji": "🟢"
    },
    65: {
        "label": "Too damp",
        "emoji": "🟡"
    }
}

RESISTANCE_TRESHOLDS: Dict[int, TresholdValue] = {
    20_000: {
        "label": "Bad",
        "emoji": "🟡"
    },
    90_000: {
        "label": "OK",
        "emoji": "🟡"
    },
    120_000: {
        "label": "Good",
        "emoji": "🟢"
    }
}

PM25_TRESHOLDS: Dict[int, TresholdValue] = {
    0: {
        "label": "Excellent",
        "emoji": "🔵"
    },
    6: {
        "label": "Good",
        "emoji": "🟢"
    },
    12: {
        "label": "OK",
        "emoji": "🟡"
    },
    35: {
        "label": "Unhealthy",
        "emoji": "🔴"
    },
    60: {
        "label": "Very unhealthy",
        "emoji": "🟣"
    }
}


PM100_TRESHOLDS: Dict[int, TresholdValue] = {
    0: {
        "label": "Excellent",
        "emoji": "🔵"
    },
    12: {
        "label": "Good",
        "emoji": "🟢"
    },
    24: {
        "label": "OK",
        "emoji": "🟡"
    },
    75: {
        "label": "Unhealthy",
        "emoji": "🔴"
    },
    120: {
        "label": "Very unhealthy",
        "emoji": "🟣"
    }
}

OUTDOOR_TEMP_TRESHOLDS: Dict[int, TresholdValue] = {
    -50: {
        "label": "Extremely frigid",
        "emoji": "⚫"
    },
    -25: {
        "label": "Very frigid",
        "emoji": "🟣"
    },
    -20: {
        "label": "Very cold",
        "emoji": "🔵"
    },
    -15: {
        "label": "Cold",
        "emoji": "🔵"
    },
    -10: {
        "label": "Mildly cold",
        "emoji": "🔵"
    },
    -5: {
        "label": "Chilly",
        "emoji": "⚪"
    },
    0: {
        "label": "Cool",
        "emoji": "⚪"
    },
    5: {
        "label": "Brisk",
        "emoji": "🟢"
    },
    10: {
        "label": "Mild",
        "emoji": "🟢"
    }, 
    15: {
        "label": "Warm",
        "emoji": "🟡"
    },
    20: {
        "label": "Very warm",
        "emoji": "🟡"
    },
    25: {
        "label": "Hot",
        "emoji": "🟠"
    },
    30: {
        "label": "Very hot",
        "emoji": "🔴"
    }
}

OUTDOOR_HUMIDITY_TRESHOLDS: Dict[int, TresholdValue] = {
    0: {
        "label": "Extremely dry",
        "emoji": "🟠"
    },
    15: {
        "label": "Very dry",
        "emoji": "🟠"
    },
    30: {
        "label": "Dry",
        "emoji": "🟡"
    },
    40: {
        "label": "Comfortable",
        "emoji": "🟢"
    },
    69: {
        "label": "Slightly humid",
        "emoji": "🟢"
    },
    75: {
        "label": "Humid",
        "emoji": "🔵"
    },
    85: {
        "label": "Very humid",
        "emoji": "🔵"
    },
    95: {
        "label": "Extremely humid",
        "emoji": "🟣"
    }
}

SUN_POSITION_TRESHOLD: Dict[int, TresholdValue] = {
    -100: {
        "label": "Night",
        "emoji": "🌌"
    },
    -18: {
        "label": "Astronomical twilight",
        "emoji": "🌙"
    },
    -12: {
        "label": "Nautical twilight",
        "emoji": "⭐"
    },
    -6: {
        "label": "Civil twilight",
        "emoji": "🌃"
    },
    -2: {
        "label": "Sunrise or -set",
        "emoji": "🌅"
    },
    2: {
        "label": "Day",
        "emoji": "☀️"
    }
}

PRESSURE_TRESHOLS: Dict[int, TresholdValue] = {
    900: {
        "label": "Extremely low pressure",
        "emoji": "🔴"
    },
    980: {
        "label": "Very low pressure",
        "emoji": "🟠"
    },
    995: {
        "label": "Low pressure",
        "emoji":  "🟡"
    },
    1005: {
        "label": "Normal pressure",
        "emoji": "🟢"
    },
    1015: {
        "label": "High pressure",
        "emoji": "🔵"
    },
    1025: {
        "label": "Very high pressure",
        "emoji": "🟣"
    }
}

logger = logging.getLogger("goober")

class ResendView(discord.ui.View):
    def __init__(self, mode: ViewType, *, timeout: float | None = None):
        super().__init__(timeout=timeout)
        self.mode: ViewType = mode
    
    @discord.ui.button(label="Refresh")
    async def refresh_callback(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.defer()
        if self.mode == "indoors":
            embed = await Climate.generate_indoor_embed()
        else:
            embed = await Climate.generate_outdoor_embed()

        embed.set_author(name=interaction.user.name, icon_url=(None if interaction.user.avatar is None else interaction.user.avatar.url))


        await interaction.followup.send(embed=embed, view=self)

class Climate(commands.Cog): 
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot: discord.ext.commands.Bot = bot
        self.description = "🌱|Monitor my indoor and outdoor climates"

    @staticmethod
    def get_ranking(current_value: float, tresholds: Dict[int, TresholdValue]) -> TresholdValue:
        """
        Gets the ranking (e.g good, bad, dangerous) for a given value
        """
        found_treshold: TresholdValue = {
            "emoji": "",
            "label": ""
        }

        for value, treshold in sorted(tresholds.items(), key=lambda item: item[0]):
            if current_value < value:
                break
            
            found_treshold = treshold

        return found_treshold
    
    @staticmethod
    def format_embed(label: str, unit: str, value: Tuple[float, float] | Tuple[float, ...], treshold: Dict[int, TresholdValue]) -> dict:
        ranking = Climate.get_ranking(value[1], treshold)
        return {
            "name": f"{label} {ranking['emoji']}",
            "value": f"{'▲' if value[1] > value[0] else '▼'} {round(value[1], 2)} {unit} (**{ranking['label']}**)"
        }
    
    @staticmethod
    async def get_prometheus_data(datapoints: List[str]) -> Dict[str, Tuple[float, float]]:
        """Gets prometheus data and returns a tuple of [30m ago, now]"""

        values: Dict[str, Tuple[float,float]] = {}
        offset_json: dict = (await requests_async.get(f"http://192.168.32.88:9999/api/v1/query?query={{__name__=~\"{'|'.join(datapoints)}\"}}+offset+30m")).json()
        now_json: dict = (await requests_async.get(f"http://192.168.32.88:9999/api/v1/query?query={{__name__=~\"{'|'.join(datapoints)}\"}}")).json()
        
        for data in now_json["data"]["result"]:
            offset_data = [obj for obj in offset_json["data"]["result"] if obj["metric"]["__name__"] == data["metric"]["__name__"]]

            if len(offset_data) != 1:
                logger.warning(f"Weird match with {data}")
                values[data["metric"]["__name__"]] = (float(data["value"][1]), float(data["value"][1]))
                

            values[data["metric"]["__name__"]] = (float(offset_data[0]["value"][1]), float(data["value"][1]))


        return values

        
    @staticmethod
    def get_sun_angle(at: datetime.datetime) -> float:
        settings: SettingsType = settings_manager.get_plugin_settings("climate", default_settings)  # type: ignore

        hour = at.hour + at.minute / 60 + at.second / 3600
        solar_hour = hour + (settings["longtitude"] - 45) / 15
        nth_day_of_year = (at - datetime.datetime(at.year, 1, 1)).days + 1
        declination = math.radians(23.445 * math.sin(math.radians((360 / 365.25) * (nth_day_of_year - 81))))
        hour_angle = math.radians(15 * (solar_hour - 12))

        result = math.degrees(math.asin(
            math.sin(declination) *
            math.sin(math.radians(settings["latitude"])) +
            math.cos(declination) *
            math.cos(math.radians(settings["latitude"])) *
            math.cos(hour_angle)
        ))

        if result > -1.0:
            refraction = 1.02 / math.tan(math.radians(result + 10.3 / (result + 5.11))) / 60
            result += refraction

        return result
        
    @staticmethod
    async def generate_outdoor_embed() -> discord.Embed:
        data = await Climate.get_prometheus_data(["mc2p5", "mc10p0", "temp", "humidity", "climate_pressure"])

        embed = discord.Embed(
            title="Outdoor climate data",
            description=f"Information about my outdoor climate"
        )

        pressure = tuple([data["climate_pressure"][i] * math.pow((1 - 119/44330), -5.225) for i in range(2)])

        embed.add_field(**Climate.format_embed("PM2.5", "µg/m³", data["mc2p5"], PM25_TRESHOLDS))
        embed.add_field(**Climate.format_embed("PM10.0", "µg/m³", data["mc10p0"], PM100_TRESHOLDS))
        embed.add_field(**Climate.format_embed("Temperature", "°C", data["temp"], OUTDOOR_TEMP_TRESHOLDS))
        embed.add_field(**Climate.format_embed("Relative Humidity", "%", data["humidity"], OUTDOOR_HUMIDITY_TRESHOLDS))
        embed.add_field(**Climate.format_embed("Air Pressure", "hPa", pressure, PRESSURE_TRESHOLS))
        embed.add_field(**Climate.format_embed("Sun angle", "°", (Climate.get_sun_angle(datetime.datetime.now() - datetime.timedelta(minutes=30)) ,Climate.get_sun_angle(datetime.datetime.now())), SUN_POSITION_TRESHOLD))
        embed.set_footer(text="▲: value increasing, ▼: value decreasing")
        return embed
    
    @staticmethod
    async def generate_indoor_embed() -> discord.Embed:
        data = await Climate.get_prometheus_data(["climate_carbon_dioxide", "climate_temp_adjusted", "climate_temp", "climate_scd40_temp", "climate_relative_humidity", "climate_scd40_humidity", "climate_air_resistance"])

        embed = discord.Embed(
            title="Indoor climate data",
            description=f"Information about my indoor climate"
        )

        calculated_temp = tuple([data['climate_scd40_temp'][i] - ((data["climate_temp"][i] - data['climate_temp_adjusted'][i]) / 2) for i in range(2)])
        air_humidity = tuple([(data["climate_scd40_humidity"][i] + data["climate_relative_humidity"][i]) / 2 for i in range(2)])

        embed.add_field(**Climate.format_embed("CO2", "PPM", data['climate_carbon_dioxide'], CO2_TRESHOLDS))
        embed.add_field(**Climate.format_embed("Temperature", "°C", calculated_temp, TEMP_TRESHOLDS))
        embed.add_field(**Climate.format_embed("Relative Humidity", "%", air_humidity, HUMIDITY_TRESHOLDS))
        embed.add_field(**Climate.format_embed("Air Resistance", "Ω", data['climate_air_resistance'], RESISTANCE_TRESHOLDS))
        embed.set_footer(text="▲: value increasing, ▼: value decreasing")

        return embed

    @commands.command()
    async def indoors(self, ctx: commands.Context):
        embed = await Climate.generate_indoor_embed()
        embed.set_author(name=ctx.author.name, icon_url=(None if ctx.author.avatar is None else ctx.author.avatar.url))
        await ctx.send(embed=embed, view=ResendView("indoors"))


    @commands.command()
    async def outdoors(self, ctx: commands.Context):
        embed = await Climate.generate_outdoor_embed()
        embed.set_author(name=ctx.author.name, icon_url=(None if ctx.author.avatar is None else ctx.author.avatar.url))
        await ctx.send(embed=embed, view=ResendView("outdoors"))

    @requires_admin()
    @commands.command()
    async def set_coords(self, ctx: commands.Context, latitude: float, longtitude: float):
        settings: SettingsType = settings_manager.get_plugin_settings("climate", default_settings) # type: ignore
        settings["latitude"] = latitude
        settings["longtitude"] = longtitude
        settings_manager.set_plugin_setting("climate", settings)

        await send_message(ctx, "Saved coordinates!")

async def setup(bot):
    await bot.add_cog(Climate(bot))
