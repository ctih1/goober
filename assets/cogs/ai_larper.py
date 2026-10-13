import json
import os
import random

import httpx
from httpx import Response
from discord.ext import commands
from discord.ext.commands import Context

from modules.sentenceprocessing import send_message


class AILarper(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "🧠|Interact with the goober gang models (2)"
        self.temp = 0.9
        self.client = httpx.AsyncClient()

        with open("assets/fonts/attachments.json", "r") as f:
            self.cache = json.load(f)

    @commands.command()
    async def larp(self, ctx: Context, *, content: str):
        content = content.strip()

        async with ctx.typing():
            response: Response = await self.client.post(
                "http://192.168.32.25:6655/generate",
                json={"prompt": content, "temperature": self.temp},
                headers={"X-Auth": os.environ.get("AI_KEY") or ""},
                timeout=120,
            )
        if response.status_code != 200:
            await send_message(
                ctx, f"Failed to generateo: {response.status_code} {response.text}"
            )
            return

        text = response.text
        text = text.replace("[attachment]", random.choice(self.cache)["url"], 1)
        text = text.replace("[attachment]", "")
        text = text.replace("\\n", "\n")
        text = text[1:-1]

        await send_message(ctx, text)

    @commands.command()
    async def set_temp(self, ctx: Context, temperature: str) -> None:
        self.temp = float(temperature)

        await send_message(ctx, "Set temp")

    @commands.command()
    async def check_larp(self, ctx: Context):
        response: Response = await self.client.get(
            "http://192.168.32.25:6655/history",
        )
        await send_message(
            ctx, f"```json\n{json.dumps(response.json(), indent=4)}\n```"
        )

    @commands.command()
    async def clear_larp(self, ctx: Context):
        response: Response = await self.client.post(
            "http://192.168.32.25:6655/clear",
        )
        await send_message(ctx, "Cleared larp")


async def setup(bot):
    await bot.add_cog(AILarper(bot))
