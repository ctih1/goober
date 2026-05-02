
import discord
from discord.ext import commands
from discord import app_commands

import discord.ext
import discord.ext.commands

import random
import asyncio
from modules.permission import requires_admin
from modules.sentenceprocessing import send_message
from modules.settings import instance as settings_manager
from typing import TypedDict, Dict, List, Union, Literal
from pytubefix import AsyncYouTube, Search, YouTube
import logging
import requests_async
import slugify
import os
import time
import base64

logger = logging.getLogger("goober")

class VideoThumbnail(TypedDict):
    quality: str
    url: str
    width: int
    height: int

class AuthorThumbnail(TypedDict):
    url: str
    width: int
    height: int
# --- Primary Types ---

class VideoEntry(TypedDict):
    type: Literal["video"]
    title: str
    videoId: str
    author: str
    authorId: str
    authorUrl: str
    videoThumbnails: List[VideoThumbnail]
    description: str
    descriptionHtml: str
    viewCount: int
    published: int
    publishedText: str
    lengthSeconds: int
    liveNow: bool
    paid: bool
    premium: bool

class WaitingUser(TypedDict):
    message: discord.Message
    videos: List[VideoEntry]
    search_string: str

class NaviDrome(commands.Cog): 
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot: discord.ext.commands.Bot = bot
        self.waiting_users: Dict[int, WaitingUser] = {}

    @commands.command()
    async def song(self, ctx: commands.Context, *args):
        message: discord.Message = await send_message(ctx, message=f"Searching...")

        res = await requests_async.get(f"https://inv.thepixora.com/api/v1/search?q={slugify.slugify(' '.join(args))}&page=0&sort=relevance&type=video")
        data: List[VideoEntry] = res.json()

        response_string = ""

        if len(data) == 0:
            await message.edit(content=f"No matches for \"{' '.join(args)}\"")
            return
        
        for i, video in enumerate(data, start=1):
            minutes = video["lengthSeconds"] // 60
            seconds = video["lengthSeconds"] - minutes * 60
            response_string += f"**{i}. {video['title'].strip()}** {video['author']} ({minutes}:{seconds})\n\n"
            
        await message.edit(content=f"Found matches. Reply with the number:\n\n{response_string}")
        self.waiting_users[ctx.author.id] = {
            "message": message,
            "search_string": " ".join(args),
            "videos": data
        }

    async def download_music(self, match: VideoEntry, message: discord.Message):
        if match["lengthSeconds"] > 7 * 60:
            await message.edit(content="Ayo sussy boy that video is looking long ash im not letting you download that shit")
            return
        
        video = AsyncYouTube(url=f"https://youtube.com/watch?v={match['videoId']}")
        stream = (await video.streams()).filter(only_audio=True, mime_type="audio/webm").first()
        if stream is None:
            await message.edit(content="No suitable audio streams found")
            return
    
        await message.edit(content="Downloading stream...")
        
        path = os.path.abspath(f"data/youtube/{match['videoId']}")
        os.makedirs(path, exist_ok=True)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: stream.download(f"data/youtube/{match['videoId']}", filename="audio.webm"))

        await message.edit(content="Downloaded stream! Downloading thumbnail..")

        thumbnail_path = os.path.join(path, "thumbnail.jpg")
        audio_path = os.path.join(path, "audio.webm")
        final_path = os.path.join(path, f"{match['videoId']}.mp3")

        res = await requests_async.get(match["videoThumbnails"][3]["url"], allow_redirects=True)
        with open(thumbnail_path, "wb") as f:
            f.write(res.content)
        
        await message.edit(content="Adding metadata with ffmpeg...")

        command = f"""{os.environ.get("FFMPEG_PATH", "ffmpeg")} -i {audio_path} -i {thumbnail_path} -map 0:a -map 1:v -c:v mjpeg -id3v2_version 3 -y {os.environ.get("FFMPEG_ARGS_AUDIO", "-ab 128k -ar 44100")} -metadata:s:v title="Album cover" -metadata:s:v comment="Cover (front)" -metadata title="{match['title']}" -metadata artist="{match['author'].replace('- Topic', "").strip()}" -metadata year="{time.strftime('%Y', time.gmtime(match['published']))}" {final_path}"""
        logger.info(command)
        code = os.system(command)
        if code != 0:
            logger.error(f"ffmpeg exited with {code}")
            await message.edit(content=f"FF Mpreg failed with error {code}")
            return
        
        await message.edit(content="Uploading...")
        try:
            res = await requests_async.post(
                os.environ["NAVIDROME_INSTANCE"],
                headers={"Authorization": f"Basic {base64.b64encode(os.environ['NAVIDROME_AUTH'].encode()).decode()}"},
                files={"file": open(final_path, "rb")}
            )
        except Exception as e:
            logger.error(e)
            await message.edit(content="Upload failed.")
            return
        
        if res.status_code != 200:
            await message.edit(content=f"Upload failed with status code {res.status_code}")
            return
        
        await message.edit(content="Uploaded succesfully!!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        waiting_object: WaitingUser | None = self.waiting_users.get(message.author.id)
        if self.bot.user not in message.mentions or not waiting_object:
            return
        
        try:            
            song_id = int(message.content.split(" ")[0]) - 1
            target_song = waiting_object["videos"][song_id]
            await waiting_object["message"].edit(content="Fetching video streams...")

            await self.download_music(target_song, waiting_object["message"])
        except ValueError:
            logger.info("Failed to convert")

async def setup(bot):
    await bot.add_cog(NaviDrome(bot))
