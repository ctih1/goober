import json
import os
from typing import Dict, List, Literal, Mapping, Any, TypedDict
from modules.keys import Language
import logging
import copy

logger = logging.getLogger("goober")

ActivityType = Literal["listening", "playing", "streaming", "competing", "watching"]

class SyncHub(TypedDict):
    url: str
    enabled: bool

class Activity(TypedDict):
    content: str
    type: ActivityType


class MiscBotOptions(TypedDict):
    ping_line: str
    activity: Activity
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
    active_model: str
    sync_hub: SyncHub


class SettingsType(TypedDict):
    bot: BotSettings
    locale: Language
    name: str
    auto_update: bool
    disable_checks: bool
    splash_text_loc: str
    cog_settings: Dict[str, Mapping[Any, Any]]


class AdminLogEvent(TypedDict):
    messageId: int
    author: int
    target: str | int
    action: Literal["del", "add", "set"]
    change: Literal["owner_ids", "blacklisted_users", "enabled_cogs"]


class Settings:
    def __init__(self) -> None:
        global instance
        instance = self

        self.path: str = os.path.join(".", "settings", "settings.json")

        if not os.path.exists(self.path):
            logger.critical(
                f"Missing settings file from {self.path}! Did you forget to copy settings.example.json?"
            )
            raise ValueError("settings.json file does not exist!")

        self.settings: SettingsType
        self.original_settings: SettingsType

        with open(self.path, "r") as f:
            self.__kv_store: dict = json.load(f)

        self.settings = SettingsType(self.__kv_store)  # type: ignore
        self.original_settings = copy.deepcopy(self.settings)

        self.log_path: str = os.path.join(".", "settings", "admin_logs.json")

        self.migrate()

    def migrate(self):
        active_song: str | None = (
            self.settings.get("bot", {}).get("misc", {}).get("active_song")
        )

        if active_song:
            logger.warning("Found deprecated active_song, migrating")

            self.settings["bot"]["misc"]["activity"] = {
                "content": active_song,
                "type": "listening",
            }

            del self.settings["bot"]["misc"]["active_song"]  # type: ignore

        sync_hub: SyncHub | None = self.settings.get("bot", {}).get("sync_hub")

        if not sync_hub:
            logger.warning("Adding sync hub settings")
            self.settings["bot"]["sync_hub"] = {
                "enabled": True,
                "url": "ws://goober.frii.site"
            } 

        if not self.settings.get("bot", {}).get("active_model"):
            logger.warning("active_model missing! Replacing with backwards compatible one")
            self.settings["bot"]["active_model"] = "markov_model.pkl"

        self.commit()

    def reload_settings(self) -> None:
        with open(self.path, "r") as f:
            self.__kv_store: dict = json.load(f)

        self.settings = SettingsType(self.__kv_store)  # type: ignore
        self.original_settings = copy.deepcopy(self.settings)

    def commit(self) -> None:
        with open(self.path, "w") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=4)

        self.original_settings = self.settings

    def discard(self) -> None:
        self.settings = self.original_settings

    def get_plugin_settings(
        self, plugin_name: str, default: Mapping[Any, Any]
    ) -> Mapping[Any, Any]:
        return self.settings["cog_settings"].get(plugin_name, default)

    def set_plugin_setting(
        self, plugin_name: str, new_settings: Mapping[Any, Any]
    ) -> None:
        """Changes a plugin setting. Commits changes"""
        self.settings["cog_settings"][plugin_name] = new_settings

        self.commit()

    def add_admin_log_event(self, event: AdminLogEvent):
        if not os.path.exists(self.log_path):
            logger.warning("Admin log doesn't exist!")
            with open(self.log_path, "w") as f:
                json.dump([], f)

        with open(self.log_path, "r") as f:
            logs: List[AdminLogEvent] = json.load(f)

        logs.append(event)

        with open(self.log_path, "w") as f:
            json.dump(logs, f, ensure_ascii=False, indent=4)


instance: Settings = Settings()
