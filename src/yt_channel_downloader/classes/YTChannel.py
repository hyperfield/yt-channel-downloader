# Author: hyperfield
# Email: inbox@quicknode.net
# Project: YT Channel Downloader
# Description: This module contains the class YTChannel.
# License: MIT License

import re
from urllib.parse import urlparse, parse_qs
from urllib import error

import requests

from .validators import YouTubeURLValidator, extract_single_media, is_supported_media_url
from .utils import QuietYDLLogger
from ..config.constants import KEYWORD_LEN, OFFSET_TO_CHANNEL_ID, DEFAULT_CHANNEL_FETCH_LIMIT, CHANNEL_FETCH_BATCH_SIZE
from .settings_manager import SettingsManager

import yt_dlp
from yt_dlp.utils import parse_duration
from PyQt6.QtCore import QObject, pyqtSignal as Signal

from .logger import get_logger


class YTChannel(QObject):
    showError = Signal(str)

    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.channelId = ""
        self.base_video_url = 'https://www.youtube.com/watch?v='
        self.video_titles_links = []
        self.logger = get_logger("YTChannel")
        self.settings_manager = SettingsManager()

    def _get_auth_params(self):
        manager = getattr(self.main_window, "youtube_auth_manager", None)
        opts = {}
        if manager and manager.is_configured:
            opts = manager.get_yt_dlp_options()
        proxy_url = self.settings_manager.build_proxy_url()
        if proxy_url:
            opts = dict(opts) if opts else {}
            opts.setdefault('proxy', proxy_url)
        return opts

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
            response = requests.get(
                url,
                timeout=10,
                proxies=self.settings_manager.build_requests_proxies(),
            )
            response.raise_for_status()
            html = response.text
            channelId_first_index = html.find("externalId") + KEYWORD_LEN + \
                OFFSET_TO_CHANNEL_ID
            channelId_last_index = channelId_first_index
            for symbol in html[channelId_first_index:]:
                if symbol == '"':
                    break
                channelId_last_index += 1
            self.channelId = html[channelId_first_index: channelId_last_index]
            return self.channelId
        except requests.exceptions.HTTPError as e:
            self.logger.exception("HTTP error while resolving channel ID: %s", e)
            status = e.response.status_code if e.response else None
            headers = e.response.headers if e.response else None
            raise error.HTTPError(url, status, str(e), headers, None) from e
        except requests.exceptions.RequestException as e:
            self.logger.exception("Request error while resolving channel ID: %s", e)
            raise error.URLError(str(e)) from e
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
        proxy_url = self.settings_manager.build_proxy_url()
        if proxy_url:
            ydl_opts['proxy'] = proxy_url
            auth_opts.setdefault('proxy', proxy_url)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(video_url, download=False)
            vid_title = video_info.get('title', 'Unknown Title')
            duration = self._extract_duration_seconds(video_info)
            return {
                'title': vid_title,
                'url': video_url,
                'duration': duration,
            }
        except yt_dlp.utils.DownloadError as e:
            self.logger.exception("Error fetching video metadata for %s: %s", video_url, e)
            self.showError.emit(f"Failed to fetch video metadata: {e}")
            raise

    def fetch_all_videos_in_channel(
        self,
        channel_id,
        limit=DEFAULT_CHANNEL_FETCH_LIMIT,
        batch_size=CHANNEL_FETCH_BATCH_SIZE,
        progress_callback=None,
        is_cancelled=None,
        start_index=1,
    ):
        """
        Fetch videos for a channel in batches so the UI can report progress
        and users can cancel long-running requests.

        Args:
            channel_id (str): The resolved YouTube channel identifier (e.g. UCxxxx...).
            limit (int | None): Maximum number of entries to fetch; None fetches all.
            batch_size (int): Number of videos to request per page/batch.
            progress_callback (callable): Optional function accepting (fetched_count, target_count).
            is_cancelled (callable): Optional function returning True when the user cancelled.
        """
        uploads_playlist_id = None
        if channel_id and channel_id.startswith("UC") and len(channel_id) > 2:
            uploads_playlist_id = f"UU{channel_id[2:]}"
        channel_url = (
            f"https://www.youtube.com/playlist?list={uploads_playlist_id}"
            if uploads_playlist_id else f"https://www.youtube.com/channel/{channel_id}/videos"
        )
        auth_opts = self._get_auth_params()
        items_to_fetch = None if limit in (None, 0) else max(1, int(limit))
        batch_size = max(1, batch_size or CHANNEL_FETCH_BATCH_SIZE)

        collected_entries = []
        start = max(1, int(start_index) if start_index else 1)

        while True:
            if is_cancelled and is_cancelled():
                self.logger.info("Channel fetch cancelled after %d items", len(collected_entries))
                break

            window_size = items_to_fetch or batch_size
            end = start + window_size - 1

            entries = self._fetch_channel_entries(
                channel_url,
                start,
                end,
                auth_opts=auth_opts,
            )
            if not entries:
                # Fallback: refetch from the beginning up to the current end and slice.
                fallback_entries = self._fetch_channel_entries(
                    channel_url,
                    1,
                    end,
                    auth_opts=auth_opts,
                    slice_start=start,
                )
                entries = fallback_entries

            if not entries:
                self.logger.warning("No entries fetched for channel %s (start=%s)", channel_id, start)
                break

            collected_entries.extend(entries)
            if progress_callback:
                progress_callback(len(collected_entries), items_to_fetch)

            if items_to_fetch is not None and len(collected_entries) >= items_to_fetch:
                collected_entries = collected_entries[:items_to_fetch]
                break

            if len(entries) < window_size:
                # No more pages to fetch
                break

            start = end + 1

        return self._normalize_entries(collected_entries)

    def _fetch_channel_entries(self, channel_url, start, end, auth_opts, slice_start=None):
        """Internal helper to fetch a slice of channel entries."""
        strategies = [
            {'playlist_items': f"{start}-{end}", 'lazy_playlist': False, 'extract_flat': True},
            {'playliststart': start, 'playlistend': end, 'lazy_playlist': False, 'extract_flat': True},
        ]

        for opts in strategies:
            ydl_opts = {
                'quiet': True,
                'skip_download': True,
                'extract_flat': True,
                'retries': 3,
                'socket_timeout': 10,
            }
            ydl_opts.update(opts)
            if auth_opts:
                ydl_opts.update(auth_opts)
            ydl_opts.setdefault('logger', QuietYDLLogger())

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(channel_url, download=False)
            except yt_dlp.utils.DownloadError as exc:
                self.logger.exception("yt-dlp failed to fetch channel videos for %s with opts %s: %s", channel_url, opts, exc)
                continue
            except Exception as exc:  # noqa: BLE001
                self.logger.exception("Unexpected error while using yt-dlp for %s with opts %s: %s", channel_url, opts, exc)
                continue

            entries = info.get('entries') if isinstance(info, dict) else None
            if entries:
                break
        else:
            entries = []

        if slice_start and slice_start > 1:
            slice_from = slice_start - 1
            slice_to = end
            entries = entries[slice_from:slice_to]

        return entries

    def _normalize_entries(self, entries):
        """Normalize yt-dlp entries to a list of {title, url, duration}."""
        seen_urls = set()
        collected = []

        for entry in entries:
            if not entry:
                continue
            video_id = entry.get('id')
            video_url = entry.get('webpage_url') or entry.get('url')
            if video_url and not video_url.startswith('http'):
                video_url = self.base_video_url + video_url
            if not video_url and video_id:
                video_url = self.base_video_url + video_id
            if not video_url:
                self.logger.debug("Skipping channel entry without resolvable URL: %s", entry)
                continue
            if video_url in seen_urls:
                continue
            seen_urls.add(video_url)

            title = entry.get('title') or entry.get('alt_title') or entry.get('fulltitle')
            duration = self._extract_duration_seconds(entry)

            metadata = None
            if not title or duration is None:
                try:
                    metadata = self.retrieve_video_metadata(video_url)
                except Exception:  # noqa: BLE001
                    self.logger.debug("Failed fallback metadata fetch for %s", video_url, exc_info=True)

            if metadata:
                title = title or metadata.get('title')
                if duration is None:
                    duration = metadata.get('duration')

            collected.append({
                'title': title or 'Unknown Title',
                'url': video_url,
                'duration': duration,
            })

        self.video_titles_links = collected
        return self.video_titles_links

    def fetch_videos_from_playlist(self, playlist_url):
        return self.fetch_videos_from_playlist_with_progress(
            playlist_url, progress_callback=None, is_cancelled=None
        )

    def fetch_videos_from_playlist_with_progress(self, playlist_url, progress_callback=None, is_cancelled=None, limit=None):
        auth_opts = self._get_auth_params()
        playlist_url = self._canonical_playlist_url(playlist_url)
        total_entries = self._get_playlist_total_count(playlist_url, auth_opts)
        if progress_callback and total_entries:
            progress_callback(0, total_entries)
        self.logger.info("Starting playlist fetch for %s (reported total: %s)", playlist_url, total_entries or "unknown")
        if YouTubeURLValidator.playlist_exists(playlist_url, auth_opts):
            video_titles_links = []
            fallback_entries = YouTubeURLValidator.extract_playlist_entries(playlist_url, auth_opts)
            total_entries = total_entries or len(fallback_entries)
            seen_urls = set()
            count = 0
            for entry in fallback_entries:
                if limit and count >= limit:
                    break
                if is_cancelled and is_cancelled():
                    self.logger.info("Playlist fetch cancelled after %d items", count)
                    break
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
                duration = self._extract_duration_seconds(entry)
                if title:
                    video_titles_links.append({
                        'title': title,
                        'url': canonical_url,
                        'duration': duration,
                    })
                    continue
                try:
                    video_data = self.retrieve_video_metadata(canonical_url)
                except Exception:
                    continue
                if video_data:
                    video_titles_links.append(video_data)
                count += 1
                if progress_callback:
                    progress_callback(count, total_entries)
                if count == total_entries or count % 25 == 0:
                    self.logger.info("Playlist fetch progress: %d/%s", count, total_entries or "unknown")
            if video_titles_links:
                return video_titles_links

        self.showError.emit("The URL is incorrect or unreachable.")
        raise ValueError("Invalid playlist URL")

    def _get_playlist_total_count(self, playlist_url, auth_opts):
        """Return playlist_count if yt-dlp reports it; otherwise None."""
        attempts = [
            {'extract_flat': True, 'playlistend': 1},
            {'extract_flat': False, 'playlistend': 1},
        ]
        for opts in attempts:
            ydl_opts = {
                'quiet': True,
                'skip_download': True,
                'playlist_items': '1',
                'yes_playlist': True,
            }
            ydl_opts.update(opts)
            if auth_opts:
                ydl_opts.update(auth_opts)
            ydl_opts.setdefault('logger', QuietYDLLogger())
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(playlist_url, download=False)
                playlist_count = info.get('playlist_count') if isinstance(info, dict) else None
                entries = info.get('entries') or []
                if playlist_count:
                    self.logger.info("yt-dlp reports playlist_count=%s for %s", playlist_count, playlist_url)
                    return int(playlist_count)
                if entries:
                    self.logger.info("yt-dlp returned %d entries (no playlist_count) for %s", len(entries), playlist_url)
                    return len(entries)
            except Exception:
                self.logger.debug("Could not determine playlist count for %s with opts %s", playlist_url, opts, exc_info=True)
        return None

    def _canonical_playlist_url(self, url):
        """Ensure we query the playlist endpoint even if a watch URL was provided."""
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        list_id = qs.get('list', [None])[0]
        if list_id:
            return f"https://www.youtube.com/playlist?list={list_id}"
        return url

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
            self.video_titles_links.append(generic)
            return self.video_titles_links

        self.showError.emit("The URL is incorrect or unreachable.")
        raise ValueError("Invalid video URL")

    @staticmethod
    def _extract_duration_seconds(info):
        if not info:
            return None

        def _coerce(value):
            if value is None:
                return None
            if isinstance(value, (int, float)):
                if value >= 0:
                    return int(value)
                return None
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    return None
                if value.isdigit():
                    return int(value)
                parsed = parse_duration(value)
                if parsed is not None:
                    return parsed
            return None

        for key in ("duration", "duration_seconds", "lengthSeconds", "length_seconds"):
            duration = _coerce(info.get(key))
            if duration is not None:
                return duration

        duration_ms = info.get('duration_ms')
        if isinstance(duration_ms, (int, float)) and duration_ms >= 0:
            return int(duration_ms // 1000)

        duration_str = info.get('duration_string')
        parsed = _coerce(duration_str)
        if parsed is not None:
            return parsed

        length_text = info.get('lengthText')
        if isinstance(length_text, dict):
            length_simple = length_text.get('simpleText') or length_text.get('accessibility', {}).get('accessibilityData', {}).get('label')
            parsed = _coerce(length_simple)
            if parsed is not None:
                return parsed

        if isinstance(length_text, str):
            parsed = _coerce(length_text)
            if parsed is not None:
                return parsed

        return None
