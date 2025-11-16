# Author: hyperfield
# Email: inbox@quicknode.net
# Project: YT Channel Downloader
# Description: This module contains the class SettingsDialog
# License: MIT License

from ..ui.ui_settings import Ui_Settings
from .settings_manager import SettingsManager

from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtCore import Qt


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)

        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlags(Qt.WindowType.Window)

        # self.setStyleSheet("""
        #     * {
        #         font-family: "Arial";
        #         font-size: 14pt;
        #     }
        #     SettingsDialog {
        #         background-color: #f0f0f0;
        #         border-radius: 10px;
        #         box-shadow: 5px 5px 15px rgba(0, 0, 0, 0.2);
        #     }
        #     QGroupBox {
        #         border: 1px solid #d3d3d3; 
        #         padding: 10px;
        #         margin-top: 10px;
        #         border-radius: 5px;
        #     }
        #     QPushButton {
        #         background-color: #0066ff;
        #         color: white;
        #         border-radius: 5px;
        #         padding: 5px 10px;
        #     }
        #     QPushButton:hover {
        #         background-color: #0000b3;
        #     }
        # """)

        self.settings_manager = SettingsManager()
        self.ui = Ui_Settings()
        self.ui.setupUi(self)

        self.ui.browse_btn.clicked.connect(self.browse_directory)
        self.ui.close_button.clicked.connect(self.close)
        self.ui.proxy_server_type.currentIndexChanged.connect(self.toggle_proxy_fields)
        self.ui.save_button.clicked.connect(self.save_settings)
        self.ui.check_audio_only.stateChanged.connect(self.toggle_video_fields)

        self.default_directory = self.settings_manager.set_default_directory()

        self.populate_ui_from_settings()
        self.toggle_proxy_fields()
        self.toggle_video_fields()

    def toggle_video_fields(self):
        is_checked = self.ui.check_audio_only.isChecked()
        self.ui.pref_vid_format_dropdown.setDisabled(is_checked)
        self.ui.pref_vid_quality_dropdown.setDisabled(is_checked)
        self.ui.pref_aud_format_dropdown.setEnabled(is_checked)
        self.ui.pref_aud_quality_dropdown.setEnabled(is_checked)

    def browse_directory(self):
        dialog = QFileDialog(self)
        options = dialog.options()
        directory = dialog.getExistingDirectory(
            self, "Select Directory", "", options=options)
        if directory:
            self.ui.save_downloads_edit.setText(directory)

    def toggle_proxy_fields(self):
        current_text = self.ui.proxy_server_type.currentText()
        is_proxy_enabled = current_text != "None"
        self.ui.proxy_server_addr.setDisabled(not is_proxy_enabled)
        self.ui.proxy_server_port.setDisabled(not is_proxy_enabled)
        if not is_proxy_enabled:
            self.ui.proxy_server_addr.clear()
            self.ui.proxy_server_port.clear()

    def populate_ui_from_settings(self):
        user_settings = self.get_settings()
        self.ui.save_downloads_edit.setText(user_settings.get('download_directory', self.default_directory))
        self.set_dropdown_index(self.ui.pref_vid_format_dropdown, user_settings.get('preferred_video_format'))
        self.set_dropdown_index(self.ui.pref_aud_format_dropdown, user_settings.get('preferred_audio_format'))
        self.set_dropdown_index(self.ui.pref_vid_quality_dropdown, user_settings.get('preferred_video_quality'))
        self.set_dropdown_index(self.ui.pref_aud_quality_dropdown, user_settings.get('preferred_audio_quality'))
        self.set_dropdown_index(self.ui.proxy_server_type, user_settings.get('proxy_server_type'))
        self.ui.proxy_server_addr.setText(user_settings.get('proxy_server_addr'))
        self.ui.proxy_server_port.setText(user_settings.get('proxy_server_port'))
        self.ui.check_audio_only.setChecked(user_settings.get('audio_only'))
        self.ui.check_download_thumbnails.setChecked(user_settings.get('download_thumbnail', False))


    def set_dropdown_index(self, dropdown, value):
        index = dropdown.findText(value)
        if index != -1:
            dropdown.setCurrentIndex(index)

    def save_settings(self):
        proxy_type = self.ui.proxy_server_type.currentText()
        proxy_addr = self.ui.proxy_server_addr.text().strip()
        proxy_port = self.ui.proxy_server_port.text().strip()

        if proxy_type == "None":
            proxy_addr = ''
            proxy_port = ''

        new_settings = {
            'download_directory': self.ui.save_downloads_edit.text(),
            'preferred_video_format': self.ui.pref_vid_format_dropdown.currentText(),
            'preferred_audio_format': self.ui.pref_aud_format_dropdown.currentText(),
            'preferred_video_quality': self.ui.pref_vid_quality_dropdown.currentText(),
            'preferred_audio_quality': self.ui.pref_aud_quality_dropdown.currentText(),
            'proxy_server_type': proxy_type,
            'proxy_server_addr': proxy_addr,
            'proxy_server_port': proxy_port,
            'download_thumbnail': self.ui.check_download_thumbnails.isChecked(),
            'audio_only': self.ui.check_audio_only.isChecked(),
            # Preserve opt-out flags that aren't represented in the UI
            'suppress_node_runtime_warning': self.settings_manager.settings.get('suppress_node_runtime_warning', False),
            'dont_show_login_prompt': self.settings_manager.settings.get('dont_show_login_prompt', False),
        }
        self.update_settings(new_settings)

    def get_settings(self):
        return self.settings_manager.settings

    def update_settings(self, new_settings):
        self.settings_manager.settings = new_settings
        self.settings_manager.save_settings_to_file(new_settings)
