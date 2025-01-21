import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import markovify
import nltk
from nltk.tokenize import word_tokenize
import random
import os
import time
import re
import os
import requests
import platform
import subprocess
import psutil
import pickle
from better_profanity import profanity
from config import *
print(splashtext) # you can use https://patorjk.com/software/taag/ for 3d text or just remove this entirely
def save_markov_model(model, filename='markov_model.pkl'):
    with open(filename, 'wb') as f:
        pickle.dump(model, f)
    print(f"Markov model saved to {filename}.")

def load_markov_model(filename='markov_model.pkl'):

    try:
        with open(filename, 'rb') as f:
            model = pickle.load(f)
        print(f"Markov model loaded from {filename}.")
        return model
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
        return None

def get_latest_version_info():

    try:

        response = requests.get(UPDATE_URL, timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: Unable to fetch version info. Status code {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"Error: Unable to connect to the update server. {e}")
        return None
async def load_cogs_from_folder(bot, folder_name="cogs"):
    for filename in os.listdir(folder_name):
        if filename.endswith(".py") and not filename.startswith("_"):
            cog_name = filename[:-3]
            try:
                await bot.load_extension(f"{folder_name}.{cog_name}")
                print(f"Loaded cog: {cog_name}")
            except Exception as e:
                print(f"Failed to load cog {cog_name}: {e}")

def get_local_version():
    """Read the current version from the local file."""
    if os.path.exists(LOCAL_VERSION_FILE):
        with open(LOCAL_VERSION_FILE, "r") as f:
            return f.read().strip()
    return "0.0.0"

latest_version = "0.0.0"
local_version = "0.0.0"

def check_for_update():
    if ALIVEPING == "false":
        return
    global latest_version, local_version 
    
    latest_version_info = get_latest_version_info()
    if not latest_version_info:
        print("Could not fetch update information.")
        return None, None 

    latest_version = latest_version_info.get("version")
    download_url = latest_version_info.get("download_url")

    if not latest_version or not download_url:
        print("Error: Invalid version information received from server.")
        return None, None 

    local_version = get_local_version() 
    if local_version != latest_version:
        print(f"New version available: {latest_version} (Current: {local_version})")
        print(f"Check {VERSION_URL}/goob/changes.txt to check out the changelog for version {latest_version}\n\n")
    else:
        print(f"You're using the latest version: {local_version}")
        print(f"Check {VERSION_URL}/goob/changes.txt to check out the changelog for version {latest_version}\n\n")


check_for_update()

def get_allocated_ram():
    system = platform.system()
    try:
        if system == "Linux":
            with open("/proc/meminfo", "r") as meminfo:
                lines = meminfo.readlines()
                total_memory = int(next(line for line in lines if "MemTotal" in line).split()[1])
                free_memory = int(next(line for line in lines if "MemFree" in line).split()[1])
                return {
                    "total_memory_kb": total_memory,
                    "free_memory_kb": free_memory,
                    "used_memory_kb": total_memory - free_memory,
                }

        elif system == "FreeBSD" or "BSD" in system:
            total_memory = int(subprocess.check_output(["sysctl", "-n", "hw.physmem"]).strip()) // 1024
            free_memory = int(subprocess.check_output(["sysctl", "-n", "vm.stats.vm.v_free_count"]).strip()) * int(subprocess.check_output(["sysctl", "-n", "hw.pagesize"]).strip()) // 1024
            return {
                "total_memory_kb": total_memory,
                "free_memory_kb": free_memory,
                "used_memory_kb": total_memory - free_memory,
            }

        elif system == "Windows":
            total_memory = psutil.virtual_memory().total // 1024
            free_memory = psutil.virtual_memory().available // 1024
            return {
                "total_memory_kb": total_memory,
                "free_memory_kb": free_memory,
                "used_memory_kb": total_memory - free_memory,
            }

        else:
            return {"error": f"Unsupported OS: {system}"}

    except Exception as e:
        return {"error": str(e)}

def get_cpu_info():
    system = platform.system()
    try:
        if system == "Linux":
            with open("/proc/cpuinfo", "r") as cpuinfo:
                lines = cpuinfo.readlines()
                cpu_info = []
                cpu_details = {}
                for line in lines:
                    if line.strip():
                        key, value = map(str.strip, line.split(":", 1))
                        cpu_details[key] = value
                    else:
                        if cpu_details:
                            cpu_info.append(cpu_details)
                            cpu_details = {}
                if cpu_details:
                    cpu_info.append(cpu_details)
                return cpu_info

        elif system == "FreeBSD" or "BSD" in system:
            cpu_count = int(subprocess.check_output(["sysctl", "-n", "hw.ncpu"]).strip())
            cpu_model = subprocess.check_output(["sysctl", "-n", "hw.model"]).strip().decode()
            return {"cpu_count": cpu_count, "cpu_model": cpu_model}

        elif system == "Windows":
            cpu_info = []
            for cpu in range(psutil.cpu_count(logical=False)):
                cpu_info.append({
                    "cpu_index": cpu,
                    "cpu_model": platform.processor(),
                    "logical_cores": psutil.cpu_count(logical=True),
                })
            return cpu_info

        else:
            return {"error": f"Unsupported OS: {system}"}

    except Exception as e:
        return {"error": str(e)}


def get_file_info(file_path):
    try:
        file_size = os.path.getsize(file_path)
        with open(file_path, "r") as f:
            lines = f.readlines()
        return {"file_size_bytes": file_size, "line_count": len(lines)}
    except Exception as e:
        return {"error": str(e)}


nltk.download('punkt')




def load_memory():
    data = []

    # load data from MEMORY_FILE
    try:
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        pass

    if not os.path.exists(MEMORY_LOADED_FILE):
        try:
            with open(DEFAULT_DATASET_FILE, "r") as f:
                default_data = json.load(f)
                data.extend(default_data) 
        except FileNotFoundError:
            pass
        with open(MEMORY_LOADED_FILE, "w") as f:
            f.write("Data loaded") 
    return data

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=4)

