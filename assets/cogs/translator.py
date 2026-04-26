"""
Adapted from https://github.com/boysugi20/python-image-translator
Please check his project out, it's very cool!
"""

from PIL import Image, ImageDraw, ImageFont
import os, easyocr
import discord
from discord.ext import commands
from discord import app_commands

import discord.ext
import discord.ext.commands

import random

from modules.permission import requires_admin
from modules.sentenceprocessing import send_message
from modules.settings import instance as settings_manager
from typing import TypedDict, List, Tuple
import requests
import math
import logging

logger = logging.getLogger("goober")

def perform_ocr(image_path: str, reader: easyocr.Reader) -> List[Tuple[List[int], str]]:
    logger.info("Performing OCR")
    # Perform OCR on the image
    result = reader.readtext(image_path, width_ths = 0.8,  decoder="wordbeamsearch")

    # Extract text and bounding boxes from the OCR result
    extracted_text_boxes = [(entry[0], entry[1]) for entry in result if entry[2] > 0.4] # type: ignore

    return extracted_text_boxes # type: ignore


def get_font(image, text, width, height):

    # Default values at start
    font_size = None  # For font size
    font = None  # For object truetype with correct font size
    box = None  # For version 8.0.0
    x = 0
    y = 0

    draw = ImageDraw.Draw(image)  # Create a draw object

    # Test for different font sizes
    for size in range(1, 500):

        # Create new font
        new_font = ImageFont.truetype("assets/fonts/TNR.ttf", size=size)
        

        # Calculate bbox for version 8.0.0
        new_box = draw.textbbox((0, 0), text, font=new_font)

        # Calculate width and height
        new_w = new_box[2] - new_box[0]  # Bottom - Top
        new_h = new_box[3] - new_box[1]  # Right - Left

        # If too big then exit with previous values
        if new_w > width or new_h > height:
            break

        # Set new current values as current values
        font_size = size
        font = new_font
        box = new_box
        w = new_w
        h = new_h

        # Calculate position (minus margins in box)
        x = (width - w) // 2 - box[0]  # Minus left margin
        y = (height - h) // 2 - box[1]  # Minus top margin

    return font, x, y


def add_discoloration(color, strength):
    r, g, b = color[:3]
    r = max(0, min(255, r + strength))
    g = max(0, min(255, g + strength))
    b = max(0, min(255, b + strength))

    if r == 255 and g == 255 and b == 255:
        r, g, b = 245, 245, 245

    return (r, g, b)


def get_background_color(image, x_min, y_min, x_max, y_max):
    image = image.convert('RGBA')  # Handle transparency

    margin = 10
    edge_region = image.crop((
        max(x_min - margin, 0),
        max(y_min - margin, 0),
        min(x_max + margin, image.width),
        min(y_max + margin, image.height),
    ))

    pixels = list(edge_region.getdata())
    opaque_pixels = [pixel[:3] for pixel in pixels if pixel[3] > 0]

    if not opaque_pixels:
        background_color = (255, 255, 255)  # fallback if all pixels are transparent
    else:
        from collections import Counter
        most_common = Counter(opaque_pixels).most_common(1)[0][0]
        background_color = most_common

    background_color = add_discoloration(background_color, 40)
    return background_color


def get_text_fill_color(background_color):
    # Calculate the luminance of the background color
    luminance = (
        0.299 * background_color[0]
        + 0.587 * background_color[1]
        + 0.114 * background_color[2]
    ) / 255

    # Determine the text color based on the background luminance
    if luminance > 0.5:
        return "black"  # Use black text for light backgrounds
    else:
        return "white"  # Use white text for dark backgrounds


def replace_text_with_translation(image_path, translated_texts, text_boxes):
    # Open the image
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)

    # Load a font
    font = ImageFont.load_default()

    # Replace each text box with translated text
    for text_box, translated in zip(text_boxes, translated_texts):

        if translated is None:
            continue

        # Set initial values
        x_min, y_min = text_box[0][0][0], text_box[0][0][1]
        x_max, y_max = text_box[0][0][0], text_box[0][0][1]

        for coordinate in text_box[0]:

            x, y = coordinate

            if x < x_min:
                x_min = x
            elif x > x_max:
                x_max = x
            if y < y_min:
                y_min = y
            elif y > y_max:
                y_max = y

        # Find the most common color in the text region
        background_color = get_background_color(image, x_min, y_min, x_max, y_max)

        # Draw a rectangle to cover the text region with the original background color
        draw.rectangle(((x_min, y_min), (x_max, y_max)), fill=background_color)

        # Calculate font size, box
        font, x, y = get_font(image, translated, x_max - x_min, y_max - y_min)

        # Draw the translated text within the box
        draw.text(
            (x_min + x, y_min + y),
            translated,
            fill=get_text_fill_color(background_color),
            font=font,
        )

    return image


