from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    tag_name: str
    html_url: str
    body: Optional[str]
    asset_url: Optional[str]
    asset_name: Optional[str]

    @property
    def display_version(self) -> str:
        return self.tag_name or self.version
