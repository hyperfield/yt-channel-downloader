import glob
import os
import re
import yt_dlp

from PyQt6.QtCore import QThread, pyqtSignal as Signal

from .utils import get_video_format_details
from .settings_manager import SettingsManager
from config.constants import settings_map


class DownloadThread(QThread):
    """
    A QThread subclass that handles downloading videos from YouTube with
    specificformats and qualities.

    Attributes:
        downloadProgressSignal (Signal): Signal emitted during the download
        process with progress details.
        downloadCompleteSignal (Signal): Signal emitted once the download
        is complete.

    Args:
        url (str): The URL of the video to be downloaded.
        index (int): The index identifier for the download, used for managing
        multiple downloads.
        title (str): The title of the video, used for naming the downloaded
        file.
        mainWindow (MainWindow): Reference to the main window of the
        applicationfor UI interactions and semaphore access.
        parent (QObject, optional): The parent QObject. Defaults to None.
    """

    downloadProgressSignal = Signal(dict)
    downloadCompleteSignal = Signal(int)

    def __init__(self, url, index, title, mainWindow, parent=None):
        super().__init__(parent)
        self.url = url
        self.index = index
        self.title = title
        self.mainWindow = mainWindow
        self.settings_manager = SettingsManager()
        self.user_settings = self.settings_manager.settings

    def run(self):
        """
        Executes the download process in a separate thread. Configures download
        options based on user preferences, fetches the video, and emits signals
        to update the UI on progress and completion.
        """

        self.mainWindow.download_semaphore.acquire()
        sanitized_title = self.sanitize_filename(self.title)
        download_directory = self.user_settings.get('download_directory')

        ydl_opts = {
            'outtmpl':
                os.path.join(download_directory, f'{sanitized_title}.%(ext)s'),
            'progress_hooks': [self.dl_hook],
        }

        if self.mainWindow.youtube_login_dialog and self.mainWindow.youtube_login_dialog.logged_in:
            cookie_file_path = self.mainWindow.youtube_login_dialog.cookie_jar_path
            ydl_opts['cookiefile'] = cookie_file_path
        else:
            cookie_file_path = None

        video_format = settings_map['preferred_video_format'].get(
            self.user_settings.get('preferred_video_format', 'Any'), 'Any')
        video_quality = settings_map['preferred_video_quality'].get(
            self.user_settings.get('preferred_video_quality',
                                   'bestvideo'), 'Any')
        
        closest_format_id = get_video_format_details(self.url, video_quality,
                                                     video_format, cookie_file_path)

        if closest_format_id:
            ydl_opts['format'] = f"{closest_format_id}+bestaudio"
        elif video_quality:
            ydl_opts['format'] = video_quality
        else:
            ydl_opts['format'] = 'bestvideo+bestaudio'

        if self.user_settings.get('audio_only'):
            audio_format = settings_map['preferred_audio_format'].get(
                self.user_settings.get('preferred_audio_format', 'Any'), 'Any')
            audio_quality = settings_map['preferred_audio_quality'].get(
                self.user_settings.get('preferred_audio_quality',
                                       'Best available'), 'bestaudio')
            if audio_format and audio_format != 'Any':
                audio_filter = f"[ext={audio_format}]"
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': audio_format
                }]
            else:
                audio_filter = ''

            ydl_opts['format'] = \
                f"{audio_quality}{audio_filter}/bestaudio/best"

            proxy_type = self.user_settings.get('proxy_server_type', None)
            proxy_addr = self.user_settings.get('proxy_server_addr', None)
            proxy_port = self.user_settings.get('proxy_server_port', None)

            if proxy_type and proxy_addr and proxy_port:
                ydl_opts['proxy'] = f"{proxy_type}://{proxy_addr}:{proxy_port}"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([self.url])
        self.downloadCompleteSignal.emit(self.index)
        self.mainWindow.download_semaphore.release()

    def dl_hook(self, d):
        """
        Callback function used by yt-dlp to handle download progress updates.

        Args:
            d (dict): A dictionary containing status information about the
            ongoing download.
        """
        if d['status'] == 'downloading':
            progress_str = d['_percent_str']
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            progress_str = ansi_escape.sub('', progress_str)
            progress = float(progress_str.strip('%'))
            self.downloadProgressSignal.emit(
                {"index": str(self.index), "progress": f"{progress} %"}
                )

    @staticmethod
    def sanitize_filename(filename):
        """
        Sanitizes the filename by removing illegal characters and checking against reserved filenames.

        Args:
            filename (str): The initial filename based on the video title.

        Returns:
            str: A sanitized filename safe for use in file systems.
        """
        filename = filename.strip()
        filename = filename.replace(' ', '_')
        # Remove or replace characters that are illegal in Windows filenames,
        # and potentially problematic for glob patterns (like square brackets)
        filename = re.sub(r'[\\/*?:"<>|\[\]]', '', filename)
        filename = filename[:250]

        # Check for Windows reserved filenames
        reserved_filenames = {
            "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5",
            "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4",
            "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
        }
        if filename.upper() in reserved_filenames:
            filename += "_"

        return filename

    @staticmethod
    def is_download_complete(filepath):
        """
        Checks if the download for a given file is complete by looking for
        temporary `.part` or `.ytdl` files.

        Args:
            filepath (str): The path to the file without the extension.

        Returns:
            bool: True if the download is complete, False otherwise.
        """

        part_files = glob.glob(f"{filepath}*.part")
        ytdl_files = glob.glob(f"{filepath}*.ytdl")

        # If any partially downloaded files are found,
        # the download is incomplete
        if part_files or ytdl_files:
            return False

        matching_files = glob.glob(f"{filepath}.*")

        # Otherwise only completely downloaded files would be found
        if not matching_files:
            return False

        return True
