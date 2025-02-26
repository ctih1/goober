import os 
from dotenv import load_dotenv
import platform
import random

def print_multicolored(text):
    print(text)

load_dotenv()
VERSION_URL = "https://goober.whatdidyouexpect.eu"
UPDATE_URL = VERSION_URL+"/latest_version.json"
LOCAL_VERSION_FILE = "current_version.txt" 
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PREFIX = os.getenv("BOT_PREFIX")
hourlyspeak = int(os.getenv("hourlyspeak"))
PING_LINE = os.getenv("PING_LINE")
random_talk_channel_id1 = int(os.getenv("rnd_talk_channel1"))
random_talk_channel_id2 = int(os.getenv("rnd_talk_channel2"))
cooldown_time = os.getenv("cooldown")
splashtext = os.getenv("splashtext")
ownerid = int(os.getenv("ownerid"))
showmemenabled = os.getenv("showmemenabled")
BLACKLISTED_USERS = os.getenv("BLACKLISTED_USERS", "").split(",")
USERTRAIN_ENABLED = os.getenv("USERTRAIN_ENABLED", "true").lower() == "true"
NAME = os.getenv("NAME")
last_random_talk_time = 0
MEMORY_FILE = "memory.json"
DEFAULT_DATASET_FILE = "defaultdataset.json"
MEMORY_LOADED_FILE = "MEMORY_LOADED"
ALIVEPING = os.getenv("ALIVEPING")
IGNOREWARNING = False
song = os.getenv("song")
arch = platform.machine()
RED = "\033[31mError: "
GREEN = "\033[32mSuccess: "
YELLOW = "\033[33mWarning: "
DEBUG = "\033[1;30mDebug: "
RESET = "\033[0m"
multicolorsplash = False


def apply_multicolor(text, chunk_size=3):
    if multicolorsplash == False:
        return
    colors = [
       "\033[38;5;196m",  # Red
       "\033[38;5;202m",  # Orange
       "\033[38;5;220m",  # Yellow
       "\033[38;5;46m",   # Green
        "\033[38;5;21m",   # Blue
        "\033[38;5;93m",   # Indigo
        "\033[38;5;201m",  # Violet
    ]
    
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    
    colored_text = ""
    for chunk in chunks:
        color = random.choice(colors)
        colored_text += f"{color}{chunk}\033[0m"
    
    return colored_text
splashtext = apply_multicolor(splashtext)

