import json
import os
from pathlib import Path
from unittest.mock import Mock

import pytest

pytest.importorskip('PyQt6')
from PyQt6.QtWidgets import QApplication
from yt_channel_downloader.classes import settings as settings_module
from yt_channel_downloader.classes import settings_manager as manager_module
from yt_channel_downloader.classes.settings import SettingsDialog
from yt_channel_downloader.classes.settings_manager import SettingsManager
from yt_channel_downloader.config.constants import DEFAULT_PLAYLIST_FETCH_LIMIT, DEFAULT_VIDEO_QUALITY


@pytest.fixture
def manager(tmp_path):
    manager = object.__new__(SettingsManager)
    manager.config_directory = str(tmp_path)
    manager.config_file_path = str(tmp_path / 'settings.json')
    manager.settings = manager.load_default_settings()
    manager._apply_environment_proxy = Mock()
    return manager


@pytest.fixture(scope='module')
def application():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def dialog(monkeypatch, manager, application):
    monkeypatch.setattr(settings_module, 'SettingsManager', lambda: manager)
    monkeypatch.setattr(settings_module.QMessageBox, 'warning', Mock())
    dialog = SettingsDialog()
    yield dialog
    dialog.close()


@pytest.mark.parametrize('payload', [None, [], 'a string', 42])
def test_non_object_json_is_backed_up_and_replaced_with_defaults(manager, payload):
    path = Path(manager.config_file_path)
    path.write_text(json.dumps(payload))

    settings = manager.load_settings()

    assert settings['preferred_video_quality'] == DEFAULT_VIDEO_QUALITY
    assert json.loads(Path(str(path) + '.corrupt').read_text()) == payload
    assert isinstance(json.loads(path.read_text()), dict)


def test_invalid_saved_values_are_repaired_consistently(manager):
    settings = manager.normalize_settings({
        'audio_only': ' false ', 'show_thumbnails': 'false',
        'preferred_video_quality': None, 'preferred_audio_format': ['mp3'],
        'playlist_fetch_limit': 999999, 'channel_fetch_limit': 'invalid',
        'download_directory': '', 'downloads_completed': -1,
        'youtube_browser_config': {'browser': 'firefox'},
    })

    assert settings['audio_only'] is False
    assert settings['show_thumbnails'] is False
    assert settings['preferred_video_quality'] == DEFAULT_VIDEO_QUALITY
    assert settings['preferred_audio_format'] == 'mp3'
    assert settings['playlist_fetch_limit'] == 50000
    assert settings['channel_fetch_limit'] == 500
    assert settings['downloads_completed'] == 0
    assert settings['youtube_browser_config'] == {'browser': 'firefox'}


def test_atomic_save_keeps_original_file_on_replace_failure(manager, monkeypatch):
    path = Path(manager.config_file_path)
    path.write_text('{"original": true}')
    monkeypatch.setattr(manager_module.os, 'replace', Mock(side_effect=OSError('disk failure')))

    with pytest.raises(OSError):
        manager.save_settings_to_file({'replacement': True})

    assert json.loads(path.read_text()) == {'original': True}
    assert list(path.parent.glob('*.tmp')) == []


@pytest.mark.parametrize('field,value', [
    ('download_directory', ''), ('proxy_server_port', '0'),
    ('proxy_server_port', '65536'), ('proxy_server_port', 'abc'),
    ('proxy_server_addr', 'https://proxy.example'), ('proxy_server_addr', 'bad host'),
])
def test_invalid_ui_values_do_not_replace_saved_settings(dialog, manager, field, value):
    original = dict(manager.settings)
    dialog.ui.proxy_server_type.setCurrentText('HTTP')
    dialog.ui.proxy_server_addr.setText('proxy.example')
    dialog.ui.proxy_server_port.setText('8080')
    widget = dialog.ui.save_downloads_edit if field == 'download_directory' else getattr(dialog.ui, field)
    widget.setText(value)

    dialog.save_settings()

    assert manager.settings == original
    settings_module.QMessageBox.warning.assert_called_once()


