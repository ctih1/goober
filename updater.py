import subprocess
import time
import sys
import os
import logging


logger = logging.getLogger("goober")

def force_update() -> None:
    logger.info("Forcefully updating...")
    stash = subprocess.run(["git", "stash"], capture_output=True)
    logger.info(stash)
    pull = subprocess.run(["git", "pull", "origin", "main"], check=True, capture_output=True)
    logger.info(pull)


force_update()