import json
from pathlib import Path
from typing import Any

from .exceptions import ConfigError


class SettingsLoader:
    """Single loader of settings from config.json"""

    __config = None

    def __new__(cls, *args, **kwargs):
        if cls.__config is None:
            cls.__config = super().__new__(cls)
        return cls.__config

    def __init__(self, filepath: str | Path):
        if hasattr(self, "filepath"):
            return
        self.filepath = filepath
        self.config = None

    def load(self) -> None:
        """Read the settings from the config file"""
        with open(self.filepath, "r") as f:
            self.config = json.load(f)

    def get(self, key: str, default: Any = ...) -> Any:
        """Return the setting by key, or the default if given"""
        if self.config is None or len(self.config) == 0:
            raise ConfigError("Config is empty. Load config first.")

        if (key not in self.config) and (default is ...):
            raise ConfigError(f"{key!r} not in config keys")

        return self.config.get(key, default)
