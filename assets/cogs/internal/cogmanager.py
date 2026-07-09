import discord
from discord.ext import commands
import discord.ext
import discord.ext.commands
from modules.permission import requires_admin
from modules.settings import instance as settings_manager
from modules.globalvars import available_cogs
import logging

settings = settings_manager.settings


COG_PREFIX = "assets.cogs."

logger = logging.getLogger("goober")

class CogManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @requires_admin()
    @commands.command()
    async def enable(self, ctx, cog_name: str):
        try:
            await self.bot.load_extension(COG_PREFIX + cog_name)
            await ctx.send(f"Loaded cog `{cog_name}` successfully.")
            settings["bot"]["enabled_cogs"].append(cog_name)
            settings_manager.add_admin_log_event(
                {
                    "action": "add",
                    "author": ctx.author.id,
                    "change": "enabled_cogs",
                    "messageId": ctx.message.id,
                    "target": cog_name,
                }
            )
            settings_manager.commit()

        except Exception as e:
            await ctx.send(f"Error enabling cog `{cog_name}`: {e}")

    @requires_admin()
    @commands.command()
    async def load(self, ctx, cog_name: str | None = None):
        if cog_name is None:
            await ctx.send("Give cog_name")
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
            settings_manager.add_admin_log_event(
                {
                    "action": "del",
                    "author": ctx.author.id,
                    "change": "enabled_cogs",
                    "messageId": ctx.message.id,
                    "target": cog_name,
                }
            )
            settings_manager.commit()
        except Exception as e:
            await ctx.send(f"Error unloading cog `{cog_name}`: {e}")

    @requires_admin()
    @commands.command()
    async def reload(self, ctx: commands.Context, cog_name: str | None = None):
        if cog_name is None:
            await ctx.send("Please provide the cog name to reload.")
            return
        
        try:
            await self.bot.unload_extension(COG_PREFIX + cog_name)
            await self.bot.load_extension(COG_PREFIX + cog_name)
            await ctx.send(f"Reloaded cog `{cog_name}` successfully.")
        except discord.ext.commands.ExtensionNotLoaded as e:
            logger.warning("Trying to find command...")
            found_cog: bool = False
            for _cog_name, cog in self.bot.cogs.items():
                for command in cog.get_commands():
                    if cog_name != command.name: continue
                    
                    await self.bot.unload_extension(COG_PREFIX + _cog_name.lower())
                    await self.bot.load_extension(COG_PREFIX + _cog_name.lower())

                    await ctx.send(f"Reloaded cog `{_cog_name.lower()}` successfully. Specify the real name next time retard.")
                    found_cog = True
                    break
                
                if found_cog: break

            if not found_cog:
                await ctx.send(f"Could not find cog or command `{cog_name}`")
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
        embed.add_field(name="Loaded cogs", value="\n".join(cogs), inline=False)
        embed.add_field(name="Available cogs", value="\n".join(available_cogs()))
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(CogManager(bot))
