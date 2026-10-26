from types import SimpleNamespace
from unittest.mock import Mock

import pytest

pytest.importorskip("PyQt6")

from yt_channel_downloader.classes import node_runtime_notifier as notifier_module
from yt_channel_downloader.classes.js_warning_tracker import JsRuntimeWarningTracker
from yt_channel_downloader.classes.node_runtime_notifier import NodeRuntimeNotifier


@pytest.mark.parametrize(("binary", "version", "supported"), [
    ("node", "v20.19.0\n", False),
    ("node", "v22.0.0\n", True),
    ("node", "v24.21.0\n", True),
    ("deno", "deno 2.2.0 (stable)\nv8 1.0.0\n", False),
    ("deno", "deno 2.3.0 (stable)\nv8 1.0.0\n", True),
    ("node", "unrecognized version\n", False),
])
def test_runtime_requires_supported_version(monkeypatch, tmp_path, binary, version, supported):
    executable = tmp_path / binary
    executable.touch()
    monkeypatch.setattr(notifier_module.shutil, "which", lambda name: str(executable) if name == binary else None)
    monkeypatch.setattr(notifier_module.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout=version))
    notifier = NodeRuntimeNotifier(SimpleNamespace(settings={}), JsRuntimeWarningTracker(), None)

    assert notifier._has_working_js_runtime() is supported


def test_forced_runtime_warning_shows_only_once_per_session():
    notifier = NodeRuntimeNotifier(SimpleNamespace(settings={}), JsRuntimeWarningTracker(), None)

    def show_prompt(settings):
        notifier.prompted_this_session = True

    notifier._show_prompt = Mock(side_effect=show_prompt)

    notifier.maybe_prompt(force=True)
    notifier.maybe_prompt(force=True)

    notifier._show_prompt.assert_called_once()
