# Author: hyperfield
# Email: inbox@quicknode.net
# Project: YT Channel Downloader
# Description: This module contains the class MainWindow
# License: MIT License

from urllib import error
import os
import math
import re
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSlot as Slot
from PyQt6 import QtGui, QtCore
from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtWidgets import (QApplication, QMainWindow, QDialog, QCheckBox,
                             QMessageBox, QPushButton, QHBoxLayout, QProgressBar)
from PyQt6.QtCore import QSemaphore
from PyQt6.QtGui import QFont
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

import assets.resources_rc as resources_rc    # Qt resources
from ui.ui_form import Ui_MainWindow
from ui.ui_about import Ui_aboutDialog
from classes.settings_manager import SettingsManager
from classes.enums import ColumnIndexes
from classes.download_thread import DownloadThread
from classes.dialogs import CustomDialog, YoutubeCookiesDialog
from classes.fetch_progress_dialog import FetchProgressDialog
from classes.login_prompt_dialog import LoginPromptDialog
from classes.delegates import CheckBoxDelegate
from classes.YTChannel import YTChannel
from classes.videoitem import VideoItem
from classes.settings import SettingsDialog
from classes.youtube_auth import YoutubeAuthManager
from classes.validators import is_supported_media_url
from classes.logger import get_logger


logger = get_logger("MainWindow")


class MainWindow(QMainWindow):
    """Main application window for the YouTube Channel Downloader.

    This class manages the primary UI components, their styling, signal
    connections, and interactions with other modules, such as Settings and
    YouTube login.

    Attributes:
        download_semaphore (QSemaphore): Controls the maximum number of
                                         simultaneous downloads.
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

    def __init__(self, parent=None):
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
        logger.info("Main window initialised")

        self.init_styles()

        # Limit to 4 simultaneous downloads
        # TODO: Make this controllable in the Settings
        self.download_semaphore = QSemaphore(4)

        self.set_icon()
        self.setup_ui()
        self.root_item = self.model.invisibleRootItem()

        self.setup_about_dialog()
        self.init_download_structs()
        self.connect_signals()
        self.initialize_settings()
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
        self.bottomButtonLayout = QHBoxLayout()
        self.bottomButtonLayout.addStretch()
        self.bottomButtonLayout.addWidget(self.cancelDownloadsButton)
        self.ui.verticalLayout.addLayout(self.bottomButtonLayout)
        self.setup_buttons()
        self.setup_tree_view_delegate()
        self.ui.actionDonate.triggered.connect(self.open_donate_url)

    def open_donate_url(self):
        """Opens the donation URL in the default web browser."""
        logger.info("Opening donation page in browser")
        QDesktopServices.openUrl(QUrl("https://liberapay.com/hyperfield/donate"))

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
        self.setup_button(self.ui.downloadSelectedVidsButton, self.dl_vids)
        self.setup_button(self.ui.getVidListButton, self.show_vid_list)

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
        self.model.itemChanged.connect(self.update_download_button_state)
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
        self.ui.treeView.viewport().update()
        self.update_cancel_button_state()

    def cleanup_download_thread(self, index):
        """Remove finished or cancelled download threads from tracking."""
        thread = self.active_download_threads.pop(index, None)
        if thread and thread in self.dl_threads:
            self.dl_threads.remove(thread)
        self.progress_widgets.pop(index, None)
        self.update_cancel_button_state()
        self.update_download_button_state()

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
        self.cleanup_download_thread(index)
        self.ui.treeView.viewport().update()
        logger.info("Download completed for row %s", index)

    def initialize_settings(self):
        """Initializes user settings from the settings manager."""
        self.settings_manager = SettingsManager()
        self.user_settings = self.settings_manager.settings

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
        speed_width = font_metrics.horizontalAdvance("000.0 MB/s") + 12
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

    def update_download_button_state(self):
        """Enable or disable the download button based on item selection.

        Scans through the model's items to determine if any are selected for
        download. If at least one item is selected, the download button is
        enabled; otherwise, it is disabled.
        """
        self.ui.downloadSelectedVidsButton.setEnabled(False)
        for row in range(self.model.rowCount()):
            item = self.model.item(row, 0)
            if item.checkState() == Qt.CheckState.Checked:
                self.ui.downloadSelectedVidsButton.setEnabled(True)

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
        self.ui.getVidListButton.setEnabled(True)

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
        self.yt_chan_vids_titles_links = \
            yt_channel.fetch_all_videos_in_channel(channel_id)

    def populate_window_list(self):
        """Populates the main window's list view with video details."""
        self.reinit_model()
        for entry in self.yt_chan_vids_titles_links:
            self._add_video_item_to_list(entry)

        self._finalize_list_view()

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

    def _create_progress_bar(self, completed=False):
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
                            finish_handler=None):
        """Helper method to start FetchProgressDialog and connect finished
        signal."""
        self.fetch_in_progress = True
        self.fetch_error_message = None
        fetch_dialog = FetchProgressDialog(channel_id, yt_channel, channel_url,
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
        self.fetch_in_progress = False
        self.fetch_error_message = None

    @Slot()
    def show_vid_list(self):
        """Fetches and displays a single video, a playlist or a channel based
        on the input URL."""
        self.window_resize_needed = True
        self.ui.getVidListButton.setEnabled(False)
        channel_url = self.ui.chanUrlEdit.text()
        logger.info("Fetching video list for URL: %s", channel_url)
        yt_channel = self._prepare_yt_channel()

        if self._is_playlist_or_video_with_playlist(yt_channel, channel_url):
            logger.debug("Detected playlist URL")
            self._start_fetch_dialog("playlist", yt_channel, channel_url,
                                     self.handle_video_list)

        elif self._is_video(yt_channel, channel_url):
            fetch_type = "short" if yt_channel.is_short_video_url(
                channel_url) else None
            logger.debug("Detected single video URL (short=%s)", bool(fetch_type))
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
        if self.fetch_in_progress:
            if not self.fetch_error_message:
                self.fetch_error_message = message
        else:
            self.display_error_dialog(message)

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
            logger.debug("Resolved channel ID: %s", channel_id)
            self._start_fetch_dialog(channel_id, yt_channel,
                                     finish_handler=self.handle_video_list)
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
        self.populate_window_list()

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

    @Slot()
    def enable_get_vid_list_button(self):
        """
        Enables the 'Get Video List' button, allowing the user to initiate 
        another video-fetching process.
        """
        self.ui.getVidListButton.setEnabled(True)

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
            if progress_bar:
                progress_bar.setRange(0, 100)
                progress_bar.setValue(int(progress))
                progress_bar.setFormat("%p%")
            progress_item = self.model.item(file_index, ColumnIndexes.PROGRESS)
            if progress_item:
                progress_item.setData(progress, Qt.ItemDataRole.UserRole)
                progress_item.setData(None, Qt.ItemDataRole.DisplayRole)
            self.ui.treeView.viewport().update()
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
