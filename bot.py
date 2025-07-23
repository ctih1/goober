import os
import re
import json
import time
import random
import traceback
import subprocess
import tempfile
import shutil
import sys
from typing import (
    List,
    Dict,
    Literal,
    Set,
    Optional,
    Tuple,
    Any,
    TypedDict,
    Union,
    Callable,
    Coroutine,
    TypeVar,
    Type,
)
import logging
from modules.prestartchecks import start_checks
from modules.logger import GooberFormatter
import modules.keys as k
from modules import key_compiler
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from modules.settings import Settings as SettingsManager
from modules.permission import requires_admin


def build_keys():
    key_compiler.build_result(
        "en",
        "assets/locales",
        types=True,
        output_path="modules/keys.py",
        generate_comments=True,
    )


build_keys()

logger = logging.getLogger("goober")
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(GooberFormatter())

file_handler = logging.FileHandler("log.txt", mode="w+", encoding="UTF-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(GooberFormatter(colors=False))

logger.addHandler(console_handler)
logger.addHandler(file_handler)

settings_manager = SettingsManager()
settings = settings_manager.settings

splash_text: str = ""

with open(settings["splash_text_loc"], "r", encoding="UTF-8") as f:
    splash_text = "".join(f.readlines())
    print(splash_text)

start_checks()

import discord
from discord.ext import commands
from discord import app_commands
from discord import Colour, Message

from better_profanity import profanity
from discord.ext import commands

from modules.markovmemory import *
from modules.sentenceprocessing import *
from modules.unhandledexception import handle_exception
from modules.image import gen_demotivator

sys.excepthook = handle_exception


class MessageMetadata(TypedDict):
    user_id: str
    user_name: str
    guild_id: str | Literal["DM"]
    guild_name: str | Literal["DM"]
    channel_id: str
    channel_name: str
    message: str
    timestamp: float


# Constants with type hints
positive_gifs: List[str] = settings["bot"]["misc"]["positive_gifs"]
currenthash: str = ""
launched: bool = False
slash_commands_enabled: bool = False

# Set up Discord bot intents and create bot instance
intents: discord.Intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot: commands.Bot = commands.Bot(
    command_prefix=settings["bot"]["prefix"],
    intents=intents,
    allowed_mentions=discord.AllowedMentions(
        everyone=False, roles=False, users=False, replied_user=True
    ),
)

# Load memory and Markov model for text generation
memory: List[str | Dict[Literal["_meta"], MessageMetadata]] = load_memory()
markov_model: Optional[markovify.Text] = load_markov_model()
if not markov_model:
    logger.error(k.markov_model_not_found())
    memory = load_memory()
    markov_model = train_markov_model(memory)

generated_sentences: Set[str] = set()
used_words: Set[str] = set()


async def load_cogs_from_folder(bot: commands.Bot, folder_name="assets/cogs"):
    for filename in [file for file in os.listdir(folder_name) if file.endswith(".py")]:
        cog_name: str = filename[:-3]
        print(cog_name)

        if cog_name not in settings["bot"]["enabled_cogs"]:
            logger.debug(f"Skipping cog {cog_name} (not in enabled cogs)")
            continue

        module_path = folder_name.replace("/", ".").replace("\\", ".") + f".{cog_name}"

        try:
            await bot.load_extension(module_path)
            logger.info(f"{k.loaded_cog()} {cog_name}")
        except Exception as e:
            logger.error(f"{k.cog_fail()} {cog_name} {e}")
            traceback.print_exc()


# Event: Called when the bot is ready
@bot.event
async def on_ready() -> None:
    global launched
    global slash_commands_enabled

    folder_name: str = "cogs"
    if launched:
        return

    await load_cogs_from_folder(bot)
    try:
        synced: List[discord.app_commands.AppCommand] = await bot.tree.sync()
        logger.info(f"{k.synced_commands()} {len(synced)} {k.synced_commands2()}")
        slash_commands_enabled = True
        logger.info(k.started(settings["name"]))

    except discord.errors.Forbidden as perm_error:
        logger.error(f"Permission error while syncing commands: {perm_error}")
        logger.error(
            "Make sure the bot has the 'applications.commands' scope and is invited with the correct permissions."
        )
        quit()
    except Exception as e:
        logger.error(f"{k.fail_commands_sync()} {e}")
        traceback.print_exc()
        quit()

    if not settings["bot"]["misc"]["active_song"]:
        return
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name=settings["bot"]["misc"]["active_song"],
        )
    )
    launched = True


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    from modules.unhandledexception import handle_exception

    if isinstance(error, commands.CommandInvokeError):
        original: Exception = error.original
        handle_exception(
            type(original),
            original,
            original.__traceback__,
            context=f"Command: {ctx.command} | User: {ctx.author}",
        )
    else:
        handle_exception(
            type(error),
            error,
            error.__traceback__,
            context=f"Command: {ctx.command} | User: {ctx.author}",
        )


