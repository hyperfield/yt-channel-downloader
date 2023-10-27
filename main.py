#!/usr/bin/env python3

# This Python file uses the following encoding: utf-8
import sys
import certifi
import os
from PySide6.QtWidgets import QApplication

from classes.mainwindow import MainWindow


os.environ['SSL_CERT_FILE'] = certifi.where()

# Important:
# You need to run the following command to generate the ui_form.py file
#     pyside6-uic form.ui -o ui_form.py, or
#     pyside2-uic form.ui -o ui_form.py

# os.environ["PYQT_DEBUG_PLUGINS"] = "1"


def main():
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.reinit_model()
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
