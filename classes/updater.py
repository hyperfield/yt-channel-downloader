from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtWidgets import QWidget

from classes.dialogs import CustomDialog
from classes.runtime_info import RuntimeInfo, RuntimeMode, detect_runtime
from config.constants import APP_VERSION, UPDATE_DOWNLOAD_URL


@dataclass(frozen=True)
class UpdateContext:
    runtime: RuntimeInfo
    current_version: str
    download_url: str


class Updater:
    """
    Simple updater helper that adapts its messaging based on how the app is
    being executed (source checkout vs. frozen bundle).

    A more sophisticated implementation can extend this class with real
    network version checks and automatic download/installation.
    """

    def __init__(self) -> None:
        self._context = UpdateContext(
            runtime=detect_runtime(),
            current_version=APP_VERSION,
            download_url=UPDATE_DOWNLOAD_URL,
        )

    def prompt_for_update(self, parent: QWidget | None = None) -> None:
        if self._context.runtime.mode is RuntimeMode.SOURCE:
            self._show_source_update_message(parent)
        else:
            self._show_frozen_update_message(parent)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _show_source_update_message(self, parent: QWidget | None) -> None:
        message = (
            f"You are running YT Channel Downloader {self._context.current_version} "
            "directly from source.<br><br>"
            "To update to the latest version, open a terminal in the project "
            "directory and run:<br>"
            "<code>git pull</code><br><br>"
            "After pulling the changes, restart the application."
        )
        dialog = CustomDialog("Update Instructions", message, parent=parent)
        dialog.exec()

    def _show_frozen_update_message(self, parent: QWidget | None) -> None:
        message = (
            f"You are running a packaged build of YT Channel Downloader "
            f"({self._context.current_version}).<br><br>"
            "Download the latest installer from "
            f"<a href=\"{self._context.download_url}\">SourceForge</a> and run it "
            "after this application exits.<br><br>"
            "Future versions can extend this dialog to download and relaunch the "
            "update automatically."
        )
        dialog = CustomDialog("Update Instructions", message, parent=parent)
        dialog.exec()
