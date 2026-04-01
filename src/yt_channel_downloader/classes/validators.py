# Author: hyperfield
# Email: inbox@quicknode.net
# Project: YT Channel Downloader
# Description: This module contains the class YouTubeURLValidator
# and DownloadThread.
# License: MIT License

import re
from typing import Any, Dict, Optional
from urllib.error import HTTPError
import yt_dlp

from .logger import get_logger
from .quiet_ydl_logger import QuietYDLLogger


logger = get_logger("YouTubeURLValidator")


class YouTubeURLValidator:
    """Helpers for validating YouTube URLs and extracting lightweight metadata."""
    @staticmethod
    def check_existence(video_id, extra_opts=None):
        """Check if a YouTube video exists and is available using yt-dlp."""
        try:
            ydl_opts = {'quiet': True}
            if extra_opts:
                ydl_opts.update(extra_opts)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}",
                                 download=False)
            return True
        except yt_dlp.utils.DownloadError:
            logger.debug("yt-dlp reported unavailable video: %s", video_id)
            return False

    @staticmethod
    def _build_ydl_opts(base_opts, extra_opts=None):
        """Merge shared yt-dlp options with per-call overrides and a quiet logger."""
        opts = base_opts.copy()
        if extra_opts:
            opts.update(extra_opts)
        opts.setdefault('logger', QuietYDLLogger())
        return opts

    @staticmethod
    def playlist_exists(playlist_url, extra_opts=None):
        """Return True when yt-dlp can resolve at least one playlist entry."""
        info = YouTubeURLValidator._safe_playlist_extract(
            playlist_url,
            {
                'quiet': False,
                'no_warnings': False,
                'skip_download': True,
                'extract_flat': True,
                'playlistend': 1,
            },
            extra_opts,
            "validate playlist",
        )
        return bool(info and YouTubeURLValidator._playlist_has_entries(info))

    @staticmethod
    def extract_playlist_entries(playlist_url, extra_opts=None):
        """Extract flat playlist entries without resolving every video in full."""
        info = YouTubeURLValidator._safe_playlist_extract(
            playlist_url,
            {
                'quiet': False,
                'no_warnings': False,
                'skip_download': True,
                'noplaylist': False,
                'playlist_items': '1-1000',
                'yes_playlist': True,
                'extract_flat': True,
            },
            extra_opts,
            "extract playlist entries",
        )
        if not info:
            return []
        return YouTubeURLValidator._playlist_entries_from_info(info, playlist_url)

    @staticmethod
    def is_valid(url_or_video_id, extra_opts=None):
        """Validate the URL or video ID."""
        candidate_url = YouTubeURLValidator._validated_youtube_url(url_or_video_id, extra_opts)
        if candidate_url:
            return True, candidate_url
        logger.warning("URL validation failed for input: %s", url_or_video_id)
        return False, None

    @staticmethod
    def _safe_playlist_extract(playlist_url, base_opts, extra_opts, action):
        ydl_opts = YouTubeURLValidator._build_ydl_opts(base_opts, extra_opts)
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(playlist_url, download=False)
        except yt_dlp.utils.DownloadError as exc:
            logger.debug("yt-dlp failed to %s for %s: %s", action, playlist_url, exc)
        except HTTPError as exc:
            logger.exception("HTTP error while trying to %s for %s: %s", action, playlist_url, exc)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected error while trying to %s for %s: %s", action, playlist_url, exc)
        return None

    @staticmethod
    def _playlist_has_entries(info):
        entries = info.get('entries') or []
        return any(entry for entry in entries) or (
            info.get('_type') != 'playlist' and info.get('webpage_url')
        )

    @staticmethod
    def _playlist_entries_from_info(info, playlist_url):
        entries = info.get('entries') or []
        if entries:
            return [entry for entry in entries if entry]
        if info.get('_type') != 'playlist' and info.get('webpage_url'):
            return [info]
        logger.warning("Playlist extraction returned no entries for URL: %s", playlist_url)
        return []

    @staticmethod
    def _validated_youtube_url(url_or_video_id, extra_opts):
        for pattern, transform in YouTubeURLValidator._video_matchers():
            match = re.match(pattern, url_or_video_id)
            if not match:
                continue
            video_id = match.group(3) if match.lastindex else url_or_video_id
            if YouTubeURLValidator.check_existence(video_id, extra_opts):
                return transform(video_id, url_or_video_id)
        return None

    @staticmethod
    def _video_matchers():
        watch_pattern = (
            r'(https?://)?'
            r'(www\.)?'
            r'youtube\.com/watch\?v='
            r'([0-9A-Za-z_-]{11})'
        )
        shorts_pattern = (
            r'(https?://)?'
            r'(www\.)?'
            r'youtube\.com/shorts/'
            r'([0-9A-Za-z_-]{11})'
        )
        short_link_pattern = (
            r'(https?://)?'
            r'(www\.)?'
            r'youtu\.be/'
            r'([0-9A-Za-z_-]{11})'
        )
        video_id_pattern = r'^[0-9A-Za-z_-]{11}$'
        return (
            (watch_pattern, lambda _video_id, original: original),
            (shorts_pattern, lambda video_id, _original: YouTubeURLValidator._watch_url(video_id)),
            (short_link_pattern, lambda video_id, _original: YouTubeURLValidator._watch_url(video_id)),
            (video_id_pattern, lambda video_id, _original: YouTubeURLValidator._watch_url(video_id)),
        )

    @staticmethod
    def _watch_url(video_id):
        return f"https://www.youtube.com/watch?v={video_id}"


