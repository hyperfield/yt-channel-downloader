"""YT Channel Downloader package."""

from __future__ import annotations

import pathlib
import re
from importlib import metadata


_FALLBACK_VERSION = "0.8.6"


def _version_from_pyproject(pyproject_path: pathlib.Path) -> str | None:
    """Parse the version from pyproject.toml without external deps."""
    try:
        text = pyproject_path.read_text()
    except Exception:
        return None
    # Simple regex to find `version = "x.y.z"` under [project]
    project_section = re.split(r"^\[project\]\s*$", text, flags=re.MULTILINE)
    if len(project_section) < 2:
        return None
    project_body = project_section[1]
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', project_body, flags=re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def _detect_version() -> str:
    # Prefer the version declared in the local pyproject.toml so running from
    # a source checkout reflects the repo version even if an older package is
    # installed elsewhere.
    project_root = pathlib.Path(__file__).resolve().parent.parent.parent
    pyproject_path = project_root / "pyproject.toml"
    version = _version_from_pyproject(pyproject_path) if pyproject_path.exists() else None
    if version:
        return version

    try:
        return metadata.version("yt-channel-downloader")
    except metadata.PackageNotFoundError:
        return _FALLBACK_VERSION


__all__ = ["__version__"]
__version__ = _detect_version()
