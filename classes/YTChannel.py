# Author: hyperfield
# Email: info@quicknode.net
# Date: October 13, 2023
# Project: YT Channel Downloader
# Description: This module contains the classes YTChannel.
# License: MIT License

import scrapetube
from pytube import YouTube
from urllib import request, error

from .constants import KEYWORD_LEN, OFFSET_TO_CHANNEL_ID


class YTChannel:
    def __init__(self):
        self.channelId = ""
        self.base_video_url = 'https://www.youtube.com/watch?v='
        self.video_titles_links = []

    def is_video_url(self, url):
        return 'youtube.com/watch?v=' in url

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

    def get_single_video(self, video_url):
        yt = YouTube(video_url)
        vid_title = yt.title
        self.video_titles_links.append([vid_title, video_url])
        return self.video_titles_links
