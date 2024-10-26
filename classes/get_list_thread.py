from PyQt6.QtCore import QThread, pyqtSignal as Signal


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

    def __init__(self, channel_id, yt_channel, channel_url=None, parent=None):
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

    def run(self):
        """
        The main execution method for the thread.

        Depending on whether a channel_id or channel_url is provided, this
        method fetches either all videos from a YouTube channel or a single
        video. Once the data is fetched, it emits the 'finished' signal
        with the video list.
        """
        video_list = []
        
        if not self.channel_id:
            video_list = self.yt_channel.get_single_video(self.channel_url)
        elif self.channel_id == "playlist":
            video_list = self.yt_channel.get_videos_from_playlist(self.channel_url)
        else:
            video_list = self.yt_channel.get_all_videos_in_channel(self.channel_id)
        
        # Ensure that an empty list doesn't crash the app
        if video_list is None:
            video_list = []
        
        self.finished.emit(video_list)
