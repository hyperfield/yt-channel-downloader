# Author: hyperfield
# Email: inbox@quicknode.net
# Project: YT Channel Downloader
# Description: This module contains the class MainWindow
# License: MIT License

from urllib import error
import os
import math
import re
import threading
from collections import deque
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar, TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6 import QtGui, QtCore
if TYPE_CHECKING:
    TSlotFunc = TypeVar("TSlotFunc", bound=Callable[..., Any])

    def Slot(*types: Any, **kwargs: Any) -> Callable[[TSlotFunc], TSlotFunc]:
        ...
else:  # pragma: no cover - import only for runtime use
    from PyQt6.QtCore import pyqtSlot as Slot
from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtWidgets import (QApplication, QMainWindow, QDialog, QCheckBox,
                             QMessageBox, QPushButton, QHBoxLayout, QProgressBar,
                             QLabel, QWidget)
from PyQt6.QtGui import QFont
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtGui import QStandardItem
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
import yt_dlp

from ..assets import resources_rc    # Qt resources  # noqa: F401  # pylint: disable=unused-import
from ..ui.ui_form import Ui_MainWindow
from ..ui.ui_about import Ui_aboutDialog
from .settings_manager import SettingsManager
from .enums import ColumnIndexes
from ..config.constants import settings_map, DEFAULT_CHANNEL_FETCH_LIMIT, DEFAULT_PLAYLIST_FETCH_LIMIT, CHANNEL_FETCH_BATCH_SIZE
from .download_thread import DownloadThread
from .dialogs import CustomDialog, YoutubeCookiesDialog
from .fetch_progress_dialog import FetchProgressDialog
from .login_prompt_dialog import LoginPromptDialog
from .delegates import CheckBoxDelegate
from .YTChannel import YTChannel
from .videoitem import VideoItem
from .settings import SettingsDialog
from .youtube_auth import YoutubeAuthManager
from .validators import is_supported_media_url
from .utils import QuietYDLLogger, filter_formats, js_warning_tracker
from .node_runtime_notifier import NodeRuntimeNotifier
from .support_prompt import SupportPrompt
from .logger import get_logger
from .updater import Updater


logger = get_logger("MainWindow")


