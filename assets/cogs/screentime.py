import discord
from discord.ext import commands
from discord import app_commands
import time
import discord.ext
import discord.ext.commands
import sqlite3
from modules.permission import requires_admin
from modules.sentenceprocessing import send_message
from modules.settings import instance as settings_manager
from humanfriendly import format_timespan
from typing import TypedDict, Dict
from logging import getLogger

logger = getLogger("goober")

class Screentime(commands.Cog): 
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot: discord.ext.commands.Bot = bot
        self.db = sqlite3.connect("presence.db")
        self.users_db = sqlite3.connect("users.db")


        self.db.execute("CREATE TABLE IF NOT EXISTS presences(user_id int NOT NULL, status varchar(32), changed_at int)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_presence_events ON presences(user_id, changed_at)")

        self.users_db.execute("CREATE TABLE IF NOT EXISTS users(user_id int PRIMARY KEY, fake_offline_count int, UNIQUE(user_id))")

        self.presence_map: Dict[int, str] = {}
        
    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member) -> None:
        if after.id not in self.presence_map:
            self.presence_map[after.id] = after.status.value
        elif self.presence_map[after.id] == after.status.value:
            return

        logger.info("Updating status DB")

        self.db.execute("INSERT INTO presences VALUES(?, ?, ?)", [after.id, after.status.value, round(time.time())])
        self.db.commit()

        self.presence_map[after.id] = after.status.value

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if isinstance(message.author, discord.User): return

        if message.author.status.value in ["offline", "invisible"]:
            self.users_db.execute("INSERT OR IGNORE INTO users(user_id, fake_offline_count) VALUES (?, ?)", [message.author.id, 0])
            self.users_db.execute("UPDATE users SET fake_offline_count = fake_offline_count + 1 WHERE user_id = ?", [message.author.id])

            self.users_db.commit()

    @commands.command()
    async def screentime(self, ctx: commands.Context, user: discord.Member | None = None):
        target = (None if not user else user.id)  or ctx.author.id

        rows = sorted(self.db.execute("SELECT * FROM presences WHERE user_id = ?", [target]), key=lambda row: row[2])
        
        online_since: int | None = None
        total_time_online: int = 0
        for row in rows:
            (user_id, presence, time_) = row
            if (presence in ["online", "dnd"]) and not online_since:
                online_since = time_
            
            if (presence == "offline" or presence == "idle") and online_since:
                total_time_online += time_ - online_since
                online_since = None
        
        if online_since:
            total_time_online += round(time.time()) - online_since

        await send_message(ctx, format_timespan(total_time_online))

async def setup(bot):
    await bot.add_cog(Screentime(bot))
