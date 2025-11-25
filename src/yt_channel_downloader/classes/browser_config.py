from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class BrowserConfig:
    browser: str
    profile: Optional[str] = None
    keyring: Optional[str] = None
    container: Optional[str] = None

    def to_settings_dict(self) -> dict:
        return {
            'browser': self.browser,
            'profile': self.profile,
            'keyring': self.keyring,
            'container': self.container,
        }

    @classmethod
    def from_settings(cls, data: Optional[dict]) -> Optional['BrowserConfig']:
        if not data or 'browser' not in data:
            return None
        return cls(
            browser=data.get('browser', ''),
            profile=data.get('profile') or None,
            keyring=(data.get('keyring') or None),
            container=data.get('container') or None,
        )

    def to_yt_dlp_tuple(self) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
        keyring = self.keyring.upper() if self.keyring else None
        return (
            self.browser,
            self.profile,
            keyring,
            self.container,
        )
