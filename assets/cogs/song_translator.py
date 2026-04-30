import discord
from discord.ext import commands
from discord import app_commands

import discord.ext
import discord.ext.commands

import random
from modules.permission import is_admin
from modules.sentenceprocessing import send_message
from modules.settings import instance as settings_manager
from typing import TypedDict, Dict, List
import time
from slugify import slugify
from pytubefix import AsyncYouTube
import requests
import logging
import math
import os
import shutil
import asyncio

logger = logging.getLogger("goober")

class LRCLIBResponse(TypedDict):
    id: int
    name: str
    trackName: str
    artistName: str
    albumName: str
    duration: float
    instrumental: bool
    plainLyrics: str
    syncedLyrics: str


class WaitingObject(TypedDict):
    video_url: str
    options: List[LRCLIBResponse]
    message: discord.Message


class SongTranslator(commands.Cog): 
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot: discord.ext.commands.Bot = bot
        self.waiting_ids: Dict[int, WaitingObject] = {}

    def get_srt_time(self, raw: str, offset: float) -> str:
        minute_offset = offset//60
        ms_offset = abs(math.floor(offset) - offset)*1000
    
        i_minutes = int(int(raw[:2]) + minute_offset)
        i_seconds = int(raw[3:5]) + math.floor(offset) - int(minute_offset * 60)
        i_milliseconds = int(round(int(raw[6:8])*10 + ms_offset, 3))
        
        if i_milliseconds > 999:
            i_milliseconds = 0
            i_seconds += 1
    
        if i_seconds >= 60:
            i_seconds = 0
            i_minutes += 1

        string =  f"00:{str(i_minutes).zfill(2)}:{str(i_seconds).zfill(2)},{str(i_milliseconds).zfill(3)}"
        logger.info(f"Raw: {raw}, now: {string}")

        return string

    def deepl_translate(self, texts: List[str]) -> List[str]:
        logger.info("Getting DEEPL Translations")
        res = requests.post("https://api-free.deepl.com/v2/translate",
                            json={
                                "text": texts,
                                "target_lang": "EN",
                                "split_sentences": "off"
                            },
                            headers={
                                "Authorization": "DeepL-Auth-Key " + os.environ["DEEPL_KEY"],
                                "Content-Type": "application/json"
                            })
        
        return [obj["text"] for obj in res.json()["translations"]]


    def turn_synced_to_srt(self, synced: str, video_length_s: float, offset: float) -> str:
        minutes = video_length_s//60
        subtitles = ""
        last_subtitle = f"00:{str(minutes).zfill(2)}:{str(video_length_s-(minutes*60)).zfill(2)},00"

        lyrics = synced.split("\n")

        texts = []

        for i, lyric in enumerate(lyrics):
            if not lyric: continue
            
            time, text = lyric.split("]", 1)

            srt_time = self.get_srt_time(time.replace("[", ""), offset)

            if i != len(lyrics)-1:
                next_time = self.get_srt_time(lyrics[i+1].split("]", 1)[0].replace("[", ""), offset)
            else:
                next_time = last_subtitle

            srt = f"{i+1}\n{srt_time} --> {next_time}\nCONTENT{i}\n\n"
            texts.append(text.strip())
            subtitles += srt

        translated_texts = self.deepl_translate(texts)
        for i, text in enumerate(translated_texts):
            subtitles = subtitles.replace(f"CONTENT{i}", text, 1)

        return subtitles

    async def translate_and_combine(self, message: discord.Message, video_id: str, video_length: float, lyrics: str, synced: bool, offset: float = 0.0) -> None:
        logger.info(f"Translating lyrics synced? {synced} ({lyrics[4:]})")
        await message.edit(content="Translating lyrics...")

        if not synced:
            translated_subtitles = "\n".join(self.deepl_translate(lyrics.split("\n")))
            await message.edit(content=translated_subtitles)
            return
    
        with open(f"data/youtube/{video_id}.srt", "w", encoding="utf-8") as f:
            f.writelines(self.turn_synced_to_srt(lyrics, video_length, offset))
        
        path = os.path.abspath(f"data/youtube/{video_id}").replace("\\", "/")
        logger.info(path)

        await message.edit(content="Burning lyrics onto video...")

        command = f'{os.environ.get("FFMPEG_PATH", "ffmpeg")} -i {path}.mp4 {os.environ.get("FFMPEG_ARGS", "")} -vf "subtitles=filename={path}.srt" {path}_sub.mp4'
        logger.info(command)
        code = os.system(command)
        if code != 0:
            logger.error(f"ffmpeg exited with {code}")
            await message.edit(content=f"FF Mpreg failed with error {code}")
            return
    
        logger.info("Done")

        if os.path.getsize(path+"_sub.mp4") < 9.5*1024*1024:
            await message.edit(content="Sending video...")
            with open(path+"_sub.mp4", "rb") as f:
                await message.reply(file=discord.File(f))
        else:
            shutil.move(path+"_sub.mp4", f"data/cdn/{video_id}_sub.mp4")
            await message.reply(content=f"https://homecdn.frii.site/vids/{video_id}_sub.mp4")


    def get_first_lyric_time(self, lyrics: str) -> str:
        return lyrics.split("\n")[0].split("]", 1)[0].replace("[", "")

    async def download_video(self, url: str, user_id: int, message: discord.Message) ->  AsyncYouTube:
        await message.edit(content="Fetching video data...")

        video = AsyncYouTube(url, use_oauth=True, allow_oauth_cache=True)

        if await video.length() > 5*60 and not is_admin(user_id):
            await message.edit(content="Video is too long!! Consult an admin to download xwx")
        
        await message.edit(content=f"Found video '{await video.title()}', downloading.. This may take a bit...")
        stream = (await video.streams()).filter(progressive=True, file_extension="mp4")
        target_stream = stream.get_by_resolution("480p") or stream.get_by_resolution("360p") or stream.get_by_resolution("240p") or stream.get_by_resolution("144p")
        assert target_stream

        loop = asyncio.get_running_loop()

        await loop.run_in_executor(None, lambda: target_stream.download(f"data/youtube", filename=video.video_id+".mp4"))

        return video


    @commands.command()
    async def translate(self, ctx: commands.Context, *args):
        logger.info(f"Trying {' '.join(args[1:])}")
        url: str = args[0]

        if not url.startswith(("https://www.youtube.com", "https://youtu.be")):
            await send_message(ctx, "Please give a YouTube link!! (starting with https://www.youtube.com)")
            return

        message = await send_message(ctx, "Searching for subtitles...")

        response = requests.get(f"https://lrclib.net/api/search?q={slugify(' '.join(args[1:]), separator='+')}")
        matches: List[LRCLIBResponse] = response.json()

        if len(matches) == 0:
            await message.edit(content=f"No lyrics available!")
            return

        if len(matches) > 1:
            response_string = ""
            
            for i, match in enumerate(matches, start=1):
                styling = "**" if match["syncedLyrics"] else ""

                response_string +=  f"""{styling} {i}. {match["artistName"]} - {match["trackName"]} {styling} ({match["duration"]}s {f"starts @ {self.get_first_lyric_time(match['syncedLyrics'])}s" if styling else ""})\n"""

            await message.edit(content=f"Found multiple matches. **Bolded entries are time synced**. Reply with the number:\n\n{response_string}")

            self.waiting_ids[ctx.author.id] = {
                "options": matches,
                "video_url": url,
                "message": message
            }

            return
        
        else:
            synced_lyrics = matches[0]["syncedLyrics"]
            lyrics = matches[0]["plainLyrics"]

        video = await self.download_video(url, ctx.author.id, message)

        await self.translate_and_combine(message, video.video_id, await video.length(), synced_lyrics or lyrics, bool(synced_lyrics))
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        waiting_object: WaitingObject | None = self.waiting_ids.get(message.author.id)

        if self.bot.user not in message.mentions or not waiting_object:
            return

        try:
            parts = message.content.split(" ")
            offset = 0

            if len(parts) > 1:
                offset = float(parts[1])

            song_id = int(parts[0])-1

            song = waiting_object["options"][song_id]
            synced_lyrics = song["syncedLyrics"]
            lyrics = song["plainLyrics"]

            video = await self.download_video(waiting_object["video_url"], message.author.id, waiting_object["message"])

            await self.translate_and_combine(waiting_object["message"], video.video_id, await video.length(), synced_lyrics or lyrics, bool(synced_lyrics), offset)
        except ValueError:
            logger.info("Failed to convert")
                

async def setup(bot):
    await bot.add_cog(SongTranslator(bot))
