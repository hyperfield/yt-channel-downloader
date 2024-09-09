import json
from appdirs import user_config_dir
import os
import platform
from pathlib import Path

from config.constants import DEFAULT_VIDEO_FORMAT, DEFAULT_AUDIO_FORMAT, \
    DEFAULT_VIDEO_QUALITY, DEFAULT_AUDIO_QUALITY


class SettingsManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
            cls._instance.config_directory = \
                cls._instance.get_config_directory()
            cls._instance.config_file_path = \
                os.path.join(cls._instance.config_directory,
                             'user_settings.json')
            cls._instance.settings = cls._instance.load_settings()
        return cls._instance

    def get_config_directory(self):
        app_dir_name = "yt_chan_dl"
        config_directory = user_config_dir(app_dir_name)
        os.makedirs(config_directory, exist_ok=True)
        return config_directory

    def load_settings(self):
        return self.read_settings_from_file()

    def read_settings_from_file(self):
        try:
            with open(self.config_file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            default_settings = self.load_default_settings()
            self.save_settings_to_file(default_settings)
            return default_settings

    def set_default_directory(self):
        if platform.system() == 'Windows':
            default_dir = Path(os.environ['USERPROFILE']) / 'Downloads'
        else:
            default_dir = Path.home() / 'Downloads'
        return str(default_dir)

    def load_default_settings(self):
        return {
            'download_directory': self.set_default_directory(),
            'preferred_video_format': DEFAULT_VIDEO_FORMAT,
            'preferred_audio_format': DEFAULT_AUDIO_FORMAT,
            'preferred_video_quality': DEFAULT_VIDEO_QUALITY,
            'preferred_audio_quality': DEFAULT_AUDIO_QUALITY,
            'proxy_server_type': '',
            'proxy_server_addr': '',
            'proxy_server_port': '',
            'audio_only': False,
            'dont_show_login_prompt': False
        }

    def save_settings_to_file(self, settings):
        with open(self.config_file_path, 'w') as f:
            json.dump(settings, f)
