from typing import Optional

from .logger import get_logger
from .js_warning_tracker import js_warning_tracker, JsRuntimeWarningTracker


logger = get_logger("QuietYDLLogger")


class QuietYDLLogger:
    """Minimal yt-dlp-compatible logger that suppresses noisy output."""

    def __init__(self, warning_tracker: Optional[JsRuntimeWarningTracker] = None):
        self.warning_tracker = warning_tracker or js_warning_tracker

    def debug(self, msg):
        logger.debug(msg)

    def info(self, msg):
        logger.debug(msg)

    def warning(self, msg):
        self.warning_tracker.mark(msg)
        logger.warning(msg)

    def log_warning(self, msg):
        """Alias for warning to keep naming explicit in code that calls it directly."""
        self.warning(msg)

    def error(self, msg):
        logger.error(msg)
