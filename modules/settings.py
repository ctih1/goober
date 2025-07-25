import json
import os
from typing import Dict, List, Literal, Mapping, Any, NotRequired, TypedDict
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
            raise ValueError("settings.json file does not exist!")

        self.settings: SettingsType
        self.original_settings: SettingsType

        with open(self.path, "r") as f:
            self.__kv_store: dict = json.load(f)

        self.settings = SettingsType(self.__kv_store)  # type: ignore
        self.original_settings = copy.deepcopy(self.settings)

        self.log_path: str = os.path.join(".", "settings", "admin_logs.json")

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
