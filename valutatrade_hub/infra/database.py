import json
import threading
from pathlib import Path
from typing import Any


class DatabaseManager:
    """Single access point to JSON files"""

    __instance = None
    __lock = threading.Lock()

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def load(self, filepath: Path) -> Any:
        """Read data from a JSON file"""
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def initialize(self, filepath: Path, default: Any) -> None:
        """Initialize missing or blank data files at application startup."""
        if not filepath.exists() or not filepath.read_text(encoding="utf-8").strip():
            self.save(filepath, default)

    def save(self, filepath: Path, data: Any) -> None:
        """Write data to a JSON file through a temporary file"""
        tmp = filepath.with_suffix(".tmp")
        with self.__lock:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            tmp.replace(filepath)
