# Author: hyperfield
# Email: info@quicknode.net
# Date: October 13, 2023
# Project: YT Channel Downloader
# Description: This module contains the classes MainWindow, GetListThread
# and DownloadThread.
# License: MIT License

from PySide6.QtCore import Qt, QThread, Signal, Slot
from ui_form import Ui_MainWindow
from PySide6 import QtGui, QtCore
from PySide6.QtWidgets import QApplication, QMainWindow, QDialog, QCheckBox
from PySide6.QtCore import QSemaphore
from urllib import error
import yt_dlp
import re
import os
import glob
from pathlib import Path

import resources    # Qt resources
from .dialogs import CustomDialog
from .checkbox import CheckBoxDelegate
from .YTChannel import YTChannel
from .settings import SettingsDialog
from ui_about import Ui_aboutDialog
from .settings_manager import SettingsManager
from .constants import settings_map


class GetListThread(QThread):
    """
    A thread class for fetching a list of videos from a YouTube channel or
    a single video.

    This class inherits from QThread and is used to retrieve either all
    videos from a given YouTube channel or a single video, based on the
    provided channel ID or video URL. The retrieval process is done in
    a separate thread to avoid blocking the main application.

    Attributes:
    finished (Signal): A signal that is emitted when the video list
                       retrieval is complete.
                       The signal sends a list of videos.

    Parameters:
    channel_id (str): The unique identifier for a YouTube channel.
                      If this is None, the class will fetch a single
                      video using channel_url.
    yt_channel (YTChannel): An instance of the YTChannel class that
                            provides the functionality to fetch
                            video details from YouTube.
    channel_url (str, optional): The URL of a single YouTube video.
                                 This is used only if channel_id is
                                 None. Defaults to None.
    parent (QObject, optional): The parent object of the thread.
                                Defaults to None.
    """
    finished = Signal(list)

    def __init__(self, channel_id, yt_channel, channel_url=None, parent=None):
        """
        Initializes the GetListThread with the necessary attributes.

        Parameters:
        channel_id (str): The unique identifier for a YouTube channel.
        yt_channel (YTChannel): An instance of the YTChannel class.
        channel_url (str, optional): The URL of a single YouTube video.
        Defaults to None.
        parent (QObject, optional): The parent object of the thread.
        Defaults to None.
        """
        super().__init__(parent)
        self.channel_id = channel_id
        self.yt_channel = yt_channel
        self.channel_url = channel_url

    def run(self):
        """
        The main execution method for the thread.

        Depending on whether a channel_id or channel_url is provided, this
        method fetches either all videos from a YouTube channel or a single
        video. Once the data is fetched, it emits the 'finished' signal
        with the video list.
        """
        if not self.channel_id:
            video_list = self.yt_channel.get_single_video(self.channel_url)
            self.finished.emit(video_list)
        elif self.channel_id == "playlist":
            video_list = self.yt_channel.get_videos_from_playlist(
                self.channel_url)
            self.finished.emit(video_list)
        else:
            video_list = self.yt_channel.get_all_videos_in_channel(
                self.channel_id)
            self.finished.emit(video_list)