class MainWindow(QMainWindow):
    """Main application window for the YouTube Channel Downloader.

    This class manages the primary UI components, their styling, signal
    connections, and interactions with other modules, such as Settings and
    YouTube login.

    Attributes:
        download_semaphore (threading.Semaphore): Controls the maximum
            number of simultaneous downloads.
        ui (Ui_MainWindow): Main UI layout.
        model (QStandardItemModel): Data model for displaying downloadable
                                    videos in a tree view.
        about_dialog (QDialog): Dialog window for the "About" information.
        settings_manager (SettingsManager): Manages user settings.
        user_settings (dict): Stores user-defined settings.
        selectAllCheckBox (QCheckBox): Checkbox for selecting all videos in
                                       the list.
        yt_chan_vids_titles_links (list): List of YouTube channel video title
                                          and link data.
        vid_dl_indexes (list): List of indexes of videos to download.
        dl_threads (list): List of download threads.
        dl_path_correspondences (dict): Map between video download paths and
                                        video data.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initializes the main window and its components.

        Args:
            parent (QWidget, optional): Parent widget, defaults to None.
        """
        super().__init__(parent)
        self.window_resize_needed = True
        self.youtube_auth_manager = None
        self.yt_chan_vids_titles_links = []
        self.progress_widgets = {}
        self.fetch_in_progress = False
        self.fetch_error_message = None
        self.updater = Updater()
        self.format_info_cache: Dict[str, dict] = {}
        self.size_estimate_cache: Dict[Tuple[str, Tuple], Optional[int]] = {}
        self.speed_history: Dict[int, deque] = {}
        self.estimated_download_sizes: Dict[int, Optional[int]] = {}
        self._settings_signature: Optional[Tuple] = None
        self._suppress_item_changed = False
        self.node_notifier: Optional[NodeRuntimeNotifier] = None
        self.support_prompt: Optional[SupportPrompt] = None
        self.channel_fetch_context: Dict[str, Any] | None = None
        self.current_fetch_is_channel = False
        logger.info("Main window initialised")

        self.init_styles()

        # Limit to 4 simultaneous downloads (threading.Semaphore avoids GUI thread stalls)
        # TODO: Make this controllable in the Settings
        self.download_semaphore = threading.Semaphore(4)

        self.set_icon()
        self.setup_ui()
        self.root_item = self.model.invisibleRootItem()
        self.selection_summary_label: QLabel = QLabel("")
        self.ui.statusbar.addPermanentWidget(self.selection_summary_label)

        self.setup_about_dialog()
        self.init_download_structs()
        self.connect_signals()
        self.initialize_settings()
        self._init_node_notifier()
        self._init_support_prompt()
        self.setup_select_all_checkbox()
        self.initialize_youtube_login()

    def init_styles(self):
        """Applies global styles and element-specific styles for the main
        window."""
        self.setStyleSheet("""
            * { font-family: "Arial"; font-size: 12pt; }
            QLabel {
                font-family: Arial;
                font-size: 14pt;
            }
            QLineEdit, QComboBox {
                border: 1px solid #A0A0A0;
                padding: 4px;
                border-radius: 4px;
            }
            QGroupBox {
                border: 1px solid #d3d3d3;
                padding: 10px;
                margin-top: 10px;
                border-radius: 5px;
            }
            QTreeView {
                border: 1px solid #A0A0A0;
                padding: 4px;
            }
            QTreeView::item {
                padding: 5px;
            }
        """)

    def set_icon(self):
        """Sets the application icon."""
        icon_path = Path(__file__).resolve().parent.parent / "icon.png"
        self.setWindowIcon(QtGui.QIcon(str(icon_path)))

    def setup_ui(self):
        """Initializes main UI components and layout."""
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.model = QtGui.QStandardItemModel()
        logger.debug("Setting up main window UI components")
        self.cancelDownloadsButton = QPushButton("Cancel downloads", self)
        self.cancelDownloadsButton.setObjectName("cancelDownloadsButton")
        self.cancelDownloadsButton.setMinimumSize(QtCore.QSize(120, 32))
        cancel_font = QFont("Arial", 10)
        cancel_font.setBold(False)
        self.cancelDownloadsButton.setFont(cancel_font)
        self.cancelDownloadsButton.setVisible(False)
        self.cancelDownloadsButton.setEnabled(False)
        self.cancelDownloadsButton.clicked.connect(self.cancel_active_downloads)
        self.loadNextButton: QPushButton = QPushButton("Fetch Next", self)
        self.loadNextButton.setObjectName("loadNextButton")
        self.loadNextButton.setMinimumSize(QtCore.QSize(140, 32))
        load_font = QFont("Courier New", 12)
        load_font.setBold(True)
        self.loadNextButton.setFont(load_font)
        self.loadNextButton.setEnabled(False)
        self.loadNextButton.clicked.connect(self.load_next_batch)
        self.bottomButtonLayout = QHBoxLayout()
        self.bottomButtonLayout.addStretch()
        self.bottomButtonLayout.addWidget(self.loadNextButton)
        self.bottomButtonLayout.addWidget(self.cancelDownloadsButton)
        self.ui.verticalLayout.addLayout(self.bottomButtonLayout)
        self.downloadSelectedVidsButton: QPushButton = self.ui.downloadSelectedVidsButton
        self.getVidListButton: QPushButton = self.ui.getVidListButton
        self._setup_update_action()
        self.setup_buttons()
        self.setup_tree_view_delegate()
        self.ui.actionDonate.triggered.connect(self.open_donate_url)

    def open_donate_url(self):
        """Opens the donation URL in the default web browser."""
        logger.info("Opening donation page in browser")
        QDesktopServices.openUrl(QUrl("https://ko-fi.com/hyperfield"))

    @Slot()
    def show_license_dialog(self) -> None:
        """Display MIT license text in a dialog."""
        license_text = (
            "<b>MIT License</b><br><br>"
            "Copyright (c) 2017-2024 hyperfield<br><br>"
            "Permission is hereby granted, free of charge, to any person obtaining a copy "
            "of this software and associated documentation files (the 'Software'), to deal "
            "in the Software without restriction, including without limitation the rights "
            "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell "
            "copies of the Software, and to permit persons to whom the Software is furnished "
            "to do so, subject to the following conditions:<br><br>"
            "The above copyright notice and this permission notice shall be included in all "
            "copies or substantial portions of the Software.<br><br>"
            "THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, "
            "INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A "
            "PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT "
            "HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION "
            "OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE "
            "SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE."
        )
        dialog = CustomDialog("MIT License", license_text, parent=self)
        dialog.exec()

    @Slot()
    def on_check_for_updates(self) -> None:
        """Show update instructions tailored to the current runtime."""
        self.updater.prompt_for_update(parent=self)

    def setup_button(self, button, callback):
        """Configures a button with the specified callback and font.

        Args:
            button (QPushButton): Button widget to set up.
            callback (function): Function to connect to button's clicked
            signal.
        """
        button.clicked.connect(callback)
        font = QFont("Arial", 12)
        font.setBold(True)
        button.setFont(font)

    def setup_buttons(self):
        """Sets up specific buttons used in the main window."""
        self.setup_button(self.downloadSelectedVidsButton, self.dl_vids)
        self.setup_button(self.getVidListButton, self.show_vid_list)

    def _setup_update_action(self) -> None:
        """Insert the Check for Updates action into the Help menu."""
        self.actionCheckForUpdates = QtGui.QAction("Check for Updates...", self)
        self.actionCheckForUpdates.setObjectName("actionCheckForUpdates")
        self.actionCheckForUpdates.setMenuRole(QtGui.QAction.MenuRole.NoRole)
        self.actionAboutQt = QtGui.QAction("About Qt", self)
        self.actionAboutQt.setMenuRole(QtGui.QAction.MenuRole.NoRole)
        self.actionAboutQt.setObjectName("actionAboutQt")
        self.actionAboutLicense = QtGui.QAction("About MIT License", self)
        self.actionAboutLicense.setMenuRole(QtGui.QAction.MenuRole.NoRole)
        self.actionAboutLicense.setObjectName("actionAboutLicense")

        insert_before = self.ui.actionDonate
        self.ui.menuHelp.insertAction(insert_before, self.actionAboutLicense)
        self.ui.menuHelp.insertAction(insert_before, self.actionAboutQt)
        self.ui.menuHelp.insertAction(insert_before, self.actionCheckForUpdates)
        self.ui.actionAbout.setText("About YT Channel Downloader")
        self.ui.actionAbout.setMenuRole(QtGui.QAction.MenuRole.NoRole)

    def setup_tree_view_delegate(self):
        """Sets up a delegate for managing custom items in the tree view."""
        cb_delegate = CheckBoxDelegate()
        self.ui.treeView.setItemDelegateForColumn(ColumnIndexes.DOWNLOAD,
                                                  cb_delegate)

    def set_bold_font(self, widget, size):
        """Applies a bold font to a specific widget.

        Args:
            widget (QWidget): The widget to apply the font to.
            size (int): The font size to set.
        """
        font = QFont("Arial", size)
        font.setBold(True)
        widget.setFont(font)

    def setup_about_dialog(self):
        """Initializes and sets up the About dialog."""
        self.about_dialog = QDialog()
        self.about_ui = Ui_aboutDialog()
        self.about_ui.setupUi(self.about_dialog)

    def connect_signals(self):
        """Connects various UI signals to their respective slots."""
        self.ui.actionAbout.triggered.connect(self.show_about_dialog)
        self.ui.actionSettings.triggered.connect(self.show_settings_dialog)
        self.ui.actionExit.triggered.connect(self.exit)
        self.actionCheckForUpdates.triggered.connect(self.on_check_for_updates)
        self.actionAboutQt.triggered.connect(QApplication.instance().aboutQt)
        self.actionAboutLicense.triggered.connect(self.show_license_dialog)
        self.model.itemChanged.connect(self.on_item_changed)
        self.update_download_button_state()

    def handle_download_error(self, data):
        """Handles download error notifications from DownloadThread."""
        index = int(data["index"])
        error_type = data.get("error", "Unexpected error")
        logger.error("Download thread %s reported error: %s", index, error_type)

        if error_type == "Download error":
            self.show_download_error(index)
        elif error_type == "Network error":
            self.show_network_error(index)
        elif error_type not in ("Cancelled",):
            self.show_unexpected_error(index)

    def show_download_error(self, index):
        """Displays a dialog for download-specific errors."""
        logger.error("Download error dialog shown for index %s", index)
        QMessageBox.critical(self, "Download Error", f"An error occurred while downloading item {index}. Please check the URL and try again.")

    def show_network_error(self, index):
        """Displays a dialog for network-related errors."""
        logger.error("Network error dialog shown for index %s", index)
        QMessageBox.warning(self, "Network Error", f"Network issue encountered while downloading item {index}. Check your internet connection and try again.")

    def show_unexpected_error(self, index):
        """Displays a dialog for unexpected errors."""
        logger.error("Unexpected error dialog shown for index %s", index)
        QMessageBox.warning(self, "Unexpected Error", f"An unexpected error occurred while downloading item {index}. Please try again later.")

    def show_download_complete(self, index):
        """Displays a dialog when a download completes successfully."""
        QMessageBox.information(self, "Download Complete", f"Download completed successfully for item {index}!")

    def update_cancel_button_state(self):
        """Enable the cancel button only when there are active downloads."""
        has_threads = bool(self.active_download_threads)
        any_running = any(
            thread.isRunning() for thread in self.active_download_threads.values()
        )
        # Show the button only if there is at least one tracked download
        # (even if cancelling), but disable it when nothing is running.
        self.cancelDownloadsButton.setVisible(has_threads)
        self.cancelDownloadsButton.setEnabled(any_running)

    def cancel_active_downloads(self):
        """Request cancellation for all active download threads."""
        if not self.active_download_threads:
            logger.info("Cancel requested with no active downloads")
            return
        logger.info("Cancelling %d active download(s)", len(self.active_download_threads))
        self.cancelDownloadsButton.setEnabled(False)
        for index, thread in list(self.active_download_threads.items()):
            if thread.isRunning():
                thread.cancel()
                progress_bar = self.progress_widgets.get(index)
                if progress_bar:
                    progress_bar.setRange(0, 0)
                    progress_bar.setFormat("Cancelling...")
            else:
                # Thread already stopped; clean up immediately.
                self.cleanup_download_thread(index)
        self.ui.treeView.viewport().update()
        self._cleanup_inactive_downloads()
        self.update_cancel_button_state()
        if not self.active_download_threads:
            self._set_fetch_controls_enabled(True)

    def cleanup_download_thread(self, index):
        """Remove finished or cancelled download threads from tracking."""
        thread = self.active_download_threads.pop(index, None)
        if thread and thread in self.dl_threads:
            self.dl_threads.remove(thread)
        self.progress_widgets.pop(index, None)
        self.speed_history.pop(index, None)
        self.update_cancel_button_state()
        self.update_download_button_state()
        if not self.active_download_threads and not self.fetch_in_progress:
            self._set_fetch_controls_enabled(True)

    def _cleanup_inactive_downloads(self):
        """Clean up threads that are no longer running."""
        inactive = [idx for idx, thread in self.active_download_threads.items() if not thread.isRunning()]
        for idx in inactive:
            self.cleanup_download_thread(idx)

    def on_download_complete(self, index):
        """Update UI after a download thread reports completion."""
        progress_bar = self.progress_widgets.get(index)
        if progress_bar:
            progress_bar.setRange(0, 100)
            progress_bar.setValue(100)
            progress_bar.setFormat("Completed")
        progress_item = self.model.item(index, ColumnIndexes.PROGRESS)
        if progress_item:
            progress_item.setData("Completed", Qt.ItemDataRole.DisplayRole)
            progress_item.setData(100.0, Qt.ItemDataRole.UserRole)
        speed_item = self.model.item(index, ColumnIndexes.SPEED)
        if speed_item:
            speed_item.setData("—", Qt.ItemDataRole.DisplayRole)
        selection_item = self.model.item(index, 0)
        if selection_item is not None:
            selection_item.setCheckState(Qt.CheckState.Unchecked)
        self.user_settings['downloads_completed'] = self.user_settings.get('downloads_completed', 0) + 1
        self.settings_manager.save_settings_to_file(self.user_settings)
        self.maybe_show_support_prompt()
        self.cleanup_download_thread(index)
        self.ui.treeView.viewport().update()
        self.update_selection_size_summary()
        logger.info("Download completed for row %s", index)

    def initialize_settings(self):
        """Initializes user settings from the settings manager."""
        self.settings_manager = SettingsManager()
        self.user_settings = self.settings_manager.settings
        self._refresh_settings_signature()
        self.user_settings.setdefault('suppress_node_runtime_warning', False)
        self.user_settings.setdefault('downloads_completed', 0)
        self.user_settings.setdefault('support_prompt_next_at', 50)
        self.user_settings.setdefault('channel_fetch_limit', DEFAULT_CHANNEL_FETCH_LIMIT)
        self.user_settings.setdefault('playlist_fetch_limit', DEFAULT_PLAYLIST_FETCH_LIMIT)
        self.user_settings.setdefault('channel_fetch_batch_size', CHANNEL_FETCH_BATCH_SIZE)

    def _init_node_notifier(self):
        """Set up the Node.js runtime notifier helper."""
        self.node_notifier = NodeRuntimeNotifier(self.settings_manager, js_warning_tracker, self)

    def _init_support_prompt(self):
        """Set up the support prompt helper."""
        self.support_prompt = SupportPrompt(self, self.settings_manager)

    def setup_select_all_checkbox(self):
        """Sets up the Select All checkbox and adds it to the layout."""
        self.select_all_checkbox = QCheckBox("Select All", self)
        self.select_all_checkbox.setVisible(False)
        self.ui.verticalLayout.addWidget(self.select_all_checkbox)
        self.select_all_checkbox.stateChanged.connect(
            self.on_select_all_state_changed)

    def init_download_structs(self):
        """Initializes download-related structures."""
        self.vid_dl_indexes = []
        self.dl_threads = []
        self.dl_path_correspondences = {}
        self.active_download_threads = {}
        self.speed_history.clear()

    def maybe_warn_node_runtime(self, force: bool = False):
        """Inform users (optionally) to install Node.js for broader YouTube support."""
        if self.user_settings.get('suppress_node_runtime_warning'):
            logger.info("Node.js warning suppressed by user preference")
            return

        node_missing = True
        node_path = shutil.which("node")
        if node_path and not force:
            try:
                subprocess.run([node_path, "--version"], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
                node_missing = False
                logger.debug("Node.js detected at %s; skipping runtime warning", node_path)
            except Exception:  # noqa: BLE001
                logger.info("Node.js binary found at %s but version check failed; will prompt", node_path)

        if not force and not node_missing:
            return

        if self._node_prompted_this_session and not force:
            logger.debug("Node.js warning already shown this session")
            return

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Optional dependency recommended")
        msg.setText("Node.js is recommended for more complete YouTube format coverage.")
        msg.setInformativeText(
            "yt-dlp reported that a JavaScript runtime is missing. "
            "Installing Node.js reduces missing formats and silences related warnings.\n\n"
            "See the README section “Recommended: Node.js runtime” for install steps."
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        dont_show = QCheckBox("Don't show again", msg)
        msg.setCheckBox(dont_show)
        msg.exec()
        self._node_prompted_this_session = True
        if dont_show.isChecked():
            self.user_settings['suppress_node_runtime_warning'] = True
            self.settings_manager.save_settings_to_file(self.user_settings)

    def _maybe_prompt_on_js_warning(self):
        """If yt-dlp emitted a JS runtime warning, prompt the user."""
        if self.node_notifier and js_warning_tracker.pop_seen():
            logger.info("yt-dlp reported missing JS runtime; showing recommendation dialog")
            self.node_notifier.maybe_prompt(force=True)

    def maybe_show_support_prompt(self):
        """Show a support prompt when download milestones are reached."""
        if not self.support_prompt:
            return
        next_at = self.user_settings.get('support_prompt_next_at', 50)
        completed = self.user_settings.get('downloads_completed', 0)
        if not self.support_prompt.should_prompt(completed, next_at):
            return
        new_threshold = self.support_prompt.show_and_get_next_threshold(completed)
        self.user_settings['support_prompt_next_at'] = new_threshold
        self.settings_manager.save_settings_to_file(self.user_settings)

    def initialize_youtube_login(self):
        """Hook up menu action and restore previously saved browser config."""
        self.youtube_auth_manager = YoutubeAuthManager(self.settings_manager, self)
        logger.info("Initialising YouTube authentication manager")
        self.ui.actionYoutube_login.triggered.connect(self.handle_youtube_login)
        self.youtube_auth_manager.login_state_changed.connect(
            self.update_youtube_login_menu)
        self.youtube_auth_manager.login_completed.connect(
            self.on_youtube_login_completed)
        self.update_youtube_login_menu()

    def handle_youtube_login(self):
        """Configure or clear yt-dlp's cookies-from-browser authentication."""
        if not self.youtube_auth_manager.is_configured:
            logger.info("Starting YouTube login configuration flow")
            user_settings = self.settings_manager.settings
            if not user_settings.get('dont_show_login_prompt'):
                login_prompt_dialog = LoginPromptDialog(self)
                if login_prompt_dialog.exec() != QDialog.DialogCode.Accepted:
                    logger.debug("YouTube login prompt dismissed by user")
                    return

            dialog = YoutubeCookiesDialog(
                self,
                config=self.youtube_auth_manager.browser_config
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                config = dialog.get_config()
                self.youtube_auth_manager.configure(config)
                logger.info("Stored cookies-from-browser settings for '%s'", config.browser)
        else:
            logger.info("User requested clearing stored YouTube login configuration")
            confirmation = QMessageBox.question(
                self,
                "Clear YouTube login",
                "This will forget the configured browser profile. Actual browser cookies remain untouched. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if confirmation == QMessageBox.StandardButton.Yes:
                self.youtube_auth_manager.clear()
                logger.info("YouTube login configuration cleared")
                QMessageBox.information(
                    self,
                    "YouTube login",
                    "The saved browser configuration was removed."
                )

    def on_youtube_login_completed(self, success, message):
        """Show feedback after attempting to configure browser cookies."""
        if success:
            logger.info("YouTube login cookies ready for reuse")
            QMessageBox.information(
                self,
                "YouTube login",
                "Browser cookies are ready. yt-dlp will use them for private downloads."
            )
        else:
            details = message or (
                "yt-dlp could not read login cookies from the selected browser profile."
            )
            logger.warning("Failed to configure YouTube login: %s", details)
            QMessageBox.warning(
                self,
                "YouTube login failed",
                details
            )

    def auto_adjust_window_size(self):
        """Dynamically adjusts the main window size based on screen and model
        dimensions.

        Calculates optimal dimensions for the main window by considering screen
        dimensions and model column widths, with a height limited to
        two-thirds of the screen height. Adjusts only if the calculated size
        is larger than the current window size.
        """
        screen = QApplication.primaryScreen()
        screen_size = screen.size()
        full_screen_width = screen_size.width()
        max_height = round(screen_size.height() * 2 / 3)

        total_width = 0
        for column in range(self.model.columnCount()):
            total_width += self.ui.treeView.columnWidth(column)
        total_width = min(total_width, full_screen_width)

        content_height = self.ui.treeView.sizeHintForRow(0) \
            * self.model.rowCount()
        content_height += self.ui.treeView.header().height()
        total_height = min(content_height, max_height)

        # Resize window only if necessary
        if total_width > self.width() or total_height > self.height():
            self.resize(math.ceil(total_width), math.ceil(total_height))

    def on_select_all_state_changed(self, state):
        """Toggle the selection state of all rows based on the 'Select All'
        checkbox.

        Parameters:
            state (int): The checkbox state, where a value of 2 signifies
            'checked' and 0 signifies 'unchecked'.

        Iterates through the model's rows, updating each item's selection state
        accordingly. If an item corresponds to a completed download, it is
        excluded from selection toggling.
        """
        new_value = state == 2
        self._suppress_item_changed = True
        for row in range(self.model.rowCount()):
            item_title_index = self.model.index(row, 1)
            item_title = self.model.data(item_title_index)
            full_file_path = self.dl_path_correspondences[item_title]

            if full_file_path and \
               DownloadThread.is_download_complete(full_file_path):
                continue

            index = self.model.index(row, 0)
            self.model.setData(index, new_value, Qt.ItemDataRole.DisplayRole)

            # Update the Qt.CheckStateRole accordingly
            new_check_state = Qt.CheckState.Checked if new_value \
                else Qt.CheckState.Unchecked
            self.model.setData(index, new_check_state,
                               Qt.ItemDataRole.CheckStateRole)
        self._suppress_item_changed = False
        self.update_download_button_state()
        self.update_selection_size_summary()

    def center_on_screen(self):
        """Center the main window on the primary screen.

        Positions the main window in the center of the screen by calculating
        the midpoint of the available screen geometry and aligning the window's
        frame geometry to this central point.
        """
        screen = QApplication.primaryScreen()
        center_point = screen.availableGeometry().center()
        frame_geom = self.frameGeometry()
        frame_geom.moveCenter(center_point)
        self.move(frame_geom.topLeft())

    def reinit_model(self):
        """Reinitialize the main model and configure the view's headers.

        Clears the current model, sets a new root item, and assigns header
        labels to match the download-related columns. Configures each header
        section's resizing mode for proportional widths, ensuring a clean,
        user-friendly presentation of the model data.
        """
        self.model.clear()
        self.root_item = self.model.invisibleRootItem()
        self.model.setHorizontalHeaderLabels(
            ['Download?', 'Title', 'Duration', 'Link', 'Speed', 'Progress'])
        self.ui.treeView.setModel(self.model)
        self.progress_widgets.clear()
        self.estimated_download_sizes.clear()
        self.speed_history.clear()

        # Set proportional widths
        header = self.ui.treeView.header()
        header.setSectionResizeMode(ColumnIndexes.DOWNLOAD,
                                    QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(ColumnIndexes.TITLE,
                                    QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(ColumnIndexes.DURATION,
                                    QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(ColumnIndexes.LINK,
                                    QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(ColumnIndexes.SPEED,
                                    QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(ColumnIndexes.PROGRESS,
                                    QHeaderView.ResizeMode.ResizeToContents)

        # Set relative stretch factors (adjust as needed)
        # To control each section individually
        header.setStretchLastSection(False)

        # Ensure "Progress" column stays narrow
        font_metrics = QFontMetrics(self.ui.treeView.font())
        max_text_width = font_metrics.horizontalAdvance("100%") + 10
        self.ui.treeView.setColumnWidth(ColumnIndexes.PROGRESS, max_text_width)
        speed_width = font_metrics.horizontalAdvance("000.00 GB/s") + 12
        self.ui.treeView.setColumnWidth(ColumnIndexes.SPEED, speed_width)
        duration_width = font_metrics.horizontalAdvance("00:00:00") + 12
        self.ui.treeView.setColumnWidth(ColumnIndexes.DURATION, duration_width)

        self.select_all_checkbox.setVisible(False)

    def show_settings_dialog(self):
        """Display the settings dialog window.

        Opens the settings dialog, allowing users to view and modify
        application preferences. This dialog is modal and will block further
        input until closed.
        """
        settings_dialog = SettingsDialog()
        settings_dialog.exec()
        self.user_settings = self.settings_manager.settings
        self._refresh_settings_signature()
        self.update_selection_size_summary()

    def show_about_dialog(self):
        """Display the 'About' dialog for the application.

        Shows a dialog with information about the application, including a link
        to external resources. The dialog closes upon clicking the 'Ok' button.
        """
        self.about_ui.aboutLabel.setOpenExternalLinks(True)
        self.about_ui.aboutOkButton.clicked.connect(self.about_dialog.accept)
        self.about_dialog.exec()

    @Slot()
    def update_youtube_login_menu(self):
        """Update the text of the YouTube login menu item based on login state.

        Checks whether browser cookies are configured and updates the
        'Youtube_login' menu action to either 'YouTube login' or
        'Clear YouTube login.'
        """
        if self.youtube_auth_manager and self.youtube_auth_manager.is_configured:
            self.ui.actionYoutube_login.setText("Clear Login")
        else:
            self.ui.actionYoutube_login.setText("Use Browser Cookies for Login")

    def _set_fetch_controls_enabled(self, enabled: bool):
        """Enable or disable URL entry and fetch controls.

        If downloads are active, controls remain disabled regardless of the requested state.
        """
        if enabled and self.active_download_threads:
            enabled = False
        self.ui.chanUrlEdit.setEnabled(enabled)
        fetch_button_enabled = enabled and not self.fetch_in_progress
        self.getVidListButton.setEnabled(fetch_button_enabled)
        self._update_load_next_button_state()

    def _update_load_next_button_state(self):
        """Enable/disable and retitle the Load Next button based on context."""
        if not hasattr(self, "loadNextButton"):
            return
        limit = self._get_channel_fetch_limit()
        self.loadNextButton.setText(f"Fetch Next {limit}")
        has_channel = bool(self.channel_fetch_context and self.channel_fetch_context.get("channel_id"))
        enabled = has_channel and not self.fetch_in_progress and not self.active_download_threads
        self.loadNextButton.setEnabled(enabled)

    def update_download_button_state(self):
        """Enable or disable the download button based on item selection.

        Scans through the model's items to determine if any are selected for
        download. If at least one item is selected, the download button is
        enabled; otherwise, it is disabled. When downloads are currently
        running the button remains disabled.
        """
        if self.active_download_threads:
            self.downloadSelectedVidsButton.setEnabled(False)
            return
        self.downloadSelectedVidsButton.setEnabled(False)
        for row in range(self.model.rowCount()):
            item = self.model.item(row, 0)
            if item.checkState() == Qt.CheckState.Checked:
                self.downloadSelectedVidsButton.setEnabled(True)

    def on_item_changed(self, item):
        """React to checkbox changes to refresh button state and size totals."""
        self.update_download_button_state()
        if self._suppress_item_changed:
            return
        if item and item.column() == ColumnIndexes.DOWNLOAD:
            self.update_selection_size_summary()

    @Slot(str)
    def display_error_dialog(self, message):
        """
        Displays an error dialog with the given message and re-enables the
        'getVidListButton'.

        Parameters:
        message (str): The error message to be displayed.
        """
        dlg = CustomDialog("URL error", message)
        dlg.exec()
        self._set_fetch_controls_enabled(True)

    def get_vid_list(self, channel_id, yt_channel):
        """
        Fetches the list of videos for a specific YouTube channel.

        Args:
            channel_id (str): The unique identifier of the YouTube channel.
            yt_channel (YouTubeChannel): The YouTubeChannel object used to
            fetch video data.

        Returns:
            None: This method modifies self.yt_chan_vids_titles_links in place
            with the latest video titles and links for the specified channel.

        Side Effects:
            Clears the current list of videos and repopulates it with the
            fetched data.
        """
        self.yt_chan_vids_titles_links.clear()
        limit = self.user_settings.get('channel_fetch_limit', DEFAULT_CHANNEL_FETCH_LIMIT)
        self.yt_chan_vids_titles_links = yt_channel.fetch_all_videos_in_channel(
            channel_id,
            limit=limit,
        )

    def populate_window_list(self):
        """Populates the main window's list view with video details."""
        self.reinit_model()
        for entry in self.yt_chan_vids_titles_links:
            self._add_video_item_to_list(entry)

        self._finalize_list_view()
        self.update_selection_size_summary()
        self._maybe_prompt_on_js_warning()
        self._maybe_prompt_on_js_warning()

    def _add_video_item_to_list(self, video_entry):
        """
        Adds a single video entry to the list view by creating a VideoItem,
        setting its properties, and appending it to the root item.
        """
        title = video_entry.get('title', 'Unknown Title')
        link = video_entry.get('url', '')
        duration = video_entry.get('duration')
        download_path = self._get_video_filepath(title)
        video_item = VideoItem(title, link, duration, download_path)
        self.root_item.appendRow(video_item.get_qt_item())
        self.dl_path_correspondences[title] = download_path
        row_index = self.model.rowCount() - 1
        progress_index = self.model.index(row_index, ColumnIndexes.PROGRESS)
        completed = DownloadThread.is_download_complete(download_path)
        progress_bar = self._create_progress_bar(completed=completed)
        self.ui.treeView.setIndexWidget(progress_index, progress_bar)
        self.progress_widgets[row_index] = progress_bar

    def _get_video_filepath(self, title):
        """Generates the file path for a given video title based on user
        settings."""
        filename = DownloadThread.sanitize_filename(title)
        download_dir = self.user_settings.get('download_directory', './')
        return os.path.join(download_dir, filename)

    def _finalize_list_view(self):
        """Adjusts and displays the list view once all items are populated."""
        self.ui.treeView.expandAll()
        self.ui.treeView.show()
        self._configure_list_columns()
        self._apply_tree_view_styles()
        if self.model.rowCount() > 0:
            self.select_all_checkbox.setVisible(True)
            if self.window_resize_needed:
                self.auto_adjust_window_size()
                self.window_resize_needed = False

    def _configure_list_columns(self):
        """Sets up column delegates and resizes columns to contents."""
        cb_delegate = CheckBoxDelegate()
        self.ui.treeView.setItemDelegateForColumn(ColumnIndexes.DOWNLOAD,
                                                  cb_delegate)
        for col in [ColumnIndexes.TITLE,
                    ColumnIndexes.DURATION,
                    ColumnIndexes.LINK,
                    ColumnIndexes.SPEED,
                    ColumnIndexes.PROGRESS]:
            self.ui.treeView.resizeColumnToContents(col)

    def _apply_tree_view_styles(self):
        """Applies styles to the tree view for a consistent appearance."""
        self.ui.treeView.setStyleSheet("""
        QTreeView::indicator:disabled {
            background-color: gray;
        }
        """)

    def update_selection_size_summary(self):
        """Calculate and display estimated download sizes for checked rows."""
        if self.model.rowCount() == 0:
            self.selection_summary_label.setText("")
            return

        selected_rows = self._checked_row_indexes()
        if not selected_rows:
            self.selection_summary_label.setText("No items selected")
            return

        total_estimated, total_remaining, has_unknown = self._calculate_selection_totals(selected_rows)
        summary = self._format_selection_summary(len(selected_rows), total_estimated, total_remaining, has_unknown)
        self.selection_summary_label.setText(summary)

    def _checked_row_indexes(self):
        """Return the row indexes that are marked for download."""
        rows = []
        for row in range(self.model.rowCount()):
            checkbox_item = self.model.item(row, ColumnIndexes.DOWNLOAD)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                rows.append(row)
        return rows

    def _calculate_selection_totals(self, selected_rows):
        """Accumulate estimated and remaining bytes for selected rows."""
        has_unknown = False
        total_bytes_estimated = 0
        total_bytes_remaining = 0

        for row in selected_rows:
            link_item = self.model.item(row, ColumnIndexes.LINK)
            if link_item is None:
                has_unknown = True
                continue

            duration_seconds = self._item_user_role(self.model.item(row, ColumnIndexes.DURATION))
            estimate = self._get_or_estimate_size(link_item.text(), duration_seconds)
            self.estimated_download_sizes[row] = estimate
            if estimate is None:
                has_unknown = True
                continue

            total_bytes_estimated += estimate
            progress_val = self._item_user_role(self.model.item(row, ColumnIndexes.PROGRESS))
            total_bytes_remaining += self._remaining_bytes(estimate, progress_val)

        return total_bytes_estimated, total_bytes_remaining, has_unknown

    @staticmethod
    def _item_user_role(item):
        """Fetch UserRole data safely."""
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    @staticmethod
    def _remaining_bytes(estimate: int, progress_val) -> int:
        """Calculate remaining bytes based on progress percentage."""
        if isinstance(progress_val, (int, float)) and 0 <= progress_val <= 100:
            return max(int(estimate * (1 - progress_val / 100.0)), 0)
        return estimate

    def _format_selection_summary(self, selected_count, total_estimated, total_remaining, has_unknown):
        """Compose the summary string for the selection label."""
        eta_text = self._estimate_total_eta(total_remaining)
        summary = f"Selected: {selected_count} | Est. download: {self._format_size(total_estimated)}"
        if has_unknown:
            summary += " (+unknown)"
        summary += f" | ETA: {eta_text}"
        return summary

    def _get_or_estimate_size(self, link: str, duration_seconds: Optional[int]) -> Optional[int]:
        """Return cached estimate when available or compute a fresh one."""
        if not link:
            return None
        settings_sig = self._settings_signature or ()
        cache_key = (link, settings_sig)
        if cache_key in self.size_estimate_cache:
            return self.size_estimate_cache[cache_key]

        info = self._fetch_format_info(link)
        estimate = self._estimate_size_from_info(info, duration_seconds)
        self.size_estimate_cache[cache_key] = estimate
        if estimate:
            # Keep a quick lookup for ETA calculations keyed by row index later
            try:
                row_index = self._link_to_row_index(link)
                if row_index is not None:
                    self.estimated_download_sizes[row_index] = estimate
            except Exception:  # noqa: BLE001
                pass
        return estimate

    def _link_to_row_index(self, link: str) -> Optional[int]:
        """Find the first row whose link matches; used to cache estimates."""
        if not link:
            return None
        for row in range(self.model.rowCount()):
            item = self.model.item(row, ColumnIndexes.LINK)
            if item and item.text() == link:
                return row
        return None

    def _fetch_format_info(self, link: str) -> Optional[dict]:
        """Fetch and cache full format metadata for a URL."""
        if not link:
            return None
        cached = self.format_info_cache.get(link)
        if cached:
            return cached

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'noplaylist': True,
            'logger': QuietYDLLogger(),
            'remote_components': ['ejs:github'],
        }
        auth_opts = self._get_auth_options() or {}
        proxy_url = self.settings_manager.build_proxy_url(self.user_settings)
        if proxy_url:
            auth_opts.setdefault('proxy', proxy_url)
            ydl_opts['proxy'] = proxy_url

        ydl_opts.update(auth_opts)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
            self.format_info_cache[link] = info
            return info
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to fetch format info for %s: %s", link, exc)
            return None

    def _estimate_size_from_info(self, info: Optional[dict], duration_seconds: Optional[int]) -> Optional[int]:
        """Estimate download size using available format metadata."""
        if info is None:
            return self._guess_size_from_bitrate(duration_seconds)

        formats = info.get('formats') or []
        if self.user_settings.get('audio_only'):
            audio_quality = self._map_setting('preferred_audio_quality', 'bestaudio')
            audio_ext = self._map_setting('preferred_audio_format', None)
            return self._estimate_audio_only_size(formats, audio_ext, audio_quality, duration_seconds)

        video_quality = self._map_setting('preferred_video_quality', 'bestvideo')
        video_ext = self._map_setting('preferred_video_format', None)
        return self._estimate_video_size(formats, video_quality, video_ext, duration_seconds)

    def _estimate_audio_only_size(
        self,
        formats,
        audio_ext: Optional[str],
        audio_quality: Optional[str],
        duration_seconds: Optional[int],
    ) -> Optional[int]:
        """Estimate size when only audio is requested."""
        audio_fmt = self._select_audio_format(formats, audio_ext, audio_quality)
        estimate = self._estimate_stream_size(audio_fmt, duration_seconds)
        if estimate is None:
            return self._guess_size_from_bitrate(duration_seconds)
        return estimate

    def _estimate_video_size(
        self,
        formats,
        video_quality: str,
        video_ext: Optional[str],
        duration_seconds: Optional[int],
    ) -> Optional[int]:
        """Estimate size when video (and optionally separate audio) is requested."""
        video_fmt = self._select_video_format(formats, video_quality, video_ext)
        total = 0

        if video_fmt:
            video_size = self._estimate_stream_size(video_fmt, duration_seconds)
            if video_size:
                total += video_size

        needs_audio = (not video_fmt) or video_fmt.get('acodec') in (None, 'none')
        if needs_audio:
            audio_fmt = self._select_audio_format(formats, None, 'bestaudio')
            audio_size = self._estimate_stream_size(audio_fmt, duration_seconds)
            if audio_size:
                total += audio_size

        if total == 0:
            return self._guess_size_from_bitrate(duration_seconds)
        return total

    def _select_video_format(self, formats, target_resolution: str, target_ext: Optional[str]):
        """Pick the best matching video stream (could be muxed) for estimates."""
        filtered = self._filter_video_formats(formats, target_ext)
        if not filtered:
            return None

        target_height = self._parse_target_height(target_resolution)
        sorted_formats = self._sort_video_formats_by_preference(filtered, target_height)
        return sorted_formats[0] if sorted_formats else None

    def _filter_video_formats(self, formats, target_ext: Optional[str]):
        """Filter and sanitize video formats based on extension preference."""
        ext_key = target_ext if target_ext not in (None, 'Any') else 'Any'
        filtered = filter_formats(formats, ext_key) or []
        if not filtered and ext_key != 'Any':
            filtered = filter_formats(formats, 'Any') or []
        return [f for f in filtered if f.get('format_id') and f.get('url')]

    def _parse_target_height(self, target_resolution: Optional[str]) -> Optional[int]:
        """Extract a numeric target height from a resolution label."""
        if not target_resolution or target_resolution == 'bestvideo':
            return None
        digits = ''.join(filter(str.isdigit, str(target_resolution)))
        if not digits:
            return None
        try:
            return int(digits)
        except ValueError:
            return None

    def _sort_video_formats_by_preference(self, formats, target_height: Optional[int]):
        """Order formats closest to the desired height, then by quality."""
        if target_height:
            def sort_key(fmt):
                height = fmt.get('height') or 0
                delta = abs(height - target_height)
                return (delta, -height, -(fmt.get('tbr') or 0))
            return sorted(formats, key=sort_key)

        return sorted(formats, key=lambda f: (-(f.get('height') or 0), -(f.get('tbr') or 0)))

    def _select_audio_format(self, formats, preferred_ext: Optional[str], preferred_quality: Optional[str]):
        """Pick the audio stream closest to the requested quality/extension."""
        audio_formats = [
            f for f in formats
            if f.get('vcodec') == 'none' and f.get('url')
        ]
        if preferred_ext and preferred_ext not in ('Any', None):
            filtered = [
                f for f in audio_formats
                if f.get('ext') == preferred_ext or preferred_ext in (f.get('acodec') or '')
            ]
            if filtered:
                audio_formats = filtered
        if not audio_formats:
            audio_formats = [f for f in formats if f.get('acodec') not in (None, 'none') and f.get('url')]
        if not audio_formats:
            return None

        target_bitrate = self._parse_bitrate_kbps(preferred_quality)
        if target_bitrate:
            audio_formats = sorted(
                audio_formats,
                key=lambda f: (
                    abs((self._get_audio_bitrate(f) or 0) - target_bitrate),
                    -(self._get_audio_bitrate(f) or 0),
                )
            )
        else:
            audio_formats = sorted(audio_formats, key=lambda f: -(self._get_audio_bitrate(f) or 0))

        return audio_formats[0]

    @staticmethod
    def _get_audio_bitrate(fmt) -> Optional[float]:
        """Return audio bitrate (abr/tbr) in kbps if present."""
        abr = fmt.get('abr') or fmt.get('tbr')
        return float(abr) if abr is not None else None

    @staticmethod
    def _get_video_bitrate(fmt) -> Optional[float]:
        """Return video bitrate (tbr/vbr) in kbps if present."""
        if fmt is None:
            return None
        for key in ('tbr', 'vbr'):
            value = fmt.get(key)
            if value is not None:
                return float(value)
        return None

    def _estimate_stream_size(self, fmt, duration_seconds: Optional[int]) -> Optional[int]:
        """Estimate size in bytes for a stream using explicit size or bitrate×duration."""
        if fmt is None:
            return None
        for key in ('filesize', 'filesize_approx'):
            value = fmt.get(key)
            if isinstance(value, (int, float)) and value > 0:
                return int(value)
        if duration_seconds and duration_seconds > 0:
            bitrate_kbps = self._get_audio_bitrate(fmt) if fmt.get('vcodec') == 'none' else self._get_video_bitrate(fmt)
            if bitrate_kbps:
                return int(bitrate_kbps * 1000 / 8 * duration_seconds)
        return None

    @staticmethod
    def _parse_bitrate_kbps(label: Optional[str]) -> Optional[int]:
        """Parse a bitrate label like '320k' into an integer kbps."""
        if not label or label == 'bestaudio':
            return None
        digits = ''.join(filter(str.isdigit, label))
        if not digits:
            return None
        try:
            return int(digits)
        except ValueError:
            return None

    def _guess_size_from_bitrate(self, duration_seconds: Optional[int]) -> Optional[int]:
        """Fallback heuristic when we can't fetch metadata."""
        if not duration_seconds or duration_seconds <= 0:
            return None
        if self.user_settings.get('audio_only'):
            bitrate_kbps = self._parse_bitrate_kbps(
                self._map_setting('preferred_audio_quality', 'bestaudio')
            ) or 192
        else:
            quality = self._map_setting('preferred_video_quality', '1080p')
            bitrate_lookup = {
                '2160p': 20000,
                '1440p': 12000,
                '1080p': 8000,
                '720p': 5000,
                '480p': 2500,
                '360p': 1200,
                '240p': 700,
                '144p': 400,
                'bestvideo': 8000,
            }
            bitrate_kbps = bitrate_lookup.get(quality, 4000)
        return int(bitrate_kbps * 1000 / 8 * duration_seconds)

    def _map_setting(self, key: str, default):
        """Resolve a user setting through settings_map with a default fallback."""
        return settings_map.get(key, {}).get(self.user_settings.get(key), default)

    def _build_settings_signature(self) -> Tuple:
        """Build a tuple that reflects current download-affecting settings."""
        return (
            self.user_settings.get('audio_only'),
            self.user_settings.get('preferred_audio_format'),
            self.user_settings.get('preferred_audio_quality'),
            self.user_settings.get('preferred_video_format'),
            self.user_settings.get('preferred_video_quality'),
        )

    def _refresh_settings_signature(self):
        """Reset caches when settings relevant to format selection change."""
        new_sig = self._build_settings_signature()
        if new_sig != self._settings_signature:
            self._settings_signature = new_sig
            self.size_estimate_cache.clear()
            self.format_info_cache.clear()

    @staticmethod
    def _format_size(num_bytes: int) -> str:
        if num_bytes is None or num_bytes <= 0:
            return "—"
        step = 1024.0
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(num_bytes)
        for unit in units:
            if size < step:
                return f"{size:.1f} {unit}" if unit != 'B' else f"{int(size)} B"
            size /= step
        return f"{size:.1f} PB"

    @staticmethod
    def _format_eta(seconds: float) -> str:
        """Short human-readable ETA (h:mm:ss or m:ss)."""
        if seconds is None or seconds <= 0:
            return "0s"
        total_seconds = int(seconds)
        minutes, sec = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:d}:{minutes:02d}:{sec:02d}"
        return f"{minutes:d}:{sec:02d}"

    def _ensure_estimate_for_index(self, index: int) -> Optional[int]:
        """Return or compute estimated total bytes for a row index."""
        if index in self.estimated_download_sizes:
            return self.estimated_download_sizes[index]
        link_item = self.model.item(index, ColumnIndexes.LINK)
        duration_item = self.model.item(index, ColumnIndexes.DURATION) if index < self.model.rowCount() else None
        duration_seconds = duration_item.data(Qt.ItemDataRole.UserRole) if duration_item else None
        estimate = self._get_or_estimate_size(link_item.text() if link_item else "", duration_seconds)
        self.estimated_download_sizes[index] = estimate
        return estimate

    def _estimate_total_eta(self, total_bytes_remaining: int) -> str:
        """Estimate total ETA for selected items based on recent speeds."""
        avg_speed = self._compute_average_speed()
        if not avg_speed or avg_speed <= 0 or not total_bytes_remaining:
            return "—"
        eta_seconds = total_bytes_remaining / avg_speed
        return self._format_eta(eta_seconds)

    def _compute_average_speed(self) -> Optional[float]:
        """Compute rolling average speed across active downloads."""
        samples = []
        for history in self.speed_history.values():
            samples.extend(history)
        if not samples:
            return None
        return sum(samples) / len(samples)

    def _create_progress_bar(self, completed=False):
        """Create a styled progress bar, optionally pre-set to completed state."""
        bar = QProgressBar(self.ui.treeView)
        bar.setRange(0, 100)
        bar.setMinimumHeight(16)
        bar.setTextVisible(True)
        bar.setStyleSheet(
            """
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                background: #f0f0f0;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #3a7bd5,
                    stop: 1 #00d2ff
                );
            }
            """
        )
        if completed:
            bar.setValue(100)
            bar.setFormat("Completed")
        else:
            bar.setValue(0)
            bar.setFormat("%p%")
        return bar

    def _start_fetch_dialog(self, channel_id, yt_channel, channel_url=None,
                            finish_handler=None, limit=None, start_index=1):
        """Helper method to start FetchProgressDialog and connect finished
        signal."""
        self.fetch_in_progress = True
        self.fetch_error_message = None
        fetch_dialog = FetchProgressDialog(channel_id, yt_channel, channel_url,
                                           limit=limit, start_index=start_index,
                                           parent=self)

        if finish_handler:
            fetch_dialog.finished.connect(finish_handler)

        fetch_dialog.finished.connect(self.enable_get_vid_list_button)
        fetch_dialog.cancelled.connect(self.enable_get_vid_list_button)
        fetch_dialog.error.connect(self._handle_fetch_error)
        fetch_dialog.finished.connect(lambda _: self._cleanup_fetch_state())
        fetch_dialog.cancelled.connect(self._cleanup_fetch_state)

        fetch_dialog.exec()

    def _get_auth_options(self):
        """Return auth options for yt-dlp calls if configured."""
        if self.youtube_auth_manager and self.youtube_auth_manager.is_configured:
            return self.youtube_auth_manager.get_yt_dlp_options()
        return {}

    @Slot(str)
    def _handle_fetch_error(self, message):
        """Display a single fetch error dialog and re-enable the UI."""
        logger.error("Fetch error encountered: %s", message)
        raw_message = self.fetch_error_message or message
        display_message = re.sub(r'\x1B\[[0-9;]*[A-Za-z]', '', raw_message)
        dlg = CustomDialog("Fetch error", display_message, parent=self)
        dlg.exec()
        self.enable_get_vid_list_button()
        self._cleanup_fetch_state()

    def _cleanup_fetch_state(self):
        """Clear fetch state flags and re-enable controls when appropriate."""
        self.fetch_in_progress = False
        self.fetch_error_message = None
        if not self.active_download_threads:
            self._set_fetch_controls_enabled(True)

    @Slot()
    def show_vid_list(self):
        """Fetches and displays a single video, a playlist or a channel based
        on the input URL."""
        if self.node_notifier:
            self.node_notifier.maybe_prompt()
        self.window_resize_needed = True
        self.getVidListButton.setEnabled(False)
        channel_url = self.ui.chanUrlEdit.text()
        logger.info("Fetching video list for URL: %s", channel_url)
        yt_channel = self._prepare_yt_channel()

        if self._is_playlist_or_video_with_playlist(yt_channel, channel_url):
            logger.debug("Detected playlist URL")
            self.current_fetch_is_channel = False
            self.channel_fetch_context = None
            playlist_limit = self._get_playlist_fetch_limit()
            self._start_fetch_dialog("playlist", yt_channel, channel_url,
                                     self.handle_video_list,
                                     limit=playlist_limit)

        elif self._is_video(yt_channel, channel_url):
            fetch_type = "short" if yt_channel.is_short_video_url(
                channel_url) else None
            logger.debug("Detected single video URL (short=%s)", bool(fetch_type))
            self.current_fetch_is_channel = False
            self.channel_fetch_context = None
            self._start_fetch_dialog(fetch_type, yt_channel, channel_url,
                                     self.handle_single_video)
        else:
            # Treat remaining YouTube URLs as channels
            if "youtube.com" in channel_url or "youtu.be" in channel_url:
                logger.debug("Attempting to fetch channel data")
                self._handle_channel_fetch(yt_channel, channel_url)
            else:
                auth_opts = self._get_auth_options()
                if is_supported_media_url(channel_url, auth_opts):
                    logger.debug("URL supported by generic extractor; treating as single media")
                    self._start_fetch_dialog(None, yt_channel, channel_url,
                                             self.handle_single_video)
                else:
                    logger.warning("Unsupported URL submitted: %s", channel_url)
                    self.display_error_dialog(
                        "The URL is incorrect or unsupported."
                    )
                    self.enable_get_vid_list_button()

    def _prepare_yt_channel(self):
        """Prepares and returns a YTChannel instance."""
        yt_channel = YTChannel(main_window=self)
        logger.debug("YTChannel helper prepared")
        yt_channel.showError.connect(self._handle_channel_error)
        return yt_channel

    @Slot(str)
    def _handle_channel_error(self, message):
        """Handle errors emitted from YTChannel helper."""
        if self.fetch_in_progress:
            if not self.fetch_error_message:
                self.fetch_error_message = message
        else:
            self.display_error_dialog(message)

    def _get_channel_fetch_limit(self):
        """Return the configured channel fetch limit with a sane fallback."""
        limit = self.user_settings.get('channel_fetch_limit', DEFAULT_CHANNEL_FETCH_LIMIT)
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = DEFAULT_CHANNEL_FETCH_LIMIT
        if limit <= 0:
            limit = DEFAULT_CHANNEL_FETCH_LIMIT
        return limit

    def _get_playlist_fetch_limit(self):
        """Return the configured playlist fetch limit with a sane fallback."""
        limit = self.user_settings.get('playlist_fetch_limit', DEFAULT_PLAYLIST_FETCH_LIMIT)
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = DEFAULT_PLAYLIST_FETCH_LIMIT
        if limit <= 0:
            limit = DEFAULT_PLAYLIST_FETCH_LIMIT
        return limit

    def _is_playlist_or_video_with_playlist(self, yt_channel, url):
        """Checks if the URL is a playlist or a video with a playlist."""
        return yt_channel.is_video_with_playlist_url(url) or \
            yt_channel.is_playlist_url(url)

    def _is_video(self, yt_channel, url):
        """Checks if the URL is a single video or a short video."""
        return yt_channel.is_video_url(url) or \
            yt_channel.is_short_video_url(url)

    def _handle_channel_fetch(self, yt_channel, channel_url):
        """Handles the logic for fetching a channel."""
        try:
            channel_id = yt_channel.get_channel_id(channel_url)
            limit = self._get_channel_fetch_limit()
            logger.debug("Resolved channel ID: %s (limit=%s)", channel_id, limit)
            self.current_fetch_is_channel = True
            self.channel_fetch_context = {
                "channel_id": channel_id,
                "channel_url": channel_url,
            }
            self._start_fetch_dialog(channel_id, yt_channel,
                                     finish_handler=self.handle_video_list,
                                     limit=limit,
                                     start_index=1)
        except (ValueError, error.URLError) as exc:
            logger.warning("Failed to resolve channel from URL %s: %s", channel_url, exc)
            self.display_error_dialog("Please check your URL")
            self.enable_get_vid_list_button()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected error fetching channel for %s: %s", channel_url, exc)
            self.display_error_dialog(
                "Failed to fetch channel details. Please try another URL."
            )
            self.enable_get_vid_list_button()

    @Slot(list)
    def handle_video_list(self, video_list):
        """
        Handles a list of video data by storing it in an attribute and 
        populating the UI with the data.

        Args:
            video_list (list): A list of video details, each containing title 
                            and link information.
        """
        self.yt_chan_vids_titles_links = video_list
        logger.info("Loaded %d videos into list", len(video_list))
        if self.current_fetch_is_channel and self.channel_fetch_context:
            self.channel_fetch_context["fetched"] = len(self.yt_chan_vids_titles_links)
        else:
            self.channel_fetch_context = None
        self.populate_window_list()
        self._update_load_next_button_state()

    @Slot(list)
    def handle_single_video(self, video_list):
        """
        Processes a single video entry by storing it and updating the UI.

        Args:
            video_list (list): A list containing the details of a single video.
        """
        self.yt_chan_vids_titles_links = video_list
        logger.info("Loaded single video into list")
        self.populate_window_list()
        self.channel_fetch_context = None
        self._update_load_next_button_state()

    @Slot()
    def load_next_batch(self):
        """Load the next batch of channel videos using the configured limit."""
        if self.fetch_in_progress:
            return
        if not self.channel_fetch_context or not self.channel_fetch_context.get("channel_id"):
            return
        limit = self._get_channel_fetch_limit()
        channel_id = self.channel_fetch_context["channel_id"]
        start_index = len(self.yt_chan_vids_titles_links) + 1
        yt_channel = self._prepare_yt_channel()
        logger.info("Fetching next %s items for channel %s starting at %s", limit, channel_id, start_index)
        self.current_fetch_is_channel = True
        self._start_fetch_dialog(channel_id, yt_channel, finish_handler=self.handle_next_batch,
                                 limit=limit, start_index=start_index)

    @Slot(list)
    def handle_next_batch(self, video_list):
        """Append newly fetched channel videos to the current list and UI."""
        if not video_list:
            QMessageBox.information(
                self,
                "No more videos",
                "No additional videos were fetched for this channel.",
            )
            return
        start_index = len(self.yt_chan_vids_titles_links)
        self.yt_chan_vids_titles_links.extend(video_list)
        for entry in video_list:
            self._add_video_item_to_list(entry)
        self._finalize_list_view()
        self.update_selection_size_summary()
        self._maybe_prompt_on_js_warning()
        if self.channel_fetch_context:
            self.channel_fetch_context["fetched"] = len(self.yt_chan_vids_titles_links)
        logger.info("Appended %d videos (total now %d)", len(video_list), len(self.yt_chan_vids_titles_links))
        self._update_load_next_button_state()

    @Slot()
    def enable_get_vid_list_button(self):
        """
        Enables the 'Get Video List' button, allowing the user to initiate 
        another video-fetching process.
        """
        if self.active_download_threads:
            return
        if self.fetch_in_progress:
            return
        self._set_fetch_controls_enabled(True)

    @Slot()
    def dl_vids(self):
        """
        Initiates the download process for all checked videos in the list.
        Clears existing download indexes, identifies checked items, and
        starts a download thread for each selected video.
        """
        self.vid_dl_indexes.clear()
        for row in range(self.model.rowCount()):
            item = self.model.item(row, 0)
            if item.checkState() == Qt.CheckState.Checked:
                # Skip already completed downloads
                title = self.model.item(row, 1).text()
                download_path = self.dl_path_correspondences.get(title)
                if download_path and DownloadThread.is_download_complete(download_path):
                    item.setCheckState(Qt.CheckState.Unchecked)
                    progress_bar = self.progress_widgets.get(row)
                    if progress_bar:
                        progress_bar.setRange(0, 100)
                        progress_bar.setValue(100)
                        progress_bar.setFormat("Completed")
                    progress_item = self.model.item(row, ColumnIndexes.PROGRESS)
                    if progress_item:
                        progress_item.setData(100.0, Qt.ItemDataRole.UserRole)
                        progress_item.setData("Completed", Qt.ItemDataRole.DisplayRole)
                    continue
                self.vid_dl_indexes.append(row)
        if not self.vid_dl_indexes:
            QMessageBox.information(
                self,
                "No videos selected",
                "Please select at least one video before starting downloads."
            )
            return
        self._set_fetch_controls_enabled(False)
        self.downloadSelectedVidsButton.setEnabled(False)
        for index in self.vid_dl_indexes:
            progress_bar = self.progress_widgets.get(index)
            if progress_bar is None:
                progress_bar = self._create_progress_bar()
                progress_index = self.model.index(index, ColumnIndexes.PROGRESS)
                self.ui.treeView.setIndexWidget(progress_index, progress_bar)
                self.progress_widgets[index] = progress_bar
            progress_bar.setRange(0, 0)
            progress_bar.setFormat("Preparing...")
            link = self.model.item(index, ColumnIndexes.LINK).text()
            title = self.model.item(index, 1).text()
            dl_thread = DownloadThread(link, index, title, self)
            dl_thread.downloadCompleteSignal.connect(self.on_download_complete)
            dl_thread.downloadProgressSignal.connect(self.update_progress)
            dl_thread.finished.connect(lambda idx=index: self.cleanup_download_thread(idx))
            self.dl_threads.append(dl_thread)
            self.active_download_threads[index] = dl_thread
            try:
                dl_thread.start()
            except RuntimeError as e:
                if len(self.dl_threads) == 0:
                    self.display_error_dialog(
                        "Trying to restart threads after a crash..."
                    )
                    self.dl_vids()
                    break
                raise RuntimeError(
                    "Failed to start download thread. Please check your "
                    "system resources.",
                    e
                )
        self.update_cancel_button_state()
                

    @Slot(dict)
    def update_progress(self, progress_data):
        """
        Updates the UI to reflect the download progress of a video.

        Args:
            progress_data (dict): A dictionary containing the index of the video 
                                and its current progress percentage.
        """
        file_index = int(progress_data["index"])
        progress_bar = self.progress_widgets.get(file_index)
        speed_item = self.model.item(file_index, ColumnIndexes.SPEED)
        if speed_item and "speed" in progress_data:
            speed_item.setData(progress_data["speed"], Qt.ItemDataRole.DisplayRole)
        if "progress" in progress_data:
            progress = float(progress_data["progress"])
            avg_speed = None
            raw_speed = progress_data.get("speed_bps")
            if raw_speed:
                history = self.speed_history.setdefault(file_index, deque(maxlen=20))
                history.append(float(raw_speed))
                avg_speed = sum(history) / len(history)
            if progress_bar:
                progress_bar.setRange(0, 100)
                progress_bar.setValue(int(progress))
                progress_bar.setFormat("%p%")
            progress_item = self.model.item(file_index, ColumnIndexes.PROGRESS)
            if progress_item:
                progress_item.setData(progress, Qt.ItemDataRole.UserRole)
                progress_item.setData(None, Qt.ItemDataRole.DisplayRole)
            self.ui.treeView.viewport().update()
            self.update_selection_size_summary()
        elif "error" in progress_data:
            error_message = progress_data["error"]
            progress_value = float(progress_data.get("progress", 0.0))
            progress_item = self.model.item(file_index, ColumnIndexes.PROGRESS)

            if error_message == "Cancelled":
                if progress_bar:
                    progress_bar.setRange(0, 100)
                    progress_bar.setValue(int(progress_value))
                    progress_bar.setFormat(f"Part-downloaded – {progress_value:.1f}%")
                if progress_item:
                    progress_item.setData(progress_value, Qt.ItemDataRole.UserRole)
                    progress_item.setData(f"Part-downloaded – {progress_value:.1f}%",
                                          Qt.ItemDataRole.DisplayRole)
                if speed_item:
                    speed_item.setData(progress_data.get("speed", "—"), Qt.ItemDataRole.DisplayRole)
            else:
                if progress_bar:
                    progress_bar.setRange(0, 100)
                    progress_bar.setValue(0)
                    progress_bar.setFormat(error_message)
                if progress_item:
                    progress_item.setData(None, Qt.ItemDataRole.UserRole)
                    progress_item.setData(error_message, Qt.ItemDataRole.DisplayRole)
                if speed_item:
                    speed_item.setData("—", Qt.ItemDataRole.DisplayRole)
                self.handle_download_error(progress_data)

            self.cleanup_download_thread(file_index)
            self.ui.treeView.viewport().update()

    def exit(self):
        """
        Exits the application by closing the PyQt main window.
        """
        QApplication.quit()
