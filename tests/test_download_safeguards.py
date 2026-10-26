import math
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import yt_dlp

pytest.importorskip("PyQt6")

from yt_channel_downloader.classes import download_thread as download_module
from yt_channel_downloader.classes.download_thread import DownloadThread
from yt_channel_downloader.classes.mainwindow import MainWindow


@pytest.fixture
def thread(monkeypatch, tmp_path):
    manager = SimpleNamespace(
        settings={"download_directory": str(tmp_path)},
        build_proxy_url=lambda _: None,
    )
    monkeypatch.setattr(download_module, "SettingsManager", lambda: manager)
    return DownloadThread("https://example.com/video", 0, "Video", SimpleNamespace())


@pytest.mark.parametrize("suffix", [
    ".jpg", ".webp", ".info.json", ".f247.webm", ".temp.mp4", ".mp4.part", ".ytdl",
])
def test_artifacts_do_not_count_as_completed_media(tmp_path, suffix):
    (tmp_path / f"video{suffix}").write_bytes(b"artifact")

    assert not DownloadThread.is_download_complete(str(tmp_path / "video"))


@pytest.mark.parametrize("extension", ["mp4", "webm", "mkv", "mp3", "ogg", "opus", "flac", "wav"])
def test_final_media_counts_as_complete_even_with_stale_fragments(tmp_path, extension):
    (tmp_path / f"video.{extension}").write_bytes(b"media")
    (tmp_path / "video.f247.webm.part").write_bytes(b"old attempt")

    assert DownloadThread.is_download_complete(str(tmp_path / "video"))


def test_completion_handles_glob_characters_in_directory(tmp_path):
    directory = tmp_path / "videos [2026]"
    directory.mkdir()
    (directory / "video.mp4").write_bytes(b"media")

    assert DownloadThread.is_download_complete(str(directory / "video"))


def test_empty_file_or_directory_is_not_completed_media(tmp_path):
    (tmp_path / "video.mp4").touch()
    (tmp_path / "video.webm").mkdir()

    assert not DownloadThread.is_download_complete(str(tmp_path / "video"))


@pytest.mark.parametrize(("details", "expected"), [
    ({"downloaded_bytes": 512, "total_bytes": 1024}, 50.0),
    ({"downloaded_bytes": 512, "total_bytes_estimate": 2048}, 25.0),
    ({"downloaded_bytes": 512, "_percent_str": "  N/A"}, 0.0),
    ({"downloaded_bytes": 512, "total_bytes": 0}, 0.0),
    ({"downloaded_bytes": 2048, "total_bytes_estimate": 1024}, 100.0),
])
def test_progress_uses_numeric_bytes_and_tolerates_unknown_size(thread, details, expected):
    updates = []
    thread.download_progress_signal.connect(updates.append)

    thread.dl_hook({"status": "downloading", **details})

    assert len(updates) == 1
    assert math.isfinite(updates[0]["progress"])
    assert updates[0]["progress"] == expected


def test_cancelled_progress_reaches_error_handler():
    window = SimpleNamespace(
        model=SimpleNamespace(item=lambda *args: None),
        progress_widgets={},
        _update_speed_item=Mock(),
        _handle_progress_update=Mock(),
        _handle_progress_error=Mock(),
    )
    update = {"index": "0", "error": "Cancelled", "progress": 42.0}

    MainWindow.update_progress(window, update)

    window._handle_progress_error.assert_called_once_with(0, None, None, update)
    window._handle_progress_update.assert_not_called()


def test_running_thread_is_retained_until_finished():
    worker = SimpleNamespace(isRunning=lambda: True)
    window = SimpleNamespace(active_download_threads={0: worker}, dl_threads=[worker])

    MainWindow.cleanup_download_thread(window, 0)

    assert window.active_download_threads[0] is worker
    assert window.dl_threads == [worker]


def test_cancelled_queued_download_does_not_fetch_metadata_or_release_unacquired_slot(thread):
    semaphore = Mock()

    def cancel_while_waiting(**kwargs):
        thread.cancel()
        return False

    semaphore.acquire.side_effect = cancel_while_waiting
    thread.main_window.download_semaphore = semaphore
    thread._perform_download = Mock()
    thread._emit_cancelled_progress = Mock()

    thread.run()

    thread._perform_download.assert_not_called()
    thread._emit_cancelled_progress.assert_called_once()
    semaphore.release.assert_not_called()


