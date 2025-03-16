import os 
from dotenv import load_dotenv
import platform
import random

load_dotenv()
VERSION_URL = "https://goober.whatdidyouexpect.eu"
UPDATE_URL = VERSION_URL+"/latest_version.json"
LOCAL_VERSION_FILE = "current_version.txt" 
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PREFIX = os.getenv("BOT_PREFIX")
hourlyspeak = int(os.getenv("hourlyspeak"))
PING_LINE = os.getenv("PING_LINE")
random_talk_channel_id1 = int(os.getenv("rnd_talk_channel1"))
LOCALE = os.getenv("locale")
gooberTOKEN = os.getenv("gooberTOKEN")
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

