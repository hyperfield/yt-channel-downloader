from typing import Any, Dict, List, Optional

import yt_dlp

from .logger import get_logger
from .quiet_ydl_logger import QuietYDLLogger
from .yt_dlp_options import javascript_options
from .validators import single_media_entry


logger = get_logger("utils")


def find_best_format_by_resolution(
    formats: List[Dict[str, Any]],
    target_resolution: str,
    target_ext: str = "Any",
):
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


def filter_formats(formats: List[Dict[str, Any]], target_ext: str) -> List[Dict[str, Any]]:
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

    highest_format = max(formats, key=lambda x: x.get('height') or 0)
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

    matched_format = _first_format_id_for_height(formats, target_height)
    if matched_format is not None:
        return matched_format

    closest_resolution = _closest_resolution(available_resolutions, target_height)
    return _first_format_id_for_height(formats, closest_resolution)


def _first_format_id_for_height(formats, height):
    for fmt in formats:
        if fmt.get('height') == height:
            return fmt['format_id']
    return None


def _closest_resolution(available_resolutions, target_height):
    return max((value for value in available_resolutions if value <= target_height), default=None)


def get_format_candidates(
    url: str,
    target_resolution: str,
    target_ext: str,
    auth_opts: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Return format IDs ordered by quality within the requested resolution limit."""
    ydl_opts = _build_metadata_opts(auth_opts)
    info = _extract_format_info(url, ydl_opts)
    if not info:
        return []

    return _dedupe_format_ids(rank_video_formats(info.get('formats', []), target_resolution, target_ext))


def rank_video_formats(formats, target_resolution, target_ext=None):
    """Prefer the highest resolution within the limit, then a native container."""
    height = _parse_target_height(target_resolution)
    candidates = _filter_candidate_formats(formats, 'Any')
    candidates = [fmt for fmt in candidates if not height or not fmt.get('height') or fmt['height'] <= height]
    return sorted(candidates, key=lambda fmt: (
        -(fmt.get('height') or 0),
        bool(target_ext and target_ext != 'Any' and fmt.get('ext') != target_ext),
        -(fmt.get('tbr') or 0),
    ))


def _build_metadata_opts(auth_opts: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Assemble yt-dlp options for metadata extraction, including auth/remote components."""
    ydl_opts = {
        **javascript_options(),
        'quiet': True,
        'no_warnings': True,
        'dump_single_json': True,
        'noplaylist': True,
        'playlist_items': '1',
        'lazy_playlist': True,
        'socket_timeout': 15,
        'logger': QuietYDLLogger(),
    }
    if auth_opts:
        ydl_opts.update(auth_opts)
    return ydl_opts


def _extract_format_info(url: str, ydl_opts: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Fetch format metadata for a URL, logging and returning None on failure."""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return single_media_entry(info, url) if info else None
    except (yt_dlp.utils.DownloadError, ValueError) as e:
        logger.exception("Error extracting info for %s: %s", url, e)
        return None


def _normalize_ext(target_ext: str) -> str:
    """Normalize extension preference into a consistent key."""
    return target_ext if target_ext and target_ext != 'Any' else 'Any'


def _filter_candidate_formats(formats: List[Dict[str, Any]], ext_key: str) -> List[Dict[str, Any]]:
    """Filter formats by extension and ensure basic video fields exist."""
    filtered = filter_formats(formats, ext_key)
    if not filtered and ext_key != 'Any':
        filtered = filter_formats(formats, 'Any')
    return [f for f in filtered if f.get('format_id') and f.get('url')]


def _parse_target_height(target_resolution: str) -> Optional[int]:
    """Extract an integer height from a resolution label, if present."""
    try:
        digits = ''.join(filter(str.isdigit, target_resolution))
        return int(digits) if digits else None
    except ValueError:
        return None


def _sort_bestvideo_formats(formats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort bestvideo candidates by height then bitrate descending."""
    return sorted(formats, key=lambda f: (-(f.get('height') or 0), -(f.get('tbr') or 0)))


def _sort_by_height_preference(
    formats: List[Dict[str, Any]],
    target_height: Optional[int],
) -> List[Dict[str, Any]]:
    """Sort formats from highest to lowest without exceeding the height limit."""
    if target_height is None:
        return _sort_bestvideo_formats(formats)
    return _sort_bestvideo_formats([fmt for fmt in formats if (fmt.get('height') or 0) <= target_height])


def _dedupe_format_ids(formats: List[Dict[str, Any]]) -> List[str]:
    """Return format_ids preserving order, removing duplicates."""
    seen: set[str] = set()
    candidates: List[str] = []
    for fmt in formats:
        fmt_id = fmt.get('format_id')
        if fmt_id and fmt_id not in seen:
            seen.add(fmt_id)
            candidates.append(fmt_id)
    return candidates


def get_video_format_details(
    url: str,
    target_resolution: str,
    target_ext: str,
    auth_opts: Optional[Dict[str, Any]] = None,
):
    candidates = get_format_candidates(url, target_resolution, target_ext, auth_opts)
    return candidates[0] if candidates else None
