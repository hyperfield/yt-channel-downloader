# Author: hyperfield
# Email: inbox@quicknode.net
# Project: YT Channel Downloader
# Description: This module contains the class YTChannel.
# License: MIT License

import re
from urllib import request, error

from classes.validators import YouTubeURLValidator, extract_single_media, is_supported_media_url
from classes.utils import QuietYDLLogger
from config.constants import KEYWORD_LEN, OFFSET_TO_CHANNEL_ID

import scrapetube
import yt_dlp
from PyQt6.QtCore import QObject, pyqtSignal as Signal

from classes.logger import get_logger


class YTChannel(QObject):
    showError = Signal(str)

    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.channelId = ""
        self.base_video_url = 'https://www.youtube.com/watch?v='
        self.video_titles_links = []
        self.logger = get_logger("YTChannel")

    def _get_auth_params(self):
        manager = getattr(self.main_window, "youtube_auth_manager", None)
        if manager and manager.is_configured:
            return manager.get_yt_dlp_options()
        return {}

    def is_video_url(self, url):
        return 'youtube.com/watch?v=' in url or 'youtu.be/' in url \
            or len(url) == 11

    def is_playlist_url(self, url):
        """Check if the URL is related to a YouTube playlist."""
        playlist_pattern = r'list=[0-9A-Za-z_-]+'
        return re.search(playlist_pattern, url) is not None

    def is_video_with_playlist_url(self, url):
        video_with_playlist_pattern = r'youtube\.com/watch\?.*v=.*&list=[0-9A-Za-z_-]+'
        return re.search(video_with_playlist_pattern, url) is not None

    def is_short_video_url(self, url):
        """Check if the URL is related to a YouTube Shorts video."""
        return 'youtube.com/shorts/' in url

    def get_channel_id(self, url):
        if "channel/" in url:
            split_url = url.split("/")
            for i in range(len(split_url)):
                if split_url[i] == "channel":
                    self.channelId = split_url[i+1]
                    return self.channelId
        try:
            html = request.urlopen(url, timeout=10).read().__str__()
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
            self.logger.exception("HTTP error while resolving channel ID: %s", e)
            raise e
        except error.URLError as e:
            self.logger.exception("URL error while resolving channel ID: %s", e)
            raise error.URLError("Invalid URL")
        except ValueError as e:
            self.logger.exception("Value error while resolving channel ID: %s", e)
            raise ValueError

    def retrieve_video_metadata(self, video_url):
        auth_opts = self._get_auth_params()
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,   # Only extract metadata
            'noplaylist': True,     # Ensure it's not extracting a playlist
            'skip_download': True,  # Skip the download step entirely
            'socket_timeout': 10,
            'extractor_args': {
                'youtube': {
                    'skip': ['signature'],
                }
            },
            'logger': QuietYDLLogger(),
        }
        ydl_opts.update(auth_opts)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(video_url, download=False)
            vid_title = video_info.get('title', 'Unknown Title')
            return [vid_title, video_url]
        except yt_dlp.utils.DownloadError as e:
            self.logger.exception("Error fetching video metadata for %s: %s", video_url, e)
            self.showError.emit(f"Failed to fetch video metadata: {e}")
            raise

    def fetch_all_videos_in_channel(self, channel_id):
        try:
            chan_video_entries = scrapetube.get_channel(channel_id)
            for entry in chan_video_entries:
                vid_title = entry['title']['runs'][0]['text']
                video_url = self.base_video_url + entry['videoId']
                self.video_titles_links.append([vid_title, video_url])
            return self.video_titles_links
        except TimeoutError:
            self.logger.error("Timeout while fetching channel videos for %s", channel_id)
            self.showError.emit("Failed to fetch channel videos: Timeout reached")
            return []
        except Exception as exc:  # noqa: BLE001
            self.logger.exception("Unexpected error fetching channel videos for %s: %s", channel_id, exc)
            self.showError.emit("Failed to fetch channel videos: unexpected error")
            return []

    def fetch_videos_from_playlist(self, playlist_url):
        auth_opts = self._get_auth_params()
        if YouTubeURLValidator.playlist_exists(playlist_url, auth_opts):
            video_titles_links = []
            fallback_entries = YouTubeURLValidator.extract_playlist_entries(playlist_url, auth_opts)
            seen_urls = set()
            for entry in fallback_entries:
                entry_id = entry.get('id')
                video_url = entry.get('webpage_url') or entry.get('url')
                if video_url and not video_url.startswith('http'):
                    video_url = self.base_video_url + video_url
                if not video_url and entry_id:
                    video_url = self.base_video_url + entry_id
                canonical_url = None
                if entry_id and len(entry_id) == 11:
                    canonical_url = self.base_video_url + entry_id
                elif video_url:
                    canonical_url = video_url
                if not canonical_url or canonical_url in seen_urls:
                    continue
                seen_urls.add(canonical_url)
                title = entry.get('title') or entry.get('alt_title')
                if title:
                    video_titles_links.append([title, canonical_url])
                    continue
                try:
                    video_data = self.retrieve_video_metadata(canonical_url)
                except Exception:
                    continue
                if video_data:
                    video_titles_links.append(video_data)

            if video_titles_links:
                return video_titles_links

        self.showError.emit("The URL is incorrect or unreachable.")
        raise ValueError("Invalid playlist URL")

    def get_single_video(self, video_url):
        auth_params = self._get_auth_params()
        validation_result, formatted_url_or_id = YouTubeURLValidator.is_valid(
            video_url, auth_params)

        if validation_result:
            video_data = self.retrieve_video_metadata(formatted_url_or_id)
            if video_data:
                self.video_titles_links.append(video_data)
            return self.video_titles_links

        # Attempt generic extraction via yt-dlp for non-YouTube URLs
        generic = extract_single_media(video_url, auth_params)
        if generic:
            self.video_titles_links.append([generic['title'], generic['url']])
            return self.video_titles_links

        self.showError.emit("The URL is incorrect or unreachable.")
        raise ValueError("Invalid video URL")
