#!/usr/bin/env python3

# This Python file uses the following encoding: utf-8
import sys
import os
import certifi
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from classes.mainwindow import MainWindow


os.environ['SSL_CERT_FILE'] = certifi.where()

# Important:
# You need to run the following command to generate a Python ui file, e.g.
#     pyuic6 form.ui -o ui_form.py


def main():
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.reinit_model()
    widget.center_on_screen()
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
