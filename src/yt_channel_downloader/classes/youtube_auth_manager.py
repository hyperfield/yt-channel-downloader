from typing import Optional, Tuple

from PyQt6.QtCore import QObject, pyqtSignal as Signal
import yt_dlp

from .browser_config import BrowserConfig
from .logger import get_logger


_DEFAULT_TEST_URL = 'https://www.youtube.com/playlist?list=WL'
_LOGIN_COOKIE_DOMAINS = (
    'youtube.com',
    'google.com',
)
_LOGIN_COOKIE_NAMES = {
    'SID',
    'SAPISID',
    'HSID',
    'SSID',
    'APISID',
    '__Secure-3PSID',
    '__Secure-1PSID',
    '__Secure-3PSIDTS',
    '__Secure-1PSIDTS',
}


class YoutubeAuthManager(QObject):
    """Manage browser-cookie based YouTube authentication for yt-dlp calls."""
    login_state_changed = Signal(bool)
    login_completed = Signal(bool, str)

    def __init__(self, settings_manager, parent: Optional[QObject] = None) -> None:
        """Restore any saved browser-cookie configuration and validate it."""
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
        """Return True when browser-cookie settings are stored."""
        return self._browser_config is not None

    @property
    def is_logged_in(self) -> bool:
        """Return the last validated logged-in state."""
        return self._logged_in

    @property
    def browser_config(self) -> Optional[BrowserConfig]:
        """Return the active browser-cookie configuration, if any."""
        return self._browser_config

    def configure(self, config: BrowserConfig) -> None:
        """Validate and persist a browser-cookie configuration."""
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
        """Remove any stored browser-cookie configuration and logged-in state."""
        self._browser_config = None
        self._logged_in = False
        settings = self._settings_manager.settings
        settings['youtube_browser_config'] = {}
        self._settings_manager.save_settings_to_file(settings)
        self.login_state_changed.emit(False)
        self._logger.info("Cleared stored browser configuration")

    def get_yt_dlp_options(self) -> dict:
        """Return yt-dlp options for reusing the configured browser cookies."""
        if not self._browser_config:
            return {}
        return {'cookiesfrombrowser': self._browser_config.to_yt_dlp_tuple()}

    @staticmethod
    def _config_summary(config: BrowserConfig) -> str:
        """Build a compact log-friendly description of a browser config."""
        return (
            f"browser={config.browser!r} "
            f"profile={config.profile or '<default>'!r} "
            f"keyring={config.keyring or '<auto>'!r} "
            f"container={config.container or '<none>'!r}"
        )

    @staticmethod
    def _has_login_cookie(jar) -> bool:
        """Return True when the cookie jar looks authenticated for YouTube."""
        return any(
            any((cookie.domain or '').endswith(domain) for domain in _LOGIN_COOKIE_DOMAINS)
            and cookie.name in _LOGIN_COOKIE_NAMES
            for cookie in jar
        )

    def _validate_browser_config(self, config: BrowserConfig) -> Tuple[bool, str]:
        """Verify that a browser-cookie configuration yields usable auth cookies."""
        self._logger.info("Validating browser cookies with %s", self._config_summary(config))
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

                logged_in = self._has_login_cookie(jar)
                if logged_in:
                    self._logger.info(
                        "Detected supported login cookies for browser '%s'",
                        config.browser,
                    )

                if not logged_in:
                    try:
                        ydl.extract_info(_DEFAULT_TEST_URL, download=False)
                    except Exception as exc:
                        self._logger.info(
                            "Private playlist probe failed for browser '%s': %s",
                            config.browser,
                            exc,
                        )
                        self._logger.debug(
                            "Private playlist probe failed for browser '%s'",
                            config.browser,
                            exc_info=True,
                        )
                    else:
                        self._logger.info(
                            "Browser '%s' passed authenticated playlist probe",
                            config.browser,
                        )
                        logged_in = True

                if not logged_in:
                    self._logger.warning("Cookies from browser '%s' did not include login tokens", config.browser)
                    return False, (
                        'The selected browser profile did not provide YouTube login cookies. '
                        'Ensure you are signed in to YouTube within that browser profile and try again.'
                    )

                return True, ''
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("Failed to validate browser cookies for '%s': %s", config.browser, exc)
            return False, str(exc)
