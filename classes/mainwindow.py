from PySide6.QtCore import QThread, Signal, Slot
from ui_form import Ui_MainWindow
from PySide6 import QtGui, QtCore
from PySide6.QtWidgets import QApplication, QMainWindow, QDialog
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
    finished = Signal(list)

    def __init__(self, channel_id, yt_channel, parent=None):
        super().__init__(parent)
        # self.settings_manager = SettingsManager()
        self.channel_id = channel_id
        self.yt_channel = yt_channel

    def run(self):
        video_list = self.yt_channel.get_all_video_in_channel(self.channel_id)
        self.finished.emit(video_list)


class DownloadThread(QThread):
    downloadProgressSignal = Signal(dict)
    downloadCompleteSignal = Signal(str)

    def __init__(self, url, index, title, parent=None):
        super().__init__(parent)
        self.url = url
        self.index = index
        self.title = title
        self.settings_manager = SettingsManager()
        self.user_settings = self.settings_manager.settings

    def run(self):
        sanitized_title = self.sanitize_filename(self.title)
        download_directory = self.user_settings.get('download_directory')

        ydl_opts = {
            'outtmpl':
                os.path.join(download_directory, f'{sanitized_title}.%(ext)s'),
            'progress_hooks': [self.dl_hook],
        }

        video_format = settings_map['preferred_video_format'].get(
            self.user_settings.get('preferred_video_format', 'Any'), 'Any')
        if video_format:
            ydl_opts['format'] = video_format
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

    def dl_hook(self, d):
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
        filename = filename.strip()
        filename = filename.replace(' ', '_')
        # remove or replace characters that are illegal in Windows filenames
        filename = re.sub(r'[\\/*?:"<>|]', '', filename)
        filename = filename[:250]
        # check for Windows reserved filenames
        reserved_filenames = {
            "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
            "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2",
            "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
        }
        if filename.upper() in reserved_filenames:
            filename += "_"

        return filename

    @staticmethod
    def is_download_complete(filepath):
        # Check if the temporary yt-dlp files exist
        if os.path.exists(filepath + ".part") or \
                os.path.exists(filepath + ".ytdl"):
            return False
        # If the final file exists and no temporary files exist,
        # the download is complete
        return bool(glob.glob(f"{filepath}.*"))


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        icon_path = Path(__file__).resolve().parent.parent / "icon.png"
        print(icon_path)
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
        self.model = QtGui.QStandardItemModel()
        self.ui.actionExit.triggered.connect(self.exit)
        self.ui.getVidListButton.clicked.connect(self.show_vid_list)
        cb_delegate = CheckBoxDelegate()
        self.ui.treeView.setItemDelegateForColumn(0, cb_delegate)
        self.model.itemChanged.connect(self.update_download_button_state)
        self.update_download_button_state()

        self.settings_manager = SettingsManager()
        self.user_settings = self.settings_manager.settings

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

    def get_vid_list(self, channel_id, yt_channel):
        self.yt_chan_vids_titles_links.clear()
        self.yt_chan_vids_titles_links = \
            yt_channel.get_all_video_in_channel(channel_id)

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
                item[3].setText("Already downloaded")
            self.rootItem.appendRow(item)
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

    @Slot()
    def show_vid_list(self):
        self.ui.getVidListButton.setEnabled(False)
        channel_url = self.ui.chanUrlEdit.text()
        yt_channel = YTChannel()
        channel_id = None
        try:
            channel_id = yt_channel.get_channel_id(channel_url)
        except ValueError:
            dlg = CustomDialog("URL error", "Please check your URL")
            dlg.exec()
            self.ui.getVidListButton.setEnabled(True)
            return
        except error.URLError:
            dlg = CustomDialog(
                "URL error", "Please check your internet connection")
            dlg.exec()
            self.ui.getVidListButton.setEnabled(True)
            return

        self.get_list_thread = GetListThread(channel_id, yt_channel)
        self.get_list_thread.finished.connect(self.handle_video_list)
        # Re-enable the button on completion
        self.get_list_thread.finished.connect(self.enable_get_vid_list_button)
        self.get_list_thread.start()

    @Slot(list)
    def handle_video_list(self, video_list):
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
            dl_thread = DownloadThread(link, index, title)
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
