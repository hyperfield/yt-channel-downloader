"""Capture the real Qt interface with offline demonstration data.

Install the project and Pillow, then run this script on the operating system
being documented. No videos are downloaded and the user's settings are untouched.
"""

import argparse
from contextlib import ExitStack
import logging
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "docs/images/fixtures"
MOVIES = (
    ("Big Buck Bunny", "YE7VzlLtp-4", 596, 156),
    ("Sintel - Open Movie by Blender Foundation", "eRsGyueVLvQ", 888, 238),
    ("Tears of Steel - Blender VFX Open Movie", "R6MlUcmOul8", 734, 204),
    ("Elephants Dream", "TLkA0RELQ1g", 653, 182),
)


def capture(output, style):
    # Capture widgets without opening windows on the user's desktop. Use the
    # native OS's Qt style; never simulate another operating system's chrome.
    platform = {"win32": "windows", "darwin": "cocoa", "linux": "offscreen"}[sys.platform]
    os.environ.setdefault("QT_QPA_PLATFORM", platform)
    os.environ["QT_SCALE_FACTOR"] = "1"
    os.environ["QT_FONT_DPI"] = "72" if sys.platform == "darwin" else "96"
    sys.path.insert(0, str(ROOT / "src"))

    import appdirs
    from PIL.ImageQt import fromqimage
    from PIL import Image
    from PyQt6 import QtCore, QtGui, QtWidgets, QtTest

    suffix = {"win32": "win", "linux": "lin", "darwin": "mac"}[sys.platform]
    output.mkdir(parents=True, exist_ok=True)
    app = QtWidgets.QApplication([])
    if style:
        if style.lower() not in [name.lower() for name in QtWidgets.QStyleFactory.keys()]:
            raise ValueError(f"Qt style {style!r} is not available on this operating system")
        app.setStyle(style)
    app.styleHints().setColorScheme(QtCore.Qt.ColorScheme.Light)
    app.setQuitOnLastWindowClosed(False)
    frames, durations = [], []

    with tempfile.TemporaryDirectory(prefix="ytcd-readme-") as temporary, ExitStack() as patches:
        # Patch before importing the app: its logger and settings manager are
        # initialized during imports and must only write to the temporary profile.
        patches.enter_context(patch.object(appdirs, "user_config_dir", return_value=temporary))
        from yt_channel_downloader.classes.mainwindow import MainWindow
        from yt_channel_downloader.classes.settings import SettingsDialog
        from yt_channel_downloader.classes.settings_manager import SettingsManager
        from yt_channel_downloader.classes.enums import ColumnIndexes

        manager = SettingsManager()
        demo_downloads = {
            "win32": "C:/Users/Demo/Downloads",
            "linux": "/home/demo/Downloads",
            "darwin": "/Users/demo/Downloads",
        }[sys.platform]
        manager.settings.update({
            "download_directory": str(Path(demo_downloads)),
            "preferred_video_format": "mp4",
            "preferred_video_quality": "1080p (Full HD)",
            "preferred_audio_format": "mp3",
            "show_thumbnails": True,
            "enable_size_estimation": True,
            "channel_fetch_limit": 500,
            "playlist_fetch_limit": 100,
            "proxy_server_type": "None",
            "proxy_server_addr": "",
            "proxy_server_port": "",
        })

        for method in (
            "initialize_youtube_login", "_schedule_auto_update_check",
            "_init_thumbnail_loader", "_init_node_notifier", "_init_support_prompt",
        ):
            patches.enter_context(patch.object(MainWindow, method, lambda self: None))
        # Fail visibly if a future UI change accidentally introduces networking.
        patches.enter_context(patch("socket.create_connection", side_effect=RuntimeError("Offline capture")))
        patches.enter_context(patch("requests.sessions.Session.request", side_effect=RuntimeError("Offline capture")))

        window = MainWindow()
        settings = None
        try:
            window.window_resize_needed = False
            window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
            window.resize(1280, 720 if sys.platform == "darwin" else 640)
            window.ui.chanUrlEdit.setText("https://www.youtube.com/@BlenderOfficial")
            window.ui.chanUrlEdit.setCursorPosition(0)
            window.yt_chan_vids_titles_links = [
                {"title": title, "url": f"https://www.youtube.com/watch?v={identifier}", "duration": duration}
                for title, identifier, duration, _size in MOVIES
            ]
            window.populate_window_list()
            for row, (_title, identifier, _duration, size) in enumerate(MOVIES):
                thumbnail = QtGui.QPixmap(str(FIXTURES / f"{identifier}.jpg"))
                if thumbnail.isNull():
                    raise RuntimeError(f"Missing thumbnail fixture: {identifier}")
                thumbnail = thumbnail.scaled(
                    96, 54, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation,
                )
                window.model.item(row, ColumnIndexes.TITLE).setData(
                    thumbnail, QtCore.Qt.ItemDataRole.DecorationRole,
                )
                link = window.model.item(row, ColumnIndexes.LINK).text()
                window.size_estimate_cache[(link, window._settings_signature)] = size * 1024 * 1024
            window.show()
            app.setActiveWindow(window)

            def settle():
                app.processEvents()
                # Allow the native style's hover/enable transitions to finish.
                QtTest.QTest.qWait(300)

            def frame(duration=650):
                settle()
                snapshot = fromqimage(window.grab().toImage()).convert("RGB")
                # Retina stills retain their native resolution; keep the GIF at
                # logical window size so it stays compact and readable inline.
                if snapshot.size != (window.width(), window.height()):
                    snapshot = snapshot.resize(
                        (window.width(), window.height()), Image.Resampling.LANCZOS,
                    )
                frames.append(snapshot)
                durations.append(duration)

            def screenshot(widget, filename):
                settle()
                if not widget.grab().save(str(output / filename)):
                    raise RuntimeError(f"Could not save {filename}")

            def click_row(row):
                index = window.model.index(row, ColumnIndexes.DOWNLOAD)
                rect = window.ui.treeView.visualRect(index)
                QtTest.QTest.mouseClick(
                    window.ui.treeView.viewport(), QtCore.Qt.MouseButton.LeftButton,
                    pos=rect.center(),
                )
                if window.model.item(row, ColumnIndexes.DOWNLOAD).checkState() != QtCore.Qt.CheckState.Checked:
                    raise RuntimeError(f"Could not select demonstration row {row}")
                if not window.downloadSelectedVidsButton.isEnabled():
                    raise RuntimeError("Selecting an item did not enable Download")

            # These are real widget interactions. Only the movie listing,
            # thumbnails and size estimates are fixtures; no transfer is faked.
            window.ui.treeView.setFocus()
            frame(1400)
            window.titleSearchEdit.setFocus()
            for character in "Sintel":
                QtTest.QTest.keyClicks(window.titleSearchEdit, character)
                frame(140)
            if any(
                window.ui.treeView.isRowHidden(row, QtCore.QModelIndex()) != (row != 1)
                for row in range(len(MOVIES))
            ):
                raise RuntimeError("Title filtering did not show only Sintel")
            frame(1000)
            click_row(1)
            frame(1100)
            QtTest.QTest.keyClick(
                window.titleSearchEdit, QtCore.Qt.Key.Key_A,
                QtCore.Qt.KeyboardModifier.ControlModifier,
            )
            QtTest.QTest.keyClick(window.titleSearchEdit, QtCore.Qt.Key.Key_Backspace)
            frame(900)
            click_row(0)
            window.ui.treeView.clearSelection()
            window.ui.treeView.setFocus()
            frame(1300)
            screenshot(window, f"screenshot_{suffix}.png")

            checkbox = window.select_all_checkbox
            checkbox_point = QtCore.QPoint(8, checkbox.height() // 2)
            QtTest.QTest.mouseClick(checkbox, QtCore.Qt.MouseButton.LeftButton, pos=checkbox_point)
            if len(window._checked_row_indexes()) != len(MOVIES):
                raise RuntimeError("Select All did not select all demonstration rows")
            frame(1000)
            QtTest.QTest.mouseClick(checkbox, QtCore.Qt.MouseButton.LeftButton, pos=checkbox_point)
            if window._checked_row_indexes():
                raise RuntimeError("Select All did not clear the demonstration selection")
            if window.downloadSelectedVidsButton.isEnabled():
                raise RuntimeError("Clearing the selection did not disable Download")
            window.ui.treeView.clearSelection()
            window.ui.treeView.setFocus()
            frame(700)

            settings = SettingsDialog()
            settings.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
            settings.show()
            app.setActiveWindow(settings)
            screenshot(settings, f"ytdl-settings_{suffix}.png")

            settings.ui.check_audio_only.setChecked(True)
            settings.ui.pref_aud_format_dropdown.setCurrentText("flac")
            if settings.ui.pref_aud_quality_dropdown.isEnabled():
                raise RuntimeError("FLAC should disable the audio bitrate control")
            screenshot(settings, f"settings-audio_{suffix}.png")
        finally:
            if settings:
                settings.close()
            window.close()
            app.processEvents()
            # Release the log file before removing the temporary profile on Windows.
            logging.shutdown()

    # One shared palette prevents colour flicker, and GIF optimization stores
    # only changed regions instead of duplicating the entire window each frame.
    palette = frames[0].quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    gif = output / f"yt-chan-dl-{suffix}.gif"
    indexed[0].save(
        gif, save_all=True, append_images=indexed[1:], duration=durations,
        loop=0, optimize=True, disposal=1,
    )
    app.quit()
    print(f"Saved current UI captures to {output}; GIF duration {sum(durations) / 1000:.2f}s")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/images")
    parser.add_argument("--style", default="windowsvista" if sys.platform == "win32" else None)
    args = parser.parse_args()
    if sys.platform not in ("win32", "linux", "darwin"):
        parser.error("Capture on Windows, Linux or macOS")
    capture(args.output_dir.resolve(), args.style)


if __name__ == "__main__":
    main()
