import scrapetube
from urllib import request, error

from .constants import KEYWORD_LEN, OFFSET_TO_CHANNEL_ID


class YTChannel:
    def __init__(self):
        self.channelId = ""

    def get_channel_id(self, url):
        if "channel/" in url:
            split_url = url.split("/")
            for i in range(len(split_url)):
                if split_url[i] == "channel":
                    self.channelId = split_url[i+1]
                    return self.channelId
        try:
            html = request.urlopen(url).read().__str__()
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
            print(e.__dict__)
            raise e
        except error.URLError as e:
            print(e.__dict__)
            raise error.URLError("Invalid URL")
        except ValueError as e:
            print(e.__dict__)
            raise ValueError

    def get_all_video_in_channel(self, channel_id):
        base_video_url = 'https://www.youtube.com/watch?v='
        video_titles_links = []
        chan_video_entries = scrapetube.get_channel(channel_id)
        for entry in chan_video_entries:
            vid_title = entry['title']['runs'][0]['text']
            video_url = base_video_url + entry['videoId']
            video_titles_links.append([vid_title, video_url])
        return video_titles_links