# Initialize the OCR reader
reader = easyocr.Reader(["sv", "it", "mt", "fr", "en"], model_storage_directory="data/models")



def deepl_translate(texts: List[str]) -> List[str]:
    logger.info("Getting DEEPL translatins")
    res = requests.post("https://api-free.deepl.com/v2/translate",
                        json={
                            "text": [f"<root>{text}</root>" for text in texts],
                            "target_lang": "EN",
                            "tag_handling": "xml",
                            "tag_handling_version": "v2",
                            "split_sentences": "off"
                        },
                        headers={
                            "Authorization": "DeepL-Auth-Key " + os.environ["DEEPL_KEY"],
                            "Content-Type": "application/json"
                        })

    logger.info(res.json())


    return [obj["text"] for obj in res.json()["translations"]]


class Translator(commands.Cog):
    # __init__ method is required with these exact parameters
    def __init__(
        self, bot: discord.ext.commands.Bot
    ):  # type hinting (aka : discord.ext.commands.Bot) isn't necessary, but provides better intellisense in code editors
        self.bot: discord.ext.commands.Bot = bot

    # A command which requires the executor to be an admin, and takes a discord user as an argument
    @requires_admin()  # from modules.permission import requires_admin
    @commands.command()
    async def translate(self, ctx: commands.Context):
        SIZE = 600
        await send_message(ctx, "Downloading your attachment")
        attachment = ctx.message.attachments[0]
        aspect_ratio = (attachment.width or 1) / (attachment.height or 1)

        if aspect_ratio < 1.0: # vertical
            height = min(SIZE, attachment.width or SIZE)
            width = round(height*aspect_ratio)
        else:
            width = min(SIZE, attachment.width or SIZE)
            height = round(width/aspect_ratio)

        image_url = attachment.proxy_url+f"{'' if attachment.proxy_url.endswith('&') else '&'}width={width}&height={height}"
        logger.info(f"Fetching attachment {image_url}   ")
        image_res = requests.get(image_url)

        with open("assets/images/cache/translaton_target.png", "wb") as f:
            f.write(image_res.content)

        await send_message(ctx, "OCR time! This might take a bit")
        extracted_text_boxes = perform_ocr("assets/images/cache/translaton_target.png", reader)

        texts_to_translate = [extracted_text_boxes[0][1]]
        
        print(extracted_text_boxes)
        last_box_bottom = extracted_text_boxes[0][0][3][1] # type: ignore
        last_box_height = abs(extracted_text_boxes[0][0][3][1] -  extracted_text_boxes[0][0][0][1]) # type: ignore

        for i in range(1, len(extracted_text_boxes)):
            processed_text = extracted_text_boxes[i][1].replace("\n", "").replace("<", "").replace(">", "")

            this_box_bottom = extracted_text_boxes[i][0][3][1] # type: ignore
            this_box_top = extracted_text_boxes[i][0][0][1] # type: ignore
            this_box_height = abs(extracted_text_boxes[i][0][3][1] -  extracted_text_boxes[i][0][0][1]) # type: ignore

            
            y_diff =  abs(this_box_top - last_box_bottom)
            height_diff = abs(last_box_height-this_box_height)

            logger.info(f"Difference: {y_diff} ({this_box_top}, {last_box_bottom}) and {height_diff} ({this_box_height}, {last_box_height})")
            if y_diff <= 16 and height_diff < 16: # type: ignore
                texts_to_translate[-1] += "<sep/>" + processed_text
            else:
                texts_to_translate.append(processed_text)

            last_box_bottom = this_box_bottom
            last_box_height = this_box_height
        
        logger.info(texts_to_translate)

        await send_message(ctx, "Translating stuff...")
        # Translate texts
        translated_texts = deepl_translate(texts_to_translate)
        
        processed_list = []

        for translation in translated_texts:
            processed_list.extend([trans.replace("<root>", "").replace("</root>", "") for trans in translation.split("<sep/>")])

        logger.info(processed_list)
        logger.info([data[1] for data in extracted_text_boxes])
        logger.info(f"{len(processed_list)} vs {len(translated_texts)} vs {len(extracted_text_boxes)}")

        # Replace text with translated text
        image = replace_text_with_translation("assets/images/cache/translaton_target.png", processed_list,
                                              extracted_text_boxes)
        
        image.save("assets/images/cache/translation.png", "png")
        
        with open("assets/images/cache/translation.png", "rb") as f:
            await send_message(ctx, "Done", file=discord.File(f))


async def setup(bot):
    await bot.add_cog(Translator(bot))
