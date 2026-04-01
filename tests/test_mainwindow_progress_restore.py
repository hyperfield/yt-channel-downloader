import pytest

pytest.importorskip("PyQt6")

from PyQt6 import QtCore, QtGui
from yt_channel_downloader.classes.enums import ColumnIndexes
from yt_channel_downloader.classes.mainwindow import MainWindow

VIDEO_ONE_PATH = "downloads/video_one.partial"
VIDEO_TWO_PATH = "downloads/video_two.partial"


def _expect_equal(actual, expected):
    if actual != expected:
        pytest.fail(f"Expected {expected!r}, got {actual!r}")


def _expect_is_none(value):
    if value is not None:
        pytest.fail(f"Expected None, got {value!r}")


def _build_row(title, link, progress, display_text):
    items = [QtGui.QStandardItem() for _ in range(ColumnIndexes.PROGRESS + 1)]
    items[ColumnIndexes.TITLE].setText(title)
    items[ColumnIndexes.LINK].setText(link)
    items[ColumnIndexes.PROGRESS].setData(progress, QtCore.Qt.ItemDataRole.UserRole)
    items[ColumnIndexes.PROGRESS].setData(display_text, QtCore.Qt.ItemDataRole.DisplayRole)
    return items


def test_snapshot_restorable_progress_state_keeps_partial_progress_for_matching_video():
    dummy = type("DummyWindow", (), {})()
    dummy.model = QtGui.QStandardItemModel()
    dummy.dl_path_correspondences = {
        "Video One": VIDEO_ONE_PATH,
        "Video Two": VIDEO_TWO_PATH,
    }
    dummy.model.appendRow(
        _build_row(
            "Video One",
            "https://www.youtube.com/watch?v=abc123",
            42.5,
            "Part-downloaded – 42.5%",
        )
    )
    dummy.model.appendRow(
        _build_row(
            "Video Two",
            "https://www.youtube.com/watch?v=def456",
            0.0,
            "",
        )
    )

    restored_state = MainWindow._snapshot_restorable_progress_state(dummy)

    _expect_equal(
        MainWindow._lookup_restorable_progress_state(
        dummy,
        "https://www.youtube.com/watch?v=abc123",
        VIDEO_ONE_PATH,
        restored_state,
        ),
        (42.5, "Part-downloaded – 42.5%"),
    )
    _expect_equal(
        MainWindow._lookup_restorable_progress_state(
        dummy,
        "https://www.youtube.com/watch?v=missing",
        VIDEO_ONE_PATH,
        restored_state,
        ),
        (42.5, "Part-downloaded – 42.5%"),
    )
    _expect_is_none(
        MainWindow._lookup_restorable_progress_state(
        dummy,
        "https://www.youtube.com/watch?v=def456",
        VIDEO_TWO_PATH,
        restored_state,
        )
    )


def test_normalize_restorable_progress_ignores_completed_and_invalid_values():
    _expect_is_none(MainWindow._normalize_restorable_progress(100.0, "Completed"))
    _expect_is_none(MainWindow._normalize_restorable_progress(0.0, ""))
    _expect_is_none(MainWindow._normalize_restorable_progress("not-a-number", ""))