def test_single_item_download_does_not_expand_playlist(thread):
    options, _ = thread._build_download_options("Video")

    assert options["noplaylist"] is True


def test_percent_placeholders_in_title_and_directory_are_literal(thread, tmp_path):
    directory = tmp_path / "%(id)s"
    thread.user_settings["download_directory"] = str(directory)
    options, _ = thread._build_download_options("Title_%(id)s")

    with yt_dlp.YoutubeDL(options) as ydl:
        filename = ydl.prepare_filename({"id": "video-id", "title": "Video", "ext": "mp4"})

    assert Path(filename).parent == directory
    assert Path(filename).name.startswith("Title_%(id)s__")
    assert Path(filename).suffix == ".mp4"


def _selected_format(selector, formats):
    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        return next(ydl.build_format_selector(selector)({
            "formats": formats,
            "has_merged_format": True,
            "incomplete_formats": False,
        }))


@pytest.mark.parametrize("candidates", [[], ["silent", "combined"]])
def test_video_prefers_combined_stream_over_silent_stream(thread, candidates):
    formats = [
        {"format_id": "combined", "ext": "mp4", "height": 360,
         "vcodec": "avc1", "acodec": "mp4a", "url": "https://example.com/combined"},
        {"format_id": "silent", "ext": "mp4", "height": 720,
         "vcodec": "avc1", "acodec": "none", "url": "https://example.com/silent"},
    ]
    selector = thread._build_format_selector(candidates, 720, "mp4")

    assert _selected_format(selector, formats)["format_id"] == "combined"


def test_video_merges_high_quality_stream_when_separate_audio_is_available(thread):
    formats = [
        {"format_id": "audio", "ext": "m4a", "vcodec": "none",
         "acodec": "mp4a", "url": "https://example.com/audio"},
        {"format_id": "combined", "ext": "mp4", "height": 360,
         "vcodec": "avc1", "acodec": "mp4a", "url": "https://example.com/combined"},
        {"format_id": "video", "ext": "mp4", "height": 720,
         "vcodec": "avc1", "acodec": "none", "url": "https://example.com/video"},
    ]
    selector = thread._build_format_selector(["video", "combined"], 720, "mp4")

    assert _selected_format(selector, formats)["format_id"] == "video+audio"


def test_audio_bitrate_is_passed_to_encoder(thread):
    thread.user_settings.update({
        "preferred_audio_format": "mp3", "preferred_audio_quality": "128 kbps",
    })
    thread._execute_download = Mock()

    thread._download_audio_only_flow({})

    options = thread._execute_download.call_args.args[0]
    assert options["postprocessors"][0]["preferredquality"] == "128"
    assert "128k" not in options["format"]


def test_audio_any_still_extracts_audio_from_combined_stream(thread):
    thread.user_settings["preferred_audio_format"] = "Any"
    thread._execute_download = Mock()

    thread._download_audio_only_flow({})

    options = thread._execute_download.call_args.args[0]
    assert options["postprocessors"][0]["preferredcodec"] == "best"


@pytest.mark.parametrize("title", ["", "###", "...", "x" * 300, "漢字" * 150])
def test_sanitized_filename_leaves_room_for_extensions_and_temporary_suffixes(title):
    filename = DownloadThread.sanitize_filename(title)

    assert filename
    assert filename.strip(". ")
    assert len(filename.encode("utf-8")) <= 200


@pytest.mark.parametrize("title", ["x" * 210, "CON"])
def test_title_only_files_are_preserved_without_assuming_their_source_or_settings(tmp_path, title):
    legacy_name = DownloadThread.sanitize_filename(title, legacy=True)
    (tmp_path / f"{legacy_name}.mp4").write_bytes(b"existing media")
    window = SimpleNamespace(user_settings={"download_directory": str(tmp_path)})

    path = MainWindow._get_video_filepath(window, title, "https://example.com/video")

    assert path != str(tmp_path / legacy_name)
    assert not DownloadThread.is_download_complete(path)
    assert (tmp_path / f"{legacy_name}.mp4").read_bytes() == b"existing media"
