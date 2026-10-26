"""Finish conversions before exposing a file as a completed download."""

import os

from yt_dlp.postprocessor.common import PostProcessor
from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessor, FFmpegVideoConvertorPP
from yt_dlp.utils import PostProcessingError, prepend_extension, replace_extension


class VideoContainerPP(FFmpegVideoConvertorPP):
    """Preserve codecs when the requested container supports them; convert otherwise."""

    def run_ffmpeg(self, path, out_path, opts, **kwargs):
        extension = os.path.splitext(out_path)[1][1:]
        try:
            return super().run_ffmpeg(path, out_path, self.stream_copy_opts(ext=extension), **kwargs)
        except PostProcessingError:
            conversion_opts = list(opts)
            if extension == '3gp':
                conversion_opts.extend(('-c:v', 'libx264', '-c:a', 'aac'))
            return super().run_ffmpeg(path, out_path, conversion_opts, **kwargs)


class AudioBitratePP(FFmpegPostProcessor):
    """Encode an explicit bitrate even when the source already uses the target codec."""

    ENCODERS = {
        'mp3': ('mp3', 'libmp3lame'), 'vorbis': ('ogg', 'libvorbis'),
        'm4a': ('m4a', 'aac'), 'aac': ('aac', 'aac'), 'opus': ('opus', 'libopus'),
    }

    def __init__(self, downloader, codec, bitrate):
        super().__init__(downloader)
        self.extension, self.encoder = self.ENCODERS[codec]
        self.codec = 'aac' if codec == 'm4a' else codec
        self.bitrate = int(bitrate)

    def run(self, info):
        source = info['filepath']
        destination = replace_extension(source, self.extension, info['ext'])
        temporary = prepend_extension(destination, 'temp') if source == destination else destination
        self.run_ffmpeg(source, temporary, ['-vn', '-acodec', self.encoder, '-b:a', f'{self.bitrate}k'])
        if temporary != destination:
            os.replace(temporary, destination)
        info['filepath'] = destination
        info['ext'] = self.extension
        info['vcodec'] = 'none'
        info['acodec'] = self.codec
        return ([source] if source != destination else []), info


class FinalizeDownloadPP(PostProcessor):
    """Give a download its final name only after all conversions and moves succeed."""

    def __init__(self, downloader, output_path, extension_override=None):
        super().__init__(downloader)
        self.output_path = output_path
        self.extension_override = extension_override

    def run(self, info):
        if self.extension_override:
            info['ext'] = self.extension_override
        destination = f"{self.output_path}.{info['ext']}"
        if info['filepath'] != destination:
            os.replace(info['filepath'], destination)
        info['filepath'] = destination
        return [], info
