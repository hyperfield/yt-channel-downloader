# Author: hyperfield
# Email: inbox@quicknode.net
# Project: YT Channel Downloader
# Description: This module contains the class GetListThread
# License: MIT License

from PyQt6.QtCore import QThread, pyqtSignal as Signal

from .logger import get_logger


logger = get_logger("GetListThread")


class GetListThread(QThread):
    """
    A thread class for fetching a list of videos from a YouTube channel or
    a single video.

    This class inherits from QThread and is used to retrieve either all
    videos from a given YouTube channel or a single video, based on the
    provided channel ID or video URL. The retrieval process is done in
    a separate thread to avoid blocking the main application.

    Attributes:
    finished (Signal): A signal that is emitted when the video list
                       retrieval is complete.
                       The signal sends a list of videos.

    Parameters:
    channel_id (str): The unique identifier for a YouTube channel.
                      If this is None, the class will fetch a single
                      video using channel_url.
    yt_channel (YTChannel): An instance of the YTChannel class that
                            provides the functionality to fetch
                            video details from YouTube.
    channel_url (str, optional): The URL of a single YouTube video.
                                 This is used only if channel_id is
                                 None. Defaults to None.
    parent (QObject, optional): The parent object of the thread.
                                Defaults to None.
    """
    finished = Signal(list)
    cancelled = Signal()
    error = Signal(str)
    progress = Signal(int, object)

    def __init__(self, channel_id, yt_channel, channel_url=None, limit=None, start_index=1, parent=None):
        """
        Initializes the GetListThread with the necessary attributes.

        Parameters:
        channel_id (str): The unique identifier for a YouTube channel.
        yt_channel (YTChannel): An instance of the YTChannel class.
        channel_url (str, optional): The URL of a single YouTube video.
        Defaults to None.
        parent (QObject, optional): The parent object of the thread.
        Defaults to None.
        """
        super().__init__(parent)
        self.channel_id = channel_id
        self.yt_channel = yt_channel
        self.channel_url = channel_url
        self.limit = limit
        self.start_index = start_index
        self._is_cancelled = False

    def run(self):
        """
        The main execution method for the thread.

        Depending on whether a channel_id or channel_url is provided, this
        method fetches either all videos from a YouTube channel or a single
        video. Once the data are fetched, it emits the 'finished' signal
        with the video list.
        """
        video_list = []

        try:
            if not self.channel_id or self.channel_id == "short":
                video_list = self.yt_channel.get_single_video(self.channel_url)
            elif self.channel_id == "playlist":
                video_list = self.yt_channel.fetch_videos_from_playlist_with_progress(
                    self.channel_url,
                    progress_callback=self._emit_progress,
                    is_cancelled=lambda: self._is_cancelled,
                    limit=self.limit,
                )
            else:
                video_list = self.yt_channel.fetch_all_videos_in_channel(
                    self.channel_id,
                    limit=self.limit,
                    progress_callback=self._emit_progress,
                    is_cancelled=lambda: self._is_cancelled,
                    start_index=self.start_index,
                )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to fetch video list: %s", exc)
            self.error.emit(str(exc))
            return

        # Ensure that an empty list doesn't crash the app
        if video_list is None:
            video_list = []

        if self._is_cancelled:
            self.cancelled.emit()
            return

        self.finished.emit(video_list)

    def cancel(self):
        self._is_cancelled = True

    def _emit_progress(self, count, total):
        self.progress.emit(count, total)