# Command: Retrain the Markov model from memory
@requires_admin()
@bot.hybrid_command(description=f"{k.command_desc_retrain()}")
async def retrain(ctx: commands.Context) -> None:
    global markov_model

    message_ref: discord.Message | None = await send_message(
        ctx, f"{k.command_markov_retrain()}"
    )
    if message_ref is None:
        logger.error("Failed to send message!")
        return

    try:
        with open(settings["bot"]["active_memory"], "r") as f:
            memory: List[str] = json.load(f)
    except FileNotFoundError:
        await send_message(ctx, f"{k.command_markov_memory_not_found()}")
        return
    except json.JSONDecodeError:
        await send_message(ctx, f"{k.command_markov_memory_is_corrupt()}")
        return

    data_size: int = len(memory)

    processing_message_ref: discord.Message | None = await send_message(
        ctx, f"{k.command_markov_retraining(data_size)}"
    )
    if processing_message_ref is None:
        logger.error("Couldnt find message processing message!")

    start_time: float = time.time()

    markov_model = train_markov_model(memory)
    save_markov_model(markov_model)

    logger.debug(f"Completed retraining in {round(time.time() - start_time,3)}s")

    await send_message(
        ctx,
        f"{k.command_markov_retrain_successful(data_size)}",
        edit=True,
        message_reference=processing_message_ref,
    )


# Command: Generate a sentence using the Markov model
@bot.hybrid_command(description=f"{k.command_desc_talk()}")
async def talk(ctx: commands.Context, sentence_size: int = 5) -> None:
    if not markov_model:
        await send_message(ctx, f"{k.command_talk_insufficent_text()}")
        return

    response: Optional[str] = None
    for _ in range(20):
        if sentence_size == 1:
            response = markov_model.make_short_sentence(max_chars=100, tries=100)
            if response:
                response = response.split()[0]
        else:
            response = markov_model.make_sentence(tries=100, max_words=sentence_size)

        if response and response not in generated_sentences:
            if sentence_size > 1:
                response = improve_sentence_coherence(response)
            generated_sentences.add(response)
            break

    if response:
        cleaned_response: str = re.sub(r"[^\w\s]", "", response).lower()
        coherent_response: str = rephrase_for_coherence(cleaned_response)
        if random.random() < 0.9 and is_positive(coherent_response):
            gif_url: str = random.choice(positive_gifs)
            combined_message: str = f"{coherent_response}\n[jif]({gif_url})"
        else:
            combined_message: str = coherent_response
        logger.info(combined_message)

        os.environ["gooberlatestgen"] = combined_message
        await send_message(ctx, combined_message)
    else:
        await send_message(ctx, f"{k.command_talk_generation_fail()}")


# New demotivator command
@bot.hybrid_command(description="Generate a demotivator poster with two lines of text")
async def demotivator(ctx: commands.Context) -> None:
    assets_folder: str = "assets/images"
    temp_input: str | None = None

    def get_random_asset_image() -> Optional[str]:
        files: List[str] = [
            f
            for f in os.listdir(assets_folder)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
        ]
        if not files:
            return None
        return os.path.join(assets_folder, random.choice(files))

    if ctx.message.attachments:
        attachment: discord.Attachment = ctx.message.attachments[0]
        if attachment.content_type and attachment.content_type.startswith("image/"):
            ext: str = os.path.splitext(attachment.filename)[1]
            temp_input = f"tempy{ext}"
            with open(temp_input, "wb") as f:
                await attachment.save(f)
            input_path: str = temp_input
        else:
            fallback_image: Optional[str] = get_random_asset_image()
            if fallback_image is None:
                await ctx.reply(k.no_image_available())
                return
            temp_input = tempfile.mktemp(suffix=os.path.splitext(fallback_image)[1])
            shutil.copy(fallback_image, temp_input)
            input_path = temp_input
    else:
        fallback_image = get_random_asset_image()
        if fallback_image is None:
            await ctx.reply(k.no_image_available())
            return
        temp_input = tempfile.mktemp(suffix=os.path.splitext(fallback_image)[1])
        shutil.copy(fallback_image, temp_input)
        input_path = temp_input

    output_path: Optional[str] = await gen_demotivator(input_path)

    if output_path is None or not os.path.isfile(output_path):
        if temp_input and os.path.exists(temp_input):
            os.remove(temp_input)
        await ctx.reply("Failed to generate demotivator.")
        return

    await ctx.send(file=discord.File(output_path))

    if temp_input and os.path.exists(temp_input):
        os.remove(temp_input)


