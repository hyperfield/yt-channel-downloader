import json
import ipaddress
import os
import platform
import re
import tempfile
from pathlib import Path

from appdirs import user_config_dir

from ..config.constants import DEFAULT_VIDEO_FORMAT, DEFAULT_AUDIO_FORMAT, \
    DEFAULT_VIDEO_QUALITY, DEFAULT_AUDIO_QUALITY, DEFAULT_CHANNEL_FETCH_LIMIT, \
    DEFAULT_PLAYLIST_FETCH_LIMIT, CHANNEL_FETCH_BATCH_SIZE, PROXY_SCHEMES, settings_map


class SettingsManager:
    _instance = None
    PROXY_SCHEMES = PROXY_SCHEMES
    PROXY_ENV_KEYS = ('http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
                      'ALL_PROXY', 'socks_proxy', 'SOCKS_PROXY')

    def __new__(cls):
        if cls._instance is None:
            instance = super(SettingsManager, cls).__new__(cls)
            instance._original_proxy_environment = {key: os.environ.get(key) for key in cls.PROXY_ENV_KEYS}
            instance.config_directory = instance.get_config_directory()
            instance.config_file_path = \
                os.path.join(instance.config_directory,
                             'user_settings.json')
            instance.settings = instance.load_settings()
            cls._instance = instance
        return cls._instance

    def get_config_directory(self):
        app_dir_name = "yt_chan_dl"
        config_directory = user_config_dir(app_dir_name)
        os.makedirs(config_directory, exist_ok=True)
        return config_directory

    def load_settings(self):
        settings = self.read_settings_from_file()
        merged_settings = self.normalize_settings(settings)
        self._apply_environment_proxy(merged_settings)
        return merged_settings

    def read_settings_from_file(self):
        try:
            with open(self.config_file_path, 'r') as f:
                settings = json.load(f)
            if not isinstance(settings, dict):
                raise ValueError('Settings must be a JSON object')
            return settings
        except FileNotFoundError:
            default_settings = self.load_default_settings()
            self._apply_environment_proxy(default_settings)
            self.save_settings_to_file(default_settings)
            return default_settings
        except ValueError:
            self._backup_corrupt_settings_file()
            default_settings = self.load_default_settings()
            self._apply_environment_proxy(default_settings)
            self.save_settings_to_file(default_settings)
            return default_settings

    def set_default_directory(self):
        if platform.system() == 'Windows':
            default_dir = Path(os.environ.get('USERPROFILE') or Path.home()) / 'Downloads'
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
            'enable_size_estimation': True,
            'suppress_node_runtime_warning': False,
            # Download milestone prompts
            'downloads_completed': 0,
            'support_prompt_next_at': 30,
            'support_prompt_last_shown_at': 0,
            'dont_show_login_prompt': False,
            'channel_fetch_limit': DEFAULT_CHANNEL_FETCH_LIMIT,
            'playlist_fetch_limit': DEFAULT_PLAYLIST_FETCH_LIMIT,
            'channel_fetch_batch_size': CHANNEL_FETCH_BATCH_SIZE,
        }

    def normalize_settings(self, settings):
        """Repair invalid saved values while retaining settings outside this dialog."""
        defaults = self.load_default_settings()
        result = {**defaults, **settings}
        for key, choices in settings_map.items():
            if not isinstance(result[key], str) or result[key] not in choices:
                result[key] = defaults[key]
        for key, default in defaults.items():
            if isinstance(default, bool):
                value = result[key]
                if isinstance(value, str) and value.strip().lower() in ('true', 'false'):
                    value = value.strip().lower() == 'true'
                result[key] = value if isinstance(value, bool) else default
        for key, minimum, maximum in (
            ('channel_fetch_limit', 1, 50000), ('playlist_fetch_limit', 1, 50000),
            ('channel_fetch_batch_size', 1, 50000), ('downloads_completed', 0, None),
            ('support_prompt_next_at', 1, None), ('support_prompt_last_shown_at', 0, None),
        ):
            value = result[key]
            try:
                if isinstance(value, bool) or isinstance(value, float):
                    raise ValueError('Expected an integer')
                value = int(value)
                if value < minimum:
                    raise ValueError('Value below minimum')
                result[key] = min(value, maximum) if maximum is not None else value
            except (TypeError, ValueError, OverflowError):
                result[key] = defaults[key]
        directory = result['download_directory']
        if not isinstance(directory, str) or not directory.strip() or '\x00' in directory:
            directory = defaults['download_directory']
        result['download_directory'] = os.path.abspath(os.path.expanduser(directory.strip()))
        proxy_type = result['proxy_server_type']
        supported_types = ('None', *(name.upper() for name in self.PROXY_SCHEMES))
        if proxy_type not in supported_types:
            result['proxy_server_type'] = 'None'
        for key in ('proxy_server_addr', 'proxy_server_port'):
            result[key] = str(result[key]).strip() if isinstance(result[key], (str, int)) else ''
        try:
            self.validate_proxy_settings(result)
        except ValueError:
            result['proxy_server_type'] = 'None'
        return result

    @staticmethod
    def validate_proxy_settings(settings):
        if settings['proxy_server_type'] == 'None':
            return
        server = settings['proxy_server_addr']
        if not server or any(character in server for character in '/?#'):
            raise ValueError('Enter a proxy hostname or IP address, without a URL scheme or path.')
        credentials, separator, host = server.rpartition('@')
        if separator:
            if not credentials or server.count('@') > 1:
                raise ValueError('Use user:password@host, with special characters URL-encoded.')
        else:
            host = server
        if not host:
            raise ValueError('Enter a proxy hostname or IP address.')
        if ':' in host:
            host = str(ipaddress.IPv6Address(host.strip('[]')))
        elif not re.fullmatch(r'[A-Za-z0-9._-]+', host.encode('idna').decode('ascii')):
            raise ValueError('Enter a valid proxy hostname or IP address.')
        settings['proxy_server_addr'] = f'{credentials}@{host}' if separator else host
        try:
            port = int(settings['proxy_server_port'])
        except ValueError as error:
            raise ValueError('Enter a proxy port between 1 and 65535.') from error
        if not 1 <= port <= 65535:
            raise ValueError('Enter a proxy port between 1 and 65535.')
        settings['proxy_server_port'] = str(port)

    def save_settings_to_file(self, settings):
        """Replace the settings file only after the complete new JSON is written."""
        path = Path(self.config_file_path)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                             prefix=path.name + '.', suffix='.tmp', delete=False) as f:
                temporary_path = f.name
                json.dump(settings, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary_path, path)
        finally:
            if temporary_path and os.path.exists(temporary_path):
                os.unlink(temporary_path)
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
    def _proxy_settings_values(self, settings=None):
        active_settings = self.settings if settings is None else settings
        return (
            (active_settings.get('proxy_server_type') or '').strip().lower(),
            (active_settings.get('proxy_server_addr') or '').strip(),
            str(active_settings.get('proxy_server_port') or '').strip(),
        )

    def _proxy_scheme(self, proxy_type: str):
        if proxy_type in ('', 'none'):
            return None
        return self.PROXY_SCHEMES.get(proxy_type)

    def build_proxy_url(self, settings=None):
        proxy_type, proxy_addr, proxy_port = self._proxy_settings_values(settings)
        scheme = self._proxy_scheme(proxy_type)
        if not all((scheme, proxy_addr, proxy_port)):
            return None
        credentials, separator, host = proxy_addr.rpartition('@')
        if not separator:
            host = proxy_addr
        if ':' in host and not host.startswith('['):
            host = f'[{host}]'
        proxy_addr = f'{credentials}@{host}' if separator else host
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
        if not hasattr(self, '_original_proxy_environment'):
            self._original_proxy_environment = {key: os.environ.get(key) for key in self.PROXY_ENV_KEYS}
        if proxy_url:
            for key in self.PROXY_ENV_KEYS:
                os.environ[key] = proxy_url
        else:
            for key, value in self._original_proxy_environment.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
