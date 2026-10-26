# Author: hyperfield
# Email: inbox@quicknode.net
# Project: YT Channel Downloader
# Description: This module contains the class YouTubeURLValidator
# and DownloadThread.
# License: MIT License

import math
from typing import Any, Dict, Optional
from urllib.error import HTTPError
import yt_dlp

from .logger import get_logger
from .quiet_ydl_logger import QuietYDLLogger
from .yt_dlp_options import javascript_options
from .source_urls import youtube_video_id


logger = get_logger("YouTubeURLValidator")


class YouTubeURLValidator:
    """Helpers for validating YouTube URLs and extracting lightweight metadata."""
    @staticmethod
    def check_existence(video_id, extra_opts=None):
        """Check if a YouTube video exists and is available using yt-dlp."""
        try:
            ydl_opts = {**javascript_options(), 'quiet': True}
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
        opts = {**javascript_options(), **base_opts}
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
    def extract_playlist_entries(playlist_url, extra_opts=None, limit=None):
        """Extract flat playlist entries without resolving every video in full."""
        info = YouTubeURLValidator._safe_playlist_extract(
            playlist_url,
            {
                'quiet': False,
                'no_warnings': False,
                'skip_download': True,
                'noplaylist': False,
                'playlist_items': f'1-{limit}' if limit else None,
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
        video_id = youtube_video_id(url_or_video_id)
        if video_id and YouTubeURLValidator.check_existence(video_id, extra_opts):
            return YouTubeURLValidator._watch_url(video_id)
        return None

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

    return _build_media_result(info, url)


def _single_media_opts(auth_opts: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Build yt-dlp options for single-item metadata extraction."""
    opts: Dict[str, Any] = {
        **javascript_options(),
        'quiet': True,
        'skip_download': True,
        'noplaylist': True,
        # Inspect at most two entries to reject collections without resolving them all.
        'playlist_items': '1:2',
        'lazy_playlist': True,
        'socket_timeout': 15,
        'logger': QuietYDLLogger(),
    }
    if auth_opts:
        opts.update(auth_opts)
    return opts


def _safe_extract_info(url: str, ydl_opts: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve a single item while retaining useful extractor errors for the UI."""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return single_media_entry(info, url) if info else None
    except yt_dlp.utils.DownloadError as exc:
        logger.debug("yt-dlp failed to extract metadata for %s: %s", url, exc)
        raise ValueError(str(exc)) from exc
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error while extracting metadata for %s: %s", url, exc)
    return None


def single_media_entry(info: Dict[str, Any], url: str) -> Optional[Dict[str, Any]]:
    """Unwrap single-item embeds, rejecting ambiguous playlists and multi-video posts."""
    if info.get('_type') not in ('playlist', 'multi_video'):
        return info
    entries = iter(info.get('entries') or [])
    first = next(entries, None)
    second = next(entries, None)
    count = info.get('playlist_count')
    if second is not None or (isinstance(count, (int, float)) and count > 1):
        raise ValueError(
            'This URL contains multiple media items. Paste a direct link to one item. '
            'Bulk channel and playlist fetching is available for YouTube only.')
    if not first:
        logger.warning("Playlist has no entries for URL: %s", url)
        return None
    return single_media_entry(first, url)


def _build_media_result(info: Dict[str, Any], original_url: str) -> Dict[str, Any]:
    """Keep the source page so yt-dlp can refresh signed streams and request headers."""
    title = info.get('title') or 'Unknown Title'
    final_url = original_url
    duration = _normalize_duration(info)
    result = {'title': title, 'url': final_url, 'duration': duration}
    for key in ('thumbnail', 'thumbnails'):
        if info.get(key):
            result[key] = info[key]
    return result


def _normalize_duration(info: Dict[str, Any]) -> Optional[int]:
    """Extract a duration in seconds from the common yt-dlp duration fields."""
    duration = _coerce_duration_value(info.get('duration'))
    if duration is not None:
        return duration
    if info.get('duration_string'):
        try:
            return _coerce_duration_value(info['duration_string'])
        except Exception:  # noqa: BLE001
            return None
    return None


def _coerce_duration_value(value: Any) -> Optional[int]:
    """Convert a duration-like value into seconds when possible."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        try:
            value = yt_dlp.utils.parse_duration(value.strip())
        except (TypeError, ValueError, OverflowError):
            return None
    if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0:
        return int(value)
    return None


def is_supported_media_url(url: str, auth_opts: Optional[Dict[str, Any]] = None) -> bool:
    """Probe support; callers must run this network operation off the GUI thread."""
    try:
        return extract_single_media(url, auth_opts=auth_opts) is not None
    except ValueError:
        return False
