# Author: hyperfield
# Email: inbox@quicknode.net
# Project: YT Channel Downloader
# Description: This module contains the class SettingsDialog
# License: MIT License

from ..ui.ui_settings import Ui_Settings
from .settings_manager import SettingsManager

from PyQt6.QtWidgets import QDialog, QFileDialog, QSpinBox, QLabel, QHBoxLayout, QVBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


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
        self._initializing = True
        self._saved_snapshot = {}
        self._init_channel_limit_controls()
        # Give the right-hand panel more vertical space for limits + checkboxes
        self.ui.verticalLayout.setSpacing(10)
        self.ui.layoutWidget_7.setMinimumHeight(220)

        self.ui.browse_btn.clicked.connect(self.browse_directory)
        self.ui.close_button.clicked.connect(self.close)
        self.ui.proxy_server_type.currentIndexChanged.connect(self.toggle_proxy_fields)
        self.ui.save_button.clicked.connect(self.save_settings)
        self.ui.check_audio_only.stateChanged.connect(self.toggle_video_fields)

        self.default_directory = self.settings_manager.set_default_directory()

        self.populate_ui_from_settings()
        self.toggle_proxy_fields()
        self.toggle_video_fields()
        self._saved_snapshot = self._gather_ui_settings()
        self._initializing = False
        self._connect_dirty_signals()
        self._update_save_button()

    def _init_channel_limit_controls(self):
        """Add controls for channel fetch limit to the existing layout."""
        # Match row height to existing dropdowns for consistent alignment.
        combo_height = self.ui.pref_vid_format_dropdown.sizeHint().height()
        combo_font = self.ui.pref_vid_format_dropdown.font()
        limits_container = QVBoxLayout()
        limits_container.setSpacing(8)
        limits_container.setContentsMargins(0, 0, 0, 0)

        self.channel_limit_layout = QHBoxLayout()
        self.channel_limit_layout.setContentsMargins(0, 0, 0, 0)
        self.channel_limit_label = QLabel("Max videos fetched per channel:")
        self.channel_limit_label.setFont(self.font())
        self.channel_limit_label.setMinimumHeight(combo_height)
        self.channel_limit_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.channel_limit_spin = QSpinBox()
        self.channel_limit_spin.setRange(1, 50000)
        self.channel_limit_spin.setSingleStep(1)
        self.channel_limit_spin.setToolTip("Higher limits may be slow on very large channels.")
        spin_font = QFont(combo_font.family(), combo_font.pointSize())
        self.channel_limit_spin.setFont(spin_font)
        self.channel_limit_spin.setFixedHeight(combo_height)
        self.channel_limit_layout.addWidget(self.channel_limit_label, 0)
        self.channel_limit_layout.addStretch(1)
        self.channel_limit_layout.addWidget(self.channel_limit_spin, 0, Qt.AlignmentFlag.AlignRight)
        self.channel_limit_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        limits_container.addLayout(self.channel_limit_layout)
        limits_container.addSpacing(int(combo_height * 1.5))
        # Playlist limit directly beneath
        self.playlist_limit_layout = QHBoxLayout()
        self.playlist_limit_layout.setContentsMargins(0, 0, 0, 0)
        self.playlist_limit_label = QLabel("Max videos fetched per playlist:")
        self.playlist_limit_label.setFont(self.font())
        self.playlist_limit_label.setMinimumHeight(combo_height)
        self.playlist_limit_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.playlist_limit_spin = QSpinBox()
        self.playlist_limit_spin.setRange(1, 50000)
        self.playlist_limit_spin.setSingleStep(1)
        self.playlist_limit_spin.setToolTip("Higher limits may be slow on very large playlists.")
        self.playlist_limit_spin.setFont(spin_font)
        self.playlist_limit_spin.setFixedHeight(combo_height)
        self.playlist_limit_layout.addWidget(self.playlist_limit_label, 0)
        self.playlist_limit_layout.addStretch(1)
        self.playlist_limit_layout.addWidget(self.playlist_limit_spin, 0, Qt.AlignmentFlag.AlignRight)
        self.playlist_limit_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        limits_container.addLayout(self.playlist_limit_layout)
        # Insert grouped limits at the top of the right-hand vertical layout
        self.ui.verticalLayout.insertLayout(0, limits_container)
        # Add a breathing room before the checkboxes beneath.
        self.ui.verticalLayout.insertSpacing(1, 32)

    def toggle_video_fields(self):
        is_checked = self.ui.check_audio_only.isChecked()
        self.ui.pref_vid_format_dropdown.setDisabled(is_checked)
        self.ui.pref_vid_quality_dropdown.setDisabled(is_checked)
        self.ui.pref_aud_format_dropdown.setEnabled(is_checked)
        self.ui.pref_aud_quality_dropdown.setEnabled(is_checked)
        self._mark_dirty()

    def browse_directory(self):
        dialog = QFileDialog(self)
        options = dialog.options()
        directory = dialog.getExistingDirectory(
            self, "Select Directory", "", options=options)
        if directory:
            self.ui.save_downloads_edit.setText(directory)
            self._mark_dirty()

    def toggle_proxy_fields(self):
        current_text = self.ui.proxy_server_type.currentText()
        is_proxy_enabled = current_text != "None"
        self.ui.proxy_server_addr.setDisabled(not is_proxy_enabled)
        self.ui.proxy_server_port.setDisabled(not is_proxy_enabled)
        if not is_proxy_enabled:
            self.ui.proxy_server_addr.clear()
            self.ui.proxy_server_port.clear()
        self._mark_dirty()

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
        # show_thumbnails currently managed via main window toggle; keep in sync with stored value
        channel_limit = user_settings.get('channel_fetch_limit')
        if channel_limit:
            try:
                self.channel_limit_spin.setValue(int(channel_limit))
            except (TypeError, ValueError):
                pass
        playlist_limit = user_settings.get('playlist_fetch_limit')
        if playlist_limit:
            try:
                self.playlist_limit_spin.setValue(int(playlist_limit))
            except (TypeError, ValueError):
                pass
        # Reset dirty tracking after populate
        self._saved_snapshot = self._gather_ui_settings()
        self._initializing = False
        self._update_save_button()

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
            'show_thumbnails': self.settings_manager.settings.get('show_thumbnails', True),
            'audio_only': self.ui.check_audio_only.isChecked(),
            # Preserve opt-out flags that aren't represented in the UI
            'suppress_node_runtime_warning': self.settings_manager.settings.get('suppress_node_runtime_warning', False),
            'dont_show_login_prompt': self.settings_manager.settings.get('dont_show_login_prompt', False),
            'downloads_completed': self.settings_manager.settings.get('downloads_completed', 0),
            'support_prompt_next_at': self.settings_manager.settings.get('support_prompt_next_at', 50),
            # Channel fetch tuning (no UI fields yet, just preserve them)
            'channel_fetch_limit': self.channel_limit_spin.value(),
            'playlist_fetch_limit': self.playlist_limit_spin.value(),
            'channel_fetch_batch_size': self.settings_manager.settings.get('channel_fetch_batch_size'),
        }
        self.update_settings(new_settings)
        self._saved_snapshot = self._gather_ui_settings()
        self._update_save_button()

    def get_settings(self):
        return self.settings_manager.settings

    def update_settings(self, new_settings):
        merged_settings = {**self.settings_manager.settings, **new_settings}
        self.settings_manager.settings = merged_settings
        self.settings_manager.save_settings_to_file(merged_settings)

    # ------------------------------------------------------------------ #
    # Dirty tracking
    # ------------------------------------------------------------------ #
    def _connect_dirty_signals(self):
        """Connect UI controls to dirty tracking."""
        self.ui.save_downloads_edit.textChanged.connect(self._mark_dirty)
        self.ui.pref_vid_format_dropdown.currentIndexChanged.connect(self._mark_dirty)
        self.ui.pref_aud_format_dropdown.currentIndexChanged.connect(self._mark_dirty)
        self.ui.pref_vid_quality_dropdown.currentIndexChanged.connect(self._mark_dirty)
        self.ui.pref_aud_quality_dropdown.currentIndexChanged.connect(self._mark_dirty)
        self.ui.proxy_server_type.currentIndexChanged.connect(self._mark_dirty)
        self.ui.proxy_server_addr.textChanged.connect(self._mark_dirty)
        self.ui.proxy_server_port.textChanged.connect(self._mark_dirty)
        self.ui.check_download_thumbnails.stateChanged.connect(self._mark_dirty)
        self.ui.check_audio_only.stateChanged.connect(self._mark_dirty)
        self.channel_limit_spin.valueChanged.connect(self._mark_dirty)
        self.playlist_limit_spin.valueChanged.connect(self._mark_dirty)

    def _gather_ui_settings(self):
        """Snapshot of editable settings for dirty comparison."""
        proxy_type = self.ui.proxy_server_type.currentText()
        proxy_addr = self.ui.proxy_server_addr.text().strip()
        proxy_port = self.ui.proxy_server_port.text().strip()
        if proxy_type == "None":
            proxy_addr = ''
            proxy_port = ''
        return {
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
            'channel_fetch_limit': self.channel_limit_spin.value(),
            'playlist_fetch_limit': self.playlist_limit_spin.value(),
        }

    def _mark_dirty(self):
        """Enable Save when user changes a value."""
        if self._initializing:
            return
        self._update_save_button()

    def _update_save_button(self):
        """Update Save button enabled state based on changes."""
        if self._initializing:
            self.ui.save_button.setEnabled(False)
            return
        current = self._gather_ui_settings()
        is_dirty = current != self._saved_snapshot
        self.ui.save_button.setEnabled(is_dirty)
