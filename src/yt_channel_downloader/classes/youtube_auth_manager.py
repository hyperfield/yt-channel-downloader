from typing import Optional, Tuple

from PyQt6.QtCore import QObject, pyqtSignal as Signal
import yt_dlp

from .browser_config import BrowserConfig
from .logger import get_logger


_DEFAULT_TEST_URL = 'https://www.youtube.com/feed/history'
_LOGIN_COOKIE_NAMES = {
    'SAPISID',
    'HSID',
    'SSID',
    'APISID',
    '__Secure-3PSID',
    '__Secure-1PSID',
}


class YoutubeAuthManager(QObject):
    login_state_changed = Signal(bool)
    login_completed = Signal(bool, str)

    def __init__(self, settings_manager, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._settings_manager = settings_manager
        config = BrowserConfig.from_settings(
            self._settings_manager.settings.get('youtube_browser_config')
        )
        self._browser_config: Optional[BrowserConfig] = config
        self._logged_in = False
        self._logger = get_logger("YoutubeAuthManager")
        if self._browser_config:
            self._logged_in, _ = self._validate_browser_config(self._browser_config)
            if self._logged_in:
                self._logger.info("Restored browser configuration for '%s'", self._browser_config.browser)

    @property
    def is_configured(self) -> bool:
        return self._browser_config is not None

    @property
    def is_logged_in(self) -> bool:
        return self._logged_in

    @property
    def browser_config(self) -> Optional[BrowserConfig]:
        return self._browser_config

    def configure(self, config: BrowserConfig) -> None:
        success, message = self._validate_browser_config(config)
        previous_state = self._logged_in
        if success:
            self._browser_config = config
            settings = self._settings_manager.settings
            settings['youtube_browser_config'] = config.to_settings_dict()
            self._settings_manager.save_settings_to_file(settings)
            self._logged_in = True
            self._logger.info("Configured yt-dlp cookies-from-browser for '%s'", config.browser)
        self.login_completed.emit(success, message)
        if self._logged_in != previous_state:
            self.login_state_changed.emit(self._logged_in)

    def clear(self) -> None:
        self._browser_config = None
        self._logged_in = False
        settings = self._settings_manager.settings
        settings['youtube_browser_config'] = {}
        self._settings_manager.save_settings_to_file(settings)
        self.login_state_changed.emit(False)
        self._logger.info("Cleared stored browser configuration")

    def get_yt_dlp_options(self) -> dict:
        if not self._browser_config:
            return {}
        return {'cookiesfrombrowser': self._browser_config.to_yt_dlp_tuple()}

    def _validate_browser_config(self, config: BrowserConfig) -> Tuple[bool, str]:
        params = {
            'quiet': True,
            'skip_download': True,
            'cookiesfrombrowser': config.to_yt_dlp_tuple(),
        }
        try:
            with yt_dlp.YoutubeDL(params) as ydl:
                jar = ydl.cookiejar
                if not jar:
                    self._logger.warning("No cookies retrieved from browser '%s'", config.browser)
                    return False, 'No cookies were found for the selected browser/profile.'

                logged_in = any(
                    cookie.domain.endswith('youtube.com')
                    and cookie.name in _LOGIN_COOKIE_NAMES
                    for cookie in jar
                )

                if not logged_in:
                    # Attempt to confirm reachability of an authenticated page to provide better feedback
                    try:
                        ydl.extract_info(_DEFAULT_TEST_URL, download=False)
                    except Exception:
                        pass
                    self._logger.warning("Cookies from browser '%s' did not include login tokens", config.browser)
                    return False, (
                        'The selected browser profile did not provide YouTube login cookies. '
                        'Ensure you are signed in to YouTube within that browser profile and try again.'
                    )

                return True, ''
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("Failed to validate browser cookies for '%s': %s", config.browser, exc)
            return False, str(exc)
