#!/usr/bin/env python3

# Author: hyperfield
# Email: inbox@quicknode.net
# Project: YT Channel Downloader
# Description: This module contains the entry point module.
# License: MIT License

import sys
import os
import certifi
from PyQt6.QtWidgets import QApplication

from classes.ffmpeg_checker import FFmpegChecker
from classes.mainwindow import MainWindow

os.environ['SSL_CERT_FILE'] = certifi.where()

# Important:
# You need to run the following command to generate a Python ui file, e.g.
#     pyuic6 form.ui -o ui_form.py


def main():
    if not FFmpegChecker.is_ffmpeg_installed():
        FFmpegChecker.show_ffmpeg_error_dialog()
        sys.exit(1)

    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.reinit_model()
    widget.center_on_screen()
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
