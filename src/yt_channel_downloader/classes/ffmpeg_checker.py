import os
import shutil
import sys
from PyQt6.QtWidgets import QApplication, QStyle

from .custom_dialog import CustomDialog


class FFmpegChecker:
    @staticmethod
    def _candidate_paths():
        """Return additional locations where ffmpeg might live."""
        candidates = []

        env_binary = os.environ.get("FFMPEG_BINARY")
        if env_binary:
            candidates.append(env_binary)

        # PyInstaller bundles can ship ffmpeg alongside the executable.
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.extend([
                os.path.join(meipass, "ffmpeg"),
                os.path.join(meipass, "bin", "ffmpeg"),
            ])

        if os.name == "nt":
            candidates.extend([
                r"C:\Program Files\FFmpeg\bin\ffmpeg.exe",
                r"C:\FFmpeg\bin\ffmpeg.exe",
                r"C:\ffmpeg.exe",
            ])
        else:
            unix_candidates = [
                "/opt/homebrew/bin/ffmpeg",
                "/usr/local/bin/ffmpeg",
                "/usr/bin/ffmpeg",
                "/opt/local/bin/ffmpeg",
                "/snap/bin/ffmpeg",
            ]
            candidates.extend(unix_candidates)

        return candidates

    @staticmethod
    def _is_executable(path):
        """Return True if the given path points to an executable file."""
        if not path:
            return False
        expanded = os.path.expanduser(path)
        if os.path.isdir(expanded):
            expanded = os.path.join(expanded, "ffmpeg")
        return os.path.isfile(expanded) and os.access(expanded, os.X_OK)

    @staticmethod
    def is_ffmpeg_installed():
        """Check if FFmpeg is installed on the system."""
        if shutil.which("ffmpeg"):
            return True

        return any(FFmpegChecker._is_executable(candidate)
                   for candidate in FFmpegChecker._candidate_paths())

    @staticmethod
    def show_ffmpeg_error_dialog():
        """Show an error dialog if FFmpeg is not installed."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])  # Create a QApplication instance if it doesn’t exist

        error_icon = app.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical)

        message = (
            "FFmpeg is required to run this application, but it is not installed on the system.<br><br>"
            "Please install FFmpeg and ensure it's in your system PATH environment variable.<br>"
            'Download FFmpeg at <a href="https://ffmpeg.org/download.html">https://ffmpeg.org/download.html</a>'
        )

        dialog = CustomDialog("FFmpeg Not Found", message, icon=error_icon)
        dialog.exec()
