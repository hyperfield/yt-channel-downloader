import os
import shutil
from PyQt6.QtWidgets import QApplication, QStyle

from classes.dialogs import CustomDialog


class FFmpegChecker:
    @staticmethod
    def is_ffmpeg_installed():
        """Check if FFmpeg is installed on the system."""
        if shutil.which("ffmpeg"):
            return True

        if os.name == "nt":  # Windows-specific checks
            possible_paths = [
                r"C:\Program Files\FFmpeg\bin\ffmpeg.exe",
                r"C:\FFmpeg\bin\ffmpeg.exe",
                r"C:\ffmpeg.exe"
            ]
            if any(os.path.exists(path) for path in possible_paths):
                return True

        return False

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
