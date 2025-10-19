# Author: hyperfield
# Email: inbox@quicknode.net
# Project: YT Channel Downloader
# Description: This module contains the class YouTubeURLValidator
# and DownloadThread.
# License: MIT License

import re
from urllib.error import HTTPError
import yt_dlp
from pytube import Playlist
from pytube.exceptions import PytubeError

from classes.logger import get_logger


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
    def playlist_exists(playlist_url):
        try:
            playlist = Playlist(playlist_url)
            # Try accessing the first video's title to ensure it exists
            if playlist.videos[0]:
                return True
            else:
                logger.warning("Playlist has no videos: %s", playlist_url)
                return False
        except (PytubeError, IndexError) as e:
            logger.exception("Failed to fetch playlist %s: %s", playlist_url, e)
            return False
        except HTTPError as e:
            logger.exception("HTTP error while fetching playlist %s: %s", playlist_url, e)
            return False

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
            return {'title': title, 'url': final_url}
    except yt_dlp.utils.DownloadError as exc:
        logger.debug("yt-dlp failed to extract metadata for %s: %s", url, exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error while extracting metadata for %s: %s", url, exc)
    return None


def is_supported_media_url(url, auth_opts=None):
    """Check whether the provided URL is supported by yt-dlp."""
    return extract_single_media(url, auth_opts=auth_opts) is not None
