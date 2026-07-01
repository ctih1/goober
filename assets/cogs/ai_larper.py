import discord
from discord.ext import commands
from discord.ext.commands import Context
import requests_async
from requests_async import Response
from modules.sentenceprocessing import send_message
import os
import json
import random

class AILarper(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "🧠|Interact with the goober gang models (2)"

        with open("assets/fonts/attachments.json", "r") as f:
            self.cache = json.load(f)


    @commands.command()
    async def larp(self, ctx: Context, *, content: str):
        content = content.strip()

        async with ctx.typing():
            response: Response = await requests_async.post("http://localhost:6655/generate", json={"prompt": content}, headers={
                "X-Auth": os.environ.get("AI_KEY")
            })
        if response.status_code != 200:
            await send_message(ctx, f"Failed to generateo: {response.status_code} {response.text}")
            return
        

        text = response.text
        text = text.replace("[attachment]", random.choice(self.cache)["url"], 1)
        text = text.replace("[attachment]", "")
        text = text.replace("\\n", "\n")
        text = text[1:-1]

        await send_message(ctx, text)


    @commands.command()
    async def check_larp(self, ctx: Context):
        response: Response = await requests_async.get("http://localhost:6655/history")
        await send_message(ctx, f"```json\n{json.dumps(response.json(), indent=4)}\n```")

    @commands.command()
    async def clear_larp(self, ctx: Context):
        response: Response = await requests_async.post("http://localhost:6655/clear")
        await send_message(ctx, f"Cleared larp")

async def setup(bot):
    await bot.add_cog(AILarper(bot))
