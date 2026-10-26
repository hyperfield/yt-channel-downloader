from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import threading

import pytest
import yt_dlp

pytest.importorskip("PyQt6")

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QCloseEvent
from yt_channel_downloader.classes import fetch_progress_dialog as fetch_module
from yt_channel_downloader.classes import download_thread as download_module
from yt_channel_downloader.classes import mainwindow as window_module
from yt_channel_downloader.classes.download_identity import download_key, download_path, index_download_paths
from yt_channel_downloader.classes.download_thread import DownloadThread
from yt_channel_downloader.classes.enums import ColumnIndexes
from yt_channel_downloader.classes.mainwindow import MainWindow
from yt_channel_downloader.classes.settings_manager import SettingsManager


URL_ONE = "https://www.youtube.com/watch?v=abc123def45"
URL_TWO = "https://www.youtube.com/watch?v=def456ghi78"


@pytest.fixture
def settings(tmp_path):
    return {
        **SettingsManager.load_default_settings(object.__new__(SettingsManager)),
        "download_directory": str(tmp_path),
        "preferred_video_quality": "720p (HD)",
        "enable_size_estimation": False,
        "show_thumbnails": False,
    }


@pytest.fixture(scope="module")
def application():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


@pytest.fixture
def window(monkeypatch, settings, application):
    manager = SimpleNamespace(settings=settings, save_settings_to_file=Mock(), build_proxy_url=lambda _: None)
    monkeypatch.setattr(window_module, "SettingsManager", lambda: manager)
    monkeypatch.setattr(download_module, "SettingsManager", lambda: manager)
    for method in ("initialize_youtube_login", "_schedule_auto_update_check", "_init_thumbnail_loader", "_init_node_notifier"):
        monkeypatch.setattr(MainWindow, method, lambda self: None)
    widget = MainWindow()
    widget.yt_chan_vids_titles_links = [{"title": "Same Title", "url": URL_ONE, "duration": 60}]
    widget.populate_window_list()
    yield widget
    widget.close()
    application.processEvents()


def test_close_keeps_a_network_worker_alive_until_it_finishes(window, application):
    started, release = threading.Event(), threading.Event()

    class RequestThread(QtCore.QThread):
        def run(self):
            started.set()
            release.wait(3)

    thread = RequestThread(window)
    thread.start()
    assert started.wait(1)
    try:
        event = QCloseEvent()
        window.closeEvent(event)
        assert not event.isAccepted()
        assert thread.isRunning()
        assert thread in window._background_threads()
    finally:
        release.set()
        assert thread.wait(2000)
        application.processEvents()


def test_rejecting_fetch_dialog_cancels_and_ignores_late_results(monkeypatch, application):
    class FakeThread(QtCore.QObject):
        finished = QtCore.pyqtSignal(list)
        cancelled = QtCore.pyqtSignal()
        error = QtCore.pyqtSignal(str)
        progress = QtCore.pyqtSignal(int, object)

        def __init__(self, *args, parent=None, **kwargs):
            super().__init__(parent)
            self.cancel = Mock()

        def start(self):
            pass

    monkeypatch.setattr(fetch_module, 'GetListThread', FakeThread)
    dialog = fetch_module.FetchProgressDialog(None, object(), 'https://example.com/video')
    cancelled, results, errors = [], [], []
    dialog.cancelled.connect(lambda: cancelled.append(True))
    dialog.finished.connect(results.append)
    dialog.error.connect(errors.append)

    dialog.reject()
    dialog.thread.finished.emit([{'title': 'Late result'}])
    dialog.thread.error.emit('Late error')
    dialog.thread.cancelled.emit()

    assert cancelled == [True]
    assert results == errors == []
    dialog.thread.cancel.assert_called_once()
    dialog.deleteLater()
    application.processEvents()


@pytest.mark.parametrize("alias", [
    "https://youtu.be/abc123def45?t=30",
    "https://www.youtube.com/watch?v=abc123def45&list=PL123&index=3",
    "https://m.youtube.com/shorts/abc123def45?feature=share",
    "https://www.youtube.com/embed/abc123def45",
    "https://www.youtube.com/live/abc123def45",
    "abc123def45",
])
def test_youtube_aliases_have_one_identity(settings, alias):
    assert download_key(alias, settings) == download_key(URL_ONE, settings)


