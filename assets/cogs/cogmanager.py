import discord
from discord.ext import commands
import discord.ext
import discord.ext.commands
from modules.permission import requires_admin
from modules.settings import Settings as SettingsManager

settings_manager = SettingsManager()
settings = settings_manager.settings


COG_PREFIX = "assets.cogs."


class CogManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @requires_admin()
    @commands.command()
    async def enable(self, ctx, cog_name: str):
        try:
            await self.bot.load_extension(COG_PREFIX + cog_name)
            await ctx.send(f"Loaded cog `{cog_name}` successfully.")
            settings["bot"]["enabled_cogs"].append(cog_name)
            settings_manager.commit()

        except Exception as e:
            await ctx.send(f"Error enabling cog `{cog_name}`: {e}")

    @requires_admin()
    @commands.command()
    async def load(self, ctx, cog_name: str | None = None):
        if cog_name is None:
            await ctx.send("Give cog_name")
            return

        if cog_name[:-3] not in settings["bot"]["enabled_cogs"]:
            await ctx.send("Please enable the cog first!")
            return
        if cog_name is None:
            await ctx.send("Please provide the cog name to load.")
            return
        try:
            await self.bot.load_extension(COG_PREFIX + cog_name)
            await ctx.send(f"Loaded cog `{cog_name}` successfully.")
        except Exception as e:
            await ctx.send(f"Error loading cog `{cog_name}`: {e}")

    @requires_admin()
    @commands.command()
    async def unload(self, ctx, cog_name: str | None = None):
        if cog_name is None:
            await ctx.send("Please provide the cog name to unload.")
            return
        try:
            await self.bot.unload_extension(COG_PREFIX + cog_name)
            await ctx.send(f"Unloaded cog `{cog_name}` successfully.")
        except Exception as e:
            await ctx.send(f"Error unloading cog `{cog_name}`: {e}")

    @requires_admin()
    @commands.command()
    async def disable(self, ctx, cog_name: str | None = None):
        if cog_name is None:
            await ctx.send("Please provide the cog name to disable.")
            return
        try:
            await self.bot.unload_extension(COG_PREFIX + cog_name)
            await ctx.send(f"Unloaded cog `{cog_name}` successfully.")
            settings["bot"]["enabled_cogs"].remove(cog_name)
            settings_manager.commit()
        except Exception as e:
            await ctx.send(f"Error unloading cog `{cog_name}`: {e}")

    @requires_admin()
    @commands.command()
    async def reload(self, ctx, cog_name: str | None = None):
        if cog_name is None:
            await ctx.send("Please provide the cog name to reload.")
            return

        if cog_name[:-3] not in settings["bot"]["enabled_cogs"]:
            await ctx.send("Please enable the cog first!")
            return
        try:
            await self.bot.unload_extension(COG_PREFIX + cog_name)
            await self.bot.load_extension(COG_PREFIX + cog_name)
            await ctx.send(f"Reloaded cog `{cog_name}` successfully.")
        except Exception as e:
            await ctx.send(f"Error reloading cog `{cog_name}`: {e}")

    @commands.command()
    async def listcogs(self, ctx):
        """Lists all currently loaded cogs in an embed."""
        cogs = list(self.bot.cogs.keys())
        if not cogs:
            await ctx.send("No cogs are currently loaded.")
            return

        embed = discord.Embed(
            title="Loaded Cogs",
            description="Here is a list of all currently loaded cogs:",
        )
        embed.add_field(name="Cogs", value="\n".join(cogs), inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(CogManager(bot))
