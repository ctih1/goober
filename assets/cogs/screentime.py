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
from typing import TypedDict, Dict, List, Tuple
from logging import getLogger
from functools import lru_cache
from datetime import datetime, timedelta
from datetime import time as dt_time

logger = getLogger("goober")


class Screentime(commands.Cog):
    def __init__(self, bot: discord.ext.commands.Bot):
        self.description = "📱|View screentime of members on the server"
        self.bot: discord.ext.commands.Bot = bot
        self.db = sqlite3.connect("presence.db")
        self.users_db = sqlite3.connect("users.db")

        self.db.execute(
            "CREATE TABLE IF NOT EXISTS presences(user_id int NOT NULL, status varchar(32), changed_at int)"
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_presence_events ON presences(user_id, changed_at)"
        )

        self.users_db.execute(
            "CREATE TABLE IF NOT EXISTS users(user_id int PRIMARY KEY, fake_offline_count int, UNIQUE(user_id))"
        )

        self.presence_map: Dict[int, str] = {}

    @commands.Cog.listener()
    async def on_presence_update(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        if after.bot:
            return

        if after.id not in self.presence_map:
            self.presence_map[after.id] = after.status.value
        elif self.presence_map[after.id] == after.status.value:
            return

        logger.debug("Updating status DB")

        self.db.execute(
            "INSERT INTO presences VALUES(?, ?, ?)",
            [after.id, after.status.value, round(time.time())],
        )
        self.db.commit()

        self.presence_map[after.id] = after.status.value

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if isinstance(message.author, discord.User):
            return
        if message.author.bot:
            return

        if message.author.status.value in ["offline", "invisible", "idle"]:
            self.users_db.execute(
                "INSERT OR IGNORE INTO users(user_id, fake_offline_count) VALUES (?, ?)",
                [message.author.id, 0],
            )
            self.users_db.execute(
                "UPDATE users SET fake_offline_count = fake_offline_count + 1 WHERE user_id = ?",
                [message.author.id],
            )

            self.users_db.commit()

    @staticmethod
    @lru_cache(typed=False)
    def get_total_screentime_seconds(
        rows: Tuple[Tuple[int, str, int]], since: int = 0
    ) -> int:
        online_since: int | None = None
        total_time_online: int = 0
        for row in rows:
            user_id, presence, time_ = row
            if time_ < since:
                continue
            if (presence in ["online", "dnd"]) and not online_since:
                online_since = time_

            if (presence == "offline" or presence == "idle") and online_since:
                total_time_online += time_ - online_since
                online_since = None

        if online_since:
            total_time_online += round(time.time()) - online_since

        return total_time_online

    @commands.command()
    async def screentime(
        self, ctx: commands.Context, user: discord.Member | None = None
    ):
        target_user = user or ctx.author
        target = target_user.id

        start = time.time()

        rows = tuple(
            sorted(
                self.db.execute("SELECT * FROM presences WHERE user_id = ?", [target]),
                key=lambda row: row[2],
            )
        )
        total_time_online = Screentime.get_total_screentime_seconds(rows)
        today = Screentime.get_total_screentime_seconds(
            rows, datetime.combine(datetime.today(), dt_time.min).timestamp()
        )
        seven_days = Screentime.get_total_screentime_seconds(
            rows,
            datetime.combine(
                datetime.today() - timedelta(days=7), dt_time.min
            ).timestamp(),
        )

        embed = discord.Embed(title="Screentime")
        embed.add_field(name="Total", value=format_timespan(total_time_online))
        embed.add_field(name="Today", value=format_timespan(today))
        embed.add_field(name="Last 7 days", value=format_timespan(seven_days))
        embed.set_footer(text=f"Processed for {(time.time() - start):.3f}s")
        embed.set_author(
            name=target_user.name,
            icon_url=(None if not target_user.avatar else target_user.avatar.url),
        )

        await send_message(ctx, embed=embed)

    @commands.command()
    async def screentime_leaderboard(self, ctx: commands.Context):
        start = time.time()

        rows = self.db.execute("SELECT * FROM presences ORDER BY user_id, changed_at")

        users: Dict[int, List[Tuple[int, str, int]]] = {}
        for row in rows:
            user_id, presence, time_ = row

            if user_id not in users:
                users[user_id] = []

            users[user_id].append((user_id, presence, time_))

        embed = discord.Embed(title="Screentime leaderboard")

        user_times = [
            (user_id, Screentime.get_total_screentime_seconds(tuple(rows)))
            for user_id, rows in users.items()
        ]
        user_times = sorted(user_times, key=lambda d: d[1], reverse=True)

        for i, (user, _time) in enumerate(user_times):
            embed.add_field(
                name=f"", value=f"{i+1}. <@{user}>: {format_timespan(_time)}"
            )

        embed.set_footer(text=f"Processing took {(time.time()-start):.3f}s")
        await ctx.reply(embed=embed)

    @requires_admin()
    @commands.command()
    async def kill_larper(self, ctx: commands.Context, *args):
        sure = " ".join(args[1:])
        id = int(args[0])

        if sure != "i am totally sure":
            await ctx.reply(
                f"Please add 'i am totally sure' to the end! Youre killing <@{id}>"
            )
            return

        self.db.execute("DELETE FROM presences WHERE user_id = ?", [id])
        self.db.commit()
        await ctx.reply(f"Larper <@{id}> killed")

    @commands.command()
    async def offline_larps(
        self, ctx: commands.Context, user: discord.Member | None = None
    ):
        target = (None if not user else user.id) or ctx.author.id

        rows = self.users_db.execute("SELECT * FROM users WHERE user_id = ?", [target])

        for row in rows:
            await ctx.reply(
                f"User has sent messages offline or while in idle: {row[1]} times"
            )
            return

        await ctx.reply("No larps!")


async def setup(bot):
    await bot.add_cog(Screentime(bot))
