import discord
from discord.ext import commands
from discord import app_commands

import discord.ext
import discord.ext.commands

import random
import time
from modules.permission import requires_admin
from modules.sentenceprocessing import send_message
from modules.settings import instance as settings_manager
from typing import TypedDict, Dict
import requests_async
import logging

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
        "emoji": "🟠"
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
    35: {
        "label": "Dry",
        "emoji": "🟡"
    },
    50: {
        "label": "Comfortable",
        "emoji": "🟢"
    },
    65: {
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

logger = logging.getLogger("goober")

class Climate(commands.Cog): 
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot: discord.ext.commands.Bot = bot
        self.description = "🌱|Monitor my indoor and outdoor climates"

    def get_ranking(self, current_value: float, tresholds: Dict[int, TresholdValue]) -> TresholdValue:
        """
        Gets the ranking (e.g good, bad, dangerous) for a given value
        """
        found_treshold: TresholdValue = {
            "emoji": "",
            "label": ""
        }

        for value, treshold in sorted(tresholds.items(), key=lambda item: item[0]):
            logger.info(str(current_value) + " " +  str(value))
            if current_value < value:
                break
            
            found_treshold = treshold

        return found_treshold
    
    def format_embed(self, label: str, unit: str, value: float, treshold: Dict[int, TresholdValue]) -> dict:
        ranking = self.get_ranking(value, treshold)
        return {
            "name": f"{label} {ranking['emoji']}",
            "value": f"{round(value, 2)} {unit} (**{ranking['label']}**)"
        }
    
    def parse_prometheus_format(self, lines: str) -> dict:
        data = {}
        for line in lines.split("\n"):
            if line.startswith("#"): continue
            if len(line) < 3: continue
            key, value = line.split(" ")

            data[key.strip()] = float(value.strip())
        
        return data

    @commands.command()
    async def indoors(self, ctx: commands.Context):
        res = await requests_async.get("http://192.168.32.88:7778/data")
        data: IndoorData = res.json()

        embed = discord.Embed(
            title="Climate data",
            description=f"Information about my indoor climate"
        )

        calculated_temp: float = data['scd40_temp'] - data['temperature_offset']
        air_humidity: float = (data["scd40_humidity"] + data["relative_humidity"]) / 2

        embed.add_field(**self.format_embed("CO2", "PPM", data['carbon_dioxide'], CO2_TRESHOLDS))
        embed.add_field(**self.format_embed("Temperature", "*C", calculated_temp, TEMP_TRESHOLDS))
        embed.add_field(**self.format_embed("Relative Humidity", "%", air_humidity, HUMIDITY_TRESHOLDS))
        embed.add_field(**self.format_embed("Air Resistance", "Ω", data['air_resistance'], RESISTANCE_TRESHOLDS))

        embed.set_footer(text=f"Last updated: {time.strftime('%H:%M:%S %d/%m/%Y', time.gmtime(data['last_update']))} (UTC)")

        await send_message(ctx, embed=embed)

    @commands.command()
    async def outdoors(self, ctx: commands.Context):
        res = await requests_async.get("http://192.168.32.2:7777/metrics")
        data = self.parse_prometheus_format(res.text)

        embed = discord.Embed(
            title="Climate data",
            description=f"Information about my outdoor climate"
        )

        embed.add_field(**self.format_embed("PM2.5", "µg/m³", data["mc2p5"], PM25_TRESHOLDS))
        embed.add_field(**self.format_embed("PM10.0", "µg/m³", data["mc10p0"], PM100_TRESHOLDS))
        embed.add_field(**self.format_embed("Temperature", "*C", data["temp"], OUTDOOR_TEMP_TRESHOLDS))
        embed.add_field(**self.format_embed("Relative Humidity", "%", data["humidity"], OUTDOOR_HUMIDITY_TRESHOLDS))

        await send_message(ctx, embed=embed)

async def setup(bot):
    await bot.add_cog(Climate(bot))
