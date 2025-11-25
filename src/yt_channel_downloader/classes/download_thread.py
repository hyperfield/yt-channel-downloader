# Author: hyperfield
# Email: inbox@quicknode.net
# Project: YT Channel Downloader
# Description: This module contains the class DownloadThread
# License: MIT License

import glob
import os
import re
import time
import unicodedata

from .utils import get_format_candidates
from .quiet_ydl_logger import QuietYDLLogger
from .settings_manager import SettingsManager
from ..config.constants import settings_map
from .logger import get_logger

import yt_dlp

from PyQt6.QtCore import QThread, pyqtSignal as Signal


logger = get_logger("DownloadThread")
ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


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
        self._last_emitted_progress = -1.0
        self._last_emit_timestamp = 0.0
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
            self._perform_download()

        except yt_dlp.utils.DownloadCancelled:
            self._emit_cancelled_progress()

        except yt_dlp.utils.DownloadError as e:
            logger.exception("Download error for %s: %s", self.url, e)
            self._emit_progress_error("Download error")

        except (ConnectionError, TimeoutError) as e:
            logger.exception("Network error for %s: %s", self.url, e)
            self._emit_progress_error("Network error")

        except Exception as e:
            logger.exception("Unexpected error for %s: %s", self.url, e)
            self._emit_progress_error("Unexpected error")

        finally:
            # Release semaphore regardless of outcome
            self.main_window.download_semaphore.release()
            logger.debug("Released download semaphore for index %s", self.index)

    def _perform_download(self):
        logger.info("Download started for index %s", self.index)
        sanitized_title = self.sanitize_filename(self.title)
        ydl_opts, auth_opts = self._build_download_options(sanitized_title)

        if self.user_settings.get('audio_only'):
            self._download_audio_only_flow(ydl_opts)
        else:
            self._download_video_flow(ydl_opts, auth_opts)

        self.downloadCompleteSignal.emit(self.index)
        logger.info("Download finished successfully for index %s", self.index)

    def _build_download_options(self, sanitized_title):
        download_directory = self.user_settings.get('download_directory')
        write_thumbnail = self.user_settings.get('download_thumbnail')
        ydl_opts = {
            'outtmpl': os.path.join(download_directory, f'{sanitized_title}.%(ext)s'),
            'progress_hooks': [self.dl_hook],
            'writethumbnail': write_thumbnail,
            'quiet': True,
            'no_warnings': True,
            'logger': QuietYDLLogger(),
            'remote_components': ['ejs:github'],
        }

        auth_opts = self._build_auth_options()
        proxy_url = self.settings_manager.build_proxy_url(self.user_settings)
        if proxy_url:
            auth_opts = dict(auth_opts) if auth_opts else {}
            auth_opts['proxy'] = proxy_url
            ydl_opts['proxy'] = proxy_url

        if auth_opts:
            ydl_opts.update(auth_opts)

        return ydl_opts, auth_opts

    def _build_auth_options(self):
        auth_opts = {}
        manager = getattr(self.main_window, "youtube_auth_manager", None)
        if manager and manager.is_configured:
            auth_opts = manager.get_yt_dlp_options()
        return auth_opts

    def _download_audio_only_flow(self, ydl_opts):
        audio_format, audio_quality = self._audio_preferences()
        audio_filter = f"[ext={audio_format}]" if audio_format and audio_format != 'Any' else ''
        if audio_filter:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_format
            }]
        ydl_opts['format'] = f"{audio_quality}{audio_filter}/bestaudio/best"

        try:
            self._execute_download(ydl_opts)
        except yt_dlp.utils.DownloadError as err:
            self._download_audio_fallback(err, ydl_opts, audio_format)

    def _download_audio_fallback(self, err, ydl_opts, audio_format):
        err_str = str(err)
        if not any(token in err_str for token in (
            "Requested format is not available",
            "HTTP Error 403",
            "HTTP Error 404",
        )):
            raise err

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

    def _audio_preferences(self):
        audio_format = settings_map['preferred_audio_format'].get(
            self.user_settings.get('preferred_audio_format', 'Any'),
            'Any')
        audio_quality = settings_map['preferred_audio_quality'].get(
            self.user_settings.get('preferred_audio_quality', 'Best available'),
            'bestaudio')
        return audio_format, audio_quality

    def _download_video_flow(self, ydl_opts, auth_opts):
        video_format, video_quality = self._video_preferences()
        ydl_opts['format_sort'] = ['hasvid']
        ydl_opts['format_sort_force'] = True
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

        height_value = self._parse_height(video_quality)
        format_string = self._build_format_selector(format_candidates, height_value, video_format)
        primary_opts = dict(ydl_opts)
        primary_opts['format'] = format_string
        logger.debug("Format selector for index %s: %s", self.index, format_string)

        try:
            self._execute_download(primary_opts)
        except yt_dlp.utils.DownloadError as err:
            self._download_video_fallback(err, ydl_opts)

    def _download_video_fallback(self, err, ydl_opts):
        err_str = str(err)
        if not any(token in err_str for token in (
            "Requested format is not available",
            "HTTP Error 403",
        )):
            raise err

        fallback_opts = dict(ydl_opts)
        fallback_opts.pop('postprocessors', None)
        fallback_opts['format'] = 'best'
        logger.warning(
            "Preferred format unavailable for index %s (%s); falling back to generic best.",
            self.index,
            err_str,
        )
        self._execute_download(fallback_opts)

    def _video_preferences(self):
        video_format = settings_map['preferred_video_format'].get(
            self.user_settings.get('preferred_video_format', 'Any'), 'Any')
        video_quality = settings_map['preferred_video_quality'].get(
            self.user_settings.get('preferred_video_quality', 'bestvideo'),
            'Any')
        if video_format == 'Any':
            video_format = None
        if video_quality in ('Any', None):
            video_quality = 'bestvideo'
        return video_format, video_quality

    @staticmethod
    def _parse_height(video_quality):
        if not video_quality or video_quality == 'bestvideo':
            return None
        digits = ''.join(filter(str.isdigit, video_quality))
        if not digits:
            return None
        try:
            return int(digits)
        except ValueError:
            return None

    def _emit_cancelled_progress(self):
        self.downloadProgressSignal.emit({
            "index": str(self.index),
            "error": "Cancelled",
            "progress": self._last_progress,
            "speed": "—",
        })
        logger.info("Download cancelled for index %s", self.index)

    def _emit_progress_error(self, message):
        self.downloadProgressSignal.emit({
            "index": str(self.index),
            "error": message,
            "speed": "—",
        })

    def _build_format_selector(self, candidates, height, file_ext):
        selectors = []
        for fmt in candidates:
            selectors.append(f"{fmt}+bestaudio")
        if height:
            selectors.append(f"bestvideo[height<={height}]+bestaudio")
            selectors.append(f"bestvideo[height<={height}]")
        if file_ext and file_ext != 'Any':
            selectors.append(f"bestvideo[ext={file_ext}]+bestaudio")
            selectors.append(f"bestvideo[ext={file_ext}]")
        selectors.append("bestvideo*+bestaudio/bestvideo*")
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

    @staticmethod
    def _format_speed(speed_bytes_per_sec):
        """
        Convert a byte-per-second speed reading into a human-readable string.
        Displays speeds in KB/s for sub-megabyte transfers and in MB/s beyond that.
        """
        if not speed_bytes_per_sec or speed_bytes_per_sec <= 0:
            return "—"

        kilobyte_per_sec = speed_bytes_per_sec / 1024
        if kilobyte_per_sec < 1:
            return f"{speed_bytes_per_sec:.0f} B/s"

        if kilobyte_per_sec < 1024:
            return f"{kilobyte_per_sec:.1f} KB/s"

        megabyte_per_sec = kilobyte_per_sec / 1024
        if megabyte_per_sec < 1024:
            return f"{megabyte_per_sec:.2f} MB/s"

        gigabyte_per_sec = megabyte_per_sec / 1024
        return f"{gigabyte_per_sec:.2f} GB/s"

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
            progress_str = ANSI_ESCAPE_RE.sub('', d['_percent_str'])
            progress = float(progress_str.strip('%'))
            self._last_progress = progress
            now = time.monotonic()
            should_emit = (
                progress >= 100.0
                or self._last_emitted_progress < 0.0
                or abs(progress - self._last_emitted_progress) >= 1.0
                or (now - self._last_emit_timestamp) >= 0.25
            )
            if should_emit:
                raw_speed = d.get('speed')
                speed_display = self._format_speed(raw_speed)
                self._last_emit_timestamp = now
                self._last_emitted_progress = progress
                self.downloadProgressSignal.emit(
                    {
                        "index": str(self.index),
                        "progress": progress,
                        "speed": speed_display,
                        "speed_bps": raw_speed,
                    }
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
