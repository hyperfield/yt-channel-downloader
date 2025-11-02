"""YT Channel Downloader package."""

from __future__ import annotations

from importlib import metadata


_FALLBACK_VERSION = "0.5.5"


def _detect_version() -> str:
    try:
        return metadata.version("yt-channel-downloader")
    except metadata.PackageNotFoundError:
        return _FALLBACK_VERSION


__all__ = ["__version__"]
__version__ = _detect_version()
