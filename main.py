#!/usr/bin/env python3

# Author: hyperfield
# Email: inbox@quicknode.net
# Last update: November 2, 2024
# Project: YT Channel Downloader
# Description: This module contains the classes MainWindow, GetListThread
# and DownloadThread.
# License: MIT License

import sys
import os
import certifi
import subprocess
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from classes.mainwindow import MainWindow


os.environ['SSL_CERT_FILE'] = certifi.where()

# Important:
# You need to run the following command to generate a Python ui file, e.g.
#     pyuic6 form.ui -o ui_form.py

def show_ffmpeg_error_dialog():
    """Show an error dialog if FFmpeg is not installed."""
    app = QApplication([])
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle("FFmpeg Not Found")
    msg_box.setText("FFmpeg is required to run this application, but it is not installed on the system.")
    msg_box.setInformativeText(
        "Please install FFmpeg and ensure it's in your system PATH environment variable."
    )
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()


def is_ffmpeg_installed():
    """Check if FFmpeg is installed on the system."""
    try:
        # Try running the ffmpeg command
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False



def main():
    if not is_ffmpeg_installed():
        show_ffmpeg_error_dialog()
        sys.exit(1)  # Exit the app if FFmpeg is not installed
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.reinit_model()
    widget.center_on_screen()
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
