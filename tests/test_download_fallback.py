from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import yt_dlp

pytest.importorskip("PyQt6")

from yt_channel_downloader.classes import download_thread as download_module
from yt_channel_downloader.classes.download_thread import DownloadThread


@pytest.fixture
def thread(monkeypatch):
    settings = {
        "download_directory": "/tmp/downloads",
        "preferred_video_quality": "Best available",
        "preferred_video_format": "Any",
    }
    manager = SimpleNamespace(settings=settings, build_proxy_url=lambda _: None)
    monkeypatch.setattr(download_module, "SettingsManager", lambda: manager)
    monkeypatch.setattr(download_module, "get_format_candidates", lambda *args: ["247"])
    return DownloadThread("https://www.youtube.com/watch?v=mn2G51fmnlI", 0, "Video", SimpleNamespace())


@pytest.mark.parametrize("message", [
    "ERROR: unable to download video data: HTTP Error 403: Forbidden",
    "ERROR: unable to download video data: HTTP Error 404: Not Found",
    "ERROR: Requested format is not available",
])
def test_best_available_retries_progressive_download(thread, message):
    options, auth = thread._build_download_options("Video")
    options["proxy"] = "http://proxy.example:8080"
    options["cookiesfrombrowser"] = ("firefox",)
    thread._execute_download = Mock(side_effect=[yt_dlp.utils.DownloadError(message), None])

    thread._download_video_flow(options, auth)

    assert thread._execute_download.call_count == 2
    fallback = thread._execute_download.call_args.args[0]
    assert fallback["format"] == "best"
    assert fallback["proxy"] == options["proxy"]
    assert fallback["cookiesfrombrowser"] == options["cookiesfrombrowser"]
    assert "format_sort" not in fallback
    assert "format_sort_force" not in fallback


def test_specific_quality_retries_before_progressive_download(thread):
    thread.user_settings.update({
        "preferred_video_quality": "1080p (Full HD)",
        "preferred_video_format": "mp4",
    })
    options, auth = thread._build_download_options("Video")
    thread._execute_download = Mock(side_effect=[
        yt_dlp.utils.DownloadError("HTTP Error 403: Forbidden"),
        yt_dlp.utils.DownloadError("HTTP Error 403: Forbidden"),
        None,
    ])

    thread._download_video_flow(options, auth)

    attempts = [call.args[0] for call in thread._execute_download.call_args_list]
    assert len(attempts) == 3
    assert "[height<=?1080]" in attempts[1]["format"]
    assert attempts[1]["postprocessors"][0]["preferedformat"] == "mp4"
    assert attempts[2]["format"] == "best[height<=?1080]"
    assert attempts[2]["postprocessors"][0]["preferedformat"] == "mp4"


@pytest.mark.parametrize("failure", [
    yt_dlp.utils.DownloadError("Sign in to confirm your age"),
    yt_dlp.utils.DownloadError("HTTP Error 429: Too Many Requests"),
    yt_dlp.utils.DownloadCancelled("Cancelled by user"),
])
def test_unrecoverable_errors_and_cancellation_do_not_retry(thread, failure):
    options, auth = thread._build_download_options("Video")
    thread._execute_download = Mock(side_effect=failure)

    with pytest.raises(type(failure)) as raised:
        thread._download_video_flow(options, auth)

    assert raised.value is failure
    assert thread._execute_download.call_count == 1


def test_unrecoverable_quality_retry_error_stops_fallback(thread):
    failure = yt_dlp.utils.DownloadError("HTTP Error 429: Too Many Requests")
    thread._execute_download = Mock(side_effect=failure)

    with pytest.raises(yt_dlp.utils.DownloadError) as raised:
        thread._download_video_fallback(
            yt_dlp.utils.DownloadError("HTTP Error 403: Forbidden"),
            {},
            "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        )

    assert raised.value is failure
    assert thread._execute_download.call_count == 1


def test_failed_progressive_retry_reports_last_error(thread):
    options, auth = thread._build_download_options("Video")
    failure = yt_dlp.utils.DownloadError("HTTP Error 404: Not Found")
    thread._execute_download = Mock(side_effect=[
        yt_dlp.utils.DownloadError("HTTP Error 403: Forbidden"), failure,
    ])

    with pytest.raises(yt_dlp.utils.DownloadError) as raised:
        thread._download_video_flow(options, auth)

    assert raised.value is failure
    assert thread._execute_download.call_count == 2
