import discord
from discord.ext import commands
import os
import requests
import ast

def get_version_url(config_file_path):
    with open(config_file_path, "r") as file:
        file_content = file.read()
    tree = ast.parse(file_content)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "VERSION_URL":
                    if isinstance(node.value, ast.Str):
                        return node.value.s 
    return None
config_file_path = "config.py"
VERSION_URL = get_version_url(config_file_path)


class grabTemplate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def download_json():
        response = requests.get(f"{VERSION_URL}/goob/template.json")
        if response.status_code == 200:
            if os.path.exists("memory.json"):
                return
            else:
                userinput = input("Do you want to download the template json instead of starting from scratch?\n(Y/N)\n")
                if userinput.lower() == "y":
                    with open("memory.json", "w", encoding="utf-8") as file:
                        file.write(response.text)
                else:
                    print("Starting from scratch...")
        elif response.status_code == 404:
            print("File not found on goober central!!")
    download_json()
async def setup(bot):
    await bot.add_cog(grabTemplate(bot))
