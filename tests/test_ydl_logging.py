from unittest.mock import Mock

from yt_channel_downloader.classes import quiet_ydl_logger as logger_module


def test_deprecation_warning_is_not_duplicated_as_error(monkeypatch):
    logger = Mock()
    monkeypatch.setattr(logger_module, "logger", logger)
    adapter = logger_module.QuietYDLLogger()
    message = "Deprecated Feature: Support for Python version 3.10 has been deprecated"

    adapter.warning(message)
    adapter.error(message)

    logger.warning.assert_called_once_with(message)
    logger.error.assert_not_called()


def test_download_errors_still_logged(monkeypatch):
    logger = Mock()
    monkeypatch.setattr(logger_module, "logger", logger)
    adapter = logger_module.QuietYDLLogger()

    adapter.error("ERROR: HTTP Error 403: Forbidden")

    logger.error.assert_called_once_with("ERROR: HTTP Error 403: Forbidden")
