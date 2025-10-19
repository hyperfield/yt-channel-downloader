from classes.settings_manager import SettingsManager
from classes.youtube_auth import YoutubeAuthManager
import yt_dlp

manager = YoutubeAuthManager(SettingsManager())
opts = manager.get_yt_dlp_options()
print('yt-dlp opts:', opts)

with yt_dlp.YoutubeDL({'quiet': True, **opts}) as ydl:
    youtube = [c.name for c in ydl.cookiejar if 'youtube' in c.domain]
    print('YouTube cookies:', youtube[:10], '… total:', len(youtube))
    info = ydl.extract_info('https://www.youtube.com/watch?v=ETU4GVTvC4g',
                            download=False)
    print('Title:', info.get('title'))
