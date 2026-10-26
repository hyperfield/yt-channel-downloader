"""Name and find downloads by source and the settings that affect their media."""

import hashlib
import json
import os
import re

from .media_files import FINAL_MEDIA_EXTENSIONS
from .source_urls import youtube_video_id

from ..config.constants import (DEFAULT_AUDIO_FORMAT, DEFAULT_AUDIO_QUALITY, DEFAULT_VIDEO_FORMAT,
                                DEFAULT_VIDEO_QUALITY, LOSSY_AUDIO_FORMATS, settings_map)


_IDENTIFIED_FILE = re.compile(r'^(?P<base>.+__(?P<key>[0-9a-f]{24}))\.(?P<suffix>.+)$')


def source_identity(url: str) -> str:
    """Treat common YouTube links to one video as the same source."""
    url = url.strip()
    video_id = youtube_video_id(url)
    if video_id:
        return f'youtube:{video_id}'
    # Query strings and fragments can identify different media on other sites.
    return url


def video_preferences(settings: dict) -> tuple:
    file_format = settings_map['preferred_video_format'].get(
        settings.get('preferred_video_format'), settings_map['preferred_video_format'][DEFAULT_VIDEO_FORMAT])
    quality = settings_map['preferred_video_quality'].get(
        settings.get('preferred_video_quality'), settings_map['preferred_video_quality'][DEFAULT_VIDEO_QUALITY])
    if file_format == 'Any':
        file_format = None
    if quality in ('Any', None):
        quality = 'bestvideo'
    return file_format, quality


def audio_preferences(settings: dict) -> tuple:
    file_format = settings_map['preferred_audio_format'].get(
        settings.get('preferred_audio_format'), settings_map['preferred_audio_format'][DEFAULT_AUDIO_FORMAT])
    quality = settings_map['preferred_audio_quality'].get(
        settings.get('preferred_audio_quality'), settings_map['preferred_audio_quality'][DEFAULT_AUDIO_QUALITY])
    if file_format not in LOSSY_AUDIO_FORMATS:
        quality = 'bestaudio'
    return file_format, quality


def download_key(url: str, settings: dict) -> str:
    """Return a stable key, excluding preferences irrelevant to the active mode."""
    audio_only = bool(settings.get('audio_only'))
    file_format, quality = audio_preferences(settings) if audio_only else video_preferences(settings)
    request = {
        # Earlier keys did not guarantee the output container or resolution policy.
        'version': 2,
        'source': source_identity(url),
        'mode': 'audio' if audio_only else 'video',
        'format': file_format or 'Any',
        'quality': quality,
    }
    encoded = json.dumps(request, sort_keys=True, ensure_ascii=True).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()[:24]


def download_directory(settings: dict) -> str:
    return os.path.abspath(os.path.expanduser(settings.get('download_directory') or '.'))


def index_download_paths(directory: str) -> dict:
    """Index final files and resumable artifacts without depending on their titles."""
    paths = {}
    ranks = {}
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                match = _IDENTIFIED_FILE.fullmatch(entry.name)
                if not match:
                    continue
                try:
                    if not entry.is_file():
                        continue
                    suffix = match['suffix']
                    complete = suffix in FINAL_MEDIA_EXTENSIONS and entry.stat().st_size > 0
                except OSError:
                    continue
                key = match['key']
                base = match['base']
                rank = (complete, base)
                if key not in ranks or rank > ranks[key]:
                    ranks[key] = rank
                    paths[key] = os.path.join(directory, base)
    except OSError:
        # Missing or unreadable destinations are handled by the download itself.
        return {}
    return paths


def download_path(sanitized_title: str, url: str, settings: dict, existing_paths=None) -> str:
    """Keep a readable title and append a source/settings key within the byte limit."""
    directory = download_directory(settings)
    key = download_key(url, settings)
    if existing_paths is None:
        existing_paths = index_download_paths(directory)
    if key not in existing_paths:
        suffix = f'__{key}'
        title = sanitized_title.encode('utf-8')[:200 - len(suffix)].decode('utf-8', errors='ignore')
        existing_paths[key] = os.path.join(directory, f'{title}{suffix}')
    return existing_paths[key]
