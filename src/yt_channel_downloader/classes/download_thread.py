# Author: hyperfield
# Email: inbox@quicknode.net
# Project: YT Channel Downloader
# Description: This module contains the class DownloadThread
# License: MIT License

import os
import re
import time
import unicodedata

from .utils import get_format_candidates
from .quiet_ydl_logger import QuietYDLLogger
from .yt_dlp_options import javascript_options
from .download_identity import audio_preferences, download_path, video_preferences
from .media_postprocessors import AudioBitratePP, FinalizeDownloadPP, VideoContainerPP
from .media_files import FINAL_MEDIA_EXTENSIONS
from .settings_manager import SettingsManager
from ..config.constants import LOSSY_AUDIO_FORMATS
from .logger import get_logger

import yt_dlp

from PyQt6.QtCore import QThread, pyqtSignal as Signal


logger = get_logger("DownloadThread")


class DownloadThread(QThread):
    """
    A QThread subclass that handles downloading videos from YouTube with
    specificformats and qualities.

    Attributes:
        download_progress_signal (Signal): Signal emitted during the download
        process with progress details.
        download_complete_signal (Signal): Signal emitted once the download
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

    download_progress_signal = Signal(dict)
    download_complete_signal = Signal(int)

    def __init__(self, url, index, title, mainWindow, parent=None, *, output_path=None):
        """Store download context and initialise throttled progress tracking."""
        super().__init__(parent)
        self.url = url
        self.index = index
        self.title = title
        self.main_window = mainWindow
        self.settings_manager = SettingsManager()
        self.user_settings = dict(self.settings_manager.settings)
        self.output_path = output_path
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
        acquired = False
        try:
            while not acquired:
                self._raise_if_cancelled()
                acquired = self.main_window.download_semaphore.acquire(timeout=0.1)
            self._raise_if_cancelled()
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
            if acquired:
                self.main_window.download_semaphore.release()
                logger.debug("Released download semaphore for index %s", self.index)

    def _raise_if_cancelled(self):
        if self._cancel_requested:
            raise yt_dlp.utils.DownloadCancelled("Cancelled by user")

    def _perform_download(self):
        """Dispatch the download through the audio-only or video flow."""
        self._raise_if_cancelled()
        logger.info(
            "Download started for index %s url=%s audio_only=%s yt_dlp=%s",
            self.index,
            self.url,
            bool(self.user_settings.get('audio_only')),
            yt_dlp.version.__version__,
        )
        sanitized_title = self.sanitize_filename(self.title)
        ydl_opts, auth_opts = self._build_download_options(sanitized_title)

        if self.user_settings.get('audio_only'):
            self._download_audio_only_flow(ydl_opts)
        else:
            self._download_video_flow(ydl_opts, auth_opts)

        self.download_complete_signal.emit(self.index)
        logger.info("Download finished successfully for index %s", self.index)

    def _build_download_options(self, sanitized_title):
        """Build the base yt-dlp options shared by all download modes."""
        write_thumbnail = self.user_settings.get('download_thumbnail')
        output_path = self.output_path or download_path(sanitized_title, self.url, self.user_settings)
        self._resolved_output_path = output_path
        output_base = output_path.replace('%', '%%')
        ydl_opts = {
            **javascript_options(),
            'outtmpl': {'default': f'{output_base}.source.%(ext)s', 'thumbnail': f'{output_base}.%(ext)s'},
            'progress_hooks': [self.dl_hook],
            'writethumbnail': write_thumbnail,
            'noplaylist': True,
            # Some extractors return a collection even with noplaylist enabled.
            'playlist_items': '1',
            'lazy_playlist': True,
            'socket_timeout': 15,
            'quiet': True,
            'no_warnings': True,
            'logger': QuietYDLLogger(),
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
        """Return yt-dlp auth options from the configured browser-cookie manager."""
        auth_opts = {}
        manager = getattr(self.main_window, "youtube_auth_manager", None)
        if manager and manager.is_configured:
            auth_opts = manager.get_yt_dlp_options()
        return auth_opts

    def _download_audio_only_flow(self, ydl_opts):
        """Download audio using the preferred selector and fallback if required."""
        audio_format, audio_quality = self._audio_preferences()
        source_ext = 'ogg' if audio_format == 'vorbis' else audio_format
        if audio_quality.endswith('k'):
            source_ext = None
        audio_filter = f"[ext={source_ext}]" if source_ext and source_ext != 'Any' else ''
        postprocessor = {
            'key': 'FFmpegExtractAudio',
            'preferredcodec': audio_format if audio_format and audio_format != 'Any' else 'best',
        }
        if audio_quality.endswith('k'):
            postprocessor['preferredquality'] = audio_quality[:-1]
        elif audio_format in LOSSY_AUDIO_FORMATS:
            postprocessor['preferredquality'] = '256' if audio_format == 'opus' else '0'
        ydl_opts['postprocessors'] = [postprocessor]
        ydl_opts['format'] = f"bestaudio{audio_filter}/bestaudio/best" if audio_filter else 'bestaudio/best'

        try:
            self._execute_download(ydl_opts)
        except yt_dlp.utils.DownloadError as err:
            self._download_audio_fallback(err, ydl_opts, audio_format)

    def _download_audio_fallback(self, err, ydl_opts, audio_format):
        """Retry audio downloads with a broader selector for recoverable format errors."""
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
            preferred_codec = audio_format if audio_format and audio_format != 'Any' else 'best'
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
        """Resolve the preferred audio format and selector from user settings."""
        return audio_preferences(self.user_settings)

    def _download_video_flow(self, ydl_opts, auth_opts):
        """Download video with a primary selector and a quality-preserving fallback."""
        self._raise_if_cancelled()
        video_format, video_quality = self._video_preferences()
        if video_format:
            ydl_opts['postprocessors'] = [{'key': 'FFmpegVideoConvertor', 'preferedformat': video_format}]
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
        quality_fallback_selector = self._build_quality_fallback_selector(height_value, video_format)
        logger.info(
            "Video selector context for index %s: requested_quality=%s requested_format=%s auth=%s "
            "candidate_count=%s candidate_preview=%s",
            self.index,
            video_quality,
            video_format or 'Any',
            bool(auth_opts),
            len(format_candidates),
            format_candidates[:5],
        )
        logger.info("Primary format selector for index %s: %s", self.index, format_string)
        if quality_fallback_selector:
            logger.info(
                "Quality-preserving fallback selector for index %s: %s",
                self.index,
                quality_fallback_selector,
            )
        primary_opts = dict(ydl_opts)
        primary_opts['format'] = format_string

        try:
            self._execute_download(primary_opts)
        except yt_dlp.utils.DownloadError as err:
            self._download_video_fallback(err, ydl_opts, quality_fallback_selector)

    @staticmethod
    def _is_retryable_video_download_error(err_str):
        """Return True when the yt-dlp error merits a selector fallback retry."""
        return any(token in err_str for token in (
            "Requested format is not available",
            "HTTP Error 403",
            "HTTP Error 404",
        ))

    def _download_video_fallback(self, err, ydl_opts, quality_fallback_selector):
        """Retry video downloads with broader selectors before giving up."""
        err_str = str(err)
        if not self._is_retryable_video_download_error(err_str):
            raise err

        if quality_fallback_selector:
            retry_opts = dict(ydl_opts)
            retry_opts.pop('format_sort', None)
            retry_opts.pop('format_sort_force', None)
            retry_opts['format'] = quality_fallback_selector
            logger.warning(
                "Preferred format failed for index %s (%s); retrying with quality-preserving selector %s",
                self.index,
                err_str,
                quality_fallback_selector,
            )
            try:
                self._execute_download(retry_opts)
                return
            except yt_dlp.utils.DownloadError as retry_err:
                err_str = str(retry_err)
                if not self._is_retryable_video_download_error(err_str):
                    raise retry_err

        fallback_opts = dict(ydl_opts)
        fallback_opts.pop('format_sort', None)
        fallback_opts.pop('format_sort_force', None)
        height = self._parse_height(self._video_preferences()[1])
        fallback_opts['format'] = f'best[height<=?{height}]' if height else 'best'
        logger.warning(
            "Preferred video download failed for index %s (%s); falling back to progressive best.",
            self.index,
            err_str,
        )
        self._execute_download(fallback_opts)

    def _video_preferences(self):
        """Resolve the preferred video extension and quality selector."""
        return video_preferences(self.user_settings)

    @staticmethod
    def _parse_height(video_quality):
        """Extract a numeric height limit from a quality selector such as 1080p."""
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
        """Notify the UI that the current download stopped at partial progress."""
        self.download_progress_signal.emit({
            "index": str(self.index),
            "error": "Cancelled",
            "progress": self._last_progress,
            "speed": "—",
        })
        logger.info("Download cancelled for index %s", self.index)

    def _emit_progress_error(self, message):
        """Notify the UI that the current download ended with an error."""
        self.download_progress_signal.emit({
            "index": str(self.index),
            "error": message,
            "speed": "—",
        })

    def _build_format_selector(self, candidates, height, file_ext):
        """Build the primary yt-dlp selector from exact candidates plus fallbacks."""
        selectors = []
        height_filter = f'[height<=?{height}]' if height else ''
        for fmt in candidates:
            selectors.append(f"{fmt}{height_filter}+bestaudio")
            selectors.append(f"{fmt}{height_filter}[acodec!=none]")
        quality_selector = self._build_quality_fallback_selector(height, file_ext)
        if quality_selector:
            selectors.append(quality_selector)
        selectors.append(f"bestvideo*{height_filter}+bestaudio/best{height_filter}/bestvideo*{height_filter}")
        return self._join_unique_selectors(selectors)

    @staticmethod
    def _has_specific_extension(file_ext) -> bool:
        return bool(file_ext and file_ext != 'Any')

    @staticmethod
    def _join_unique_selectors(selectors) -> str:
        seen = set()
        ordered = []
        for item in selectors:
            if item not in seen:
                seen.add(item)
                ordered.append(item)
        return '/'.join(ordered)

    def _build_quality_fallback_selector(self, height, file_ext):
        """Retry without format IDs, keeping the resolution limit before conversion."""
        if height:
            return f"bestvideo[height<=?{height}]+bestaudio/best[height<=?{height}]"
        if self._has_specific_extension(file_ext):
            return 'bestvideo+bestaudio/best'
        return ''

    def _execute_download(self, options):
        """Run yt-dlp with the prepared options, respecting cancellation."""
        self._raise_if_cancelled()
        options = dict(options)
        audio_encoder = None
        video_converter = None
        explicit_audio_bitrate = bool(self.user_settings.get('audio_only') and self._audio_preferences()[1].endswith('k'))
        postprocessors = []
        for processor in options.get('postprocessors', []):
            if processor['key'] == 'FFmpegExtractAudio' and explicit_audio_bitrate:
                audio_encoder = processor
            elif processor['key'] == 'FFmpegVideoConvertor':
                video_converter = processor
            else:
                postprocessors.append(processor)
        options['postprocessors'] = postprocessors
        with yt_dlp.YoutubeDL(options) as ydl:
            if video_converter:
                ydl.add_post_processor(VideoContainerPP(ydl, preferedformat=video_converter['preferedformat']))
            if audio_encoder:
                ydl.add_post_processor(AudioBitratePP(
                    ydl, audio_encoder['preferredcodec'], audio_encoder['preferredquality']))
            raw_aac = self.user_settings.get('audio_only') and self._audio_preferences()[0] == 'aac'
            ydl.add_post_processor(FinalizeDownloadPP(
                ydl, self._resolved_output_path, 'aac' if raw_aac else None), when='after_move')
            self._raise_if_cancelled()
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
        self._raise_if_cancelled()
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes')
            progress = self._last_progress
            if total and total > 0 and downloaded is not None:
                progress = max(0.0, min(100.0, 100.0 * downloaded / total))
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
                self.download_progress_signal.emit(
                    {
                        "index": str(self.index),
                        "progress": progress,
                        "speed": speed_display,
                        "speed_bps": raw_speed,
                    }
                )

    @staticmethod
    def sanitize_filename(filename, *, legacy=False):
        """
        Sanitizes the filename by removing illegal characters, emoji, hashtags, and
        other symbols unsuitable for file names. Also checks against reserved filenames.

        Args:
            filename (str): The initial filename based on the video title.
            legacy (bool): Preserve the old naming rules when finding existing files.

        Returns:
            str: A sanitized filename safe for use in file systems.
        """
        # Remove leading and trailing whitespace
        filename = filename.strip()

        # Normalize Unicode characters to decompose accents and remove emojis
        filename = unicodedata.normalize("NFKD", filename)

        # Remove emoji and other non-ASCII characters
        excluded_categories = ("So",) if legacy else ("So", "Cc", "Cs")
        filename = ''.join(c for c in filename if not
                           unicodedata.category(c).startswith(excluded_categories))

        # Replace spaces with underscores
        filename = filename.replace(' ', '_')

        # Remove characters that are illegal in Windows filenames and hashtags
        filename = re.sub(r'[\\/*?:"<>|\[\]#]', '', filename)

        # Check for Windows reserved filenames and modify if necessary
        reserved_filenames = {
            "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5",
            "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4",
            "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
        }
        if legacy:
            filename = filename[:250]
            return filename + '_' if filename.upper() in reserved_filenames else filename
        if filename.split('.', 1)[0].upper() in reserved_filenames:
            filename = '_' + filename

        # Leave space for stream IDs, extensions, and yt-dlp's temporary suffixes.
        return filename.encode('utf-8')[:200].decode('utf-8', errors='ignore').rstrip('. ') or 'video'

    @staticmethod
    def is_download_complete(filepath):
        """
        Check for a nonempty final media file, excluding thumbnails and fragments.

        Args:
            filepath (str): The path to the file without the extension.

        Returns:
            bool: True if the download is complete, False otherwise.
        """

        for extension in FINAL_MEDIA_EXTENSIONS:
            candidate = f"{filepath}.{extension}"
            try:
                if os.path.isfile(candidate) and os.path.getsize(candidate) > 0:
                    return True
            except OSError:
                continue
        return False
