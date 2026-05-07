import discord
from discord.ext import commands
from discord.ext.commands import Context
import requests
from requests import Response
from modules.sentenceprocessing import send_message
import os

class AIConnector(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "🧠|Interact with the goober gang models"


    @commands.command()
    async def do(self, ctx: Context, *, content: str):
        comparing = False
        person = ""

        if "!charlie" in content:
            person ="charles"
            content = content.replace("!charlie", "")

        if "!expect" in content:
            person ="expect"
            content = content.replace("!expect", "")

        if "!rock" in content:
            person ="rock"
            content = content.replace("!rock", "")

        if "!compare" in content:
            person = "compare"
            content = content.replace("!compare", "")
            comparing = True

        content = content.strip()

        async with ctx.typing():
            response: Response = requests.post("http://192.168.32.88:3800/generate", json={"prompt": content, "person": person}, headers={
                "X-Auth": os.environ.get("AI_KEY")
            })
        if response.status_code != 200:
            await send_message(ctx, f"Failed to generateo: {response.status_code} {response.text}")
            return
        
        if comparing:
            json: dict = response.json()["generated"]
            await send_message(ctx, f"Charles: {json[0]}\n\nExpect: {json[1]}\n\nRock: {json[2]}\n\nRuotsin: {json[3]}\n\nAll: {json[4]}")
        else:
            await send_message(ctx, response.json().get("generated", "Failed to generate???"))

async def setup(bot):
    await bot.add_cog(AIConnector(bot))
