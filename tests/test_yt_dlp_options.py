from types import SimpleNamespace

import pytest
import yt_dlp

from yt_channel_downloader.classes.utils import _build_metadata_opts
from yt_channel_downloader.classes.validators import YouTubeURLValidator, _single_media_opts


@pytest.mark.parametrize("build_options", [
    _build_metadata_opts,
    _single_media_opts,
    lambda overrides: YouTubeURLValidator._build_ydl_opts({"quiet": True}, overrides),
])
def test_metadata_enables_node_alongside_deno(build_options):
    options = build_options({"proxy": "http://proxy.example:8080"})

    with yt_dlp.YoutubeDL(options) as ydl:
        assert set(ydl.params["js_runtimes"]) == {"deno", "node"}
        assert "ejs:github" in ydl.params["remote_components"]
        assert ydl.params["proxy"] == "http://proxy.example:8080"


def test_metadata_preserves_explicit_runtime_override():
    runtimes = {"node": {"path": "/custom/node"}}
    options = _build_metadata_opts({"js_runtimes": runtimes})

    assert options["js_runtimes"] == runtimes


def test_download_enables_node_alongside_deno(monkeypatch):
    pytest.importorskip("PyQt6")
    from yt_channel_downloader.classes import download_thread as download_module

    manager = SimpleNamespace(
        settings={"download_directory": "/tmp/downloads"},
        build_proxy_url=lambda _: None,
    )
    monkeypatch.setattr(download_module, "SettingsManager", lambda: manager)
    thread = download_module.DownloadThread("https://example.com/video", 0, "Video", SimpleNamespace())

    options, _ = thread._build_download_options("Video")

    with yt_dlp.YoutubeDL(options) as ydl:
        assert set(ydl.params["js_runtimes"]) == {"deno", "node"}
