from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication
from yt_channel_downloader.classes import mainwindow


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


def test_about_dialog_displays_runtime_release_metadata(monkeypatch, application):
    monkeypatch.setattr(mainwindow, "__version__", "1.2.3")
    monkeypatch.setattr(mainwindow, "__release_date__", "2027-02-03")
    window = SimpleNamespace()

    mainwindow.MainWindow.setup_about_dialog(window)

    text = window.about_ui.aboutLabel.text()
    assert "Version:</span> 1.2.3" in text
    assert "Release date: </span>2027-02-03" in text
    assert "{version}" not in text
    assert "{release_date}" not in text
    window.about_dialog.close()
