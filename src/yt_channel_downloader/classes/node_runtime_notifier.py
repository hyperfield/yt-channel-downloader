# Author: hyperfield
# Project: YT Channel Downloader
# Description: Helper to prompt users to install a JavaScript runtime for yt-dlp

import shutil
import subprocess

from PyQt6.QtWidgets import QMessageBox, QCheckBox
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from .logger import get_logger


logger = get_logger("NodeRuntimeNotifier")


class NodeRuntimeNotifier:
    """Encapsulates detection and prompting for an optional JS runtime."""

    def __init__(self, settings_manager, warning_tracker, parent):
        self.settings_manager = settings_manager
        self.warning_tracker = warning_tracker
        self.parent = parent
        self.prompted_this_session = False

    def maybe_prompt(self, *, force=False, require_logged_warning=False):
        """
        Show a recommendation dialog if no JS runtime is available or yt-dlp reported it.

        Args:
            force (bool): Prompt even if a runtime binary is present (used when yt-dlp warns).
            require_logged_warning (bool): Only prompt if yt-dlp logged the JS runtime warning.
        """
        settings = self.settings_manager.settings
        if settings.get('suppress_node_runtime_warning'):
            logger.info("JS runtime recommendation suppressed by user preference")
            return

        if require_logged_warning and not self.warning_tracker.pop_seen():
            return

        if not force and self._has_working_js_runtime():
            return

        if self.prompted_this_session and not force:
            logger.debug("JS runtime warning already shown this session")
            return

        self._show_prompt(settings)

    def _has_working_js_runtime(self) -> bool:
        """Check for a usable JavaScript runtime (Node.js or Deno) on PATH."""
        for binary in ("node", "deno"):
            runtime_path = shutil.which(binary)
            if not runtime_path:
                continue
            try:
                subprocess.run([runtime_path, "--version"], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
                logger.debug("%s detected at %s", binary, runtime_path)
                return True
            except Exception:  # noqa: BLE001
                logger.info("%s binary found at %s but version check failed", binary, runtime_path)
        return False

    def _show_prompt(self, settings):
        """Render and handle the optional-runtime dialog."""
        msg = QMessageBox(self.parent)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Optional dependency recommended")
        msg.setText("A JavaScript runtime is recommended for more complete YouTube format coverage.")
        msg.setInformativeText(
            "A JavaScript runtime to facilitate downloading of videos is missing. "
            "Installing it reduces missing formats. It is recommended that you\n\n"
            "install Deno, since node.js may still go undetected by yt-dlp."
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        deno_btn = msg.addButton("Open Deno.com", QMessageBox.ButtonRole.ActionRole)
        dont_show = QCheckBox("Don't show again", msg)
        msg.setCheckBox(dont_show)
        msg.exec()
        self.prompted_this_session = True

        if msg.clickedButton() == deno_btn:
            QDesktopServices.openUrl(QUrl("https://deno.com/"))

        if dont_show.isChecked():
            settings['suppress_node_runtime_warning'] = True
            self.settings_manager.save_settings_to_file(settings)
