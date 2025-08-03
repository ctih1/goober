import logging
from modules.logger import GooberFormatter
from modules import key_compiler
import tracemalloc

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

logger.info("Starting...")
def build_keys():
    logger.info("Building keys")
    key_compiler.build_result(
        "en",
        "assets/locales",
        types=True,
        output_path="modules/keys.py",
        generate_comments=True,
    )
    logger.info("Built keys!")

build_keys()

import os
import time
import random
import traceback
import tempfile
import shutil
import sys
from typing import (
    List,
    Dict,
    Literal,
    Set,
    Optional,
    TypedDict
)
import logging
from modules.prestartchecks import start_checks
import modules.keys as k
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from modules.settings import instance as settings_manager, ActivityType
from modules.sync_connector import instance as sync_connector
import threading

messages_recieved = 0


settings = settings_manager.settings
k.change_language(settings["locale"])

splash_text: str = ""

with open(settings["splash_text_loc"], "r", encoding="UTF-8") as f:
    splash_text = "".join(f.readlines())
    print(splash_text)

start_checks()

import discord
from discord.ext import commands

from better_profanity import profanity
from discord.ext import commands

from modules.markovmemory import *
from modules.sentenceprocessing import *
from modules.unhandledexception import handle_exception
from modules.image import gen_demotivator

sys.excepthook = handle_exception
tracemalloc.start()
class MessageMetadata(TypedDict):
    user_id: str
    user_name: str
    guild_id: str | Literal["DM"]
    guild_name: str | Literal["DM"]
    channel_id: str
    channel_name: str
    message: str
    timestamp: float

os.makedirs("data", exist_ok=True)

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
markov_model: markovify.Text | None = load_markov_model()
if not markov_model:
    logger.error(k.markov_model_not_found())
    memory = load_memory()
    markov_model = train_markov_model(memory)

generated_sentences: Set[str] = set()
used_words: Set[str] = set()


async def load_cogs_from_folder(bot: commands.Bot, folder_name="assets/cogs"):
    for filename in [file for file in os.listdir(folder_name) if file.endswith(".py")]:
        cog_name: str = filename[:-3]

        if (
            "internal" not in folder_name
            and cog_name not in settings["bot"]["enabled_cogs"]
        ):
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

    folder_name: str = "cogs"
    if launched:
        return

    await load_cogs_from_folder(bot, "assets/cogs/internal")
    await load_cogs_from_folder(bot)
    try:
        synced: List[discord.app_commands.AppCommand] = await bot.tree.sync()

        logger.info(f"{k.synced_commands()} {len(synced)} {k.synced_commands2()}")
        logger.info(k.started(settings["name"]))

    except discord.errors.Forbidden as perm_error:
        logger.error(f"Permission error while syncing commands: {perm_error}")
        logger.error(
            "Make sure the bot has the 'applications.commands' scope and is invited with the correct permissions."
        )
    except Exception as e:
        logger.error(f"{k.fail_commands_sync()} {e}")
        traceback.print_exc()

    if not settings["bot"]["misc"]["activity"]["content"]:
        return


    activities: Dict[ActivityType, discord.ActivityType] = {
        "listening": discord.ActivityType.listening,
        "playing": discord.ActivityType.playing,
        "streaming": discord.ActivityType.streaming,
        "competing": discord.ActivityType.competing,
        "watching": discord.ActivityType.watching,
    }

    await bot.change_presence(
        activity=discord.Activity(
            type=activities.get(
                settings["bot"]["misc"]["activity"]["type"],
                discord.ActivityType.unknown,
            ),
            name=settings["bot"]["misc"]["activity"]["content"],
        )
    )
    launched = True

    logger.info(f"Running as {bot.user}")


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

    output_path: Optional[str] = await gen_demotivator(input_path) # type: ignore

    if output_path is None or not os.path.isfile(output_path):
        if temp_input and os.path.exists(temp_input):
            os.remove(temp_input)
        await ctx.reply("Failed to generate demotivator.")
        return

    await ctx.send(file=discord.File(output_path))

    if temp_input and os.path.exists(temp_input):
        os.remove(temp_input)


# Event: Called on every message
@bot.event
async def on_message(message: discord.Message) -> None:
    global memory, markov_model, messages_recieved

    messages_recieved += 1
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

    if message.author.id in settings["bot"]["blacklisted_users"]:
        return

    await bot.process_commands(message)

    if not message.content:
        return

    if not settings["bot"]["user_training"]:
        return

    
    if (
        settings["bot"]["misc"]["block_profanity"] and 
        profanity.contains_profanity(message.content)
    ):
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

        if messages_recieved % 10 == 0:
            logger.info("Saving memory")
            save_memory(memory)

    if len(message.content.strip().split()) < 1:
        logger.info("Skipping positivty checks due to message being too short")
        return

    sentiment_score = is_positive(
        message.content
    )  # doesnt work but im scared to change the logic now please ignore
    if sentiment_score > 0.8:
        if not settings["bot"]["react_to_messages"]:
            return

        if not sync_connector.can_react(message.id):
            logger.info("Sync hub determined that this instance cannot react")
            return
        

        emoji = random.choice(EMOJIS)
        try:
            await message.add_reaction(emoji)
        except Exception as e:
            logger.info(f"Failed to react with emoji: {e}")


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


observer = Observer()
observer.schedule(Handler(), "assets/locales")
observer.start()

# Start the bot
if __name__ == "__main__":
    bot.run(os.environ.get("DISCORD_BOT_TOKEN", ""))
