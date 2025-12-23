import json
import os
import platform
from pathlib import Path

from appdirs import user_config_dir

from ..config.constants import DEFAULT_VIDEO_FORMAT, DEFAULT_AUDIO_FORMAT, \
    DEFAULT_VIDEO_QUALITY, DEFAULT_AUDIO_QUALITY, DEFAULT_CHANNEL_FETCH_LIMIT, \
    DEFAULT_PLAYLIST_FETCH_LIMIT, CHANNEL_FETCH_BATCH_SIZE


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
        defaults = self.load_default_settings()
        merged_settings = {**defaults, **settings}
        self._apply_environment_proxy(merged_settings)
        return merged_settings

    def read_settings_from_file(self):
        try:
            with open(self.config_file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            default_settings = self.load_default_settings()
            self._apply_environment_proxy(default_settings)
            self.save_settings_to_file(default_settings)
            return default_settings
        except json.JSONDecodeError:
            self._backup_corrupt_settings_file()
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
            'show_thumbnails': True,
            'suppress_node_runtime_warning': False,
            # Download milestone prompts
            'downloads_completed': 0,
            'support_prompt_next_at': 30,
            'dont_show_login_prompt': False,
            'channel_fetch_limit': DEFAULT_CHANNEL_FETCH_LIMIT,
            'playlist_fetch_limit': DEFAULT_PLAYLIST_FETCH_LIMIT,
            'channel_fetch_batch_size': CHANNEL_FETCH_BATCH_SIZE,
        }

    def save_settings_to_file(self, settings):
        with open(self.config_file_path, 'w') as f:
            json.dump(settings, f)
        self._apply_environment_proxy(settings)

    def _backup_corrupt_settings_file(self):
        if not os.path.exists(self.config_file_path):
            return
        backup_path = f"{self.config_file_path}.corrupt"
        try:
            os.replace(self.config_file_path, backup_path)
        except OSError:
            pass

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
