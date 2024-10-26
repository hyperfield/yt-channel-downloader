# Author: hyperfield
# Email: info@quicknode.net
# Last updated: Oct 24, 2024
# Project: YT Channel Downloader
# Description: This module contains the classes YTChannel.
# License: MIT License

import scrapetube
import yt_dlp
from pytube import Playlist
from pytube.exceptions import PytubeError
import re
from urllib import request, error
from PyQt6.QtCore import QObject, pyqtSignal as Signal

from .validators import YouTubeURLValidator
from config.constants import KEYWORD_LEN, OFFSET_TO_CHANNEL_ID


class YTChannel(QObject):
    showError = Signal(str)

    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.channelId = ""
        self.base_video_url = 'https://www.youtube.com/watch?v='
        self.video_titles_links = []

    def is_video_url(self, url):
        return 'youtube.com/watch?v=' in url or len(url) == 11

    def is_playlist_url(self, url):
        """Check if the URL is related to a YouTube playlist."""
        playlist_pattern = r'list=[0-9A-Za-z_-]+'
        return re.search(playlist_pattern, url) is not None

    def is_video_with_playlist_url(self, url):
        video_with_playlist_pattern = r'youtube\.com/watch\?.*v=.*&list=[0-9A-Za-z_-]+'
        return re.search(video_with_playlist_pattern, url) is not None

    def get_channel_id(self, url):
        if "channel/" in url:
            split_url = url.split("/")
            for i in range(len(split_url)):
                if split_url[i] == "channel":
                    self.channelId = split_url[i+1]
                    return self.channelId
        try:
            html = request.urlopen(url).read().__str__()
            channelId_first_index = html.find("externalId") + KEYWORD_LEN + \
                OFFSET_TO_CHANNEL_ID
            channelId_last_index = channelId_first_index
            for symbol in html[channelId_first_index:]:
                if symbol == '"':
                    break
                channelId_last_index += 1
            self.channelId = html[channelId_first_index: channelId_last_index]
            return self.channelId
        except error.HTTPError as e:
            print(e.__dict__)
            raise e
        except error.URLError as e:
            print(e.__dict__)
            raise error.URLError("Invalid URL")
        except ValueError as e:
            print(e.__dict__)
            raise ValueError

    def retrieve_video_metadata(self, video_url):
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,  # Only extract metadata
            'noplaylist': True,    # Ensure it's not extracting a playlist
            'skip_download': True, # Skip the download step entirely
            'extractor_args': {
                'youtube': {
                    'skip': ['signature']
                }
            }
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(video_url, download=False)
            vid_title = video_info.get('title', 'Unknown Title')
            return [vid_title, video_url]
        except yt_dlp.utils.DownloadError as e:
            print(f"Error fetching video metadata: {e}")
            self.showError.emit(f"Failed to fetch video metadata: {e}")
            return None

    def get_all_videos_in_channel(self, channel_id):
        chan_video_entries = scrapetube.get_channel(channel_id)
        for entry in chan_video_entries:
            vid_title = entry['title']['runs'][0]['text']
            video_url = self.base_video_url + entry['videoId']
            self.video_titles_links.append([vid_title, video_url])
        return self.video_titles_links

    def get_videos_from_playlist(self, playlist_url):
        if YouTubeURLValidator.playlist_exists(playlist_url):
            try:
                playlist = Playlist(playlist_url)
                video_titles_links = []

                for video_url in playlist.video_urls:
                    video_data = self.retrieve_video_metadata(video_url)
                    if video_data:
                        video_titles_links.append(video_data)

                return video_titles_links

            except (PytubeError, Exception) as e:
                print(f"Error fetching playlist details: {e}")
                self.showError.emit(f"Failed to fetch playlist details: {e}")
                return []

        self.showError.emit("The URL is incorrect or unreachable.")
        return []


    def get_single_video(self, video_url):
        validation_result, formatted_url_or_id = YouTubeURLValidator.is_valid(video_url)

        if validation_result:
            video_data = self.retrieve_video_metadata(formatted_url_or_id)
            if video_data:
                self.video_titles_links.append(video_data)
            return self.video_titles_links

        self.showError.emit("The URL is incorrect or unreachable.")
        return None
