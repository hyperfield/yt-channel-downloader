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
            return False

    @staticmethod
    def playlist_exists(playlist_url):
        try:
            playlist = Playlist(playlist_url)
            # Try accessing the first video's title to ensure it exists
            if playlist.videos[0]:
                return True
            else:
                print("Playlist seems to exist but has no videos.")
                return False
        except (PytubeError, IndexError) as e:
            print(f"Failed to fetch playlist or playlist is empty: {e}")
            return False
        except HTTPError as e:
            print(f"Failed to retrieve a possible playlist due to HTTP Error {e.code}: {e.reason}")
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
        return False, None
