"""Non-YouTube routing, single-item extraction, and native-container regressions."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import yt_dlp

from yt_channel_downloader.classes import validators
from yt_channel_downloader.classes import utils
from yt_channel_downloader.classes.YTChannel import YTChannel
from yt_channel_downloader.classes.download_identity import download_key, index_download_paths, source_identity
from yt_channel_downloader.classes.download_thread import DownloadThread
from yt_channel_downloader.classes.mainwindow import MainWindow
from yt_channel_downloader.classes.get_list_thread import GetListThread
from yt_channel_downloader.classes.source_urls import youtube_url_parts, youtube_video_id
from yt_channel_downloader.classes.validators import extract_single_media, single_media_entry


@pytest.mark.parametrize('url', [
    'https://vimeo.com/123?list=456',
    'https://example.com/watch?v=abc123def45&list=PL123',
    'https://youtube.com.example.org/shorts/abc123def45',
    'https://example.com/?next=https://youtube.com/watch?v=abc123def45',
    'https://example.com/channel/abc123def45',
    'abcdefghij!',
])
def test_external_urls_are_never_classified_as_youtube(url):
    channel = YTChannel.__new__(YTChannel)
    assert not channel.is_video_url(url)
    assert not channel.is_playlist_url(url)
    assert not channel.is_short_video_url(url)
    assert not channel.is_video_with_playlist_url(url)
    assert youtube_url_parts(url) is None
    assert youtube_video_id(url) is None
    assert YTChannel._channel_id_from_url(url) is None
    assert MainWindow._extract_youtube_id(url) is None
    assert source_identity(url) == url


@pytest.mark.parametrize('url', [
    'https://m.youtube.com/watch?feature=share&v=abc123def45',
    'https://music.youtube.com/watch?v=abc123def45',
    'https://www.youtube.com/embed/abc123def45',
    'https://www.youtube.com/live/abc123def45',
    'youtu.be/abc123def45',
    'abc123def45',
])
def test_real_youtube_aliases_remain_recognized(url):
    assert youtube_video_id(url) == 'abc123def45'
    assert YTChannel.is_video_url(None, url)


class _FakeYoutubeDL:
    info = None
    captured = None
    failure = None

    def __init__(self, opts):
        type(self).captured = opts

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def extract_info(self, url, download=False):
        if self.failure:
            raise self.failure
        return self.info


@pytest.fixture
def extractor(monkeypatch):
    monkeypatch.setattr(validators.yt_dlp, 'YoutubeDL', _FakeYoutubeDL)
    monkeypatch.setattr(_FakeYoutubeDL, 'failure', None)
    return _FakeYoutubeDL


def test_generic_metadata_keeps_source_url_and_previews(extractor):
    extractor.info = {
        'title': 'Private clip', 'url': 'https://cdn.example.com/signed?expires=123',
        'webpage_url': 'https://example.com/redirect', 'duration': 21.9,
        'thumbnail': 'https://example.com/preview.jpg',
        'thumbnails': [{'url': 'https://example.com/large.jpg'}],
    }
    original = 'https://example.com/post/42?media=2'

    result = extract_single_media(original, {'proxy': 'http://proxy.example.com:3128'})

    assert result == {'title': 'Private clip', 'url': original, 'duration': 21,
                      'thumbnail': extractor.info['thumbnail'], 'thumbnails': extractor.info['thumbnails']}
    assert extractor.captured['proxy'] == 'http://proxy.example.com:3128'
    assert extractor.captured['playlist_items'] == '1:2'
    assert extractor.captured['socket_timeout'] == 15


@pytest.mark.parametrize('kind', ['playlist', 'multi_video'])
def test_collections_fail_clearly_without_consuming_the_entire_source(extractor, kind):
    def entries():
        yield {'title': 'One', 'url': 'https://example.com/one'}
        yield {'title': 'Two', 'url': 'https://example.com/two'}
        pytest.fail('More than two entries were inspected')
    extractor.info = {'_type': kind, 'entries': entries()}

    with pytest.raises(ValueError, match='multiple media items.*direct link'):
        extract_single_media('https://example.com/collection')


def test_single_item_wrappers_supply_real_format_info_for_selection(extractor):
    entry = {'title': 'Video', 'formats': [{'format_id': 'direct', 'height': 360,
             'vcodec': 'h264', 'acodec': 'aac', 'ext': 'mp4', 'url': 'https://example.com/stream'}]}
    extractor.info = {'_type': 'playlist', 'entries': [
        {'_type': 'multi_video', 'entries': [entry]},
    ]}

    assert single_media_entry(extractor.info, 'https://example.com/embed') is entry
    assert utils.get_format_candidates('https://example.com/embed', '720p', 'mp4') == ['direct']


def test_provider_errors_reach_the_user_instead_of_becoming_invalid_url(extractor):
    extractor.failure = yt_dlp.utils.DownloadError('Login required for this provider')
    with pytest.raises(ValueError, match='Login required'):
        extract_single_media('https://example.com/private')


@pytest.mark.parametrize(('duration', 'expected'), [
    (None, None), (float('nan'), None), (float('inf'), None), (-1, None),
    (True, None), ('-10', None), ('unknown', None), ('1:02', 62), ('123', 123), (0, 0),
])
def test_bad_or_unknown_durations_do_not_break_sources(duration, expected):
    assert validators._normalize_duration({'duration': duration}) == expected


def test_valid_duration_string_falls_back_after_invalid_numeric_duration():
    assert validators._normalize_duration({'duration': float('nan'), 'duration_string': '1:02'}) == 62


@pytest.mark.parametrize('suffix', ['ts', 'm2ts', 'mts', 'mpeg', 'mpe', 'vob'])
def test_native_mpeg_containers_are_complete_and_preferred_by_the_index(tmp_path, suffix):
    key = download_key('https://example.com/clip', {})
    base = tmp_path / f'Old_title__{key}'
    base.with_suffix('.' + suffix).write_bytes(b'final media')
    (tmp_path / f'New_title__{key}.source.{suffix}').write_bytes(b'unfinished')

    assert DownloadThread.is_download_complete(str(base))
    assert index_download_paths(str(tmp_path))[key] == str(base)
    base.with_suffix('.' + suffix).unlink()
    assert not DownloadThread.is_download_complete(str(base))


def test_external_fetch_routes_without_network_checks_or_youtube_runtime_prompts(monkeypatch):
    url = 'https://vimeo.com/123?list=456'
    monkeypatch.setattr(validators, 'extract_single_media', Mock(side_effect=AssertionError('GUI network request')))
    channel = YTChannel.__new__(YTChannel)
    generic = Mock()
    window = SimpleNamespace(
        ui=SimpleNamespace(chanUrlEdit=SimpleNamespace(text=lambda: '  ' + url + '  ')),
        node_notifier=Mock(), _set_fetch_controls_enabled=Mock(), _prepare_yt_channel=lambda: channel,
        _is_playlist_or_video_with_playlist=lambda channel, value: channel.is_playlist_url(value),
        _is_video=lambda channel, value: channel.is_video_url(value),
        _start_generic_media_fetch=generic,
    )

    MainWindow._show_vid_list_internal(window, append=True)

    generic.assert_called_once_with(channel, url, True)
    window.node_notifier.maybe_prompt.assert_not_called()


def test_generic_fetch_clears_previous_channel_pagination_context():
    window = SimpleNamespace(current_fetch_is_channel=True, channel_fetch_context={'channel_id': 'old'},
                             _start_fetch_dialog=Mock(), _single_video_finish_handler=lambda append: None)
    MainWindow._start_generic_media_fetch(window, object(), 'https://example.com/video', False)
    assert window.current_fetch_is_channel is False
    assert window.channel_fetch_context is None


def test_first_size_estimate_uses_the_background_worker():
    window = SimpleNamespace(
        model=SimpleNamespace(rowCount=lambda: 1), _checked_row_indexes=lambda: [0],
        _is_size_estimation_enabled=lambda: True, _size_recalc_indicator_needed=False,
        _settings_signature=(), size_estimate_cache={}, _item_text=lambda *_: 'https://example.com/video',
        _start_async_selection_summary=Mock(return_value=True),
        _calculate_selection_totals=Mock(side_effect=AssertionError('GUI network estimate')),
    )
    assert MainWindow._selection_summary_text(window) is None
    window._start_async_selection_summary.assert_called_once_with([0])


def test_cancelled_fetch_does_not_start_metadata_extraction():
    channel = SimpleNamespace(get_single_video=Mock())
    thread = GetListThread(None, channel, 'https://example.com/video')
    cancelled = []
    thread.cancelled.connect(lambda: cancelled.append(True))
    thread.cancel()

    thread.run()

    channel.get_single_video.assert_not_called()
    assert cancelled == [True]


def test_provider_failure_after_cancel_does_not_show_an_error():
    def resolve(_):
        thread.cancel()
        raise ValueError('Network failure after cancellation')
    thread = GetListThread(None, SimpleNamespace(get_single_video=resolve), 'https://example.com/video')
    cancelled, errors = [], []
    thread.cancelled.connect(lambda: cancelled.append(True))
    thread.error.connect(errors.append)

    thread.run()

    assert cancelled == [True]
    assert errors == []
