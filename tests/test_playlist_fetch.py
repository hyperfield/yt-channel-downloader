import importlib
import pathlib
import pytest
import sys
import types


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from yt_channel_downloader.classes.validators import YouTubeURLValidator  # noqa: E402
import yt_channel_downloader.classes.validators as validators_module  # noqa: E402


def _expect_equal(actual, expected):
    if actual != expected:
        pytest.fail(f"Expected {expected!r}, got {actual!r}")


def _expect_true(value):
    if value is not True:
        pytest.fail(f"Expected True, got {value!r}")


class _DummyYoutubeDL:
    captured_opts = None

    def __init__(self, opts):
        type(self).captured_opts = opts

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def extract_info(self, playlist_url, download=False):
        return {
            "_type": "playlist",
            "entries": [
                {"id": "abc123def45", "title": "Video One"},
            ],
        }


def _import_ytchannel_module():
    try:
        return importlib.import_module("yt_channel_downloader.classes.YTChannel")
    except ModuleNotFoundError as exc:
        if exc.name not in {"PyQt6", "PyQt6.QtCore"}:
            raise

    sys.modules.pop("yt_channel_downloader.classes.YTChannel", None)

    pyqt6_module = types.ModuleType("PyQt6")
    qtcore_module = types.ModuleType("PyQt6.QtCore")

    class QObject:
        def __init__(self, parent=None):
            self.parent = parent

    class _Signal:
        def connect(self, *args, **kwargs):
            return None

        def emit(self, *args, **kwargs):
            return None

    def pyqtSignal(*args, **kwargs):
        return _Signal()

    qtcore_module.QObject = QObject
    qtcore_module.pyqtSignal = pyqtSignal
    pyqt6_module.QtCore = qtcore_module

    sys.modules.setdefault("PyQt6", pyqt6_module)
    sys.modules["PyQt6.QtCore"] = qtcore_module

    return importlib.import_module("yt_channel_downloader.classes.YTChannel")


def test_extract_playlist_entries_requests_flat_playlist_metadata(monkeypatch):
    monkeypatch.setattr(validators_module.yt_dlp, "YoutubeDL", _DummyYoutubeDL)

    entries = YouTubeURLValidator.extract_playlist_entries(
        "https://www.youtube.com/playlist?list=PL123"
    )

    _expect_true(_DummyYoutubeDL.captured_opts["extract_flat"])
    _expect_equal(entries, [{"id": "abc123def45", "title": "Video One"}])


def test_playlist_collection_respects_limit_for_flat_entries():
    ytchannel_module = _import_ytchannel_module()
    channel = ytchannel_module.YTChannel()

    progress_updates = []
    entries = [
        {"id": "abc123def45", "title": "Video One"},
        {"id": "def456ghi78", "title": "Video Two"},
        {"id": "ghi789jkl01", "title": "Video Three"},
    ]

    collected = ytchannel_module.YTChannel._collect_playlist_entries(
        channel,
        entries,
        limit=2,
        is_cancelled=None,
        progress_callback=lambda count, total: progress_updates.append((count, total)),
        total_entries=3,
    )

    _expect_equal([item["title"] for item in collected], ["Video One", "Video Two"])
    _expect_equal(progress_updates, [(1, 3), (2, 3)])
