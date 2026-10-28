from datetime import date
from importlib import metadata

from yt_channel_downloader import __release_date__, __version__


def test_package_version_matches_installed_metadata():
    assert __version__ == metadata.version("yt-channel-downloader")


def test_release_date_uses_iso_format():
    assert date.fromisoformat(__release_date__).isoformat() == __release_date__
