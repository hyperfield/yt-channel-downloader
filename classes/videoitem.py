"""
This module defines the VideoItem class used to represent video items in a
list view, including methods to initialize and manage UI elements for each
item.
"""
from classes.download_thread import DownloadThread

from PyQt6 import QtGui, QtCore


class VideoItem:
    """
    Represents a video item with relevant data and methods to interact with
    a list view in a PyQt application.

    Attributes:
        title (str): The title of the video.
        link (str): The link to the video.
        download_path (str): The file path where the video is downloaded.
        is_download_complete (bool): Indicates if the video has been fully
                                     downloaded.
        qt_item (list): List of QStandardItem objects for UI representation.
    """
    def __init__(self, title, link, download_path):
        """
        Initializes a VideoItem instance, checks the download status,
        and creates the corresponding UI items.

        Args:
            title (str): The title of the video.
            link (str): The link to the video.
            download_path (str): The file path of the video download.
        """
        self.title = title
        self.link = link
        self.download_path = download_path
        self.is_download_complete = DownloadThread.is_download_complete(
            self.download_path)
        self._create_qt_item()

    def _create_qt_item(self):
        """
        Creates a list of QStandardItem objects representing the video
        in a list view. Marks items as complete if the download is finished.
        """
        self.item_checkbox = QtGui.QStandardItem()
        self.item_checkbox.setCheckable(True)
        self.item_checkbox.setCheckState(QtCore.Qt.CheckState.Checked if
                                         self.is_download_complete else
                                         QtCore.Qt.CheckState.Unchecked)
        item_title = QtGui.QStandardItem(self.title)
        item_link = QtGui.QStandardItem(self.link)
        item_speed = QtGui.QStandardItem("—")
        item_progress = QtGui.QStandardItem()
        if self.is_download_complete:
            item_progress.setData(100.0, QtCore.Qt.ItemDataRole.UserRole)
            item_progress.setData("Completed", QtCore.Qt.ItemDataRole.DisplayRole)
        else:
            item_progress.setData(0.0, QtCore.Qt.ItemDataRole.UserRole)
            item_progress.setData("", QtCore.Qt.ItemDataRole.DisplayRole)
        self.qt_item = [self.item_checkbox, item_title, item_link,
                        item_speed, item_progress]

        if self.is_download_complete:
            self._deactivate_qt_item()

    def _deactivate_qt_item(self):
        """
        Applies a gray foreground to the items and disables editing/checking
        if the video is marked as complete.
        """
        gray_brush = QtGui.QBrush(QtGui.QColor('grey'))
        for subitem in self.qt_item[:-1]:
            subitem.setForeground(gray_brush)
        self.item_checkbox.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable |
                                    QtCore.Qt.ItemFlag.ItemIsUserTristate)
        speed_item = self.qt_item[-2]
        speed_item.setData("—", QtCore.Qt.ItemDataRole.DisplayRole)
        progress_item = self.qt_item[-1]
        progress_item.setData(100.0, QtCore.Qt.ItemDataRole.UserRole)
        progress_item.setData("Completed", QtCore.Qt.ItemDataRole.DisplayRole)

    def mark_as_complete(self):
        """Public method to deactivate UI items when the download is
        complete."""
        self._deactivate_qt_item()

    def get_qt_item(self):
        """
        Returns the list of QStandardItem objects for UI display.

        Returns:
            list: The list of QStandardItem objects.
        """
        return self.qt_item
