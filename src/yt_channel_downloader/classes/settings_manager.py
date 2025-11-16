import json
import os
import platform
from pathlib import Path

from appdirs import user_config_dir

from ..config.constants import DEFAULT_VIDEO_FORMAT, DEFAULT_AUDIO_FORMAT, \
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
        settings = self.read_settings_from_file()
        self._apply_environment_proxy(settings)
        return settings

    def read_settings_from_file(self):
        try:
            with open(self.config_file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            default_settings = self.load_default_settings()
            self._apply_environment_proxy(default_settings)
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
            'proxy_server_type': 'None',
            'proxy_server_addr': '',
            'proxy_server_port': '',
            'download_thumbnail': False,
            'audio_only': False,
            'suppress_node_runtime_warning': False,
            'dont_show_login_prompt': False
        }

    def save_settings_to_file(self, settings):
        with open(self.config_file_path, 'w') as f:
            json.dump(settings, f)
        self._apply_environment_proxy(settings)

    # ------------------------------------------------------------------ #
    # Proxy helpers
    # ------------------------------------------------------------------ #
    def build_proxy_url(self, settings=None):
        settings = settings or self.settings
        proxy_type = (settings.get('proxy_server_type') or '').strip().lower()
        proxy_addr = (settings.get('proxy_server_addr') or '').strip()
        proxy_port = (settings.get('proxy_server_port') or '').strip()

        if proxy_type in ('', 'none'):
            return None

        scheme_map = {
            'https': 'https',
            'socks4': 'socks4',
            'socks5': 'socks5',
        }
        scheme = scheme_map.get(proxy_type)
        if not scheme or not proxy_addr or not proxy_port:
            return None

        return f"{scheme}://{proxy_addr}:{proxy_port}"

    def build_requests_proxies(self, settings=None):
        proxy_url = self.build_proxy_url(settings=settings)
        if not proxy_url:
            return {}
        return {
            'http': proxy_url,
            'https': proxy_url,
        }

    def _apply_environment_proxy(self, settings):
        proxy_url = self.build_proxy_url(settings=settings)
        env_keys = ('http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'socks_proxy', 'SOCKS_PROXY')
        if proxy_url:
            for key in env_keys:
                os.environ[key] = proxy_url
        else:
            for key in env_keys:
                os.environ.pop(key, None)
