# Author: hyperfield
# Email: inbox@quicknode.net
# Project: YT Channel Downloader
# Description: This module contains the class YouTubeURLValidator
# and DownloadThread.
# License: MIT License

import re
from urllib.error import HTTPError
import yt_dlp

from classes.logger import get_logger
from classes.utils import QuietYDLLogger


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
                'quiet': True,
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
            'quiet': True,
            'skip_download': True,
            'extract_flat': True,
            'playlistend': 100,
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


def extract_single_media(url, auth_opts=None):
    """
    Extract single media metadata for any yt-dlp supported URL.

    Returns:
        dict | None: Metadata dict containing title and url if successful.
    """
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'noplaylist': True,
    }
    if auth_opts:
        ydl_opts.update(auth_opts)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info.get('_type') == 'playlist':
                entries = info.get('entries') or []
                first = next((entry for entry in entries if entry), None)
                if not first:
                    logger.warning("Playlist has no entries for URL: %s", url)
                    return None
                info = first
            title = info.get('title') or 'Unknown Title'
            final_url = info.get('webpage_url') or info.get('url') or url
            duration = info.get('duration')
            if isinstance(duration, float):
                duration = int(duration)
            if isinstance(duration, str):
                duration = int(duration) if duration.isdigit() else yt_dlp.utils.parse_duration(duration)
            if duration is None and info.get('duration_string'):
                try:
                    duration = yt_dlp.utils.parse_duration(info['duration_string'])
                except Exception:  # noqa: BLE001
                    duration = None
            return {'title': title, 'url': final_url, 'duration': duration}
    except yt_dlp.utils.DownloadError as exc:
        logger.debug("yt-dlp failed to extract metadata for %s: %s", url, exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error while extracting metadata for %s: %s", url, exc)
    return None


def is_supported_media_url(url, auth_opts=None):
    """Check whether the provided URL is supported by yt-dlp."""
    return extract_single_media(url, auth_opts=auth_opts) is not None