def train_markov_model(memory, additional_data=None):
    if not memory:
        return None
    text = "\n".join(memory)
    if additional_data:
        text += "\n" + "\n".join(additional_data)
    model = markovify.NewlineText(text, state_size=2)
    return model
#this doesnt work and im extremely pissed and mad
def append_mentions_to_18digit_integer(message):
    pattern = r'\b\d{18}\b'
    return re.sub(pattern, lambda match: f"<@{match.group(0)}>", message)

def preprocess_message(message):
    message = append_mentions_to_18digit_integer(message)
    tokens = word_tokenize(message)
    tokens = [token for token in tokens if token.isalnum()]
    return " ".join(tokens)


intents = discord.Intents.default()

intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)
memory = load_memory() 
markov_model = load_markov_model()
if not markov_model:
    print("No saved Markov model found. Starting from scratch.")
    memory = load_memory()
    markov_model = train_markov_model(memory)

generated_sentences = set()
used_words = set()

slash_commands_enabled = False
@bot.event
async def on_ready():
    folder_name = "cogs"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"Folder '{folder_name}' created.")
    else:
        print(f"Folder '{folder_name}' already exists. skipping...")
    markov_model = train_markov_model(memory)
    await load_cogs_from_folder(bot)
    global slash_commands_enabled
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
        slash_commands_enabled = True
        ping_server()
    except Exception as e:
        print(f"Failed to sync commands: {e}")
        quit
    post_message.start()
    if not song:
        return  
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f"{song}"))

