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
                             QLabel, QWidget, QSizePolicy)
from PyQt6.QtGui import QFont
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtGui import QStandardItem, QPixmap
from PyQt6.QtCore import QUrl, QSize
from PyQt6.QtGui import QDesktopServices
import yt_dlp

from ..assets import resources_rc    # Qt resources  # noqa: F401  # pylint: disable=unused-import
from ..ui.ui_form import Ui_MainWindow
from ..ui.ui_about import Ui_aboutDialog
from .settings_manager import SettingsManager
from .enums import ColumnIndexes
from ..config.constants import (
    settings_map,
    DEFAULT_CHANNEL_FETCH_LIMIT,
    DEFAULT_PLAYLIST_FETCH_LIMIT,
    CHANNEL_FETCH_BATCH_SIZE,
    SUPPORT_URL,
)
from .download_thread import DownloadThread
from .custom_dialog import CustomDialog
from .youtube_cookies_dialog import YoutubeCookiesDialog
from .fetch_progress_dialog import FetchProgressDialog
from .login_prompt_dialog import LoginPromptDialog
from .checkbox_delegate import CheckBoxDelegate
from .YTChannel import YTChannel
from .videoitem import VideoItem, THUMBNAIL_URL_ROLE
from .thumbnail_loader import ThumbnailLoader
from .settings import SettingsDialog
from .youtube_auth_manager import YoutubeAuthManager
from .validators import is_supported_media_url
from .quiet_ydl_logger import QuietYDLLogger
from .utils import filter_formats
from .js_warning_tracker import js_warning_tracker
from .node_runtime_notifier import NodeRuntimeNotifier
from .support_prompt import (
    DEFAULT_SUPPORT_PROMPT_INITIAL_THRESHOLD,
    SupportPrompt,
)
from .logger import get_logger
from .updater import Updater
from .update_status import UpdateStatus
from .selection_size_worker import SelectionSizeWorker
from .auto_update_worker import AutoUpdateWorker


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
        self.thumbnail_loader: Optional[ThumbnailLoader] = None
        self.thumbnail_targets: Dict[int, str] = {}
        self.prefetched_thumbnails: Dict[int, QPixmap] = {}
        self._size_recalc_indicator_needed = False
        self._size_recalc_worker: Optional[SelectionSizeWorker] = None
        self._size_recalc_watchdog: Optional[QtCore.QTimer] = None
        self._size_recalc_worker_thread: Optional[QtCore.QThread] = None
        self._size_recalc_generation: int = 0
        self.node_notifier: Optional[NodeRuntimeNotifier] = None
        self.support_prompt: Optional[SupportPrompt] = None
        self._auto_update_thread: Optional[QtCore.QThread] = None
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
        self.size_estimate_toggle: Optional[QCheckBox] = None
        self.recalc_status_widget: QWidget = self._build_recalc_status_widget()
        self.ui.statusbar.addPermanentWidget(self.recalc_status_widget)
        self.ui.statusbar.addPermanentWidget(self.selection_summary_label)

        self.setup_about_dialog()
        self.init_download_structs()
        self.connect_signals()
        self.initialize_settings()
        self._init_node_notifier()
        self._init_support_prompt()
        self.setup_select_all_checkbox()
        self.initialize_youtube_login()
        self._schedule_auto_update_check()
        self._init_thumbnail_loader()
        QtCore.QCoreApplication.instance().aboutToQuit.connect(self._shutdown_background_workers)

    def init_styles(self):
        """Applies global styles and element-specific styles for the main
        window."""
        self.setStyleSheet("""
            * { font-family: "Arial"; font-size: 12pt; }
            QLabel {
                font-family: Arial;
                font-size: 14pt;
            }
            QPushButton#getVidListButton,
            QPushButton#getVidListAddButton {
                font-size: 9pt;
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
        self.getVidListAddButton: QPushButton = self.ui.getVidListAddButton
        self._setup_update_action()
        self.setup_buttons()
        self.setup_tree_view_delegate()
        self.ui.actionDonate.triggered.connect(self.open_donate_url)

    def open_donate_url(self):
        """Opens the donation URL in the default web browser."""
        logger.info("Opening donation page in browser")
        QDesktopServices.openUrl(QUrl(SUPPORT_URL))

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

    def setup_button(self, button, callback, font_size=12):
        """Configures a button with the specified callback and font.

        Args:
            button (QPushButton): Button widget to set up.
            callback (function): Function to connect to button's clicked
            signal.
            font_size (int): Font size to apply.
        """
        button.clicked.connect(callback)
        font = QFont("Arial", font_size)
        font.setBold(True)
        button.setFont(font)

    def setup_buttons(self):
        """Sets up specific buttons used in the main window."""
        self.setup_button(self.downloadSelectedVidsButton, self.dl_vids)
        self.setup_button(self.getVidListButton, self.show_vid_list, font_size=9)
        self.setup_button(self.getVidListAddButton, self.show_vid_list_add, font_size=9)

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
        self.user_settings.setdefault('support_prompt_next_at', DEFAULT_SUPPORT_PROMPT_INITIAL_THRESHOLD)
        self.user_settings.setdefault('channel_fetch_limit', DEFAULT_CHANNEL_FETCH_LIMIT)
        self.user_settings.setdefault('playlist_fetch_limit', DEFAULT_PLAYLIST_FETCH_LIMIT)
        self.user_settings.setdefault('channel_fetch_batch_size', CHANNEL_FETCH_BATCH_SIZE)
        self.user_settings.setdefault('show_thumbnails', True)
        self.user_settings.setdefault('enable_size_estimation', True)

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
        self.ui.verticalLayout.addSpacing(12)
        self.size_estimate_toggle = QCheckBox("Calculate estimated sizes", self)
        self.size_estimate_toggle.setVisible(False)
        self.size_estimate_toggle.setChecked(self.user_settings.get('enable_size_estimation', True))
        self.size_estimate_toggle.toggled.connect(self.on_size_estimation_toggled)
        self.ui.verticalLayout.addWidget(self.size_estimate_toggle)
        self.show_thumbnails_toggle = QCheckBox("Show thumbnails", self)
        self.show_thumbnails_toggle.setVisible(False)
        self.show_thumbnails_toggle.setChecked(self.user_settings.get('show_thumbnails', True))
        self.show_thumbnails_toggle.toggled.connect(self.on_show_thumbnails_toggled)
        self.ui.verticalLayout.addWidget(self.show_thumbnails_toggle)
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
        next_at = self.user_settings.get('support_prompt_next_at', DEFAULT_SUPPORT_PROMPT_INITIAL_THRESHOLD)
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
        if new_value and self._is_size_estimation_enabled():
            if self._size_recalc_worker_thread and self._size_recalc_worker_thread.isRunning():
                # Restart estimation for the new selection set.
                self._cancel_selection_recalc()
            self._size_recalc_indicator_needed = True
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
        self.thumbnail_targets.clear()
        self.prefetched_thumbnails.clear()

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
        if self.size_estimate_toggle:
            self.size_estimate_toggle.setVisible(False)
        if hasattr(self, "show_thumbnails_toggle") and self.show_thumbnails_toggle:
            self.show_thumbnails_toggle.setVisible(False)

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
        self.getVidListAddButton.setEnabled(fetch_button_enabled)
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
        fetch buttons.

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
        if self._is_thumbnail_enabled() and self.thumbnail_loader:
            thumb_items = []
            for idx, entry in enumerate(self.yt_chan_vids_titles_links):
                url = self._thumbnail_url_for_entry(entry)
                thumb_items.append((idx, url))
            self.prefetched_thumbnails = self.thumbnail_loader.preload_bulk(thumb_items)
        else:
            self.prefetched_thumbnails = {}
        for entry in self.yt_chan_vids_titles_links:
            self._add_video_item_to_list(entry)

        self._finalize_list_view()
        self.update_selection_size_summary()
        self._maybe_prompt_on_js_warning()
        self._maybe_prompt_on_js_warning()
        # Ensure thumbnails queue after the view is built when enabled.
        if self._is_thumbnail_enabled():
            QtCore.QTimer.singleShot(0, self._warm_thumbnails_for_current_rows)

    def _add_video_item_to_list(self, video_entry):
        """
        Adds a single video entry to the list view by creating a VideoItem,
        setting its properties, and appending it to the root item.
        """
        title = video_entry.get('title', 'Unknown Title')
        link = video_entry.get('url', '')
        duration = video_entry.get('duration')
        download_path = self._get_video_filepath(title)
        thumbnail_url = self._thumbnail_url_for_entry(video_entry)
        video_item = VideoItem(title, link, duration, download_path, thumbnail_url=thumbnail_url)
        self.root_item.appendRow(video_item.get_qt_item())
        self.dl_path_correspondences[title] = download_path
        row_index = self.model.rowCount() - 1
        self._apply_row_height_hint(row_index)
        progress_index = self.model.index(row_index, ColumnIndexes.PROGRESS)
        completed = DownloadThread.is_download_complete(download_path)
        progress_bar = self._create_progress_bar(completed=completed)
        self.ui.treeView.setIndexWidget(progress_index, progress_bar)
        self.progress_widgets[row_index] = progress_bar
        preloaded = self.prefetched_thumbnails.get(row_index)
        if preloaded:
            title_item = self.model.item(row_index, ColumnIndexes.TITLE)
            if title_item:
                title_item.setData(preloaded, Qt.ItemDataRole.DecorationRole)
        else:
            self._maybe_queue_thumbnail(row_index)

    def _get_video_filepath(self, title):
        """Generates the file path for a given video title based on user
        settings."""
        filename = DownloadThread.sanitize_filename(title)
        download_dir = self.user_settings.get('download_directory', './')
        return os.path.join(download_dir, filename)

    def _thumbnail_url_for_entry(self, video_entry: dict) -> Optional[str]:
        """Return a best-effort thumbnail URL for a video entry."""
        thumb = video_entry.get('thumbnail')
        if isinstance(thumb, str) and thumb:
            return thumb

        thumbs = video_entry.get('thumbnails')
        if isinstance(thumbs, list):
            for cand in thumbs:
                url = None
                if isinstance(cand, dict):
                    url = cand.get('url') or cand.get('thumb')
                elif isinstance(cand, str):
                    url = cand
                if url:
                    return url

        link = video_entry.get('url') or ""
        video_id = self._extract_youtube_id(link)
        if video_id:
            return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        return None

    def _update_icon_size(self):
        """Set icon size based on thumbnail toggle to avoid oversized rows."""
        if self._is_thumbnail_enabled():
            self.ui.treeView.setIconSize(QSize(96, 54))
        else:
            self.ui.treeView.setIconSize(QSize(0, 0))
        self.ui.treeView.scheduleDelayedItemsLayout()

    def _row_height_target(self) -> int:
        """Compute a target row height for current mode."""
        base = QFontMetrics(self.ui.treeView.font()).height() + 12
        if self._is_thumbnail_enabled():
            return max(base, self.ui.treeView.iconSize().height() + 8)
        return base

    def _apply_row_height_hint(self, row_index: int):
        """Set a size hint on row to encourage correct row height."""
        height = self._row_height_target()
        # Apply to the title item; Qt will use the largest sizeHint in the row.
        title_item = self.model.item(row_index, ColumnIndexes.TITLE)
        if title_item:
            title_item.setSizeHint(QSize(0, height))
        checkbox_item = self.model.item(row_index, ColumnIndexes.DOWNLOAD)
        if checkbox_item:
            checkbox_item.setSizeHint(QSize(0, height))

    def _refresh_row_heights(self):
        """Trigger a relayout after icon size changes."""
        target = self._row_height_target()
        for row in range(self.model.rowCount()):
            title_item = self.model.item(row, ColumnIndexes.TITLE)
            if title_item:
                title_item.setSizeHint(QSize(0, target))
            checkbox_item = self.model.item(row, ColumnIndexes.DOWNLOAD)
            if checkbox_item:
                checkbox_item.setSizeHint(QSize(0, target))
        self.ui.treeView.doItemsLayout()
        self.ui.treeView.viewport().update()

    def _init_thumbnail_loader(self):
        """Set up the thumbnail loader helper."""
        self.thumbnail_loader = ThumbnailLoader(self)
        self.thumbnail_loader.thumbnail_ready.connect(self._on_thumbnail_ready)
        self.thumbnail_loader.thumbnail_failed.connect(self._on_thumbnail_failed)
        # Honor the saved preference if toggle not yet created.
        if hasattr(self, "show_thumbnails_toggle") and self.show_thumbnails_toggle:
            self.show_thumbnails_toggle.setChecked(self.user_settings.get('show_thumbnails', True))

    def _is_thumbnail_enabled(self) -> bool:
        """Return whether thumbnail display is enabled."""
        if not self.user_settings.get('show_thumbnails', True):
            return False
        if self.show_thumbnails_toggle:
            return self.show_thumbnails_toggle.isChecked()
        # Fallback to enabled when toggle not yet constructed
        return True

    def _clear_all_thumbnails(self):
        """Remove decoration role thumbnails from current rows."""
        for row in range(self.model.rowCount()):
            item = self.model.item(row, ColumnIndexes.TITLE)
            if item:
                item.setData(None, Qt.ItemDataRole.DecorationRole)
        self._update_icon_size()
        self.ui.treeView.doItemsLayout()

    def _warm_thumbnails_for_current_rows(self, force: bool = False):
        """Queue thumbnails for all current rows (lazy)."""
        rows = range(self.model.rowCount())
        self._warm_thumbnails_for_rows(rows, force=force)

    def _warm_thumbnails_for_rows(self, rows, force: bool = False):
        """Queue thumbnails for the specified rows."""
        if not force and not self._is_thumbnail_enabled():
            return
        for row in rows:
            self._maybe_queue_thumbnail(row, force=force)

    def _maybe_queue_thumbnail(self, row_index: int, force: bool = False):
        """Request thumbnail fetch for a row if enabled and url available."""
        if not force and not self._is_thumbnail_enabled():
            logger.info("Thumbnail queue skipped (disabled): row=%s", row_index)
            return
        title_item = self.model.item(row_index, ColumnIndexes.TITLE)
        if not title_item:
            logger.info("Thumbnail queue skipped (no title item): row=%s", row_index)
            return
        url = title_item.data(THUMBNAIL_URL_ROLE)
        if not url:
            logger.info("Thumbnail queue skipped (no url): row=%s", row_index)
            return
        self.thumbnail_targets[row_index] = url
        if self.thumbnail_loader:
            logger.info("Queueing thumbnail fetch: row=%s url=%s", row_index, url)
            self.thumbnail_loader.fetch(row_index, url)
        else:
            logger.info("Thumbnail loader not initialized; skipping fetch for row=%s", row_index)

    @Slot(int, QtGui.QPixmap)
    def _on_thumbnail_ready(self, row_index: int, pixmap: QPixmap):
        """Apply thumbnail when fetch completes."""
        if not self._is_thumbnail_enabled():
            return
        title_item = self.model.item(row_index, ColumnIndexes.TITLE)
        if not title_item:
            return
        current_url = title_item.data(THUMBNAIL_URL_ROLE)
        expected_url = self.thumbnail_targets.get(row_index)
        if expected_url and current_url == expected_url:
            logger.info("Thumbnail ready: row=%s url=%s", row_index, expected_url)
            title_item.setData(pixmap, Qt.ItemDataRole.DecorationRole)
            try:
                idx = self.model.index(row_index, ColumnIndexes.TITLE)
                self.ui.treeView.update(idx)
            except Exception:  # noqa: BLE001
                pass
        else:
            logger.info("Thumbnail ready discarded (mismatch): row=%s current_url=%s expected=%s", row_index, current_url, expected_url)

    @Slot(int)
    def _on_thumbnail_failed(self, row_index: int):
        """Handle thumbnail failure silently."""
        url = self.thumbnail_targets.get(row_index)
        logger.info("Thumbnail fetch failed: row=%s url=%s", row_index, url)

    def _shutdown_background_workers(self):
        """Ensure background threads/executors are stopped before exit."""
        if self._size_recalc_worker_thread and self._size_recalc_worker_thread.isRunning():
            self._size_recalc_worker_thread.quit()
            self._size_recalc_worker_thread.wait(1500)
        self._size_recalc_worker_thread = None
        self._size_recalc_worker = None

        if self._auto_update_thread and self._auto_update_thread.isRunning():
            self._auto_update_thread.quit()
            self._auto_update_thread.wait(1500)
        self._auto_update_thread = None

        if self.thumbnail_loader:
            try:
                self.thumbnail_loader.shutdown()
            except Exception:  # noqa: BLE001
                pass

    @staticmethod
    def _extract_youtube_id(link: str) -> Optional[str]:
        """Extract a YouTube video ID from common URL shapes."""
        if not link:
            return None
        if "youtu.be/" in link:
            parts = link.split("youtu.be/")
            if len(parts) > 1:
                vid = parts[1].split("?")[0].split("&")[0]
                return vid or None
        if "watch?v=" in link:
            parts = link.split("watch?v=")
            if len(parts) > 1:
                vid = parts[1].split("&")[0]
                return vid or None
        if "/shorts/" in link:
            parts = link.split("/shorts/")
            if len(parts) > 1:
                vid = parts[1].split("?")[0].split("&")[0]
                return vid or None
        return None

    def _finalize_list_view(self):
        """Adjusts and displays the list view once all items are populated."""
        self.ui.treeView.expandAll()
        self.ui.treeView.show()
        self._configure_list_columns()
        self._apply_tree_view_styles()
        if self.model.rowCount() > 0:
            self.select_all_checkbox.setVisible(True)
            if self.size_estimate_toggle:
                self.size_estimate_toggle.setVisible(True)
            if self.show_thumbnails_toggle:
                self.show_thumbnails_toggle.setVisible(True)
            if self._is_thumbnail_enabled():
                self._warm_thumbnails_for_current_rows()
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
        self._update_icon_size()
        self._refresh_row_heights()
        self.ui.treeView.setStyleSheet("""
        QTreeView::indicator:disabled {
            background-color: gray;
        }
        """)

    def update_selection_size_summary(self):
        """Calculate and display estimated download sizes for checked rows."""
        if self._size_recalc_worker_thread and not self._size_recalc_worker_thread.isRunning():
            self._cleanup_async_thread(self._size_recalc_worker_thread)

        if self.model.rowCount() == 0:
            self.selection_summary_label.setText("")
            return

        selected_rows = self._checked_row_indexes()
        if not selected_rows:
            self.selection_summary_label.setText("No items selected")
            return

        if not self._is_size_estimation_enabled():
            summary = f"Selected: {len(selected_rows)} | Size estimation disabled"
            self.selection_summary_label.setText(summary)
            self._hide_recalc_status()
            self._stop_recalc_watchdog()
            return

        if self._size_recalc_indicator_needed and selected_rows:
            if self._start_async_selection_summary(selected_rows):
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

        for idx, row in enumerate(selected_rows):
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

    def _start_async_selection_summary(self, selected_rows) -> bool:
        """Kick off selection size recalculation in a background thread."""
        if not self._is_size_estimation_enabled():
            return False
        if self._size_recalc_worker_thread and self._size_recalc_worker_thread.isRunning():
            return True

        rows_data = []
        for row in selected_rows:
            link_item = self.model.item(row, ColumnIndexes.LINK)
            if link_item is None:
                continue
            duration_seconds = self._item_user_role(self.model.item(row, ColumnIndexes.DURATION))
            progress_val = self._item_user_role(self.model.item(row, ColumnIndexes.PROGRESS))
            rows_data.append({
                "row": row,
                "link": link_item.text(),
                "duration": duration_seconds,
                "progress": progress_val,
            })

        if not rows_data:
            self._size_recalc_indicator_needed = False
            return False

        self._show_recalc_status()
        thread = QtCore.QThread(self)
        self._size_recalc_generation += 1
        generation = self._size_recalc_generation
        worker = SelectionSizeWorker(
            rows_data,
            lambda link, dur: self._get_or_estimate_size(link, dur, cache_row_lookup=False),
            self._remaining_bytes,
            generation,
        )
        self._size_recalc_worker = worker
        worker.moveToThread(thread)
        worker.finished.connect(self._on_async_selection_summary_finished)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(thread.quit)
        thread.started.connect(worker.run)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._cleanup_async_thread(thread))
        self._size_recalc_worker_thread = thread
        thread.start()
        per_item_ms = 2000
        timeout_ms = max(5000, len(rows_data) * per_item_ms)
        self._start_recalc_watchdog(timeout_ms)
        return True

    def _cancel_selection_recalc(self):
        """User-requested cancellation of size recalculation."""
        self._size_recalc_generation += 1
        if self._size_recalc_worker:
            self._size_recalc_worker.request_size_eta_cancellation()
        if self._size_recalc_worker_thread and self._size_recalc_worker_thread.isRunning():
            self._size_recalc_worker_thread = None
        self._size_recalc_worker = None
        self._size_recalc_indicator_needed = False
        self._stop_recalc_watchdog()
        self._hide_recalc_status()

    def _is_size_estimation_enabled(self) -> bool:
        """Return whether the user enabled size/ETA estimation."""
        try:
            return bool(self.size_estimate_toggle.isChecked())
        except Exception:  # noqa: BLE001
            return False

    def on_size_estimation_toggled(self, checked: bool):
        """Handle user toggling size estimation on/off."""
        if not checked:
            self._cancel_selection_recalc()
        else:
            self._size_recalc_indicator_needed = True
        self.user_settings['enable_size_estimation'] = checked
        try:
            self.settings_manager.save_settings_to_file(self.user_settings)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to persist size estimation toggle: %s", exc)
        self.update_selection_size_summary()

    def on_show_thumbnails_toggled(self, checked: bool):
        """Handle user toggle for showing thumbnails in the list."""
        self.user_settings['show_thumbnails'] = checked
        try:
            self.settings_manager.save_settings_to_file(self.user_settings)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to persist show_thumbnails toggle: %s", exc)

        if not checked:
            self._clear_all_thumbnails()
        else:
            self.thumbnail_targets.clear()
            QtCore.QTimer.singleShot(0, lambda: self._warm_thumbnails_for_current_rows(force=True))
        self._update_icon_size()
        self._refresh_row_heights()

    def _schedule_auto_update_check(self):
        """Start an automatic update check shortly after launch."""
        QtCore.QTimer.singleShot(1200, self._start_auto_update_check)

    def _start_auto_update_check(self):
        """Run the update check in the background; notify only on availability."""
        if self._auto_update_thread:
            return
        thread = QtCore.QThread(self)
        worker = AutoUpdateWorker(self.updater)
        worker.moveToThread(thread)
        worker.finished.connect(self._handle_auto_update_result)
        worker.finished.connect(worker.deleteLater)
        thread.started.connect(worker.run)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: setattr(self, "_auto_update_thread", None))
        self._auto_update_thread = thread
        thread.start()

    @Slot(object)
    def _handle_auto_update_result(self, result):
        """Show update notice only when a newer release is available."""
        if not result or result.status != UpdateStatus.AVAILABLE:
            return
        try:
            title, message = self.updater._build_dialog_content(result)
            dialog = CustomDialog(title, message, parent=self)
            dialog.exec()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to display update dialog: %s", exc)

    @Slot(object, object, bool, dict, int, int, bool)
    def _on_async_selection_summary_finished(self, total_estimated, total_remaining, has_unknown, per_row_estimates, selected_count, generation, cancelled):
        """Handle completion of background selection size calculation."""
        if generation != self._size_recalc_generation:
            logger.debug("Ignoring stale selection size result (generation %s != %s)", generation, self._size_recalc_generation)
            return
        if cancelled:
            self._size_recalc_indicator_needed = False
            self._stop_recalc_watchdog()
            self._hide_recalc_status()
            return
        if per_row_estimates:
            self.estimated_download_sizes.update(per_row_estimates)

        summary = self._format_selection_summary(selected_count, total_estimated, total_remaining, has_unknown)
        self.selection_summary_label.setText(summary)
        self._size_recalc_indicator_needed = False
        self._stop_recalc_watchdog()
        self._hide_recalc_status()

    def _cleanup_async_thread(self, thread: QtCore.QThread):
        """Reset thread pointer when recalculation worker finishes."""
        if self._size_recalc_worker_thread is thread:
            self._size_recalc_worker_thread = None
            self._size_recalc_worker = None
        self._stop_recalc_watchdog()
        if self.recalc_status_widget.isVisible() and not self._size_recalc_indicator_needed:
            self._hide_recalc_status()

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

    def _get_or_estimate_size(self, link: str, duration_seconds: Optional[int], cache_row_lookup: bool = True) -> Optional[int]:
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
        if estimate and cache_row_lookup:
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
        base_audio = self._audio_only_formats(formats)
        audio_formats = self._filter_audio_by_extension(base_audio, preferred_ext) or base_audio
        if not audio_formats:
            audio_formats = self._fallback_audio_formats(formats)
        if not audio_formats:
            return None

        return self._pick_best_audio_by_bitrate(audio_formats, preferred_quality)

    def _audio_only_formats(self, formats):
        return [f for f in formats if f.get('vcodec') == 'none' and f.get('url')]

    def _fallback_audio_formats(self, formats):
        return [f for f in formats if f.get('acodec') not in (None, 'none') and f.get('url')]

    def _filter_audio_by_extension(self, audio_formats, preferred_ext: Optional[str]):
        if preferred_ext in (None, 'Any'):
            return audio_formats
        return [
            f for f in audio_formats
            if f.get('ext') == preferred_ext or preferred_ext in (f.get('acodec') or '')
        ]

    def _pick_best_audio_by_bitrate(self, audio_formats, preferred_quality: Optional[str]):
        target_bitrate = self._parse_bitrate_kbps(preferred_quality)
        bitrate = lambda f: self._get_audio_bitrate(f) or 0  # noqa: E731
        if target_bitrate:
            sorted_audio = sorted(
                audio_formats,
                key=lambda f: (abs(bitrate(f) - target_bitrate), -bitrate(f)),
            )
        else:
            sorted_audio = sorted(audio_formats, key=lambda f: -bitrate(f))
        return sorted_audio[0] if sorted_audio else None

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
        signature_was_set = self._settings_signature is not None
        if new_sig != self._settings_signature:
            self._settings_signature = new_sig
            self.size_estimate_cache.clear()
            self.format_info_cache.clear()
            if signature_was_set:
                self._size_recalc_indicator_needed = True

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

    @staticmethod
    def _indeterminate_progress_stylesheet() -> str:
        """Style indeterminate bars to match fetch progress visuals."""
        return """
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #3a7bd5,
                    stop: 1 #00d2ff
                );
                width: 20px;
            }
        """

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

    def _build_recalc_status_widget(self) -> QWidget:
        """Build the status bar widget used during size recalculations."""
        widget = QWidget(self)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.recalc_status_label = QLabel("Calculating download size estimates...", widget)
        self.recalc_status_bar = QProgressBar(widget)
        self.recalc_status_bar.setRange(0, 0)
        self.recalc_status_bar.setTextVisible(False)
        self.recalc_status_bar.setMinimumWidth(240)
        self.recalc_status_bar.setSizePolicy(QSizePolicy.Policy.Expanding,
                                             QSizePolicy.Policy.Preferred)
        self.recalc_status_bar.setStyleSheet(self._indeterminate_progress_stylesheet())

        self.recalc_cancel_button = QPushButton("Cancel", widget)
        self.recalc_cancel_button.setObjectName("recalcCancelButton")
        self.recalc_cancel_button.setFixedHeight(22)
        self.recalc_cancel_button.clicked.connect(self._cancel_selection_recalc)

        layout.addWidget(self.recalc_status_label)
        layout.addWidget(self.recalc_status_bar, 1)
        layout.addWidget(self.recalc_cancel_button)
        widget.setVisible(False)
        return widget

    def _show_recalc_status(self):
        """Show an indeterminate bar while re-estimating selection sizes."""
        if hasattr(self, "recalc_status_widget"):
            self.recalc_status_widget.setVisible(True)
            self.selection_summary_label.setVisible(False)
            QApplication.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents)

    def _hide_recalc_status(self):
        """Hide the recalculation indicator and restore the selection summary."""
        if hasattr(self, "recalc_status_widget"):
            self.recalc_status_widget.setVisible(False)
            self.selection_summary_label.setVisible(True)

    def _start_recalc_watchdog(self, timeout_ms: int):
        """Start a watchdog timer to hide the spinner if work stalls."""
        self._stop_recalc_watchdog()
        timer = QtCore.QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(timeout_ms)
        timer.timeout.connect(self._handle_recalc_timeout)
        timer.start()
        self._size_recalc_watchdog = timer

    def _stop_recalc_watchdog(self):
        """Stop and clear the recalculation watchdog timer."""
        if self._size_recalc_watchdog:
            self._size_recalc_watchdog.stop()
            self._size_recalc_watchdog.deleteLater()
            self._size_recalc_watchdog = None

    def _handle_recalc_timeout(self):
        """Hide the recalculation indicator if the worker runs too long."""
        if self._size_recalc_worker_thread and self._size_recalc_worker_thread.isRunning():
            logger.warning("Selection size recalculation exceeded timeout; hiding indicator.")
            # Allow a new recalculation to start even if the old worker lingers.
            if self._size_recalc_worker:
                self._size_recalc_worker.request_size_eta_cancellation()
            self._size_recalc_worker_thread = None
            self._size_recalc_worker = None
            self._size_recalc_generation += 1
        self._size_recalc_indicator_needed = False
        self._hide_recalc_status()
        self._stop_recalc_watchdog()

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
        self._show_vid_list_internal(append=False)

    @Slot()
    def show_vid_list_add(self):
        """Fetches and appends videos to the existing list based on the URL."""
        self._show_vid_list_internal(append=True)

    def _show_vid_list_internal(self, append: bool):
        """Shared fetch handler for replace and append modes."""
        if self.node_notifier:
            self.node_notifier.maybe_prompt()
        self.window_resize_needed = True
        self._set_fetch_controls_enabled(False)
        channel_url = self.ui.chanUrlEdit.text()
        logger.info("Fetching video list for URL: %s (append=%s)", channel_url, append)
        yt_channel = self._prepare_yt_channel()

        if self._is_playlist_or_video_with_playlist(yt_channel, channel_url):
            logger.debug("Detected playlist URL")
            self.current_fetch_is_channel = False
            self.channel_fetch_context = None
            playlist_limit = self._get_playlist_fetch_limit()
            finish_handler = self.handle_video_list_add if append else self.handle_video_list
            self._start_fetch_dialog("playlist", yt_channel, channel_url,
                                     finish_handler,
                                     limit=playlist_limit)

        elif self._is_video(yt_channel, channel_url):
            fetch_type = "short" if yt_channel.is_short_video_url(
                channel_url) else None
            logger.debug("Detected single video URL (short=%s)", bool(fetch_type))
            self.current_fetch_is_channel = False
            self.channel_fetch_context = None
            finish_handler = self.handle_single_video_add if append else self.handle_single_video
            self._start_fetch_dialog(fetch_type, yt_channel, channel_url,
                                     finish_handler)
        else:
            # Treat remaining YouTube URLs as channels
            if "youtube.com" in channel_url or "youtu.be" in channel_url:
                logger.debug("Attempting to fetch channel data")
                self._handle_channel_fetch(yt_channel, channel_url, append=append)
            else:
                auth_opts = self._get_auth_options()
                if is_supported_media_url(channel_url, auth_opts):
                    logger.debug("URL supported by generic extractor; treating as single media")
                    finish_handler = self.handle_single_video_add if append else self.handle_single_video
                    self._start_fetch_dialog(None, yt_channel, channel_url,
                                             finish_handler)
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

    def _handle_channel_fetch(self, yt_channel, channel_url, append: bool = False):
        """Handles the logic for fetching a channel."""
        try:
            channel_id = yt_channel.get_channel_id(channel_url)
            limit = self._get_channel_fetch_limit()
            logger.debug("Resolved channel ID: %s (limit=%s)", channel_id, limit)
            self.current_fetch_is_channel = not append
            if append:
                self.channel_fetch_context = None
            else:
                self.channel_fetch_context = {
                    "channel_id": channel_id,
                    "channel_url": channel_url,
                }
            finish_handler = self.handle_video_list_add if append else self.handle_video_list
            self._start_fetch_dialog(channel_id, yt_channel,
                                     finish_handler=finish_handler,
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
    def handle_video_list_add(self, video_list):
        """Append fetched items to the current list."""
        self.current_fetch_is_channel = False
        self.channel_fetch_context = None
        self._append_video_list(video_list)

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

    @Slot(list)
    def handle_single_video_add(self, video_list):
        """Append a single video entry to the existing list."""
        self.current_fetch_is_channel = False
        self.channel_fetch_context = None
        self._append_video_list(video_list)

    def _append_video_list(self, video_list):
        """Append fetched video entries to the existing list view."""
        if self.ui.treeView.model() is not self.model or not hasattr(self, "root_item"):
            self.reinit_model()
        if not video_list:
            self._finalize_list_view()
            self.update_selection_size_summary()
            self._maybe_prompt_on_js_warning()
            self._update_load_next_button_state()
            return
        start_index = len(self.yt_chan_vids_titles_links)
        if self._is_thumbnail_enabled() and self.thumbnail_loader:
            thumb_items = []
            for offset, entry in enumerate(video_list):
                url = self._thumbnail_url_for_entry(entry)
                thumb_items.append((start_index + offset, url))
            try:
                prefetched = self.thumbnail_loader.preload_bulk(thumb_items)
                self.prefetched_thumbnails.update(prefetched)
            except Exception as exc:  # noqa: BLE001
                logger.info("Thumbnail preload for append failed: %s", exc)
        self.yt_chan_vids_titles_links.extend(video_list)
        for entry in video_list:
            self._add_video_item_to_list(entry)
        self._finalize_list_view()
        if self._is_thumbnail_enabled():
            new_rows = range(start_index, self.model.rowCount())
            QtCore.QTimer.singleShot(0, lambda: self._warm_thumbnails_for_rows(new_rows, force=True))
        self.update_selection_size_summary()
        self._maybe_prompt_on_js_warning()
        logger.info("Appended %d videos (total now %d)", len(video_list), len(self.yt_chan_vids_titles_links))
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
        # Preload thumbnails for the incoming batch before adding rows.
        if self._is_thumbnail_enabled() and self.thumbnail_loader:
            thumb_items = []
            for offset, entry in enumerate(video_list):
                url = self._thumbnail_url_for_entry(entry)
                thumb_items.append((start_index + offset, url))
            try:
                prefetched = self.thumbnail_loader.preload_bulk(thumb_items)
                self.prefetched_thumbnails.update(prefetched)
            except Exception as exc:  # noqa: BLE001
                logger.info("Thumbnail preload for next batch failed: %s", exc)

        self.yt_chan_vids_titles_links.extend(video_list)
        for entry in video_list:
            self._add_video_item_to_list(entry)
        self._finalize_list_view()
        if self._is_thumbnail_enabled():
            new_rows = range(start_index, self.model.rowCount())
            QtCore.QTimer.singleShot(0, lambda: self._warm_thumbnails_for_rows(new_rows, force=True))
        self.update_selection_size_summary()
        self._maybe_prompt_on_js_warning()
        if self.channel_fetch_context:
            self.channel_fetch_context["fetched"] = len(self.yt_chan_vids_titles_links)
        logger.info("Appended %d videos (total now %d)", len(video_list), len(self.yt_chan_vids_titles_links))
        self._update_load_next_button_state()

    @Slot()
    def enable_get_vid_list_button(self):
        """
        Enables the fetch buttons, allowing the user to initiate
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
        self._update_speed_item(speed_item, progress_data)

        if "progress" in progress_data:
            self._handle_progress_update(file_index, progress_bar, progress_data)
            return

        if "error" in progress_data:
            self._handle_progress_error(file_index, progress_bar, speed_item, progress_data)

    def _update_speed_item(self, speed_item, progress_data):
        if speed_item and "speed" in progress_data:
            speed_item.setData(progress_data["speed"], Qt.ItemDataRole.DisplayRole)

    def _handle_progress_update(self, file_index, progress_bar, progress_data):
        progress = float(progress_data["progress"])
        raw_speed = progress_data.get("speed_bps")
        self._record_speed_history(file_index, raw_speed)
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

    def _handle_progress_error(self, file_index, progress_bar, speed_item, progress_data):
        error_message = progress_data["error"]
        progress_value = float(progress_data.get("progress", 0.0))
        progress_item = self.model.item(file_index, ColumnIndexes.PROGRESS)

        if error_message == "Cancelled":
            self._mark_cancelled_progress(progress_bar, progress_item, speed_item, progress_data, progress_value)
        else:
            self._mark_failed_progress(progress_bar, progress_item, speed_item, error_message)
            self.handle_download_error(progress_data)

        self.cleanup_download_thread(file_index)
        self.ui.treeView.viewport().update()

    def _record_speed_history(self, file_index, raw_speed):
        if raw_speed:
            history = self.speed_history.setdefault(file_index, deque(maxlen=20))
            history.append(float(raw_speed))

    def _mark_cancelled_progress(self, progress_bar, progress_item, speed_item, progress_data, progress_value):
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

    def _mark_failed_progress(self, progress_bar, progress_item, speed_item, error_message):
        if progress_bar:
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            progress_bar.setFormat(error_message)
        if progress_item:
            progress_item.setData(None, Qt.ItemDataRole.UserRole)
            progress_item.setData(error_message, Qt.ItemDataRole.DisplayRole)
        if speed_item:
            speed_item.setData("—", Qt.ItemDataRole.DisplayRole)

    def exit(self):
        """
        Exits the application by closing the PyQt main window.
        """
        self._shutdown_background_workers()
        QApplication.quit()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: D401
        """Ensure background threads are stopped before window closes."""
        self._shutdown_background_workers()
        super().closeEvent(event)
