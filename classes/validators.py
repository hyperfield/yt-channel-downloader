# Author: hyperfield
# Email: inbox@quicknode.net
# Last update: November 2, 2024
# Project: YT Channel Downloader
# Description: This module contains the classes MainWindow, GetListThread
# and DownloadThread.
# License: MIT License

import re
from urllib.error import HTTPError
import yt_dlp
from pytube import Playlist
from pytube.exceptions import PytubeError


class YouTubeURLValidator:
    @staticmethod
    def check_existence(video_id):
        """Check if a YouTube video exists and is available using yt-dlp."""
        try:
            ydl_opts = {'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
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
    def is_valid(url_or_video_id):
        """Validate the URL or video ID."""
        # Pattern for regular YouTube videos
        url_pattern = r'(https?://)?(www\.)?(youtube\.com|youtu\.?be)/watch\?v=([0-9A-Za-z_-]{11})'
        
        # Pattern for YouTube Shorts
        shorts_pattern = r'(https?://)?(www\.)?youtube\.com/shorts/([0-9A-Za-z_-]{11})'
        
        # Pattern for a direct video ID
        video_id_pattern = r'^[0-9A-Za-z_-]{11}$'

        # Check if the URL is a regular video
        url_match = re.match(url_pattern, url_or_video_id)
        if url_match:
            video_id = url_match.group(4)
            if YouTubeURLValidator.check_existence(video_id):
                return True, url_or_video_id
        
        # Check if the URL is a YouTube Shorts video
        shorts_match = re.match(shorts_pattern, url_or_video_id)
        if shorts_match:
            video_id = shorts_match.group(3)
            if YouTubeURLValidator.check_existence(video_id):
                # Convert Shorts URL to standard watch URL
                full_url = f"https://www.youtube.com/watch?v={video_id}"
                return True, full_url

        # Check if it's a direct video ID
        elif re.match(video_id_pattern, url_or_video_id):
            if YouTubeURLValidator.check_existence(url_or_video_id):
                full_url = f"https://www.youtube.com/watch?v={url_or_video_id}"
                return True, full_url
        
        # If no matches
        return False, None
