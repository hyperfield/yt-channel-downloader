"""Recognize final media containers without accepting thumbnails or stream artifacts."""

from yt_dlp.utils import MEDIA_EXTENSIONS


# yt-dlp's display-oriented extension groups omit native MPEG transport/program streams.
FINAL_MEDIA_EXTENSIONS = frozenset((
    *MEDIA_EXTENSIONS.video, *MEDIA_EXTENSIONS.audio,
    'ts', 'mts', 'm2ts', 'mpeg', 'mpe', 'vob',
))
