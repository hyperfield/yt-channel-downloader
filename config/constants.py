DEFAULT_VIDEO_FORMAT = 'Any'
DEFAULT_AUDIO_FORMAT = 'mp3'
DEFAULT_AUDIO_QUALITY = 'Best available'
DEFAULT_VIDEO_QUALITY = '1080p (Full HD)'

settings_map = {
    'preferred_video_quality': {
        'Best available': 'bestvideo',
        '2160p (4K)': '2160p',
        '1440p (2K)': '1440p',
        '1080p (Full HD)': '1080p',
        '720p (HD)': '720p',
        '480p': '480p',
        '360p': '360p',
        '240p': '240p',
        '144p': '144p'
    },

    'preferred_audio_quality': {
        'Best available': 'bestaudio',
        '320 kbps': '320k',
        '256 kbps': '256k',
        '192 kbps': '192k',
        '160 kbps': '160k',
        '128 kbps': '128k',
        '64 kbps': '64k',
        '32 kbps': '32k',
    },

    'preferred_video_format': {
        'Any': None,
        'mp4': 'mp4',
        'webm': 'webm',
        'avi': 'avi',
        'mov': 'mov',
        'mkv': 'mkv',
        'flv': 'flv',
        '3gp': '3gp',
    },

    'preferred_audio_format': {
        'Any': None,
        'mp3': 'mp3',
        'ogg / oga [Vorbis]': 'vorbis',
        'm4a': 'm4a',
        'aac': 'aac',
        'opus': 'opus',
        'flac': 'flac',
        'wav': 'wav',
    }
}

KEYWORD = "externalId"
KEYWORD_LEN = len(KEYWORD)
OFFSET_TO_CHANNEL_ID = 3
