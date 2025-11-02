import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from .settings_manager import SettingsManager


_BASE_LOGGER_NAME = "yt_channel_downloader"
_configured = False


def _configure_logging(level: int = logging.INFO) -> logging.Logger:
    global _configured
    root_logger = logging.getLogger(_BASE_LOGGER_NAME)
    if _configured:
        return root_logger

    config_dir = Path(SettingsManager().get_config_directory())
    log_dir = config_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "application.log"

    root_logger.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    root_logger.propagate = False
    root_logger.debug("Logging configured. Log file: %s", log_path)
    _configured = True
    return root_logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Return a configured logger scoped under the application namespace.

    Args:
        name (Optional[str]): Optional suffix for the logger (e.g. module name).

    Returns:
        logging.Logger: Configured logger instance.
    """
    root_logger = _configure_logging()
    if not name:
        return root_logger
    full_name = f"{_BASE_LOGGER_NAME}.{name}"
    return logging.getLogger(full_name)
