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
        opts = base_opts.copy()
        if extra_opts:
            opts.update(extra_opts)
        opts.setdefault('logger', QuietYDLLogger())
        return opts

    @staticmethod
    def playlist_exists(playlist_url, extra_opts=None):
        try:
            ydl_opts = YouTubeURLValidator._build_ydl_opts({
                'quiet': False,
                'no_warnings': False,
                'skip_download': True,
                'extract_flat': True,
                'playlistend': 1,
            }, extra_opts)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(playlist_url, download=False)
            entries = info.get('entries') or []
            if any(entry for entry in entries):
                return True
            if info.get('_type') != 'playlist' and info.get('webpage_url'):
                return True
        except yt_dlp.utils.DownloadError as e:
            logger.debug("yt-dlp failed to validate playlist %s: %s", playlist_url, e)
        except Exception as e:  # noqa: BLE001
            logger.exception("Unexpected error while validating playlist %s: %s", playlist_url, e)
        except HTTPError as e:
            logger.exception("HTTP error while validating playlist %s: %s", playlist_url, e)
        return False

    @staticmethod
    def extract_playlist_entries(playlist_url, extra_opts=None):
        base_opts = {
            'quiet': False,
            'no_warnings': False,
            'skip_download': True,
            'noplaylist': False,
            'playlist_items': '1-1000',
            'yes_playlist': True,
        }
        ydl_opts = YouTubeURLValidator._build_ydl_opts(base_opts, extra_opts)
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(playlist_url, download=False)
        except yt_dlp.utils.DownloadError as e:
            logger.debug("yt-dlp failed to extract playlist entries for %s: %s", playlist_url, e)
            return []
        except Exception as e:  # noqa: BLE001
            logger.exception("Unexpected error while extracting playlist %s: %s", playlist_url, e)
            return []

        entries = info.get('entries') or []
        if entries:
            return [entry for entry in entries if entry]

        if info.get('_type') != 'playlist' and info.get('webpage_url'):
            return [info]

        logger.warning("Playlist extraction returned no entries for URL: %s", playlist_url)
        return []

    @staticmethod
    def is_valid(url_or_video_id, extra_opts=None):
        """Validate the URL or video ID."""
        url_pattern = (
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

        # Check if the URL is a regular video
        url_match = re.match(url_pattern, url_or_video_id)
        if url_match:
            video_id = url_match.group(3)
            if YouTubeURLValidator.check_existence(video_id, extra_opts):
                return True, url_or_video_id

        # Check if the URL is a YouTube Shorts video
        shorts_match = re.match(shorts_pattern, url_or_video_id)
        if shorts_match:
            video_id = shorts_match.group(3)
            if YouTubeURLValidator.check_existence(video_id, extra_opts):
                # Convert Shorts URL to standard watch URL
                full_url = f"https://www.youtube.com/watch?v={video_id}"
                return True, full_url

        # Check if the URL is a youtu.be short link
        short_link_match = re.match(short_link_pattern, url_or_video_id)
        if short_link_match:
            video_id = short_link_match.group(3)
            if YouTubeURLValidator.check_existence(video_id, extra_opts):
                # Convert to standard watch URL
                full_url = f"https://www.youtube.com/watch?v={video_id}"
                return True, full_url

        # Check if it's a direct video ID
        if re.match(video_id_pattern, url_or_video_id):
            if YouTubeURLValidator.check_existence(url_or_video_id, extra_opts):
                full_url = f"https://www.youtube.com/watch?v={url_or_video_id}"
                return True, full_url

        # If no matches
        logger.warning("URL validation failed for input: %s", url_or_video_id)
        return False, None


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
    opts: Dict[str, Any] = {
        'quiet': True,
        'skip_download': True,
        'noplaylist': True,
    }
    if auth_opts:
        opts.update(auth_opts)
    return opts


def _safe_extract_info(url: str, ydl_opts: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        logger.debug("yt-dlp failed to extract metadata for %s: %s", url, exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error while extracting metadata for %s: %s", url, exc)
    return None


def _first_playlist_entry(info: Dict[str, Any], url: str) -> Optional[Dict[str, Any]]:
    if info.get('_type') != 'playlist':
        return info
    entries = info.get('entries') or []
    first = next((entry for entry in entries if entry), None)
    if not first:
        logger.warning("Playlist has no entries for URL: %s", url)
        return None
    return first


def _build_media_result(info: Dict[str, Any], original_url: str) -> Dict[str, Any]:
    title = info.get('title') or 'Unknown Title'
    final_url = info.get('webpage_url') or info.get('url') or original_url
    duration = _normalize_duration(info)
    return {'title': title, 'url': final_url, 'duration': duration}


def _normalize_duration(info: Dict[str, Any]) -> Optional[int]:
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
