import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import requests_async
from modules.sentenceprocessing import send_message
import os
from colorsys import hsv_to_rgb
import random


class Text(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.spotify_header_font = ImageFont.truetype("assets/fonts/resotyc-Regular.ttf", 54)
        self.spotify_artist_font = ImageFont.truetype("assets/fonts/gevher-black.otf", 58)

        self.assets = os.path.join("assets", "images")
        self.cache = os.path.join(self.assets, "cache")
        os.makedirs(self.cache, exist_ok=True)

        self.description = "🖋️|Create inspirational posters"


    @commands.command()
    async def this_is(self, ctx: commands.Context, *args):
        artist: str = " ".join(args)
        top_text = "THIS IS"

        if ";" in artist:
            (top_text, artist) = artist.split(";", 1)
        
        if len(ctx.message.attachments) == 0:
            await ctx.reply("Please send an image along w the message!")
            return

        with open(os.path.join(self.cache, "artist.png"), "wb") as f:
            res = await requests_async.get(ctx.message.attachments[0].url)
            f.write(res.content)

        image = Image.new("RGB", (512, 512), 0xffffff)
        image.paste(tuple([round(r*255) for r in hsv_to_rgb(random.random(), 0.7, 0.9)]), (0, round(image.size[1]/2), image.size[0], image.size[1]))

        draw = ImageDraw.Draw(image)

        top_length = self.spotify_header_font.getlength(top_text)/2
        draw.text((image.size[0]/2 - top_length, 32), top_text, font=self.spotify_header_font, fill="black")
        draw.text((image.size[0]/2 - self.spotify_artist_font.getlength(artist)/2, 430), artist, font=self.spotify_artist_font, fill="black")

        artist_image = Image.open(os.path.join(self.cache, "artist.png"))
        artist_ratio = artist_image.height / artist_image.width

        if artist_ratio > 1:
            artist_image = artist_image.resize((round(300/artist_ratio), 300))
        else:
            artist_image = artist_image.resize((360, round(360*artist_ratio)))

        spotify_logo = Image.open(os.path.join(self.assets, "spotify.png")).convert("RGBA")
        spotify_logo = spotify_logo.resize((50,50))

        if top_length > 400:
            image.paste(spotify_logo, (16,16, 50+16, 50+16), spotify_logo)

        (x,y) = image.size[0]//2 - artist_image.size[0]//2, image.size[0] // 2 - artist_image.size[1]//2
        image.paste(artist_image, (x,y, x+artist_image.width, y+artist_image.height))

        image.save(os.path.join(self.cache, "this_is.png"))


        await send_message(ctx, file=discord.File(os.path.join(self.cache, "this_is.png")))


    @commands.command()
    async def tzu(self, ctx: commands.Context, *args):
        quote: str = " ".join(args)

        await ctx.reply(None)


async def setup(bot):
    await bot.add_cog(Text(bot))
