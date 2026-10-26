# Author: hyperfield
# Project: YT Channel Downloader
# Description: Helper to prompt users to install a JavaScript runtime for yt-dlp

from pathlib import Path
import re
import shutil
import subprocess  # nosec B404 - only used with fixed argv lists and validated absolute executable paths

from PyQt6.QtWidgets import QMessageBox, QCheckBox
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from .logger import get_logger
from .yt_dlp_options import MIN_JS_RUNTIME_VERSIONS


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

        if self.prompted_this_session:
            logger.debug("JS runtime warning already shown this session")
            return

        self._show_prompt(settings)

    def _has_working_js_runtime(self) -> bool:
        """Check for a usable JavaScript runtime (Node.js or Deno) on PATH."""
        for binary, minimum_version in MIN_JS_RUNTIME_VERSIONS.items():
            runtime_path = shutil.which(binary)
            if not runtime_path:
                continue
            runtime_path = self._validated_runtime_path(runtime_path)
            if not runtime_path:
                continue
            try:
                result = subprocess.run([runtime_path, "--version"], check=True,  # nosec B603
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                        text=True, timeout=2, shell=False)
                match = re.search(r'(?:^|\s)v?(\d+)\.(\d+)\.(\d+)', result.stdout)
                if not match or tuple(map(int, match.groups())) < minimum_version:
                    logger.info("%s at %s is not a supported runtime version", binary, runtime_path)
                    continue
                logger.debug("%s detected at %s", binary, runtime_path)
                return True
            except Exception:  # noqa: BLE001
                logger.info("%s binary found at %s but version check failed", binary, runtime_path)
        return False

    @staticmethod
    def _validated_runtime_path(runtime_path: str) -> str | None:
        """Resolve PATH results to an absolute executable file before running it."""
        try:
            resolved = Path(runtime_path).resolve(strict=True)
        except (OSError, RuntimeError):
            return None
        if not resolved.is_absolute() or not resolved.is_file():
            return None
        return str(resolved)

    def _show_prompt(self, settings):
        """Render and handle the optional-runtime dialog."""
        msg = QMessageBox(self.parent)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Optional dependency recommended")
        msg.setText("A JavaScript runtime is recommended for more complete YouTube format coverage.")
        msg.setInformativeText(
            "A JavaScript runtime to facilitate downloading of videos is missing. "
            "Installing it reduces missing formats. Install Deno 2.3 or newer "
            "(recommended), or Node.js 22 or newer."
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
