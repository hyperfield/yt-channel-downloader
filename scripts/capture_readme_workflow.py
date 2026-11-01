"""Record a real fetch/filter/select/download workflow for the README.

Run on the operating system being documented, with the project, Pillow,
FFmpeg/ffprobe, and a supported JavaScript runtime installed. This contacts
YouTube and downloads one public Blender video into a temporary directory.
"""

import argparse
from contextlib import ExitStack
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CHANNEL = "https://www.youtube.com/channel/UCSMOQeBJ2RAnuFungnQOxLg"
FRAME_MS = 125


def record(output, recording, url, title_filter, rate_limit):
    platform, suffix = {
        "darwin": ("cocoa", "mac"),
        "win32": ("windows", "win"),
        "linux": ("offscreen", "lin"),
    }[sys.platform]
    os.environ.setdefault("QT_QPA_PLATFORM", platform)
    os.environ["QT_SCALE_FACTOR"] = "1"
    os.environ["QT_FONT_DPI"] = "72" if sys.platform == "darwin" else "96"
    sys.path.insert(0, str(ROOT / "src"))

    import appdirs
    from PIL import Image
    from PIL.ImageQt import fromqimage
    from PyQt6 import QtCore, QtWidgets, QtTest

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not shutil.which("ffprobe"):
        raise RuntimeError("Install FFmpeg and ffprobe before recording a download")
    output.mkdir(parents=True, exist_ok=True)
    recording.mkdir(parents=True, exist_ok=True)
    # Each run has its own raw frames, so reruns cannot reuse stale captures.
    frames_directory = Path(tempfile.mkdtemp(prefix="frames-", dir=recording))
    app = QtWidgets.QApplication([])
    if sys.platform == "win32":
        app.setStyle("windowsvista")
    app.styleHints().setColorScheme(QtCore.Qt.ColorScheme.Light)
    app.setQuitOnLastWindowClosed(False)
    frames, errors = [], []
    phase = "intro"
    selected_row = None
    started = time.monotonic()

    with tempfile.TemporaryDirectory(prefix="ytcd-workflow-") as temporary, ExitStack() as patches:
        patches.enter_context(patch.object(appdirs, "user_config_dir", return_value=temporary))
        from yt_channel_downloader import __version__
        from yt_channel_downloader.classes.mainwindow import MainWindow
        from yt_channel_downloader.classes.settings_manager import SettingsManager
        from yt_channel_downloader.classes.download_thread import DownloadThread
        from yt_channel_downloader.classes.fetch_progress_dialog import FetchProgressDialog
        from yt_channel_downloader.classes.enums import ColumnIndexes

        manager = SettingsManager()
        downloads = Path(temporary) / "downloads"
        downloads.mkdir()
        manager.settings.update({
            "download_directory": str(downloads),
            "preferred_video_format": "mp4",
            "preferred_video_quality": "480p",
            "audio_only": False,
            "download_thumbnail": False,
            "show_thumbnails": True,
            "enable_size_estimation": True,
            "channel_fetch_limit": 8,
            "playlist_fetch_limit": 8,
            "proxy_server_type": "None",
        })
        for method in (
            "initialize_youtube_login", "_schedule_auto_update_check",
            "_init_node_notifier", "_init_support_prompt", "auto_adjust_window_size",
        ):
            patches.enter_context(patch.object(MainWindow, method, lambda self: None))

        # Suppress incidental prompts, but fail the recording if fetching or
        # downloading fails. Neither provider results nor progress are mocked.
        for method in ("display_error_dialog", "_handle_fetch_error", "handle_download_error"):
            patches.enter_context(patch.object(
                MainWindow, method, lambda self, message: errors.append(str(message)),
            ))

        original_options = DownloadThread._build_download_options

        def limited_options(worker, title):
            options, auth = original_options(worker, title)
            options["ratelimit"] = rate_limit
            return options, auth

        patches.enter_context(patch.object(DownloadThread, "_build_download_options", limited_options))
        original_fetch_init = FetchProgressDialog.__init__

        def hidden_fetch_init(dialog, *args, **kwargs):
            original_fetch_init(dialog, *args, **kwargs)
            dialog.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)

        patches.enter_context(patch.object(FetchProgressDialog, "__init__", hidden_fetch_init))
        window = MainWindow()
        window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
        window.resize(1280, 900)
        window.show()
        app.setActiveWindow(window)

        def grab(widget):
            snapshot = fromqimage(widget.grab().toImage()).convert("RGB")
            return snapshot.resize((widget.width(), widget.height()), Image.Resampling.LANCZOS)

        def snapshot():
            picture = grab(window)
            # The fetch dialog is a separate top-level native window. Composite
            # its real widget capture at its actual position over the parent.
            for widget in app.topLevelWidgets():
                if isinstance(widget, FetchProgressDialog) and widget.isVisible():
                    origin = widget.geometry().topLeft() - window.geometry().topLeft()
                    picture.paste(grab(widget), (origin.x(), origin.y()))
            state = phase
            progress = None
            if selected_row is not None:
                item = window.model.item(selected_row, ColumnIndexes.PROGRESS)
                if item:
                    progress = item.data(QtCore.Qt.ItemDataRole.UserRole)
                    if phase == "download":
                        state = "transfer" if isinstance(progress, (int, float)) and 0 < progress < 100 else "preparing"
            path = frames_directory / f"{len(frames):05d}.png"
            picture.resize((1100, 773), Image.Resampling.LANCZOS).save(path)
            frames.append({
                "file": str(path), "phase": state, "progress": progress,
                "time": round(time.monotonic() - started, 3),
            })

        timer = QtCore.QTimer()
        timer.timeout.connect(snapshot)
        timer.start(FRAME_MS)

        def pause(milliseconds):
            QtTest.QTest.qWait(milliseconds)
            if errors:
                raise RuntimeError("Capture failed: " + "; ".join(errors))

        def wait_until(condition, timeout=180):
            deadline = time.monotonic() + timeout
            while not condition():
                pause(FRAME_MS)
                if time.monotonic() > deadline:
                    raise TimeoutError(f"Timed out during {phase}")

        try:
            pause(750)
            phase = "url"
            window.ui.chanUrlEdit.setFocus()
            QtTest.QTest.keyClicks(window.ui.chanUrlEdit, url, delay=12)
            pause(250)
            phase = "fetch"
            QtTest.QTest.mouseClick(window.getVidListButton, QtCore.Qt.MouseButton.LeftButton)
            pause(125)
            if window.model.rowCount() == 0:
                raise RuntimeError("Fetching did not return any items")
            phase = "listed"
            window.ui.treeView.setFocus()
            pause(1000)

            phase = "filter"
            window.titleSearchEdit.setFocus()
            QtTest.QTest.keyClicks(window.titleSearchEdit, title_filter, delay=110)
            pause(125)
            visible = [
                row for row in range(window.model.rowCount())
                if not window.ui.treeView.isRowHidden(row, QtCore.QModelIndex())
            ]
            if len(visible) != 1:
                raise RuntimeError(f"Expected one match for {title_filter!r}; found {len(visible)}")
            selected_row = visible[0]
            phase = "filtered"
            pause(500)
            index = window.model.index(selected_row, ColumnIndexes.DOWNLOAD)
            QtTest.QTest.mouseClick(
                window.ui.treeView.viewport(), QtCore.Qt.MouseButton.LeftButton,
                pos=window.ui.treeView.visualRect(index).center(),
            )
            if window._checked_row_indexes() != [selected_row]:
                raise RuntimeError("The filtered item was not selected")
            phase = "selected"
            wait_until(lambda: not window.recalc_status_widget.isVisible(), timeout=30)
            pause(700)
            phase = "cleared"
            window.titleSearchEdit.setFocus()
            QtTest.QTest.keyClick(
                window.titleSearchEdit, QtCore.Qt.Key.Key_A,
                QtCore.Qt.KeyboardModifier.ControlModifier,
            )
            QtTest.QTest.keyClick(window.titleSearchEdit, QtCore.Qt.Key.Key_Backspace)
            window.ui.treeView.clearSelection()
            window.ui.treeView.setFocus()
            pause(800)
            if not window.downloadSelectedVidsButton.isEnabled():
                raise RuntimeError("Selecting an item did not enable Download")
            video = window._item_text(selected_row, ColumnIndexes.LINK)
            title = window._item_text(selected_row, ColumnIndexes.TITLE)
            phase = "download"
            QtTest.QTest.mouseClick(window.downloadSelectedVidsButton, QtCore.Qt.MouseButton.LeftButton)
            wait_until(lambda: window._item_text(selected_row, ColumnIndexes.PROGRESS) == "Completed")
            wait_until(lambda: not window.active_download_threads)
            files = list(downloads.glob("*.mp4"))
            if len(files) != 1 or files[0].stat().st_size == 0:
                raise RuntimeError("The download did not create one complete MP4")
            probe = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries", "stream=codec_type,height",
                "-of", "json", str(files[0]),
            ], check=True, capture_output=True, text=True)
            streams = json.loads(probe.stdout)["streams"]
            if not any(stream.get("codec_type") == "audio" for stream in streams):
                raise RuntimeError("The downloaded MP4 has no audio stream")
            heights = [stream["height"] for stream in streams if stream.get("codec_type") == "video"]
            if not heights or max(heights) > 480:
                raise RuntimeError("The downloaded video did not respect the 480p cap")
            phase = "complete"
            pause(2000)
            metadata = {
                "version": __version__, "source": url, "video": video, "title": title,
                "rate_limit": rate_limit, "bytes": files[0].stat().st_size,
                "streams": streams, "frames": frames,
            }
        finally:
            timer.stop()
            window.close()
            for thread in window._background_threads():
                if thread.isRunning():
                    thread.wait(20000)
            app.processEvents()
            logging.shutdown()
            app.quit()

    # Preserve every action, while shortening network waits and repetitive
    # transfer frames. Retained frames keep their original chronological order.
    limits = {"fetch": 8, "selected": 6, "preparing": 6, "transfer": 40}
    selected = []
    for state in dict.fromkeys(frame["phase"] for frame in frames):
        group = [frame for frame in frames if frame["phase"] == state]
        count = min(len(group), limits.get(state, len(group)))
        selected.extend(group[round(index * (len(group) - 1) / max(1, count - 1))] for index in range(count))
    selected.sort(key=lambda frame: frame["time"])
    if not any(frame["phase"] == "transfer" for frame in selected):
        raise RuntimeError("No real transfer progress was recorded")
    edited = Path(tempfile.mkdtemp(prefix="edited-", dir=recording))
    for index, frame in enumerate(selected):
        shutil.copyfile(frame["file"], edited / f"{index:05d}.png")
    gif = output / f"yt-channel-downloader-demo-{suffix}.gif"
    subprocess.run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-framerate", "8",
        "-i", str(edited / "%05d.png"), "-filter_complex",
        "[0:v]split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle",
        "-loop", "0", str(gif),
    ], check=True)
    metadata.update({"gif": str(gif), "retained_frames": len(selected), "duration": len(selected) / 8})
    (recording / "capture.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Saved {gif}: {len(selected)} frames, {len(selected) / 8:.2f}s, {gif.stat().st_size:,} bytes")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/images")
    parser.add_argument("--recording-dir", type=Path, default=ROOT / "build/readme-workflow")
    parser.add_argument("--url", default=CHANNEL)
    parser.add_argument("--filter", default="Recap")
    parser.add_argument("--rate-limit", type=int, default=512 * 1024)
    args = parser.parse_args()
    if sys.platform not in ("darwin", "win32", "linux"):
        parser.error("Capture on macOS, Windows, or Linux")
    if args.rate_limit <= 0:
        parser.error("--rate-limit must be positive")
    record(args.output_dir.resolve(), args.recording_dir.resolve(), args.url, args.filter, args.rate_limit)


if __name__ == "__main__":
    main()
