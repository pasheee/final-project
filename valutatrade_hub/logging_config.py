import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOGGING_FILEPATH = Path.cwd() / "logs" / "actions.log"


def setup_logging(fmt: str, level: str = "INFO") -> None:
    """Configure file logging with rotation and the selected level"""
    LOGGING_FILEPATH.parent.mkdir(exist_ok=True)

    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%dT%H:%M:%S")
    file_handler = RotatingFileHandler(
        LOGGING_FILEPATH, maxBytes=int(1e6), backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.addHandler(file_handler)
    root.setLevel(level)
