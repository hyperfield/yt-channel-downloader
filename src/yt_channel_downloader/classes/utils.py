import yt_dlp

from .logger import get_logger


logger = get_logger("utils")


class QuietYDLLogger:
    """Minimal yt-dlp-compatible logger that suppresses noisy output."""

    def debug(self, msg):
        logger.debug(msg)

    def info(self, msg):
        logger.debug(msg)

    def warning(self, msg):
        logger.debug(msg)

    def error(self, msg):
        logger.error(msg)


def find_best_format_by_resolution(formats, target_resolution, target_ext="Any"):
    """
    Finds the best video format from a list of formats based on the target
    resolution and an optional target container extension.

    Parameters:
    - formats (list of dicts): A list of format dictionaries as returned by
      yt_dlp.
    - target_resolution (str): The desired video resolution as a string
      (e.g., '1080p'). If 'bestvideo' is specified, the function selects the
      highest available resolution.
    - target_ext (str): The desired video container extension
      (e.g., 'mp4', 'webm').
      If 'Any' is specified, the container extension is not considered in
      the selection.

    Returns:
    - str: The format_id of the closest matching format based on the specified
      criteria.
      Returns None if no suitable format is found.
    """

    # Filter formats based on extension and presence of video
    filtered_formats = filter_formats(formats, target_ext)

    if target_resolution == "bestvideo":
        return find_highest_resolution(filtered_formats)

    # Attempt to find the closest resolution, defaulting to the next available
    return find_closest_resolution_with_fallback(filtered_formats,
                                                 target_resolution)


def filter_formats(formats, target_ext):
    """Filters formats by the given container extension and ensures they
    contain video."""
    if target_ext != "Any":
        filtered_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('ext') == target_ext]
    else:
        filtered_formats = [f for f in formats if f.get('vcodec') != 'none']

    return filtered_formats


def find_highest_resolution(formats):
    """Finds the format with the highest resolution from a list of formats."""
    if not formats:
        return None

    highest_format = max(formats, key=lambda x: x.get('height', 0))
    return highest_format['format_id']


def find_closest_resolution_with_fallback(formats, target_resolution):
    """
    Finds the format closest to the target resolution. If the exact resolution
    is not available, defaults to the next available resolution.
    """
    if not formats:
        return None

    target_height = int(target_resolution[:-1])
    available_resolutions = sorted([f.get('height') for f in formats if f.get('height')])

    # First, check if the target resolution is available
    if target_height in available_resolutions:
        for format in formats:
            if format.get('height') == target_height:
                return format['format_id']

    # Find the next closest resolution, either higher or lower
    closest_resolution = min(available_resolutions, key=lambda x: abs(x - target_height))
    for format in formats:
        if format.get('height') == closest_resolution:
            return format['format_id']

    return None


def get_format_candidates(url, target_resolution, target_ext, auth_opts=None):
    """Return format_ids ordered by closeness to the requested resolution."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'dump_single_json': True,
        'noplaylist': True,
        'logger': QuietYDLLogger(),
    }
    if auth_opts:
        ydl_opts.update(auth_opts)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as e:
        logger.exception("Error extracting info for %s: %s", url, e)
        return []

    formats = info.get('formats', [])
    ext_key = target_ext if target_ext and target_ext != 'Any' else 'Any'
    filtered = filter_formats(formats, ext_key)
    if not filtered and ext_key != 'Any':
        filtered = filter_formats(formats, 'Any')

    filtered = [f for f in filtered if f.get('format_id') and f.get('height') and f.get('url')]
    if not filtered:
        return []

    if target_resolution == 'bestvideo':
        sorted_formats = sorted(filtered, key=lambda f: (-(f.get('height') or 0), -(f.get('tbr') or 0)))
    else:
        try:
            target_height = int(''.join(filter(str.isdigit, target_resolution)))
        except ValueError:
            target_height = None

        if target_height is None:
            sorted_formats = filtered
        else:
            def sort_key(fmt):
                height = fmt.get('height') or 0
                delta = height - target_height
                return (abs(delta), 0 if delta <= 0 else 1, -height if delta <= 0 else height)

            sorted_formats = sorted(filtered, key=sort_key)

    seen = set()
    candidates = []
    for fmt in sorted_formats:
        fmt_id = fmt.get('format_id')
        if fmt_id and fmt_id not in seen:
            seen.add(fmt_id)
            candidates.append(fmt_id)

    return candidates


def get_video_format_details(url, target_resolution, target_ext, auth_opts=None):
    candidates = get_format_candidates(url, target_resolution, target_ext, auth_opts)
    return candidates[0] if candidates else None
