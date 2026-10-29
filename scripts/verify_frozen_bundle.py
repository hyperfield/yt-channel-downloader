"""Exercise a frozen bundle with temporary settings and a local media fixture."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from importlib import metadata
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
import threading
from functools import partial
import wave


def check_local_download(directory: Path) -> None:
    import yt_dlp

    fixture = directory / "fixture.wav"
    with wave.open(str(fixture), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8000)
        output.writeframes(b"\x00\x00" * 800)

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(Handler, directory=str(directory)),
    )
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        with yt_dlp.YoutubeDL({
            "quiet": True,
            "noprogress": True,
            "cachedir": False,
            "proxy": "",
            "outtmpl": str(directory / "download.%(ext)s"),
        }) as downloader:
            info = downloader.extract_info(
                f"http://127.0.0.1:{server.server_port}/fixture.wav", download=True,
            )
            downloaded = Path(downloader.prepare_filename(info))
        assert downloaded.read_bytes() == fixture.read_bytes()
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)


def check_qt() -> None:
    from PyQt6 import QtCore, QtGui, QtWidgets
    from yt_channel_downloader.classes.mainwindow import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    for method in (
        "initialize_youtube_login", "_schedule_auto_update_check",
        "_init_thumbnail_loader", "_init_node_notifier", "_init_support_prompt",
    ):
        setattr(MainWindow, method, lambda self: None)
    window = MainWindow()
    try:
        assert not window.windowIcon().isNull()
        assert not QtGui.QPixmap(":/images/icon.png").isNull()
        loop = QtCore.QEventLoop()
        received = []

        class Worker(QtCore.QThread):
            value = QtCore.pyqtSignal(int)

            def run(self):
                self.value.emit(42)

        worker = Worker()
        worker.value.connect(received.append)
        worker.finished.connect(loop.quit)
        QtCore.QTimer.singleShot(5000, loop.quit)
        worker.start()
        loop.exec()
        assert worker.wait(5000)
        app.processEvents()
        assert received == [42]
    finally:
        window.close()
        app.processEvents()


def main() -> None:
    assert getattr(sys, "frozen", False), "Run the frozen diagnostic executable."
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    with tempfile.TemporaryDirectory(prefix="yt-channel-downloader-bundle-check-") as temporary:
        directory = Path(temporary)
        import appdirs
        appdirs.user_config_dir = lambda *args, **kwargs: str(directory / "settings")
        try:
            from yt_channel_downloader import __version__
            from yt_channel_downloader.classes.runtime_info import detect_runtime
            import certifi
            import ssl
            import yt_dlp
            from yt_dlp.dependencies import yt_dlp_ejs as ejs_dependency
            from yt_dlp.extractor import gen_extractor_classes
            from yt_dlp.extractor.youtube import YoutubeIE
            from yt_dlp_ejs.yt import solver

            assert detect_runtime().is_frozen
            assert metadata.version("yt-channel-downloader") == __version__
            ssl.create_default_context(cafile=certifi.where())
            extractors = list(gen_extractor_classes())
            assert len(extractors) > 1000
            with yt_dlp.YoutubeDL({"quiet": True, "cachedir": False}) as downloader:
                assert isinstance(downloader.get_info_extractor("Youtube"), YoutubeIE)
                for name in ("Vimeo", "Generic"):
                    assert downloader.get_info_extractor(name).ie_key() == name
            assert ejs_dependency
            scripts = {"core": solver.core(), "lib": solver.lib()}
            assert all(len(script) > 100 for script in scripts.values())
            check_local_download(directory)
            check_qt()
            result = {
                "version": __version__,
                "python": sys.version.split()[0],
                "yt_dlp": yt_dlp.version.__version__,
                "yt_dlp_ejs": metadata.version("yt-dlp-ejs"),
                "extractor_count": len(extractors),
                "ejs_bytes": {name: len(script.encode("utf-8")) for name, script in scripts.items()},
                "checks": ["metadata", "TLS certificates", "extractors", "EJS resources", "local download", "Qt window/resources", "Qt threading"],
            }
            print("BUNDLE_CHECK_RESULT " + json.dumps(result, sort_keys=True))
        finally:
            logging.shutdown()


if __name__ == "__main__":
    main()