bot.remove_command("help")


# Command: Show help information
@bot.hybrid_command(description=f"{k.command_desc_help()}")
async def help(ctx: commands.Context) -> None:
    embed: discord.Embed = discord.Embed(
        title=f"{k.command_help_embed_title()}",
        description=f"{k.command_help_embed_desc()}",
        color=Colour(0x000000),
    )

    command_categories: Dict[str, List[str]] = {
        f"{k.command_help_categories_general()}": [
            "mem",
            "talk",
            "about",
            "ping",
            "impact",
            "demotivator",
            "help",
        ],
        f"{k.command_help_categories_admin()}": ["stats", "retrain", "setlanguage"],
    }

    custom_commands: List[str] = []
    for cog_name, cog in bot.cogs.items():
        for command in cog.get_commands():
            if (
                command.name
                not in command_categories[f"{k.command_help_categories_general()}"]
                and command.name
                not in command_categories[f"{k.command_help_categories_admin()}"]
            ):
                custom_commands.append(command.name)

    if custom_commands:
        embed.add_field(
            name=f"{k.command_help_categories_custom()}",
            value="\n".join(
                [f"{settings["bot"]["prefix"]}{command}" for command in custom_commands]
            ),
            inline=False,
        )

    for category, commands_list in command_categories.items():
        commands_in_category: str = "\n".join(
            [f"{settings["bot"]["prefix"]}{command}" for command in commands_list]
        )
        embed.add_field(name=category, value=commands_in_category, inline=False)

    await send_message(ctx, embed=embed)


@requires_admin()
@bot.hybrid_command(description=f"{k.command_desc_setlang()}")
@app_commands.describe(locale="Choose your language")
async def setlanguage(ctx: commands.Context, locale: str) -> None:
    await ctx.defer()
    k.change_language(locale)
    await ctx.send(":thumbsup:")


# Event: Called on every message
@bot.event
async def on_message(message: discord.Message) -> None:
    global memory, markov_model
    EMOJIS = [
        "\U0001f604",
        "\U0001f44d",
        "\U0001f525",
        "\U0001f4af",
        "\U0001f389",
        "\U0001f60e",
    ]  # originally was emojis but it would probably shit itself on systems without unicode so....
    if message.author.bot:
        return

    if str(message.author.id) in settings["bot"]["blacklisted_users"]:
        return

    commands = [
        settings["bot"]["prefix"] + command.name for command in bot.tree.get_commands()
    ]

    if message.content.startswith(tuple(commands)):
        logger.info(f"{k.command_ran(message.author.name, message.content)}")
        await bot.process_commands(message)
        return

    if (
        profanity.contains_profanity(message.content)
        and settings["bot"]["misc"]["block_profanity"]
    ):
        return

    if message.content:
        if not settings["bot"]["user_training"]:
            return

        formatted_message: str = append_mentions_to_18digit_integer(message.content)
        cleaned_message: str = preprocess_message(formatted_message)
        if cleaned_message:
            memory.append(cleaned_message)

            message_metadata: MessageMetadata = {
                "user_id": str(message.author.id),
                "user_name": str(message.author),
                "guild_id": str(message.guild.id) if message.guild else "DM",
                "guild_name": str(message.guild.name) if message.guild else "DM",
                "channel_id": str(message.channel.id),
                "channel_name": str(message.channel),
                "message": message.content,
                "timestamp": time.time(),
            }
            try:
                if isinstance(memory, list):
                    memory.append({"_meta": message_metadata})
                else:
                    logger.warning("Memory is not a list; can't append metadata")
            except Exception as e:
                logger.warning(f"Failed to append metadata to memory: {e}")

            save_memory(memory)

        sentiment_score = is_positive(
            message.content
        )  # doesnt work but im scared to change the logic now please ignore
        if sentiment_score > 0.8:
            if not settings["bot"]["react_to_messages"]:
                return
            emoji = random.choice(EMOJIS)
            try:
                await message.add_reaction(emoji)
            except Exception as e:
                logger.info(f"Failed to react with emoji: {e}")

    await bot.process_commands(message)


# Event: Called on every interaction (slash command, etc.)
@bot.event
async def on_interaction(interaction: discord.Interaction) -> None:
    logger.info(f"{k.command_ran_s(interaction.user.name)} {interaction.user.name}")


