import pytest

pytest.importorskip("PyQt6")

from yt_channel_downloader.classes.download_thread import DownloadThread
from yt_channel_downloader.classes.mainwindow import MainWindow
from yt_channel_downloader.classes.settings_manager import SettingsManager


def _expect_equal(actual, expected):
    if actual != expected:
        pytest.fail(f"Expected {expected!r}, got {actual!r}")


class _DummyWindow:
    _thumbnail_candidate_url = staticmethod(MainWindow._thumbnail_candidate_url)
    _extract_youtube_id = staticmethod(MainWindow._extract_youtube_id)
    _iter_thumbnail_urls = MainWindow._iter_thumbnail_urls


def test_build_proxy_url_uses_supported_proxy_types():
    manager = object.__new__(SettingsManager)

    _expect_equal(
        SettingsManager.build_proxy_url(
            manager,
            {
                "proxy_server_type": "HTTPS",
                "proxy_server_addr": "proxy.example.com",
                "proxy_server_port": "8443",
            },
        ),
        "https://proxy.example.com:8443",
    )
    _expect_equal(
        SettingsManager.build_proxy_url(
            manager,
            {
                "proxy_server_type": "SOCKS5",
                "proxy_server_addr": "127.0.0.1",
                "proxy_server_port": "1080",
            },
        ),
        "socks5://127.0.0.1:1080",
    )


def test_build_proxy_url_rejects_disabled_or_incomplete_proxy_settings():
    manager = object.__new__(SettingsManager)

    _expect_equal(
        SettingsManager.build_proxy_url(
            manager,
            {
                "proxy_server_type": "None",
                "proxy_server_addr": "proxy.example.com",
                "proxy_server_port": "8443",
            },
        ),
        None,
    )
    _expect_equal(
        SettingsManager.build_proxy_url(
            manager,
            {
                "proxy_server_type": "HTTPS",
                "proxy_server_addr": "",
                "proxy_server_port": "8443",
            },
        ),
        None,
    )


def test_build_quality_fallback_selector_preserves_height_then_extension():
    thread = object.__new__(DownloadThread)

    _expect_equal(
        DownloadThread._build_quality_fallback_selector(thread, 1080, "mp4"),
        "bestvideo[ext=mp4][height<=1080]+bestaudio/"
        "best[ext=mp4][height<=1080]/"
        "bestvideo[height<=1080]+bestaudio/"
        "best[height<=1080]",
    )
    _expect_equal(
        DownloadThread._build_quality_fallback_selector(thread, None, "webm"),
        "bestvideo[ext=webm]+bestaudio/best[ext=webm]",
    )
    _expect_equal(
        DownloadThread._build_quality_fallback_selector(thread, None, "Any"),
        "",
    )


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://youtu.be/abc123def45?t=12", "abc123def45"),
        ("https://www.youtube.com/watch?v=abc123def45&list=PL123", "abc123def45"),
        ("https://www.youtube.com/shorts/abc123def45?feature=share", "abc123def45"),
        ("https://example.com/video", None),
    ],
)
def test_extract_youtube_id_handles_common_url_shapes(url, expected):
    _expect_equal(MainWindow._extract_youtube_id(url), expected)


def test_thumbnail_url_prefers_declared_thumbnail_candidates():
    dummy = _DummyWindow()
    entry = {
        "thumbnail": "",
        "thumbnails": [
            {"thumb": ""},
            {"url": "https://img.example.com/thumb.jpg"},
        ],
        "url": "https://www.youtube.com/watch?v=abc123def45",
    }

    _expect_equal(
        MainWindow._thumbnail_url_for_entry(dummy, entry),
        "https://img.example.com/thumb.jpg",
    )


def test_thumbnail_url_falls_back_to_youtube_default_when_needed():
    dummy = _DummyWindow()
    entry = {
        "title": "No explicit thumbnails",
        "url": "https://www.youtube.com/watch?v=abc123def45",
    }

    _expect_equal(
        MainWindow._thumbnail_url_for_entry(dummy, entry),
        "https://i.ytimg.com/vi/abc123def45/hqdefault.jpg",
    )
