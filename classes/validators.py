# Author: hyperfield
# Email: info@quicknode.net
# Date: March 10, 2024
# Project: YT Channel Downloader
# Description: This module contains the classes YTChannel.
# License: MIT License

import re
from pytube import YouTube, Playlist
from pytube.exceptions import VideoUnavailable, PytubeError
from urllib.error import HTTPError


class YouTubeURLValidator:
    @staticmethod
    def check_existence(video_id):
        """Check if a YouTube video exists and is available."""
        try:
            yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")
            yt.check_availability()
            return True
        except VideoUnavailable:
            return False

    @staticmethod
    def playlist_exists(playlist_url):
        try:
            playlist = Playlist(playlist_url)
            if playlist.video_urls:
                first_video = playlist.videos[0]
                _ = first_video.title
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
    def is_valid(url_or_video_id):
        """Validate the URL or video ID."""
        url_pattern = r'(https?://)?(www\.)?(youtube\.com|youtu\.?be)/watch\?v=([0-9A-Za-z_-]{11})'
        video_id_pattern = r'^[0-9A-Za-z_-]{11}$'

        url_match = re.match(url_pattern, url_or_video_id)
        if url_match:
            video_id = url_match.group(4)
            if YouTubeURLValidator.check_existence(video_id):
                return True, url_or_video_id
            else:
                return False, None
        elif re.match(video_id_pattern, url_or_video_id):
            if YouTubeURLValidator.check_existence(url_or_video_id):
                full_url = f"https://www.youtube.com/watch?v={url_or_video_id}"
                return True, full_url
            else:
                return False, None
        else:
            return False, None
