# Author: hyperfield
# Email: info@quicknode.net
# Date: March 10, 2024
# Project: YT Channel Downloader
# Description: This module contains the classes YTChannel.
# License: MIT License

import scrapetube
import re
from pytube import YouTube, Playlist
from urllib import request, error
from PySide6.QtCore import QObject, Signal

from .validators import YouTubeURLValidator
from .constants import KEYWORD_LEN, OFFSET_TO_CHANNEL_ID


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

    def get_all_videos_in_channel(self, channel_id):
        chan_video_entries = scrapetube.get_channel(channel_id)
        for entry in chan_video_entries:
            vid_title = entry['title']['runs'][0]['text']
            video_url = self.base_video_url + entry['videoId']
            self.video_titles_links.append([vid_title, video_url])
        return self.video_titles_links

    def get_videos_from_playlist(self, playlist_url):
        if YouTubeURLValidator.playlist_exists(playlist_url):
            playlist = Playlist(playlist_url)
            for video_url in playlist.video_urls:
                try:
                    yt = YouTube(video_url)
                    vid_title = yt.title
                    self.video_titles_links.append([vid_title, video_url])

                except Exception as e:
                    # Handle potential exceptions (e.g., VideoUnavailable)
                    print(f"Error fetching video details: {e}")

            return self.video_titles_links

        self.showError.emit("The URL is incorrect or unreachable.")
        return

    def get_single_video(self, video_url):
        validation_result, formatted_url_or_id =\
            YouTubeURLValidator.is_valid(video_url)

        if validation_result:
            yt = YouTube(formatted_url_or_id)
            vid_title = yt.title
            self.video_titles_links.append([vid_title, video_url])
            return self.video_titles_links

        self.showError.emit("The URL is incorrect or unreachable.")
        return