def extract_single_media(url: str, auth_opts: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Extract single media metadata for any yt-dlp supported URL.

    Returns:
        dict | None: Metadata dict containing title and url if successful.
    """
    ydl_opts = _single_media_opts(auth_opts)
    info = _safe_extract_info(url, ydl_opts)
    if not info:
        return None

    entry = _first_playlist_entry(info, url)
    if not entry:
        return None

    return _build_media_result(entry, url)


def _single_media_opts(auth_opts: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Build yt-dlp options for single-item metadata extraction."""
    opts: Dict[str, Any] = {
        'quiet': True,
        'skip_download': True,
        'noplaylist': True,
    }
    if auth_opts:
        opts.update(auth_opts)
    return opts


def _safe_extract_info(url: str, ydl_opts: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract yt-dlp metadata while normalising expected failures to None."""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        logger.debug("yt-dlp failed to extract metadata for %s: %s", url, exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error while extracting metadata for %s: %s", url, exc)
    return None


def _first_playlist_entry(info: Dict[str, Any], url: str) -> Optional[Dict[str, Any]]:
    """Return the first real entry when a single-media probe yields a playlist."""
    if info.get('_type') != 'playlist':
        return info
    entries = info.get('entries') or []
    first = next((entry for entry in entries if entry), None)
    if not first:
        logger.warning("Playlist has no entries for URL: %s", url)
        return None
    return first


def _build_media_result(info: Dict[str, Any], original_url: str) -> Dict[str, Any]:
    """Normalise yt-dlp metadata into the app's title/url/duration shape."""
    title = info.get('title') or 'Unknown Title'
    final_url = info.get('webpage_url') or info.get('url') or original_url
    duration = _normalize_duration(info)
    return {'title': title, 'url': final_url, 'duration': duration}


def _normalize_duration(info: Dict[str, Any]) -> Optional[int]:
    """Extract a duration in seconds from the common yt-dlp duration fields."""
    duration = _coerce_duration_value(info.get('duration'))
    if duration is not None:
        return duration
    if info.get('duration_string'):
        try:
            return yt_dlp.utils.parse_duration(info['duration_string'])
        except Exception:  # noqa: BLE001
            return None
    return None


def _coerce_duration_value(value: Any) -> Optional[int]:
    """Convert a duration-like value into seconds when possible."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        if value.isdigit():
            return int(value)
        return yt_dlp.utils.parse_duration(value)
    return None


def is_supported_media_url(url: str, auth_opts: Optional[Dict[str, Any]] = None) -> bool:
    """Check whether the provided URL is supported by yt-dlp."""
    return extract_single_media(url, auth_opts=auth_opts) is not None
