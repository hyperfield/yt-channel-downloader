from PySide6.QtWidgets import QDialog
from PySide6.QtWidgets import QFileDialog
from ui_settings import Ui_Settings

from .settings_manager import SettingsManager


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.settings_manager = SettingsManager()
        self.ui = Ui_Settings()
        self.ui.setupUi(self)
        self.ui.browse_btn.clicked.connect(self.browse_directory)
        self.ui.close_button.clicked.connect(self.close)
        self.ui.proxy_server_type.currentIndexChanged.connect(
            self.toggle_proxy_fields)
        self.ui.save_button.clicked.connect(
            self.save_settings)
        self.toggle_proxy_fields()
        self.toggle_video_fields()
        self.ui.check_audio_only.stateChanged.connect(
            self.toggle_video_fields)
        self.toggle_video_fields()
        self.populate_ui_from_settings()

    def toggle_video_fields(self):
        """Disable or Enable video related dropdowns based on checkbox
        state."""
        is_checked = self.ui.check_audio_only.isChecked()
        self.ui.pref_vid_format_dropdown.setDisabled(is_checked)
        self.ui.pref_vid_quality_dropdown.setDisabled(is_checked)
        self.ui.pref_aud_format_dropdown.setEnabled(is_checked)
        self.ui.pref_aud_quality_dropdown.setEnabled(is_checked)

    def browse_directory(self):
        options = QFileDialog.Options()
        directory = QFileDialog.getExistingDirectory(
          self, "Select Directory", "", options=options)
        if directory:
            self.ui.save_downloads_edit.setText(directory)

    def toggle_proxy_fields(self, index=-1):
        if index == -1:
            current_text = self.ui.proxy_server_type.currentText()
        else:
            current_text = self.ui.proxy_server_type.itemText(index)

        if current_text == "None":
            self.ui.proxy_server_addr.setDisabled(True)
            self.ui.proxy_server_port.setDisabled(True)
        else:
            self.ui.proxy_server_addr.setDisabled(False)
            self.ui.proxy_server_port.setDisabled(False)

    def populate_ui_from_settings(self):
        user_settings = self.settings_manager.settings

        default_directory = self.settings_manager.set_default_directory()
        self.ui.save_downloads_edit.setText(
            user_settings.get('download_directory', default_directory))

        index = self.ui.pref_vid_format_dropdown.findText(
            user_settings.get('preferred_video_format'))
        if index != -1:
            self.ui.pref_vid_format_dropdown.setCurrentIndex(index)

        index = self.ui.pref_aud_format_dropdown.findText(
            user_settings.get('preferred_audio_format'))
        if index != -1:
            self.ui.pref_aud_format_dropdown.setCurrentIndex(index)

        index = self.ui.pref_vid_quality_dropdown.findText(
            user_settings.get('preferred_video_quality'))
        if index != -1:
            self.ui.pref_vid_quality_dropdown.setCurrentIndex(index)

        index = self.ui.pref_aud_quality_dropdown.findText(
            user_settings.get('preferred_audio_quality'))
        if index != -1:
            self.ui.pref_aud_quality_dropdown.setCurrentIndex(index)

        index = self.ui.proxy_server_type.findText(
            user_settings.get('proxy_server_type'))
        if index != -1:
            self.ui.proxy_server_type.setCurrentIndex(index)

        self.ui.proxy_server_addr.setText(
            user_settings.get('proxy_server_addr'))
        self.ui.proxy_server_port.setText(
            user_settings.get('proxy_server_port'))

        self.ui.check_audio_only.setChecked(
            user_settings.get('audio_only'))

    def save_settings(self):
        self.settings_manager.settings = {
            'download_directory': self.ui.save_downloads_edit.text(),
            'preferred_video_format':
                self.ui.pref_vid_format_dropdown.currentText(),
            'preferred_audio_format':
                self.ui.pref_aud_format_dropdown.currentText(),
            'preferred_video_quality':
                self.ui.pref_vid_quality_dropdown.currentText(),
            'preferred_audio_quality':
                self.ui.pref_aud_quality_dropdown.currentText(),
            'proxy_server_type': self.ui.proxy_server_type.currentText(),
            'proxy_server_addr': self.ui.proxy_server_addr.text(),
            'proxy_server_port': self.ui.proxy_server_port.text(),
            'audio_only': self.ui.check_audio_only.isChecked(),
        }
        self.settings_manager.save_settings_to_file(
            self.settings_manager.settings)