def ping_server():
    if ALIVEPING == "false":
        print("Pinging is disabled! Not telling the server im on...")
        return
    allocated_ram = get_allocated_ram()
    cpuinfo = get_cpu_info()
    file_info = get_file_info(MEMORY_FILE)
    payload = {
        "name": NAME,
        "allocated_ram": allocated_ram,
        "cpuinfo": cpuinfo,
        "memory_file_info": file_info,
        "version": local_version,
        "slash_commands": slash_commands_enabled
    }
    try:
        response = requests.post(VERSION_URL+"/ping", json=payload)
        if response.status_code == 200:
            print("Sent alive ping to goober central!")
        else:
            print(f"Failed to send data. Server returned status code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred while sending data: {str(e)}")

positive_keywords = ["happy", "good", "great", "amazing", "awesome", "joy", "love", "fantastic", "positive", "cheerful", "victory", "favorite", "lmao", "lol", "xd", "XD", "xD", "Xd"]

positive_gifs = os.getenv("POSITIVE_GIFS").split(',')

def is_positive(sentence):
    sentence_lower = sentence.lower()
    return any(keyword in sentence_lower for keyword in positive_keywords)

async def send_message(ctx, message=None, embed=None, file=None, edit=False, message_reference=None):
    if edit and message_reference:
        try:
            # Editing the existing message
            await message_reference.edit(content=message, embed=embed)
        except Exception as e:
            await ctx.send(f"Failed to edit message: {e}")
    else:
        if hasattr(ctx, "respond"):
            # For slash command contexts
            sent_message = None
            if embed:
                sent_message = await ctx.respond(embed=embed, ephemeral=False)
            elif message:
                sent_message = await ctx.respond(message, ephemeral=False)
            if file:
                sent_message = await ctx.respond(file=file, ephemeral=False)
        else:

            sent_message = None
            if embed:
                sent_message = await ctx.send(embed=embed)
            elif message:
                sent_message = await ctx.send(message)
            if file:
                sent_message = await ctx.send(file=file)
        return sent_message




@bot.hybrid_command(description="Retrains the Markov model manually.")
async def retrain(ctx):
    if ctx.author.id != ownerid:
        return

    message_ref = await send_message(ctx, "Retraining the Markov model... Please wait.")
    try:
        with open(MEMORY_FILE, 'r') as f:
            memory = json.load(f)
    except FileNotFoundError:
        await send_message(ctx, "Error: memory file not found!")
        return
    except json.JSONDecodeError:
        await send_message(ctx, "Error: memory file is corrupted!")
        return
    data_size = len(memory)
    processed_data = 0
    processing_message_ref = await send_message(ctx, f"Processing {processed_data}/{data_size} data points...")
    start_time = time.time()
    for i, data in enumerate(memory):
        processed_data += 1
        if processed_data % 1000 == 0 or processed_data == data_size:
            await send_message(ctx, f"Processing {processed_data}/{data_size} data points...", edit=True, message_reference=processing_message_ref)

    global markov_model
    
    markov_model = train_markov_model(memory)
    save_markov_model(markov_model)

    await send_message(ctx, f"Markov model retrained successfully using {data_size} data points!", edit=True, message_reference=processing_message_ref)

@bot.hybrid_command(description="talks n like stuf")
async def talk(ctx):
    if not markov_model:
        await send_message(ctx, "I need to learn more from messages before I can talk.")
        return

    response = None
    for _ in range(20):  # Try to generate a coherent sentence
        response = markov_model.make_sentence(tries=100)
        if response and response not in generated_sentences:
            # Preprocess the sentence for grammar improvements
            response = improve_sentence_coherence(response)
            generated_sentences.add(response)
            break

    if response:
        cleaned_response = re.sub(r'[^\w\s]', '', response).lower()
        coherent_response = rephrase_for_coherence(cleaned_response)
        if random.random() < 0.9 and is_positive(coherent_response):
            gif_url = random.choice(positive_gifs)
            combined_message = f"{coherent_response}\n[jif]({gif_url})"
        else:
            combined_message = coherent_response
        await send_message(ctx, combined_message)
    else:
        await send_message(ctx, "I have nothing to say right now!")