def test_different_sources_and_generic_query_values_remain_distinct(settings):
    urls = [URL_ONE, URL_TWO, "https://example.com/watch?v=1", "https://example.com/watch?v=2"]

    assert len({download_key(url, settings) for url in urls}) == len(urls)


@pytest.mark.parametrize("change", [
    {"preferred_video_quality": "1080p (Full HD)"},
    {"preferred_video_format": "mp4"},
    {"audio_only": True},
])
def test_video_output_preferences_separate_requests(settings, change):
    assert download_key(URL_ONE, settings) != download_key(URL_ONE, {**settings, **change})


@pytest.mark.parametrize("change", [
    {"preferred_audio_quality": "128 kbps"},
    {"preferred_audio_format": "flac"},
])
def test_audio_output_preferences_separate_requests(settings, change):
    settings["audio_only"] = True

    assert download_key(URL_ONE, settings) != download_key(URL_ONE, {**settings, **change})


def test_irrelevant_preferences_do_not_change_video_identity(settings):
    change = {
        "preferred_audio_quality": "128 kbps", "preferred_audio_format": "flac",
        "download_thumbnail": True, "proxy_server_addr": "example.com",
    }

    assert download_key(URL_ONE, settings) == download_key(URL_ONE, {**settings, **change})


def test_same_sanitized_title_does_not_overwrite_other_source(settings):
    first = download_path("Same_Title", URL_ONE, settings)
    second = download_path("Same_Title", URL_TWO, settings)

    assert first != second
    assert len(Path(first).name.encode("utf-8")) <= 200


def test_long_unicode_title_retains_identity_within_filename_limit(settings):
    path = download_path(DownloadThread.sanitize_filename("漢字" * 150), URL_ONE, settings)

    assert len(Path(path).name.encode("utf-8")) <= 200
    assert Path(path).name.endswith(download_key(URL_ONE, settings))


@pytest.mark.parametrize("artifact", [".mp4", ".f247.webm.part"])
def test_title_change_reuses_identity_for_existing_file_or_resume(settings, artifact):
    original = download_path("Old_Title", URL_ONE, settings)
    Path(original + artifact).write_bytes(b"download data")

    assert download_path("New_Title", URL_ONE, settings) == original


def test_index_prefers_completed_media_over_another_titles_partial_attempt(settings):
    key = download_key(URL_ONE, settings)
    directory = Path(settings["download_directory"])
    (directory / f"A_Title__{key}.mp4").write_bytes(b"media")
    (directory / f"Z_Title__{key}.mp4.part").write_bytes(b"partial")

    assert index_download_paths(str(directory))[key] == str(directory / f"A_Title__{key}")


def test_gui_and_worker_use_the_same_identity_and_literal_template(window):
    path = window._get_video_filepath("Same Title", URL_ONE)
    worker = window._register_download_thread(0)
    options, _ = worker._build_download_options("Same_Title")

    with yt_dlp.YoutubeDL(options) as ydl:
        filename = ydl.prepare_filename({"id": "abc123def45", "title": "Same Title", "ext": "mp4"})

    assert filename == path + ".source.mp4"
    window.cleanup_download_thread(0)


def test_same_title_completed_video_does_not_skip_other_source(window):
    first = window._get_video_filepath("Same Title", URL_ONE)
    Path(first + ".mp4").write_bytes(b"first video")
    window.yt_chan_vids_titles_links.append({"title": "Same Title", "url": URL_TWO})
    window.populate_window_list()
    checkbox = window.model.item(1, ColumnIndexes.DOWNLOAD)
    checkbox.setCheckState(QtCore.Qt.CheckState.Checked)

    assert window._is_download_complete_for_row(0)
    assert not window._is_download_complete_for_row(1)
    assert window._selected_download_rows() == [1]
    assert window.dl_path_correspondences[URL_ONE] != window.dl_path_correspondences[URL_TWO]


def test_aliases_of_one_video_do_not_queue_competing_writes(window):
    alias = "https://youtu.be/abc123def45?t=30"
    window.yt_chan_vids_titles_links.append({"title": "A Different Title", "url": alias})
    window.populate_window_list()
    for row in range(2):
        window.model.item(row, ColumnIndexes.DOWNLOAD).setCheckState(QtCore.Qt.CheckState.Checked)

    assert window._selected_download_rows() == [0]
    assert window.dl_path_correspondences[URL_ONE] == window.dl_path_correspondences[alias]


