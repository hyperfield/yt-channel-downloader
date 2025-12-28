# Author: hyperfield
# Project: YT Channel Downloader
# Description: Helper to prompt users for support after download milestones.

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QMessageBox

from .logger import get_logger
from ..config.constants import SUPPORT_URL


logger = get_logger("SupportPrompt")

# Default download-count thresholds for when to re-prompt.
DEFAULT_SUPPORT_PROMPT_SHORT_SNOOZE = 25
DEFAULT_SUPPORT_PROMPT_MEDIUM_SNOOZE = 50
DEFAULT_SUPPORT_PROMPT_LONG_SNOOZE = 100
DEFAULT_SUPPORT_PROMPT_INITIAL_THRESHOLD = DEFAULT_SUPPORT_PROMPT_SHORT_SNOOZE


class SupportPrompt:
    """Encapsulates support prompt thresholds and dialog presentation.

    The prompt offers three choices:
    - Support: snooze longer (e.g., 500 downloads)
    - I'm not yet sure: shorter snooze (e.g., 50 downloads)
    - I cannot donate: medium snooze (e.g., 150 downloads)
    """

    def __init__(
        self,
        parent,
        settings_manager,
        short_snooze: int = DEFAULT_SUPPORT_PROMPT_SHORT_SNOOZE,
        medium_snooze: int = DEFAULT_SUPPORT_PROMPT_MEDIUM_SNOOZE,
        long_snooze: int = DEFAULT_SUPPORT_PROMPT_LONG_SNOOZE,
    ):
        self.parent = parent
        self.settings_manager = settings_manager
        self.default_short_snooze = short_snooze
        self.default_medium_snooze = medium_snooze
        self.default_long_snooze = long_snooze

    def should_prompt(self, completed: int, next_at: int) -> bool:
        """Return True if we reached the threshold for showing the support prompt."""
        return completed >= next_at

    def show_and_get_next_threshold(self, completed: int) -> int:
        """Show prompt and return the next threshold based on user choice."""
        msg = QMessageBox(self.parent)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Support YT Channel Downloader")
        msg.setText("Enjoying the app? Supporting the project keeps it maintained and improves new features.")
        msg.setInformativeText(
            "If it's saved you time, please consider a small contribution. "
            "You can defer or opt out for a while if now isn't the right time."
        )

        support_btn = msg.addButton("Support", QMessageBox.ButtonRole.AcceptRole)
        later_btn = msg.addButton("I'm not yet sure", QMessageBox.ButtonRole.DestructiveRole)
        cannot_btn = msg.addButton("I cannot donate", QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        if msg.clickedButton() == support_btn:
            logger.info("User chose Support; opening donation page and snoozing long.")
            opened = QDesktopServices.openUrl(QUrl(SUPPORT_URL))
            if not opened:
                logger.warning("Failed to open support URL: %s", SUPPORT_URL)
            return completed + self.default_long_snooze
        if msg.clickedButton() == cannot_btn:
            logger.info("User chose Cannot donate; snoozing medium.")
            return completed + self.default_medium_snooze

        logger.info("User chose Not sure; snoozing short.")
        return completed + self.default_short_snooze
