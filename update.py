import requests
import os
import argparse

# config
DEFAULT_VERSION_URL = "https://goober.whatdidyouexpect.eu/latest_version.json"
LOCAL_VERSION_FILE = "current_version.txt"
SCRIPT_FILE = "bot.py"
CONFIG_FILE = "config.py"

def get_latest_version_info(version_url):
    """Fetch the latest version information from the server."""
    try:
        response = requests.get(version_url, timeout=5)
        response.raise_for_status()  # Will raise HTTPError for bad responses
        return response.json()
    except requests.RequestException as e:
        print(f"Error: Unable to connect to the update server. {e}")
        return None

def get_local_version():
    """Read the current version from the local file."""
    if os.path.exists(LOCAL_VERSION_FILE):
        with open(LOCAL_VERSION_FILE, "r") as f:
            return f.read().strip()
    return "0.0.0"  # Default version if file doesn't exist

def save_local_version(version):
    """Save the current version to the local file."""
    with open(LOCAL_VERSION_FILE, "w") as f:
        f.write(version)

def download_file(url, destination):
    """Download a file from the given URL and save it to the destination."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Will raise HTTPError for bad responses
        with open(destination, "wb") as f:
            f.write(response.content)
        print(f"Successfully downloaded the file to {destination}.")
    except requests.RequestException as e:
        print(f"Error: Failed to download the file from {url}. {e}")

def check_for_update(version_url):
    """Check if a new version is available and update the script if needed."""
    latest_version_info = get_latest_version_info(version_url)
    if not latest_version_info:
        print("Could not fetch update information.")
        return
    latest_version = latest_version_info.get("version")
    download_url = latest_version_info.get("download_url")
    config_url = latest_version_info.get("config_url")
    if not latest_version or not download_url:
        print("Error: Invalid version information received from server.")
        return
    local_version = get_local_version()
    if local_version != latest_version:
        print(f"New version available: {latest_version} (Current: {local_version})")
        print("Downloading the new version...")
        download_file(download_url, SCRIPT_FILE)
        download_file(config_url, CONFIG_FILE)
        save_local_version(latest_version)
        print("Update complete! Restart the bot to use the new version.")
    else:
        print(f"You're using the latest version: {local_version}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check for updates and download the latest version of the bot.")
    parser.add_argument("--host", type=str, help="Custom version URL", default=DEFAULT_VERSION_URL)

    args = parser.parse_args()
    check_for_update(args.host)