@bot.hybrid_command(description="asks n like shit")
async def ask(ctx, *, argument: str):
    if markov_model:
        response = None
        for _ in range(20):
            try:
                response = markov_model.make_sentence_with_start(argument, tries=100)
                if response and response not in generated_sentences:
                    response = improve_sentence_coherence(response)
                    generated_sentences.add(response)
                    break
            except KeyError as e:
                continue  
            except markovify.text.ParamError as e:
                continue 
        if response:
                cleaned_response = re.sub(r'[^\w\s]', '', response)
                cleaned_response = cleaned_response.lower()
                coherent_response = rephrase_for_coherence(cleaned_response)
                if random.random() < 0.9:
                    if is_positive(coherent_response):
                        gif_url = random.choice(positive_gifs)
                        combined_message = f"{coherent_response}\n[jif]({gif_url})"
                        await send_message(ctx, combined_message)
                    else:
                        await send_message(ctx, coherent_response)
                else:
                    await send_message(ctx, coherent_response)
        else:
            await send_message(ctx, "I couldn't come up with something relevant to that!")
    else:
        await send_message(ctx, "I need to learn more from messages before I can talk.")

def improve_sentence_coherence(sentence):

    sentence = sentence.replace(" i ", " I ")  
    return sentence

def rephrase_for_coherence(sentence):

    words = sentence.split()

    coherent_sentence = " ".join(words)
    return coherent_sentence

bot.help_command = None


@bot.hybrid_command(description="help")
async def help(ctx):
    embed = discord.Embed(
        title="Bot Help",
        description="List of commands grouped by category.",
        color=discord.Color.blue()
    )

    command_categories = {
        "General": ["mem", "talk", "ask", "about", "ping"],
        "Administration": ["stats", "retrain"]
    }

    custom_commands = []
    for cog_name, cog in bot.cogs.items():
        for command in cog.get_commands():
            if command.name not in command_categories["General"] and command.name not in command_categories["Administration"]:
                custom_commands.append(command.name)

    if custom_commands:
        embed.add_field(name="Custom Commands", value="\n".join([f"{PREFIX}{command}" for command in custom_commands]), inline=False)

    for category, commands_list in command_categories.items():
        commands_in_category = "\n".join([f"{PREFIX}{command}" for command in commands_list])
        embed.add_field(name=category, value=commands_in_category, inline=False)

    await send_message(ctx, embed=embed)




@bot.event
async def on_message(message):
    global memory, markov_model, last_random_talk_time

    if message.author.bot:
        return

    if str(message.author.id) in BLACKLISTED_USERS:
        return

    random_talk_channels = [random_talk_channel_id2, random_talk_channel_id1] 
    cooldowns = {
        random_talk_channel_id2: 1, 
    }
    default_cooldown = 10800

    if message.content.startswith((f"{PREFIX}talk", f"{PREFIX}mem", f"{PREFIX}help", f"{PREFIX}stats", f"{PREFIX}")):
        await bot.process_commands(message)
        return

    if profanity.contains_profanity(message.content):
        return

    if message.content:
        if not USERTRAIN_ENABLED:
            return
        formatted_message = append_mentions_to_18digit_integer(message.content)
        cleaned_message = preprocess_message(formatted_message)
        if cleaned_message:
            memory.append(cleaned_message)
            save_memory(memory)


    cooldown_time = cooldowns.get(message.channel.id, default_cooldown)
    if message.reference and message.reference.message_id:
        replied_message = await message.channel.fetch_message(message.reference.message_id)
        if replied_message.author == bot.user:  
            print("Bot is replying to a message directed at it!")
            response = None
            for _ in range(10):  
                response = markov_model.make_sentence(tries=100)
                if response and response not in generated_sentences:
                    response = improve_sentence_coherence(response)
                    generated_sentences.add(response)
                    break
            if response:
                await message.channel.send(response)
            return 

    # random chance for bot to talk
    random_chance = random.randint(0, 20)

    # talk randomly only in the specified channels
    if message.channel.id in random_talk_channels and random_chance >= 10:
        current_time = time.time()
        print(f"Random chance: {random_chance}, Time passed: {current_time - last_random_talk_time}")

        if current_time - last_random_talk_time >= cooldown_time:
            print("Bot is talking randomly!")
            last_random_talk_time = current_time

            response = None
            for _ in range(10): 
                response = markov_model.make_sentence(tries=100)
                if response and response not in generated_sentences:
                    response = improve_sentence_coherence(response)
                    generated_sentences.add(response)
                    break

            if response:
                await message.channel.send(response)

    # process any commands in the message
    await bot.process_commands(message)

