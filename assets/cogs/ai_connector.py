import discord
from discord.ext import commands
from discord.ext.commands import Context
import requests
from requests import Response

class AIConnector(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
            response: Response = requests.post("http://host.docker.internal:3800/generate", json={"prompt": content, "person": person})

        if comparing:
            json: dict = response.json()["generated"]
            await ctx.send(f"Charles: {json[0]}\n\nExpect: {json[1]}\n\nRock: {json[2]}\n\nRuotsin: {json[3]}\n\nAll: {json[4]}")
        else:
            await ctx.send(response.json()["generated"])

async def setup(bot):
    await bot.add_cog(AIConnector(bot))
