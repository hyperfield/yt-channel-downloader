# Author: hyperfield
# Email: inbox@quicknode.net
# Last update: September 6, 2024
# Project: YT Channel Downloader
# Description: This module contains the classes MainWindow, GetListThread
# and DownloadThread.
# License: MIT License

from urllib import error
import os
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSlot as Slot
from ui.ui_form import Ui_MainWindow
from PyQt6 import QtGui, QtCore
from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, QCheckBox
from PyQt6.QtCore import QSemaphore

import assets.resources_rc as resources_rc    # Qt resources
from .get_list_thread import GetListThread
from .download_thread import DownloadThread
from .dialogs import CustomDialog
from .dialogs import YoutubeLoginDialog
from .login_prompt_dialog import LoginPromptDialog
from .delegates import CheckBoxDelegate
from .YTChannel import YTChannel
from .settings import SettingsDialog
from ui.ui_about import Ui_aboutDialog
from .settings_manager import SettingsManager


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setStyleSheet("""
            MainWindow {
                background-color: #f0f0f0;
                border-radius: 10px;
                box-shadow: 5px 5px 15px rgba(0, 0, 0, 0.2);
            }
            QGroupBox { 
                border: 1px solid #d3d3d3; 
                padding: 10px; 
                margin-top: 10px; 
                border-radius: 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        # Limit to 4 simultaneous downloads
        self.download_semaphore = QSemaphore(4)
        icon_path = Path(__file__).resolve().parent.parent / "icon.png"
        self.setWindowIcon(QtGui.QIcon(str(icon_path)))
        self.ui = Ui_MainWindow()
        self.center_on_screen()
        self.ui.setupUi(self)

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

        self.youtube_login_dialog = None  # Initialize to None
        self.ui.actionYoutube_login.triggered.connect(
            self.handle_youtube_login)

        self.check_youtube_login_status()

    def check_youtube_login_status(self):
        config_dir = self.settings_manager.get_config_directory()
        cookie_jar_path = Path(config_dir) / "youtube_cookies.txt"
        self.youtube_login_dialog = YoutubeLoginDialog(cookie_jar_path)
        self.update_youtube_login_menu()

    def show_youtube_login_dialog(self):
        if self.youtube_login_dialog and self.youtube_login_dialog.logged_in:
            self.youtube_login_dialog.logout()
            self.youtube_login_dialog = None  # Destroy the current instance
            self.ui.actionYoutube_login.setText("YouTube login")
        else:
            if self.youtube_login_dialog is None:
                config_dir = self.settings_manager.get_config_directory()
                cookie_jar_path = Path(config_dir) / "youtube_cookies.txt"
                self.youtube_login_dialog = YoutubeLoginDialog(cookie_jar_path)
                self.youtube_login_dialog.logged_in_signal.connect(
                    self.update_youtube_login_menu)

            self.youtube_login_dialog.show()

    def handle_youtube_login(self):
        if not self.youtube_login_dialog:
            config_dir = self.settings_manager.get_config_directory()
            cookie_jar_path = Path(config_dir) / "youtube_cookies.txt"
            self.youtube_login_dialog = YoutubeLoginDialog(cookie_jar_path)

        self.youtube_login_dialog.logged_in_signal.connect(
                self.update_youtube_login_menu)

        if not self.youtube_login_dialog.logged_in:
            user_settings = self.settings_manager.settings
            if not user_settings.get('dont_show_login_prompt'):
                login_prompt_dialog = LoginPromptDialog(self)
                if login_prompt_dialog.exec() == QDialog.DialogCode.Accepted:
                    self.show_youtube_login_dialog()
            else:
                self.show_youtube_login_dialog()
        else:
            # If already logged in, perform logout
            self.youtube_login_dialog.logout()
            self.ui.actionYoutube_login.setText("YouTube login")
            self.youtube_login_dialog = None

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

        self.resize(int(total_width), self.height())

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
            self.model.setData(index, newValue, Qt.ItemDataRole.DisplayRole)

            # Update the Qt.CheckStateRole accordingly
            newCheckState = Qt.CheckState.Checked if newValue \
                else Qt.CheckState.Unchecked
            self.model.setData(index, newCheckState,
                               Qt.ItemDataRole.CheckStateRole)

    def center_on_screen(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.geometry()
        x_center = (screen_geometry.width() - window_geometry.width()) // 2
        y_center = (screen_geometry.height() - window_geometry.height()) // 2
        self.move(int(x_center), int(y_center))

    def reinit_model(self):
        self.model.clear()
        self.rootItem = self.model.invisibleRootItem()
        self.model.setHorizontalHeaderLabels(['Download?', 'Title',
                                              'Link', 'Progress'])
        self.ui.treeView.setModel(self.model)
        self.selectAllCheckBox.setVisible(False)

    def showSettingsDialog(self):
        settings_dialog = SettingsDialog()
        settings_dialog.exec()

    def show_about_dialog(self):
        self.about_ui.aboutLabel.setOpenExternalLinks(True)
        self.about_ui.aboutOkButton.clicked.connect(self.about_dialog.accept)
        self.about_dialog.exec()

    @Slot()
    def update_youtube_login_menu(self):
        if self.youtube_login_dialog and self.youtube_login_dialog.logged_in:
            self.ui.actionYoutube_login.setText("YouTube logout")
        else:
            self.ui.actionYoutube_login.setText("YouTube login")

    def update_download_button_state(self):
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
                item_checkbox.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable
                                       | QtCore.Qt.ItemFlag.ItemIsUserTristate)
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
            if item.checkState() == Qt.CheckState.Checked:  # Update here
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

    @Slot(dict)
    def update_progress(self, progress_data):
        file_index = int(progress_data["index"])
        progress = progress_data["progress"]
        progress_item = QtGui.QStandardItem(str(progress))
        self.model.setItem(int(file_index), 3, progress_item)
        self.ui.treeView.viewport().update()

    def exit(self):
        QApplication.quit()
