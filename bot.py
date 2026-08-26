import difflib
import logging
import tracemalloc

from modules import key_compiler
from modules.logger import GooberFormatter

try:
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), 0x0004)
except Exception:  # noqa: S110
    pass

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

import logging
import os
import random
import shutil
import sys
import tempfile
import time
import traceback
from typing import Dict, List, Literal, Set, TypedDict

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import modules.keys as k
from modules.prestartchecks import start_checks
from modules.settings import ActivityType
from modules.settings import instance as settings_manager
from modules.sync_connector import instance as sync_connector

messages_recieved = 0


settings = settings_manager.settings
k.change_language(settings["locale"])

splash_text: str = ""

with open(settings["splash_text_loc"], "r", encoding="UTF-8") as f:
    splash_text = "".join(f.readlines())
    print(splash_text)

start_checks()

import discord
from better_profanity import profanity
from discord.ext import commands

from modules.image import gen_demotivator
from modules.markovmemory import *
from modules.sentenceprocessing import *
from modules.unhandledexception import handle_exception, handle_exception_with_context

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

positive_gifs: List[str] = settings["bot"]["misc"]["positive_gifs"]
currenthash: str = ""
launched: bool = False
slash_commands_enabled: bool = False

intents: discord.Intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.presences = True
intents.members = True

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
cog_load_times: Dict[str, float] = {}


async def load_cogs_from_folder(bot: commands.Bot, folder_name="assets/cogs"):
    for filename in [file for file in os.listdir(folder_name) if file.endswith(".py")]:
        cog_name: str = filename[:-3]

        if "internal" not in folder_name and cog_name not in settings["bot"]["enabled_cogs"]:
            logger.debug(f"Skipping cog {cog_name} (not in enabled cogs)")
            continue

        module_path = folder_name.replace("/", ".").replace("\\", ".") + f".{cog_name}"

        try:
            start = time.time()
            await bot.load_extension(module_path)
            logger.info(f"Loaded cog {cog_name} in {time.time() - start:.3f}s")

            cog_load_times[cog_name] = time.time() - start
        except Exception as e:
            logger.error(f"{k.cog_fail()} {cog_name} {e}")
            traceback.print_exc()

    strang = ""
    for name, _time in sorted(cog_load_times.items(), key=lambda i: i[1], reverse=True):
        strang += f"{name}: {_time:.4f}s\n"

    os.environ["BOT_LAUNCH_DEBUG_SHIT"] = strang


# Event: Called when the bot is ready
@bot.event
async def on_ready() -> None:
    global launched

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
    logger.info(type(error))
    if isinstance(error, commands.errors.CommandNotFound):
        target = (
            ctx.message.content.removeprefix(settings["bot"]["prefix"]).split(" ")[0]
            if not ctx.command
            else ctx.command.qualified_name
        )
        proper_command = difflib.get_close_matches(
            word=(target),
            possibilities=[cmd.qualified_name for cmd in bot.commands],
            n=1,
            cutoff=0.9 if (len(target) > 8 or "_" in target) else 0.8,
        )
        if proper_command and proper_command[0].strip() != target.strip():
            logger.info(f"Fixed command {target} -> {proper_command[0]}")
            message = ctx.message
            message.content = message.content.replace(target, proper_command[0], 1)
            await command_handler(message)
            return

        embed = discord.Embed(color=0xFC1C03)
        embed.title = "Command not found"
        embed.description = f"{error}"

        await send_message(ctx, embed=embed)
        return

    if isinstance(error, commands.CommandInvokeError):
        original: Exception = error.original
        await handle_exception_with_context(
            ctx,
            type(original),
            original,
            original.__traceback__,
            context=f"Command: {ctx.command} | User: {ctx.author}",
        )
    else:
        await handle_exception_with_context(
            ctx,
            type(error),
            error,
            error.__traceback__,
            context=f"Command: {ctx.command} | User: {ctx.author}",
        )


@bot.event
async def on_message(message: discord.Message) -> None:
    global messages_recieved

    logger.debug(f"{message}\n")

    messages_recieved += 1

    if message.author.bot:
        return

    if message.author.id in settings["bot"]["blacklisted_users"]:
        return

    await bot.process_commands(message)

    if not message.content:
        return

    if not settings["bot"]["user_training"]:
        return

    if settings["bot"]["misc"]["block_profanity"] and profanity.contains_profanity(
        message.content
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
            await save_memory(memory)


@bot.event
async def on_interaction(interaction: discord.Interaction) -> None:
    logger.info(f"{k.command_ran_s(interaction.user.name)} {interaction.user.name}")


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
    except Exception as e:
        logger.warning(e)
        return False

    return True


async def command_handler(message: discord.Message) -> None:
    reloading = False

    if message.content.endswith("#r"):
        reloading = True
        message.content = message.content[:-2]

    ctx = await bot.get_context(message)

    if ctx.command:
        logger.info(f"{message.author} ran {ctx.command.name}")
        if reloading:
            logger.debug("Reloading first...")
            reload_command = bot.get_command("reload")
            assert reload_command

            await reload_command(ctx, cog_name=ctx.command.name, force="yes")

    await bot.invoke(ctx)


bot.on_message = command_handler


def improve_sentence_coherence(sentence: str) -> str:
    sentence = sentence.replace(" i ", " I ")
    return sentence


if __name__ == "__main__":
    bot.run(os.environ.get("DISCORD_BOT_TOKEN", ""))
