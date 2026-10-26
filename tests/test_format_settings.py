from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import yt_dlp

pytest.importorskip('PyQt6')

from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessor
from yt_dlp.utils import PostProcessingError
from yt_channel_downloader.classes import download_thread as download_module
from yt_channel_downloader.classes.download_identity import audio_preferences, download_key, video_preferences
from yt_channel_downloader.classes.download_thread import DownloadThread
from yt_channel_downloader.classes.mainwindow import MainWindow
from yt_channel_downloader.classes.media_postprocessors import FinalizeDownloadPP, VideoContainerPP
from yt_channel_downloader.classes.settings_manager import SettingsManager
from yt_channel_downloader.classes.utils import rank_video_formats
from yt_channel_downloader.config.constants import settings_map


def _video(identifier, height, extension='mp4'):
    return {'format_id': identifier, 'height': height, 'ext': extension, 'vcodec': 'h264',
            'acodec': 'aac', 'url': f'https://example.com/{identifier}'}


@pytest.fixture
def worker(monkeypatch, tmp_path):
    defaults = SettingsManager.load_default_settings(object.__new__(SettingsManager))
    manager = SimpleNamespace(settings={**defaults, 'download_directory': str(tmp_path)}, build_proxy_url=lambda _: None)
    monkeypatch.setattr(download_module, 'SettingsManager', lambda: manager)
    monkeypatch.setattr(download_module, 'get_format_candidates', lambda *args: [])
    return DownloadThread('https://example.com/video', 0, 'Video', SimpleNamespace())


def _select(selector, formats):
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        return list(ydl.build_format_selector(selector)({
            'formats': formats, 'has_merged_format': True, 'incomplete_formats': False,
        }))


def test_video_candidates_prioritize_resolution_within_limit_then_native_container():
    formats = [_video('above', 1080), _video('low-native', 360), _video('720-webm', 720, 'webm')]

    assert [fmt['format_id'] for fmt in rank_video_formats(formats, '720p', 'mp4')] == ['720-webm', 'low-native']


def test_selectors_enforce_maximum_even_for_explicit_format_ids(worker):
    selector = worker._build_format_selector(['above', 'below'], 720, 'mp4')
    formats = [_video('below', 360), _video('above', 1080)]

    assert _select(selector, formats)[0]['format_id'] == 'below'
    assert not _select(selector, [_video('above', 1080)])


def test_unknown_source_resolution_remains_downloadable(worker):
    selector = worker._build_format_selector([], 720, None)

    assert _select(selector, [_video('direct-url', None)])[0]['format_id'] == 'direct-url'


@pytest.mark.parametrize('file_format', list(settings_map['preferred_video_format']))
def test_every_video_output_format_is_applied_to_download_and_fallback(worker, file_format):
    worker.user_settings['preferred_video_format'] = file_format
    worker._execute_download = Mock(side_effect=[yt_dlp.utils.DownloadError('HTTP Error 403'), None])

    options, auth = worker._build_download_options('Video')
    worker._download_video_flow(options, auth)

    for call in worker._execute_download.call_args_list:
        if file_format == 'Any':
            assert not call.args[0].get('postprocessors')
        else:
            assert call.args[0]['postprocessors'][0]['preferedformat'] == file_format


@pytest.mark.parametrize('file_format', ['Any', 'flac', 'wav'])
def test_inapplicable_audio_bitrate_does_not_change_output_identity(file_format):
    base = {'audio_only': True, 'preferred_audio_format': file_format}

    assert audio_preferences({**base, 'preferred_audio_quality': '128 kbps'})[1] == 'bestaudio'
    assert download_key('https://example.com/video', {**base, 'preferred_audio_quality': '128 kbps'}) == download_key(
        'https://example.com/video', {**base, 'preferred_audio_quality': '320 kbps'})


def test_missing_preferences_use_same_defaults_as_settings_manager():
    defaults = SettingsManager.load_default_settings(object.__new__(SettingsManager))

    assert video_preferences({}) == video_preferences(defaults)
    assert audio_preferences({}) == audio_preferences(defaults)


class _AudioEstimate:
    _audio_only_formats = MainWindow._audio_only_formats
    _filter_audio_by_extension = MainWindow._filter_audio_by_extension
    _fallback_audio_formats = MainWindow._fallback_audio_formats
    _pick_best_audio_by_bitrate = MainWindow._pick_best_audio_by_bitrate
    _parse_bitrate_kbps = staticmethod(MainWindow._parse_bitrate_kbps)
    _get_audio_bitrate = staticmethod(MainWindow._get_audio_bitrate)


def test_audio_estimate_selects_download_source_rather_than_encoder_bitrate():
    formats = [
        {'format_id': 'low', 'url': 'https://example.com/low', 'vcodec': 'none', 'acodec': 'mp3', 'ext': 'mp3', 'abr': 64},
        {'format_id': 'high', 'url': 'https://example.com/high', 'vcodec': 'none', 'acodec': 'opus', 'ext': 'webm', 'abr': 160},
    ]

    selected = MainWindow._select_audio_format(_AudioEstimate(), formats, 'mp3', '64k')

    assert selected['format_id'] == 'high'


def test_video_container_remuxes_before_reencoding(monkeypatch):
    runner = Mock()
    monkeypatch.setattr(FFmpegPostProcessor, 'run_ffmpeg', runner)
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        processor = VideoContainerPP(ydl, preferedformat='mkv')
        processor.run({'filepath': 'source.mp4', 'ext': 'mp4', 'vcodec': 'h264', 'acodec': 'aac'})

    assert runner.call_count == 1
    arguments = list(runner.call_args.args[2])
    assert arguments[arguments.index('-c') + 1] == 'copy'


def test_incompatible_container_converts_after_remux_failure(monkeypatch):
    runner = Mock(side_effect=[PostProcessingError('incompatible codecs'), None])
    monkeypatch.setattr(FFmpegPostProcessor, 'run_ffmpeg', runner)
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        processor = VideoContainerPP(ydl, preferedformat='3gp')
        processor.run({'filepath': 'source.mp4', 'ext': 'mp4', 'vcodec': 'mpeg4', 'acodec': 'aac'})

    assert runner.call_count == 2
    assert 'libx264' in runner.call_args.args[2]


def test_failed_or_unfinished_conversion_does_not_count_as_completed(tmp_path):
    base = str(tmp_path / 'video')
    (tmp_path / 'video.source.mp4').write_bytes(b'source media')

    assert not DownloadThread.is_download_complete(base)
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        FinalizeDownloadPP(ydl, base).run({'filepath': base + '.source.mp4', 'ext': 'mp4'})
    assert DownloadThread.is_download_complete(base)
