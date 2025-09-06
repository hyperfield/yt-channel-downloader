# Author: hyperfield
# Email: inbox@quicknode.net
# Project: YT Channel Downloader
# Description: This module contains the class FetchProgressDialog
# License: MIT License

"""
This module defines a `FetchProgressDialog` class that represents a dialog
for tracking the progress of fetching a list of items from a YouTube channel.
It handles starting the fetch process, displaying elapsed time, and providing
cancellation options.

The module is intended for use in PyQt applications where fetching video lists
may take an indeterminate amount of time.
"""
from PyQt6.QtCore import pyqtSignal as Signal
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, \
    QPushButton
from PyQt6.QtCore import Qt, QTimer

from classes.get_list_thread import GetListThread
from config.constants import MS_PER_SECOND


class FetchProgressDialog(QDialog):
    """
    A QDialog subclass to display and manage the progress of fetching
    video items.

    Attributes:
        finished (Signal): Emitted when the fetch operation completes
                           successfully, with the video list as an argument.
        cancelled (Signal): Emitted when the fetch operation is cancelled.
        thread (GetListThread): The thread responsible for fetching video data.
        timer (QTimer): A timer for updating the elapsed time label.
        elapsed_seconds (int): The number of seconds elapsed since the fetch
                               started.
    """
    finished = Signal(list)
    cancelled = Signal()

    def __init__(self, channel_id, yt_channel, channel_url=None, parent=None):
        """
        Initializes the dialog and starts the fetch operation in a separate
        thread.

        Args:
            channel_id (str): The ID of the YouTube channel or playlist.
            yt_channel (YTChannel): An instance of YTChannel for operations.
            channel_url (str, optional): The URL of the YouTube channel or
                                         video. Defaults to None.
            parent (QWidget, optional): The parent widget of the dialog.
                                        Defaults to None.
        """
        super().__init__(parent)
        self.setWindowTitle("Fetching items")

        self.setFixedSize(400, 200)
        self.layout = QVBoxLayout(self)

        self.message_label = QLabel("Fetching the list of items... This may take some time, depending on the number of items.")
        self.message_label.setWordWrap(True)
        self.layout.addWidget(self.message_label)

        self.timer_label = QLabel("Time Elapsed: 0 seconds")
        self.layout.addWidget(self.timer_label)

        self.progress_bar = QProgressBar(self)
        # Set range to 0 to make the progress bar indefinite
        self.progress_bar.setRange(0, 0)
        self.layout.addWidget(self.progress_bar)

        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.clicked.connect(self.on_fetch_cancel)
        self.layout.addWidget(self.cancel_button,
                              alignment=Qt.AlignmentFlag.AlignCenter)

        if parent:
            parent_center = parent.geometry().center()
            dialog_rect = self.geometry()
            dialog_rect.moveCenter(parent_center)
            QTimer.singleShot(0, lambda: self.setGeometry(dialog_rect))

        self.thread = GetListThread(channel_id, yt_channel, channel_url)
        self.thread.finished.connect(self.on_fetch_complete)
        self.thread.cancelled.connect(self.on_fetch_cancel)

        # Timer setup
        self.elapsed_seconds = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)

        self.apply_style()
        self.timer.start(MS_PER_SECOND)
        self.thread.start()

    def update_timer(self):
        """Update the timer label to show elapsed time."""
        self.elapsed_seconds += 1
        self.timer_label.setText(f"Time elapsed: {self.elapsed_seconds} seconds")

    def on_fetch_cancel(self):
        """Stop the timer and close the dialog."""
        self.timer.stop()
        self.thread.cancel()
        self.cancelled.emit()
        self.reject()

    def start_fetch(self):
        """Run this to display the dialog and start the fetch."""
        self.show()
        self.exec()

    def on_fetch_complete(self, video_list):
        """Handle thread completion and emit finished signal with results."""
        self.timer.stop()
        self.finished.emit(video_list)
        self.accept()

    def apply_style(self):
        """
        Applies custom CSS styles to the progress bar and buttons for
        enhanced UI appearance.
        """
        self.progress_bar.setStyleSheet("""
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
            QPushButton {
                font-weight: bold;
            }
        """)
