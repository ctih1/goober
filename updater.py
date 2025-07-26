import subprocess
import time
import sys
import os

def force_update() -> None:
    print("Forcefully updating...")
    stash = subprocess.run(["git", "stash"], capture_output=True)
    print(stash)
    pull = subprocess.run(["git", "pull", "origin", "main"], check=True, capture_output=True)
    print(pull)

    print("Starting bot")
    os.execv(sys.executable, [sys.executable, "bot.py"])

force_update()