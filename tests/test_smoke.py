import pathlib
import re
import sys
from typing import Optional


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from yt_channel_downloader import __version__  # noqa: E402


def _read_pyproject_version() -> Optional[str]:
    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    try:
        text = pyproject_path.read_text()
    except Exception:
        return None
    project_section = re.split(r"^\[project\]\s*$", text, flags=re.MULTILINE)
    if len(project_section) < 2:
        return None
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', project_section[1], flags=re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip()


def test_package_imports_and_has_version():
    assert isinstance(__version__, str)
    assert __version__


def test_version_matches_pyproject_when_available():
    pyproject_version = _read_pyproject_version()
    if pyproject_version:
        assert __version__ == pyproject_version
