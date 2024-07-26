import yt_dlp


def find_best_format_by_resolution(
        formats, target_resolution, target_ext="Any"):
    """
    Finds the best video format from a list of formats based on the target
    resolution and an optional target container extension.

    Parameters:
    - formats (list of dicts): A list of format dictionaries as returned by
      yt_dlp.
    - target_resolution (str): The desired video resolution as a string
      (e.g., '1080p').
      If 'bestvideo' is specified, the function selects the highest available
      resolution.
    - target_ext (str): The desired video container extension
      (e.g., 'mp4', 'webm').
      If 'Any' is specified, the container extension is not considered
      in the selection.

    Returns:
    - str: The format_id of the closest matching format based on the specified
      criteria.
      Returns None if no suitable format is found.
    """

    filtered_formats = [f for f in formats if f.get('vcodec') != 'none' and
                        f.get('ext') == target_ext
                        if target_ext != "Any"]

    if not filtered_formats:
        filtered_formats = [f for f in formats if f.get('vcodec') != 'none']

    closest_format = None

    if target_resolution == "bestvideo":
        closest_format = max(filtered_formats,
                             key=lambda x: x.get('height', 0))
        return closest_format['format_id']

    min_diff = float('inf')
    target_height = int(target_resolution[:-1])

    for format in filtered_formats:
        height = format.get('height')
        width = format.get('width')
        if (height and width) and (height > width):
            height, width = width, height

        diff = abs(height - target_height)
        if diff < min_diff:
            min_diff = diff
            closest_format = format

    return closest_format['format_id']


def get_video_format_details(url, target_resolution='bestvideo',
                             target_container="Any", cookie_file_path=None):
    """
    Retrieves video format details for a given URL using yt_dlp,
    filtering by resolution and container format.

    Parameters:
    - url (str): The URL of the video to analyze.
    - target_resolution (str): The target resolution to filter
      by (e.g., '1080p').
      Use 'bestvideo' to select the highest available resolution.
    - target_container (str): The container format to filter by
      (e.g., 'mp4', 'webm').
      Use 'Any' to ignore container format in the selection.
    - cookie_file_path (str, optional): The path to the cookie file
      to use for authentication. Required for private or age-restricted
      videos.

    Returns:
    - str: The format_id of the video that best matches the criteria.
      Returns None if no suitable format is found or if an error occurs
      during video retrieval.
    """
    ydl_opts = {'noplaylist': True}

    if cookie_file_path:
        ydl_opts['cookiefile'] = cookie_file_path

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            video_info = ydl.extract_info(url, download=False)
            return find_best_format_by_resolution(video_info['formats'],
                                                  target_resolution,
                                                  target_container)
    except yt_dlp.utils.DownloadError as e:
        # Handle download errors, such as authentication failures
        print(f"Failed to extract video information: {e}")
        return None
