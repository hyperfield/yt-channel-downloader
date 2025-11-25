from .logger import get_logger

logger = get_logger("JsRuntimeWarningTracker")


class JsRuntimeWarningTracker:
    """Tracks whether yt-dlp reported missing JavaScript runtime."""

    def __init__(self):
        self._seen = False

    def mark(self, msg):
        """Record that the JS runtime warning was seen if it appears in the message."""
        if isinstance(msg, str) and "No supported JavaScript runtime could be found" in msg:
            self._seen = True

    def pop_seen(self):
        """Return and reset the warning-seen flag."""
        seen = self._seen
        self._seen = False
        return seen


js_warning_tracker = JsRuntimeWarningTracker()
