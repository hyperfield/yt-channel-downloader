# Author: hyperfield
# Email: inbox@quicknode.net
# Project: YT Channel Downloader
# Description: This module contains the class DownloadThread
# License: MIT License

import glob
import os
import re
import unicodedata

from classes.utils import get_format_candidates, QuietYDLLogger
from classes.settings_manager import SettingsManager
from config.constants import settings_map
from classes.logger import get_logger

import yt_dlp

from PyQt6.QtCore import QThread, pyqtSignal as Signal


logger = get_logger("DownloadThread")


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
        self.main_window = mainWindow
        self.settings_manager = SettingsManager()
        self.user_settings = self.settings_manager.settings
        self._cancel_requested = False
        self._last_progress = 0.0
        logger.debug("DownloadThread initialised for index %s, URL: %s", index, url)

    def cancel(self):
        """Signal the running download to halt."""
        self._cancel_requested = True

    def run(self):
        """
        Executes the download process in a separate thread with exception handling.
        Configures download options based on user preferences, fetches the video,
        and emits signals to update the UI on progress and completion.
        """
        self.main_window.download_semaphore.acquire()
        try:
            logger.info("Download started for index %s", self.index)
            sanitized_title = self.sanitize_filename(self.title)
            download_directory = self.user_settings.get('download_directory')
            write_thumbnail = self.user_settings.get('download_thumbnail')

            ydl_opts = {
                'outtmpl': os.path.join(download_directory, f'{sanitized_title}.%(ext)s'),
                'progress_hooks': [self.dl_hook],
                'writethumbnail': write_thumbnail,
                'quiet': True,
                'no_warnings': True,
                'logger': QuietYDLLogger(),
            }

            auth_opts = {}
            if self.main_window.youtube_auth_manager and \
                    self.main_window.youtube_auth_manager.is_configured:
                auth_opts = self.main_window.youtube_auth_manager.get_yt_dlp_options()
                ydl_opts.update(auth_opts)

            # Set video/audio format preferences
            video_format = settings_map['preferred_video_format'].get(
                self.user_settings.get('preferred_video_format', 'Any'), 'Any')
            video_quality = settings_map['preferred_video_quality'].get(
                self.user_settings.get('preferred_video_quality', 'bestvideo'),
                'Any')
            if video_format == 'Any':
                video_format = None
            if video_quality in ('Any', None):
                video_quality = 'bestvideo'

            if self.user_settings.get('audio_only'):
                audio_format = settings_map['preferred_audio_format'].get(
                    self.user_settings.get('preferred_audio_format', 'Any'),
                    'Any')
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
                ydl_opts['format'] = f"{audio_quality}{audio_filter}/bestaudio/best"
            else:
                format_candidates = get_format_candidates(
                    self.url,
                    video_quality,
                    video_format,
                    auth_opts,
                )
                if not format_candidates:
                    logger.warning(
                        "No exact format candidates for index %s (requested=%s/%s). Will attempt generic fallback.",
                        self.index,
                        video_quality,
                        video_format or 'Any',
                    )
                ydl_opts['format_candidates'] = format_candidates

            # Set proxy if needed
            proxy_type = self.user_settings.get('proxy_server_type', None)
            proxy_addr = self.user_settings.get('proxy_server_addr', None)
            proxy_port = self.user_settings.get('proxy_server_port', None)

            if proxy_type and proxy_addr and proxy_port:
                ydl_opts['proxy'] = f"{proxy_type}://{proxy_addr}:{proxy_port}"

            if self.user_settings.get('audio_only'):
                try:
                    self._execute_download(ydl_opts)
                except yt_dlp.utils.DownloadError as err:
                    err_str = str(err)
                    if any(token in err_str for token in (
                        "Requested format is not available",
                        "HTTP Error 403",
                        "HTTP Error 404",
                    )):
                        fallback_opts = dict(ydl_opts)
                        fallback_opts['format'] = 'best'
                        postprocessors = fallback_opts.get('postprocessors')
                        if not postprocessors:
                            preferred_codec = audio_format if audio_format and audio_format != 'Any' else 'mp3'
                            fallback_opts['postprocessors'] = [{
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': preferred_codec
                            }]
                        logger.warning(
                            "Audio-only format unavailable for index %s (%s); falling back to progressive best.",
                            self.index,
                            err_str,
                        )
                        self._execute_download(fallback_opts)
                    else:
                        raise
            else:
                format_candidates = get_format_candidates(
                    self.url,
                    video_quality,
                    video_format,
                    auth_opts,
                )
                height_value = None
                if video_quality and video_quality != 'bestvideo':
                    digits = ''.join(filter(str.isdigit, video_quality))
                    if digits:
                        try:
                            height_value = int(digits)
                        except ValueError:
                            height_value = None
                format_string = self._build_format_selector(format_candidates, height_value, video_format)
                primary_opts = dict(ydl_opts)
                primary_opts['format'] = format_string
                try:
                    self._execute_download(primary_opts)
                except yt_dlp.utils.DownloadError as err:
                    err_str = str(err)
                    if any(token in err_str for token in (
                        "Requested format is not available",
                        "HTTP Error 403",
                    )):
                        fallback_opts = dict(ydl_opts)
                        fallback_opts.pop('postprocessors', None)
                        fallback_opts['format'] = 'best'
                        logger.warning(
                            "Preferred format unavailable for index %s (%s); falling back to generic best.",
                            self.index,
                            err_str,
                        )
                        self._execute_download(fallback_opts)
                    else:
                        raise

            # Emit signal on successful download
            self.downloadCompleteSignal.emit(self.index)
            logger.info("Download finished successfully for index %s", self.index)

        except yt_dlp.utils.DownloadCancelled:
            self.downloadProgressSignal.emit({"index": str(self.index),
                                              "error": "Cancelled",
                                              "progress": self._last_progress})
            logger.info("Download cancelled for index %s", self.index)

        except yt_dlp.utils.DownloadError as e:
            # Handle yt-dlp-specific download errors
            logger.exception("Download error for %s: %s", self.url, e)
            self.downloadProgressSignal.emit({"index": str(self.index),
                                              "error": "Download error"})

        except (ConnectionError, TimeoutError) as e:
            # Handle network-related errors
            logger.exception("Network error for %s: %s", self.url, e)
            self.downloadProgressSignal.emit({"index": str(self.index),
                                              "error": "Network error"})

        except Exception as e:
            # Handle any other unforeseen errors
            logger.exception("Unexpected error for %s: %s", self.url, e)
            self.downloadProgressSignal.emit({"index": str(self.index),
                                              "error": "Unexpected error"})

        finally:
            # Release semaphore regardless of outcome
            self.main_window.download_semaphore.release()
            logger.debug("Released download semaphore for index %s", self.index)

    def _build_format_selector(self, candidates, height, file_ext):
        selectors = []
        for fmt in candidates:
            selectors.append(f"{fmt}+bestaudio")
        if height:
            selectors.append(f"bestvideo[height<={height}]+bestaudio")
            selectors.append(f"best[height<={height}]")
        if file_ext and file_ext != 'Any':
            selectors.append(f"bestvideo[ext={file_ext}]+bestaudio")
            selectors.append(f"best[ext={file_ext}]")
        selectors.append("bestvideo+bestaudio")
        selectors.append("best")
        seen = set()
        ordered = []
        for item in selectors:
            if item not in seen:
                seen.add(item)
                ordered.append(item)
        return '/'.join(ordered)

    def _execute_download(self, options):
        with yt_dlp.YoutubeDL(options) as ydl:
            if self._cancel_requested:
                raise yt_dlp.utils.DownloadCancelled("Cancelled by user")
            ydl.download([self.url])

    def dl_hook(self, d):
        """
        Callback function used by yt-dlp to handle download progress updates.

        Args:
            d (dict): A dictionary containing status information about the
            ongoing download.
        """
        if self._cancel_requested:
            raise yt_dlp.utils.DownloadCancelled("Cancelled by user")
        if d['status'] == 'downloading':
            progress_str = d['_percent_str']
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            progress_str = ansi_escape.sub('', progress_str)
            progress = float(progress_str.strip('%'))
            self._last_progress = progress
            self.downloadProgressSignal.emit(
                {"index": str(self.index), "progress": progress}
            )

    @staticmethod
    def sanitize_filename(filename):
        """
        Sanitizes the filename by removing illegal characters, emoji, hashtags, and
        other symbols unsuitable for file names. Also checks against reserved filenames.

        Args:
            filename (str): The initial filename based on the video title.

        Returns:
            str: A sanitized filename safe for use in file systems.
        """
        # Remove leading and trailing whitespace
        filename = filename.strip()

        # Normalize Unicode characters to decompose accents and remove emojis
        filename = unicodedata.normalize("NFKD", filename)

        # Remove emoji and other non-ASCII characters
        filename = ''.join(c for c in filename if not
                           unicodedata.category(c).startswith("So"))

        # Replace spaces with underscores
        filename = filename.replace(' ', '_')

        # Remove characters that are illegal in Windows filenames and hashtags
        filename = re.sub(r'[\\/*?:"<>|\[\]#]', '', filename)

        filename = filename[:250]

        # Check for Windows reserved filenames and modify if necessary
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
