# Author: hyperfield
# Email: inbox@quicknode.net
# Project: YT Channel Downloader
# Description: Custom dialog helper.
# License: MIT License

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTextBrowser,
    QVBoxLayout,
)


class CustomDialog(QDialog):
    def __init__(self, title, message, icon=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)

        QBtn = QDialogButtonBox.StandardButton.Ok
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)

        self.layout = QVBoxLayout()

        if icon:
            icon_label = QLabel()
            icon_label.setPixmap(icon.pixmap(32, 32))
            self.layout.addWidget(icon_label)

        dlg_message = QTextBrowser()
        dlg_message.setOpenExternalLinks(True)
        dlg_message.setText(message)
        dlg_message.setMinimumWidth(380)
        dlg_message.setMinimumHeight(120)
        dlg_message.setSizeAdjustPolicy(QTextBrowser.SizeAdjustPolicy.AdjustToContents)

        self.layout.addWidget(dlg_message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)