# Global check: Block blacklisted users from running commands
@bot.check
async def block_blacklisted(ctx: commands.Context) -> bool:
    if ctx.author.id not in settings["bot"]["blacklisted_users"]:
        return True

    try:
        if isinstance(ctx, discord.Interaction):
            if not ctx.response.is_done():
                await ctx.response.send_message(k.blacklisted(), ephemeral=True)
            else:
                await ctx.followup.send(k.blacklisted(), ephemeral=True)
        else:
            await ctx.send(k.blacklisted_user(), ephemeral=True)
    except:
        return False

    return True


# Command: Show bot latency
@bot.hybrid_command(description=f"{k.command_desc_ping()}")
async def ping(ctx: commands.Context) -> None:
    await ctx.defer()
    latency: int = round(bot.latency * 1000)

    embed: discord.Embed = discord.Embed(
        title="Pong!!",
        description=(
            settings["bot"]["misc"]["ping_line"],
            f"`{k.command_ping_embed_desc()}: {latency}ms`\n",
        ),
        color=Colour(0x000000),
    )
    embed.set_footer(
        text=f"{k.command_ping_footer()} {ctx.author.name}",
        icon_url=ctx.author.display_avatar.url,
    )

    await ctx.send(embed=embed)


# Command: Show about information
@bot.hybrid_command(description=f"{k.command_about_desc()}")
async def about(ctx: commands.Context) -> None:
    embed: discord.Embed = discord.Embed(
        title=f"{k.command_about_embed_title()}", description="", color=Colour(0x000000)
    )

    embed.add_field(
        name=k.command_about_embed_field1(), value=f"{settings["name"]}", inline=False
    )

    embed.add_field(
        name=k.command_about_embed_field2name(),
        value=k.command_about_embed_field2value(
            local_version=local_version, latest_version=latest_version
        ),
        inline=False,
    )

    embed.add_field(name="Github", value=f"https://github.com/gooberinc/goober")

    await send_message(ctx, embed=embed)


@requires_admin()
@bot.hybrid_command(description="stats")
async def stats(ctx: commands.Context) -> None:
    memory_file: str = "memory.json"
    file_size: int = os.path.getsize(memory_file)

    with open(memory_file, "r") as file:
        line_count: int = sum(1 for _ in file)

    embed: discord.Embed = discord.Embed(
        title=f"{k.command_stats_embed_title()}",
        description=f"{k.command_stats_embed_desc()}",
        color=Colour(0x000000),
    )
    embed.add_field(
        name=f"{k.command_stats_embed_field1name()}",
        value=f"{k.command_stats_embed_field1value(file_size=file_size, line_count=line_count)}",
        inline=False,
    )
    embed.add_field(
        name=f"{k.command_stats_embed_field2name()}",
        value=f"{k.command_stats_embed_field2value(local_version=local_version, latest_version=latest_version)}",
        inline=False,
    )
    embed.add_field(
        name=f"{k.command_stats_embed_field3name()}",
        value=f"{k.command_stats_embed_field3value(
        NAME=settings["name"], PREFIX=settings["bot"]["prefix"], ownerid=settings["bot"]["owner_ids"][0],
        PING_LINE=settings["bot"]["misc"]["ping_line"], showmemenabled=settings["bot"]["allow_show_mem_command"],
        USERTRAIN_ENABLED=settings["bot"]["user_training"], song=settings["bot"]["misc"]["active_song"],
        splashtext=splash_text
    )}",
        inline=False,
    )

    await send_message(ctx, embed=embed)


# Command: Upload memory.json to litterbox.catbox.moe and return the link
@bot.hybrid_command()
async def mem(ctx: commands.Context) -> None:
    if not settings["bot"]["allow_show_mem_command"]:
        return

    command: str = (
        """curl -F "reqtype=fileupload" -F "time=1h" -F "fileToUpload=@memory.json" https://litterbox.catbox.moe/resources/internals/api.php"""
    )
    memorylitter: subprocess.CompletedProcess = subprocess.run(
        command, shell=True, capture_output=True, text=True
    )
    logger.debug(memorylitter)
    await send_message(ctx, memorylitter.stdout.strip())


# Helper: Improve sentence coherence (simple capitalization fix)
def improve_sentence_coherence(sentence: str) -> str:
    # Capitalizes "i" to "I" in the sentence
    sentence = sentence.replace(" i ", " I ")
    return sentence


class OnMyWatch:
    watchDirectory = "assets/locales"

    def __init__(self):
        self.observer = Observer()

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.watchDirectory, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(5)
        except:
            self.observer.stop()
            print("Observer Stopped")

        self.observer.join()


class Handler(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.is_directory:
            return None

        elif event.event_type == "modified":
            build_keys()


# Start the bot
bot.run(os.environ.get("DISCORD_BOT_TOKEN", ""))
