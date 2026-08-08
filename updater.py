import logging
import subprocess
from dotenv import load_dotenv

logger = logging.getLogger("goober")


def force_update() -> str:
    logger.info("Forcefully updating...")
    stash = subprocess.run(["git", "stash"], capture_output=True)
    logger.info(stash)
    pull = subprocess.run(
        ["git", "pull", "origin", "main"], check=True, capture_output=True
    )

    load_dotenv()
    return pull.stdout.decode("utf-8")
