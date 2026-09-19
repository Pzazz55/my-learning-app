"""Application-wide logging configuration.

Every module obtains a logger through :func:`get_logger`. The first call
configures a single root handler that writes rotating log files to the
``logs/`` directory and also mirrors records to the console, so the same
messages appear in the terminal/Streamlit output and in ``logs/app.log``.

Usage
-----
    from backend.services.logging_config import get_logger

    logger = get_logger(__name__)
    logger.info("Something happened")
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ``backend/services/logging_config.py`` -> project root is two levels up.
BASE_DIR = Path(__file__).resolve().parents[2]
LOGS_DIR = BASE_DIR / "logs"
LOG_FILE = LOGS_DIR / "app.log"

_CONFIGURED = False
_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(level: int = logging.INFO) -> None:
    """Configure the root logger once per process.

    Safe to call repeatedly: subsequent calls are no-ops after the first
    successful configuration. Failures (for example a read-only filesystem)
    never raise - logging simply falls back to the console handler.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Console handler - keeps messages visible in the Streamlit terminal.
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        root.addHandler(console)

    # Rotating file handler - writes to logs/app.log (5 MB x 3 backups).
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError:
        # If the log directory cannot be created we still log to the console.
        pass

    _CONFIGURED = True


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a logger, configuring logging on first use."""
    configure_logging()
    return logging.getLogger(name or "study_sprint")
