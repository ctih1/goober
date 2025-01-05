import discord
from discord.ext import commands
import os 

class CogManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner_id = int(os.getenv("ownerid"))
    @commands.command()
    async def load(self, ctx, cog_name: str = None):
        if ctx.author.id != self.owner_id:
            await ctx.send("You do not have permission to use this command.")
            return
        if cog_name is None:
            await ctx.send("Please provide the cog name to load.")
            return
        try:
            await self.bot.load_extension(f"cogs.{cog_name}")
            await ctx.send(f"Loaded cog `{cog_name}` successfully.")
        except Exception as e:
            await ctx.send(f"Error loading cog `{cog_name}`: {e}")

    @commands.command()
    async def unload(self, ctx, cog_name: str = None):
        if ctx.author.id != self.owner_id:
            await ctx.send("You do not have permission to use this command.")
            return
        if cog_name is None:
            await ctx.send("Please provide the cog name to unload.")
            return
        try:
            await self.bot.unload_extension(f"cogs.{cog_name}")
            await ctx.send(f"Unloaded cog `{cog_name}` successfully.")
        except Exception as e:
            await ctx.send(f"Error unloading cog `{cog_name}`: {e}")

    @commands.command()
    async def reload(self, ctx, cog_name: str = None):
        
        if ctx.author.id != self.owner_id:
            await ctx.send("You do not have permission to use this command.")
            return
        if cog_name is None:
            await ctx.send("Please provide the cog name to reload.")
            return
        try:
            await self.bot.unload_extension(f"cogs.{cog_name}")
            await self.bot.load_extension(f"cogs.{cog_name}")
            await ctx.send(f"Reloaded cog `{cog_name}` successfully.")
        except Exception as e:
            await ctx.send(f"Error reloading cog `{cog_name}`: {e}")

async def setup(bot):
    await bot.add_cog(CogManager(bot))