class DownloadThread(QThread):
    """
    A QThread subclass that handles downloading videos from YouTube with
    specificformats and qualities.

    Attributes:
        downloadProgressSignal (Signal): Signal emitted during the download
        process with progress details.
        downloadCompleteSignal (Signal): Signal emitted once the download
        is complete.

    Args:
        url (str): The URL of the video to be downloaded.
        index (int): The index identifier for the download, used for managing
        multiple downloads.
        title (str): The title of the video, used for naming the downloaded
        file.
        mainWindow (MainWindow): Reference to the main window of the
        applicationfor UI interactions and semaphore access.
        parent (QObject, optional): The parent QObject. Defaults to None.
    """

    downloadProgressSignal = Signal(dict)
    downloadCompleteSignal = Signal(str)

    def __init__(self, url, index, title, mainWindow, parent=None):
        super().__init__(parent)
        self.url = url
        self.index = index
        self.title = title
        self.mainWindow = mainWindow
        self.settings_manager = SettingsManager()
        self.user_settings = self.settings_manager.settings

    def run(self):
        """
        Executes the download process in a separate thread. Configures download
        options based on user preferences, fetches the video, and emits signals
        to update the UI on progress and completion.
        """
        from .utils import get_video_format_details
        self.mainWindow.download_semaphore.acquire()
        sanitized_title = self.sanitize_filename(self.title)
        download_directory = self.user_settings.get('download_directory')

        ydl_opts = {
            'outtmpl':
                os.path.join(download_directory, f'{sanitized_title}.%(ext)s'),
            'progress_hooks': [self.dl_hook],
        }

        video_format = settings_map['preferred_video_format'].get(
            self.user_settings.get('preferred_video_format', 'Any'), 'Any')
        video_quality = settings_map['preferred_video_quality'].get(
            self.user_settings.get('preferred_video_quality',
                                   'bestvideo'), 'Any')

        closest_format_id = get_video_format_details(
            self.url, video_quality, video_format)

        if closest_format_id:
            ydl_opts['format'] = f"{closest_format_id}+bestaudio"
        elif video_quality:
            ydl_opts['format'] = video_quality
        else:
            ydl_opts['format'] = 'bestvideo+bestaudio'

        if self.user_settings.get('audio_only'):
            audio_format = settings_map['preferred_audio_format'].get(
                self.user_settings.get('preferred_audio_format', 'Any'), 'Any')
            audio_quality = settings_map['preferred_audio_quality'].get(
                self.user_settings.get('preferred_audio_quality',
                                       'Best available'), 'bestaudio')
            if audio_format and audio_format != 'Any':
                audio_filter = f"[ext={audio_format}]"
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': audio_format
                }]
            else:
                audio_filter = ''

            ydl_opts['format'] = \
                f"{audio_quality}{audio_filter}/bestaudio/best"

            proxy_type = self.user_settings.get('proxy_server_type', None)
            proxy_addr = self.user_settings.get('proxy_server_addr', None)
            proxy_port = self.user_settings.get('proxy_server_port', None)

            if proxy_type and proxy_addr and proxy_port:
                ydl_opts['proxy'] = f"{proxy_type}://{proxy_addr}:{proxy_port}"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([self.url])
        self.downloadCompleteSignal.emit(self.index)
        self.mainWindow.download_semaphore.release()

    def dl_hook(self, d):
        """
        Callback function used by yt-dlp to handle download progress updates.

        Args:
            d (dict): A dictionary containing status information about the
            ongoing download.
        """
        if d['status'] == 'downloading':
            progress_str = d['_percent_str']
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            progress_str = ansi_escape.sub('', progress_str)
            progress = float(progress_str.strip('%'))
            self.downloadProgressSignal.emit(
                {"index": str(self.index), "progress": f"{progress} %"}
                )

    @staticmethod
    def sanitize_filename(filename):
        """
        Sanitizes the filename by removing illegal characters and checking against reserved filenames.

        Args:
            filename (str): The initial filename based on the video title.

        Returns:
            str: A sanitized filename safe for use in file systems.
        """
        filename = filename.strip()
        filename = filename.replace(' ', '_')
        # Remove or replace characters that are illegal in Windows filenames,
        # and potentially problematic for glob patterns (like square brackets)
        filename = re.sub(r'[\\/*?:"<>|\[\]]', '', filename)
        filename = filename[:250]

        # Check for Windows reserved filenames
        reserved_filenames = {
            "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5",
            "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4",
            "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
        }
        if filename.upper() in reserved_filenames:
            filename += "_"

        return filename

    @staticmethod
    def is_download_complete(filepath):
        """
        Checks if the download for a given file is complete by looking for
        temporary `.part` or `.ytdl` files.

        Args:
            filepath (str): The path to the file without the extension.

        Returns:
            bool: True if the download is complete, False otherwise.
        """

        part_files = glob.glob(f"{filepath}*.part")
        ytdl_files = glob.glob(f"{filepath}*.ytdl")

        # If any partially downloaded files are found,
        # the download is incomplete
        if part_files or ytdl_files:
            return False

        matching_files = glob.glob(f"{filepath}.*")

        # Otherwise only completely downloaded files would be found
        if not matching_files:
            return False

        return True


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Limit to 3 simultaneous downloads
        self.download_semaphore = QSemaphore(3)
        icon_path = Path(__file__).resolve().parent.parent / "icon.png"
        self.setWindowIcon(QtGui.QIcon(str(icon_path)))
        self.ui = Ui_MainWindow()
        self.center_on_screen()
        self.ui.setupUi(self)

        # Initialize About Dialog
        self.about_dialog = QDialog()
        self.about_ui = Ui_aboutDialog()
        self.about_ui.setupUi(self.about_dialog)
        self.ui.actionAbout.triggered.connect(self.show_about_dialog)

        self.ui.actionSettings.triggered.connect(self.showSettingsDialog)
        dlVidsButton = self.ui.downloadSelectedVidsButton
        dlVidsButton.clicked.connect(self.dl_vids)
        self.yt_chan_vids_titles_links = []
        self.vid_dl_indexes = []
        self.dl_threads = []
        self.dl_path_correspondences = {}
        self.model = QtGui.QStandardItemModel()
        self.ui.actionExit.triggered.connect(self.exit)
        self.ui.getVidListButton.clicked.connect(self.show_vid_list)
        cb_delegate = CheckBoxDelegate()
        self.ui.treeView.setItemDelegateForColumn(0, cb_delegate)
        self.model.itemChanged.connect(self.update_download_button_state)
        self.update_download_button_state()

        self.settings_manager = SettingsManager()
        self.user_settings = self.settings_manager.settings

        self.selectAllCheckBox = QCheckBox("Select All", self)
        self.selectAllCheckBox.setVisible(False)
        self.ui.verticalLayout.addWidget(self.selectAllCheckBox)
        self.selectAllCheckBox.stateChanged.connect(
            self.onSelectAllStateChanged)

    def autoAdjustWindowWidth(self):
        # Obtain general screen size
        screen = QApplication.primaryScreen()
        screen_size = screen.size()
        half_screen_width = screen_size.width() / 2

        # Calculate total width needed by the treeView
        # according to populated contents
        total_width = self.ui.treeView.viewport().sizeHint().width()
        for column in range(self.model.columnCount()):
            total_width += self.ui.treeView.columnWidth(column)

        # Adjust the width for layout margins, scrollbars, etc.
        total_width += self.ui.treeView.verticalScrollBar().width() * 3
        total_width += self.ui.treeView.frameWidth() * 2
        total_width = min(total_width, half_screen_width)
        self.resize(total_width, self.height())

    def onSelectAllStateChanged(self, state):
        newValue = state == 2

        for row in range(self.model.rowCount()):
            item_title_index = self.model.index(row, 1)
            item_title = self.model.data(item_title_index)
            full_file_path = self.dl_path_correspondences[item_title]

            if full_file_path and \
               DownloadThread.is_download_complete(full_file_path):
                continue

            index = self.model.index(row, 0)
            self.model.setData(index, newValue, Qt.DisplayRole)

            # Update the Qt.CheckStateRole accordingly
            newCheckState = Qt.Checked if newValue else Qt.Unchecked
            self.model.setData(index, newCheckState, Qt.CheckStateRole)

    def center_on_screen(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.geometry()
        x_center = (screen_geometry.width() - window_geometry.width()) / 2
        y_center = (screen_geometry.height() - window_geometry.height()) / 2
        self.move(x_center, y_center)

    def reinit_model(self):
        self.model.clear()
        self.rootItem = self.model.invisibleRootItem()
        self.model.setHorizontalHeaderLabels(['Download?', 'Title',
                                              'Link', 'Progress'])
        self.ui.treeView.setModel(self.model)
        self.selectAllCheckBox.setVisible(False)

    def showSettingsDialog(self):
        settings_dialog = SettingsDialog()
        settings_dialog.exec_()

    def show_about_dialog(self):
        self.about_ui.aboutLabel.setOpenExternalLinks(True)
        self.about_ui.aboutOkButton.clicked.connect(self.about_dialog.accept)
        self.about_dialog.exec_()

    def update_download_button_state(self):
        self.ui.downloadSelectedVidsButton.setEnabled(False)
        for row in range(self.model.rowCount()):
            item = self.model.item(row, 0)
            if item.checkState() == QtCore.Qt.Checked:
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
        self.yt_chan_vids_titles_links.clear()
        self.yt_chan_vids_titles_links = \
            yt_channel.get_all_videos_in_channel(channel_id)

    def populate_window_list(self):
        self.reinit_model()
        for title_link in self.yt_chan_vids_titles_links:
            item_checkbox = QtGui.QStandardItem()
            item_checkbox.setCheckable(True)
            item_title = QtGui.QStandardItem(title_link[0])
            item_link = QtGui.QStandardItem(title_link[1])
            item_title_text = item_title.text()
            filename = DownloadThread.sanitize_filename(item_title_text)
            item = [item_checkbox, item_title,
                    item_link, QtGui.QStandardItem()]
            download_directory = self.user_settings.get(
                'download_directory', './')
            full_file_path = os.path.join(download_directory, filename)
            if DownloadThread.is_download_complete(full_file_path):
                item_checkbox.setFlags(QtCore.Qt.ItemIsSelectable
                                       | QtCore.Qt.ItemIsUserTristate)
                item_title.setForeground(QtGui.QBrush(QtGui.QColor('grey')))
                item_checkbox.setForeground(QtGui.QBrush(QtGui.QColor('grey')))
                item_link.setForeground(QtGui.QBrush(QtGui.QColor('grey')))
                item[3].setText("Complete")
            self.rootItem.appendRow(item)
            self.dl_path_correspondences[item_title_text] = full_file_path
        self.ui.treeView.expandAll()
        self.ui.treeView.show()
        cb_delegate = CheckBoxDelegate()
        self.ui.treeView.setItemDelegateForColumn(0, cb_delegate)
        self.ui.treeView.resizeColumnToContents(0)
        self.ui.treeView.resizeColumnToContents(1)
        self.ui.treeView.resizeColumnToContents(2)
        self.ui.treeView.resizeColumnToContents(3)
        self.ui.treeView.setStyleSheet("""
        QTreeView::indicator:disabled {
            background-color: gray;
        }
        """)
        if self.model.rowCount() > 0:
            self.selectAllCheckBox.setVisible(True)
            self.autoAdjustWindowWidth()

    @Slot()
    def show_vid_list(self):
        self.ui.getVidListButton.setEnabled(False)
        channel_url = self.ui.chanUrlEdit.text()
        yt_channel = YTChannel()
        yt_channel.showError.connect(self.display_error_dialog)
        channel_id = None

        if yt_channel.is_video_with_playlist_url(channel_url) or \
           yt_channel.is_playlist_url(channel_url):
            # Handle playlist URL
            self.get_list_thread = GetListThread(
                "playlist", yt_channel, channel_url)
            self.get_list_thread.finished.connect(self.handle_video_list)
            self.get_list_thread.finished.connect(
                self.enable_get_vid_list_button)
            self.get_list_thread.start()

        elif yt_channel.is_video_url(channel_url):
            # Debug exception
            self.get_list_thread = GetListThread(channel_id, yt_channel,
                                                 channel_url)
            self.get_list_thread.finished.connect(self.handle_single_video)
            # Re-enable the button on completion
            self.get_list_thread.finished.connect(
                self.enable_get_vid_list_button)
            self.get_list_thread.start()

        else:
            # Handle as channel URL
            try:
                channel_id = yt_channel.get_channel_id(channel_url)
            except ValueError:
                self.display_error_dialog("Please check your URL")
                return
            except error.URLError:
                self.display_error_dialog("Please check your URL")
                return

            self.get_list_thread = GetListThread(channel_id, yt_channel)
            self.get_list_thread.finished.connect(self.handle_video_list)
            # Re-enable the button on completion
            self.get_list_thread.finished.connect(
                self.enable_get_vid_list_button)
            self.get_list_thread.start()

    @Slot(list)
    def handle_video_list(self, video_list):
        self.yt_chan_vids_titles_links = video_list
        self.populate_window_list()

    @Slot(list)
    def handle_single_video(self, video_list):
        self.yt_chan_vids_titles_links = video_list
        self.populate_window_list()

    @Slot()
    def enable_get_vid_list_button(self):
        self.ui.getVidListButton.setEnabled(True)

    @Slot()
    def dl_vids(self):
        # get all the indexes of the checked items
        self.vid_dl_indexes.clear()
        for row in range(self.model.rowCount()):
            item = self.model.item(row, 0)
            if item.checkState() == QtCore.Qt.Checked:
                self.vid_dl_indexes.append(row)
        for index in self.vid_dl_indexes:
            progress_item = QtGui.QStandardItem()
            self.model.setItem(index, 3, progress_item)
            link = self.model.item(index, 2).text()
            title = self.model.item(index, 1).text()
            dl_thread = DownloadThread(link, index, title, self)
            dl_thread.downloadCompleteSignal.connect(self.populate_window_list)
            dl_thread.downloadProgressSignal.connect(self.update_progress)
            self.dl_threads.append(dl_thread)
            dl_thread.start()

    @Slot(str, int)
    def update_progress(self, progress_data):
        file_index = int(progress_data["index"])
        progress = progress_data["progress"]
        progress_item = QtGui.QStandardItem(str(progress))
        self.model.setItem(int(file_index), 3, progress_item)
        self.ui.treeView.viewport().update()

    def exit(self):
        QApplication.quit()
