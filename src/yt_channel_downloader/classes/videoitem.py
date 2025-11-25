"""
This module defines the VideoItem class used to represent video items in a
list view, including methods to initialize and manage UI elements for each
item.
"""
from .download_thread import DownloadThread

from PyQt6 import QtGui, QtCore

THUMBNAIL_URL_ROLE = QtCore.Qt.ItemDataRole.UserRole + 10


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
    def __init__(self, title, link, duration_seconds, download_path, thumbnail_url=None):
        """
        Initializes a VideoItem instance, checks the download status,
        and creates the corresponding UI items.

        Args:
            title (str): The title of the video.
            link (str): The link to the video.
            duration_seconds (int | None): Video length in seconds if known.
            download_path (str): The file path of the video download.
            thumbnail_url (str | None): URL to a representative thumbnail image.
        """
        self.title = title
        self.link = link
        self.duration_seconds = duration_seconds
        self.download_path = download_path
        self.thumbnail_url = thumbnail_url
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
        self.item_checkbox.setCheckState(
            QtCore.Qt.CheckState.Unchecked if self.is_download_complete
            else QtCore.Qt.CheckState.Unchecked
        )
        item_title = QtGui.QStandardItem(self.title)
        if self.thumbnail_url:
            item_title.setData(self.thumbnail_url, THUMBNAIL_URL_ROLE)
        item_link = QtGui.QStandardItem(self.link)
        duration_value = self._coerce_duration_value(self.duration_seconds)
        duration_display = self._format_duration(duration_value)
        item_duration = QtGui.QStandardItem(duration_display)
        if duration_value is not None:
            item_duration.setData(duration_value, QtCore.Qt.ItemDataRole.UserRole)
        item_speed = QtGui.QStandardItem("—")
        item_progress = QtGui.QStandardItem()
        if self.is_download_complete:
            item_progress.setData(100.0, QtCore.Qt.ItemDataRole.UserRole)
            item_progress.setData("Completed", QtCore.Qt.ItemDataRole.DisplayRole)
        else:
            item_progress.setData(0.0, QtCore.Qt.ItemDataRole.UserRole)
            item_progress.setData("", QtCore.Qt.ItemDataRole.DisplayRole)
        self.qt_item = [
            self.item_checkbox,
            item_title,
            item_duration,
            item_link,
            item_speed,
            item_progress,
        ]

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
        self.item_checkbox.setCheckState(QtCore.Qt.CheckState.Unchecked)
        self.item_checkbox.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable)
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

    @staticmethod
    def _coerce_duration_value(duration_seconds):
        if duration_seconds is None:
            return None
        try:
            total_seconds = int(float(duration_seconds))
        except (TypeError, ValueError):
            return None
        return total_seconds if total_seconds >= 0 else None

    @staticmethod
    def _format_duration(duration_seconds):
        if duration_seconds is None:
            return "—"
        hours, remainder = divmod(duration_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours:d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:d}:{seconds:02d}"