@bot.hybrid_command(description="ping")
async def ping(ctx):
    await ctx.defer()
    latency = round(bot.latency * 1000)

    LOLembed = discord.Embed(
        title="Pong!!",
        description=(
            f"{PING_LINE}\n"
            f"`Bot Latency: {latency}ms`\n"
        ),
        color=discord.Color.blue()
    )
    LOLembed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar.url)

    await ctx.send(embed=LOLembed)

@bot.hybrid_command(description="about bot")
async def about(ctx):
    print("-------UPDATING VERSION INFO-------\n\n")
    try:
        check_for_update()
    except Exception as e:
        pass
    print("-----------------------------------")
    embed = discord.Embed(title="About me", description="", color=discord.Color.blue())
    embed.add_field(name="Name", value=f"{NAME}", inline=False)
    embed.add_field(name="Version", value=f"Local: {local_version} \nLatest: {latest_version}", inline=False)

    await send_message(ctx, embed=embed)


@bot.hybrid_command(description="stats")
async def stats(ctx):
    if ctx.author.id != ownerid: 
        return
    print("-------UPDATING VERSION INFO-------\n\n")
    try:
        check_for_update()
    except Exception as e:
        pass
    print("-----------------------------------")
    memory_file = 'memory.json'
    file_size = os.path.getsize(memory_file)
    
    with open(memory_file, 'r') as file:
        line_count = sum(1 for _ in file)
    
    embed = discord.Embed(title="Bot Stats", description="Data about the the bot's memory.", color=discord.Color.blue())
    embed.add_field(name="File Stats", value=f"Size: {file_size} bytes\nLines: {line_count}", inline=False)
    embed.add_field(name="Version", value=f"Local: {local_version} \nLatest: {latest_version}", inline=False)
    embed.add_field(name="Variable Info", value=f"Name: {NAME} \nPrefix: {PREFIX} \nOwner ID: {ownerid} \nCooldown: {cooldown_time} \nPing line: {PING_LINE} \nMemory Sharing Enabled: {showmemenabled} \nUser Training Enabled: {USERTRAIN_ENABLED} \nLast Random TT: {last_random_talk_time} \nSong: {song} \nSplashtext: ```{splashtext}```", inline=False)
 
    await send_message(ctx, embed=embed)



@bot.hybrid_command()
async def mem(ctx):
    if showmemenabled != "true":
        return
    memory = load_memory()
    memory_text = json.dumps(memory, indent=4)
    
    if len(memory_text) > 1024:
        with open(MEMORY_FILE, "r") as f:
            await send_message(ctx, file=discord.File(f, MEMORY_FILE))
    else:
        embed = discord.Embed(title="Memory Contents", description="The bot's memory.", color=discord.Color.blue())
        embed.add_field(name="Memory Data", value=f"```json\n{memory_text}\n```", inline=False)
        await send_message(ctx, embed=embed)


def improve_sentence_coherence(sentence):
    sentence = sentence.replace(" i ", " I ")
    return sentence

@tasks.loop(minutes=60)
async def post_message():
    channel_id = hourlyspeak
    channel = bot.get_channel(channel_id)
    if channel and markov_model:
        response = None
        for _ in range(20): 
            response = markov_model.make_sentence(tries=100)
            if response and response not in generated_sentences:
                generated_sentences.add(response)
                break

        if response:
            await channel.send(response)

bot.run(TOKEN)