def test_failed_save_keeps_live_values_and_save_button_dirty(dialog, manager):
    original = dict(manager.settings)
    manager.save_settings_to_file = Mock(side_effect=OSError('disk full'))
    dialog.ui.save_downloads_edit.setText(str(Path(manager.config_directory) / 'new'))

    dialog.save_settings()

    assert manager.settings == original
    assert dialog.ui.save_button.isEnabled()
    settings_module.QMessageBox.warning.assert_called_once()


@pytest.mark.parametrize(('host', 'url'), [
    ('::1', 'http://[::1]:8080'),
    ('user:password@proxy.example', 'http://user:password@proxy.example:8080'),
    ('user:password@[::1]', 'http://user:password@[::1]:8080'),
])
def test_successful_save_preserves_hidden_fields_and_clears_dirty_state(dialog, manager, host, url):
    manager.settings['youtube_browser_config'] = {'browser': 'firefox'}
    dialog.ui.proxy_server_type.setCurrentText('HTTP')
    dialog.ui.proxy_server_addr.setText(host)
    dialog.ui.proxy_server_port.setText('+8080')
    dialog.playlist_limit_spin.setValue(2500)

    dialog.save_settings()

    assert manager.settings['youtube_browser_config'] == {'browser': 'firefox'}
    assert manager.settings['playlist_fetch_limit'] == 2500
    assert manager.build_proxy_url() == url
    assert json.loads(Path(manager.config_file_path).read_text()) == manager.settings
    assert not dialog.ui.save_button.isEnabled()


def test_disabling_proxy_preserves_server_for_switching_back(dialog):
    dialog.ui.proxy_server_type.setCurrentText('SOCKS5')
    dialog.ui.proxy_server_addr.setText('127.0.0.1')
    dialog.ui.proxy_server_port.setText('1080')

    dialog.ui.proxy_server_type.setCurrentText('None')
    dialog.ui.proxy_server_type.setCurrentText('SOCKS5')

    assert dialog.ui.proxy_server_addr.text() == '127.0.0.1'
    assert dialog.ui.proxy_server_port.text() == '1080'


@pytest.mark.parametrize('file_format', ['Any', 'flac', 'wav'])
def test_bitrate_control_is_inapplicable_to_native_and_lossless_audio(dialog, file_format):
    dialog.ui.check_audio_only.setChecked(True)
    dialog.ui.pref_aud_quality_dropdown.setCurrentText('128 kbps')

    dialog.ui.pref_aud_format_dropdown.setCurrentText(file_format)

    assert not dialog.ui.pref_aud_quality_dropdown.isEnabled()
    assert dialog.ui.pref_aud_quality_dropdown.currentText() == 'Best available'
    dialog.ui.pref_aud_format_dropdown.setCurrentText('mp3')
    assert dialog.ui.pref_aud_quality_dropdown.isEnabled()


def test_proxy_none_restores_existing_environment_instead_of_deleting_it(manager, monkeypatch):
    for key in manager.PROXY_ENV_KEYS:
        monkeypatch.setenv(key, 'original')
    manager._original_proxy_environment = {key: 'original' for key in manager.PROXY_ENV_KEYS}
    enabled = {'proxy_server_type': 'HTTP', 'proxy_server_addr': 'proxy.example', 'proxy_server_port': '8080'}

    SettingsManager._apply_environment_proxy(manager, enabled)
    assert os.environ['https_proxy'] == 'http://proxy.example:8080'
    SettingsManager._apply_environment_proxy(manager, {'proxy_server_type': 'None'})

    assert all(os.environ[key] == 'original' for key in manager.PROXY_ENV_KEYS)


def test_empty_explicit_proxy_settings_do_not_reuse_active_proxy(manager):
    manager.settings.update(proxy_server_type='HTTP', proxy_server_addr='proxy.example', proxy_server_port='8080')

    assert manager.build_proxy_url({}) is None
