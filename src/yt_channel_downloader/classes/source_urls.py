"""Recognize YouTube links without mistaking other sites or query values for them."""

import re
from urllib.parse import parse_qs, urlsplit


_VIDEO_ID = re.compile(r'[A-Za-z0-9_-]{11}')
_YOUTUBE_HOSTS = frozenset((
    'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com',
    'youtube-nocookie.com', 'www.youtube-nocookie.com', 'youtu.be', 'www.youtu.be',
))


def youtube_url_parts(url):
    """Return parsed parts only for an HTTP(S) URL on a recognized YouTube host."""
    value = url.strip()
    try:
        parts = urlsplit(value if '://' in value else 'https://' + value)
        if parts.scheme in ('http', 'https') and parts.hostname in _YOUTUBE_HOSTS:
            return parts
    except ValueError:
        pass
    return None


def youtube_video_id(url):
    value = url.strip()
    if _VIDEO_ID.fullmatch(value):
        return value
    parsed = youtube_url_parts(value)
    if not parsed:
        return None
    parts = parsed.path.strip('/').split('/')
    video_id = None
    if parsed.hostname in ('youtu.be', 'www.youtu.be'):
        video_id = parts[0]
    elif parts[0] == 'watch':
        video_id = parse_qs(parsed.query).get('v', [None])[0]
    elif len(parts) >= 2 and parts[0] in ('shorts', 'embed', 'live', 'v'):
        video_id = parts[1]
    return video_id if video_id and _VIDEO_ID.fullmatch(video_id) else None


def youtube_playlist_id(url):
    parsed = youtube_url_parts(url)
    value = parse_qs(parsed.query).get('list', [''])[0] if parsed else ''
    return value if re.fullmatch(r'[A-Za-z0-9_-]+', value) else None


def is_http_media_url(url):
    """Validate URL syntax without issuing a network request on the GUI thread."""
    try:
        parsed = urlsplit(url.strip())
        return parsed.scheme in ('http', 'https') and bool(parsed.hostname)
    except ValueError:
        return False