def _change_settings(monkeypatch, window, **changes):
    def save_and_close():
        window.settings_manager.settings = {**window.settings_manager.settings, **changes}

    monkeypatch.setattr(window_module, "SettingsDialog", lambda: SimpleNamespace(exec=save_and_close))
    window.show_settings_dialog()


@pytest.mark.parametrize("changes", [
    {"preferred_video_quality": "1080p (Full HD)"},
    {"preferred_video_format": "mp4"},
    {"audio_only": True},
])
def test_settings_change_reenables_completed_rows_for_new_request(monkeypatch, window, changes):
    original = window._get_video_filepath("Same Title", URL_ONE)
    Path(original + ".mp4").write_bytes(b"720p video")
    window.populate_window_list()
    assert not window.model.item(0, ColumnIndexes.DOWNLOAD).isEnabled()

    _change_settings(monkeypatch, window, **changes)

    checkbox = window.model.item(0, ColumnIndexes.DOWNLOAD)
    assert checkbox.isEnabled()
    assert window._get_video_filepath("Same Title", URL_ONE) != original
    assert window.model.item(0, ColumnIndexes.PROGRESS).data(QtCore.Qt.ItemDataRole.UserRole) == 0.0
    checkbox.setCheckState(QtCore.Qt.CheckState.Checked)
    assert window._selected_download_rows() == [0]
    assert Path(original + ".mp4").read_bytes() == b"720p video"


def test_partial_progress_does_not_transfer_to_another_quality(monkeypatch, window):
    checkbox = window.model.item(0, ColumnIndexes.DOWNLOAD)
    checkbox.setCheckState(QtCore.Qt.CheckState.Checked)
    progress = window.model.item(0, ColumnIndexes.PROGRESS)
    progress.setData(42.5, QtCore.Qt.ItemDataRole.UserRole)
    progress.setData("Part-downloaded – 42.5%", QtCore.Qt.ItemDataRole.DisplayRole)

    _change_settings(monkeypatch, window, preferred_video_quality="1080p (Full HD)")

    assert window.model.item(0, ColumnIndexes.PROGRESS).data(QtCore.Qt.ItemDataRole.UserRole) == 0.0
    assert window.model.item(0, ColumnIndexes.DOWNLOAD).checkState() == QtCore.Qt.CheckState.Checked


def test_changing_destination_does_not_reuse_old_directorys_completed_state(monkeypatch, window, tmp_path):
    original = window._get_video_filepath("Same Title", URL_ONE)
    Path(original + ".mp4").write_bytes(b"media")
    window.populate_window_list()
    new_directory = tmp_path / "other"

    _change_settings(monkeypatch, window, download_directory=str(new_directory))

    assert Path(window._get_video_filepath("Same Title", URL_ONE)).parent == new_directory
    assert not window._is_download_complete_for_row(0)
    assert window.model.item(0, ColumnIndexes.DOWNLOAD).isEnabled()


def test_list_rebuild_indexes_destination_once(window, monkeypatch):
    scanner = Mock(wraps=window_module.index_download_paths)
    monkeypatch.setattr(window_module, "index_download_paths", scanner)
    window.yt_chan_vids_titles_links = [
        {"title": "Same Title", "url": f"https://example.com/video/{index}"}
        for index in range(20)
    ]

    window.populate_window_list()

    scanner.assert_called_once()


def test_channel_limit_change_updates_fetch_next_button(monkeypatch, window):
    _change_settings(monkeypatch, window, channel_fetch_limit=25)

    assert window.loadNextButton.text() == 'Fetch Next 25'


def test_completed_file_survives_title_change_and_new_fetch(window):
    original = window._get_video_filepath("Same Title", URL_ONE)
    Path(original + ".mp4").write_bytes(b"media")
    window.yt_chan_vids_titles_links[0]["title"] = "Renamed"

    window.populate_window_list()

    assert window._get_video_filepath("Renamed", URL_ONE) == original
    assert window._is_download_complete_for_row(0)


def test_worker_keeps_queued_settings_when_shared_settings_change(window):
    worker = window._register_download_thread(0)
    original = worker.output_path
    window.settings_manager.settings["preferred_video_quality"] = "1080p (Full HD)"
    options, _ = worker._build_download_options("Same_Title")

    assert worker._video_preferences()[1] == "720p"
    with yt_dlp.YoutubeDL(options) as ydl:
        assert ydl.prepare_filename({"id": "abc123def45", "ext": "mp4"}) == original + ".source.mp4"
    window.cleanup_download_thread(0)
