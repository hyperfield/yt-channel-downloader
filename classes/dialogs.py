# Author: hyperfield
# Email: inbox@quicknode.net
# Project: YT Channel Downloader
# Description: This module contains dialog helpers for the UI.
# License: MIT License

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt

from .youtube_auth import BrowserConfig

BROWSER_CHOICES = [
    ('chrome', 'Chrome / Chromium'),
    ('firefox', 'Firefox'),
    ('brave', 'Brave'),
    ('edge', 'Microsoft Edge'),
    ('opera', 'Opera'),
    ('safari', 'Safari (macOS)'),
    ('vivaldi', 'Vivaldi'),
    ('whale', 'Naver Whale'),
]


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


class YoutubeCookiesDialog(QDialog):
    """Dialog allowing the user to configure cookies-from-browser settings."""

    def __init__(self, parent: QWidget | None = None, config: BrowserConfig | None = None):
        super().__init__(parent)
        self.setWindowTitle("Configure YouTube login")

        self.browser_combo = QComboBox(self)
        for key, label in BROWSER_CHOICES:
            self.browser_combo.addItem(label, userData=key)

        self.profile_input = QLineEdit(self)
        self.profile_input.setPlaceholderText("Optional. Leave blank for default profile.")

        self.keyring_input = QLineEdit(self)
        self.keyring_input.setPlaceholderText("Optional keyring backend (e.g. kwallet5, gnomekeyring).")
        self.container_input = QLineEdit(self)
        self.container_input.setPlaceholderText("Optional container name (Firefox Multi-Account).")

        if config:
            index = self.browser_combo.findData(config.browser)
            if index >= 0:
                self.browser_combo.setCurrentIndex(index)
            self.profile_input.setText(config.profile or "")
            self.keyring_input.setText(config.keyring or "")
            self.container_input.setText(config.container or "")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        form_layout = QFormLayout()
        form_layout.addRow("Browser", self.browser_combo)
        form_layout.addRow("Profile", self.profile_input)
        form_layout.addRow("Keyring", self.keyring_input)
        form_layout.addRow("Container", self.container_input)

        root_layout = QVBoxLayout(self)
        info_label = QLabel(
            "Select the browser profile that is already signed in to YouTube. "
            "yt-dlp will reuse its cookies to access private or age-restricted videos.",
            self,
        )
        info_label.setWordWrap(True)
        root_layout.addWidget(info_label)
        root_layout.addLayout(form_layout)
        root_layout.addWidget(buttons)

    def get_config(self) -> BrowserConfig:
        browser = self.browser_combo.currentData()
        profile = self.profile_input.text().strip() or None
        container = self.container_input.text().strip() or None
        keyring = self.keyring_input.text().strip() or None
        if keyring:
            keyring = keyring.lower()
        return BrowserConfig(
            browser=browser,
            profile=profile,
            keyring=keyring,
            container=container,
        )
