import json
import os
from typing import List, Mapping, Any, TypedDict
from modules.keys import Language
import logging 
import copy

logger = logging.getLogger("goober")

class MiscBotOptions(TypedDict):
    ping_line: str
    active_song: str
    positive_gifs: List[str]
    block_profanity: bool

class BotSettings(TypedDict):
    prefix: str
    owner_ids: List[int]
    blacklisted_users: List[int]
    user_training: bool
    allow_show_mem_command: bool
    react_to_messages: bool
    misc: MiscBotOptions
    enabled_cogs: List[str]
    active_memory: str

class SettingsType(TypedDict):
    bot: BotSettings
    locale: Language
    name: str
    auto_update: bool
    disable_checks: bool
    splash_text_loc: str

class Settings:
    def __init__(self) -> None:
        self.path: str = os.path.join(".", "settings", "settings.json")

        if not os.path.exists(self.path):
            raise ValueError("settings.json file does not exist!")
        
        self.settings: SettingsType
        self.original_settings: SettingsType
        
        with open(self.path, "r") as f:
            self.__kv_store: dict = json.load(f)
        
        self.settings = SettingsType(self.__kv_store) # type: ignore
        self.original_settings = copy.deepcopy(self.settings)

    def commit(self) -> None:
        with open(self.path, "w") as f:
            json.dump(self.settings, f, indent=4)

        self.original_settings = self.settings
    
    def discard(self) -> None:
        self.settings = self.original_settings