"""utils/logger.py — Consistent logging across the pipeline."""
import logging
import sys
from pathlib import Path
from datetime import datetime

_LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
_LOG_DIR.mkdir(exist_ok=True)

_LOG_FILE = _LOG_DIR / f"pipeline_{datetime.utcnow().strftime('%Y-%m-%d')}.log"

_fmt = logging.Formatter(
    "[%(asctime)s] %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

_file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
_file_handler.setFormatter(_fmt)

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(_fmt)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(_console_handler)
        logger.addHandler(_file_handler)
        logger.setLevel(logging.INFO)
    return logger
