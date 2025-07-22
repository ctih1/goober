import requests
import subprocess
import sys
import logging
import json
import time
import random
import modules.keys as k
from modules.globalvars import *
from modules.settings import Settings as SettingsManager

settings_manager = SettingsManager()
settings = settings_manager.settings

logger = logging.getLogger("goober")
launched = False

# Run a shell command and return its output
def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

# Check if the remote branch is ahead of the local branch
def is_remote_ahead(branch='main', remote='origin'):
    run_cmd(f'git fetch {remote}')
    count = run_cmd(f'git rev-list --count HEAD..{remote}/{branch}')
    return int(count) > 0

# Automatically update the local repository if the remote is ahead
def auto_update(branch='main', remote='origin'):
    if launched == True:
        print(k.already_started())
        return
    if settings["auto_update"] != "True":
        pass  # Auto-update is disabled
    if is_remote_ahead(branch, remote):
        logger.info(k.remote_ahead(remote, branch))
        pull_result = run_cmd(f'git pull {remote} {branch}')
        logger.info(pull_result)
        logger.info(k.please_restart())
        sys.exit(0)
    else:
        logger.info(k.local_ahead(remote, branch))

def get_latest_version_info():
    try:
        unique_suffix = f"{int(time.time())}_{random.randint(0, 9999)}"
        url = f"{UPDATE_URL}?_={unique_suffix}"
        
        curl_cmd = [
            "curl",
            "-s",
            "-H", "Cache-Control: no-cache",
            "-H", "Pragma: no-cache",
            url
        ]

        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=5)
        content = result.stdout
        
        if result.returncode != 0:
            logger.error(f"curl failed with return code {result.returncode}")
            return None

        try:
            data = json.loads(content)
            return data
        except json.JSONDecodeError:
            logger.error("JSON decode failed")
            logger.error(content[:500])
            return None

    except Exception as e:
        logger.error(f"Exception in get_latest_version_info: {e}")
        return None

# Check if an update is available and perform update if needed
def check_for_update(): 
    global latest_version, local_version, launched

    latest_version_info = get_latest_version_info()
    if not latest_version_info:
        logger.error(f"{k.fetch_update_fail()}")
        return None

    latest_version = latest_version_info.get("version")
    os.environ['gooberlatest_version'] = latest_version
    download_url = latest_version_info.get("download_url")

    if not latest_version or not download_url:
        logger.error(k.invalid_server())
        return None
    
    # Check if local_version is valid
    if local_version == "0.0.0" or None:
        logger.error(k.cant_find_local_version())
        return
    # Compare local and latest versions

    if local_version < latest_version:
        logger.warning(k.new_version(latest_version=latest_version, local_version=local_version))
        logger.warning(k.changelog(VERSION_URL=VERSION_URL))
        auto_update()

    elif beta == True:
        logger.warning(f"You are running an \"unstable\" version of Goober, do not expect it to work properly.\nVersion {local_version}\nServer: {latest_version}{RESET}")
    elif local_version > latest_version:
        logger.warning(f"{k.modification_warning()}")
    elif local_version == latest_version:
        logger.info(f"{k.latest_version()} {local_version}")
        logger.info(f"{k.latest_version2(VERSION_URL=VERSION_URL)}\n\n")
    launched = True
    return latest_version