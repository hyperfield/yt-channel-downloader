from __future__ import annotations

import html
import logging
import re
from typing import Any, Optional

import requests
from PyQt6.QtWidgets import QWidget

from .custom_dialog import CustomDialog
from .runtime_info import RuntimeInfo, detect_runtime
from .runtime_mode import RuntimeMode
from .update_context import UpdateContext
from .release_info import ReleaseInfo
from .update_status import UpdateStatus
from .update_result import UpdateResult
from .update_fetch_error import UpdateFetchError
from ..config.constants import (
    APP_VERSION,
    GITHUB_RELEASES_API_URL,
    GITHUB_RELEASES_PAGE_URL,
    UPDATE_CHECK_TIMEOUT,
    UPDATE_DOWNLOAD_URL,
)


logger = logging.getLogger(__name__)


class Updater:
    """
    Simple updater helper that adapts its messaging based on how the app is
    being executed (source checkout vs. frozen bundle).

    A more sophisticated implementation can extend this class with real
    network version checks and automatic download/installation.
    """

    def __init__(self) -> None:
        self._context = UpdateContext(
            runtime=detect_runtime(),
            current_version=APP_VERSION,
            download_url=UPDATE_DOWNLOAD_URL,
        )
        self._latest_result: Optional[UpdateResult] = None

    def prompt_for_update(self, parent: QWidget | None = None) -> None:
        result = self._check_for_updates()
        title, message = self._build_dialog_content(result)
        dialog = CustomDialog(title, message, parent=parent)
        dialog.exec()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _check_for_updates(self) -> UpdateResult:
        if self._latest_result:
            return self._latest_result

        try:
            release = self._fetch_latest_release()
        except UpdateFetchError as exc:
            logger.warning("Update check failed: %s", exc)
            result = UpdateResult(status=UpdateStatus.ERROR, error=str(exc))
        else:
            if self._is_remote_newer(release.version, self._context.current_version):
                logger.info(
                    "Update available: current=%s, latest=%s",
                    self._context.current_version,
                    release.display_version,
                )
                result = UpdateResult(status=UpdateStatus.AVAILABLE, release=release)
            else:
                logger.info(
                    "Application is up to date: current=%s, latest=%s",
                    self._context.current_version,
                    release.display_version,
                )
                result = UpdateResult(status=UpdateStatus.UP_TO_DATE, release=release)

        self._latest_result = result
        return result

    def _fetch_latest_release(self) -> ReleaseInfo:
        data = self._request_release_data()
        normalized_version, tag_name = self._extract_version_info(data)
        html_url = str(data.get("html_url") or GITHUB_RELEASES_PAGE_URL)
        asset_url, asset_name = self._extract_asset_info(data.get("assets"))
        body = self._extract_body(data.get("body"))

        return ReleaseInfo(
            version=normalized_version,
            tag_name=tag_name,
            html_url=html_url,
            body=body,
            asset_url=asset_url,
            asset_name=asset_name,
        )

    def _request_release_data(self) -> dict[str, Any]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": f"yt-channel-downloader/{self._context.current_version}",
        }
        try:
            response = requests.get(
                GITHUB_RELEASES_API_URL,
                timeout=UPDATE_CHECK_TIMEOUT,
                headers=headers,
            )
        except requests.RequestException as exc:
            raise UpdateFetchError("Network problem contacting GitHub.") from exc

        self._ensure_success_status(response)

        try:
            data: dict[str, Any] = response.json()
        except ValueError as exc:
            raise UpdateFetchError("Invalid JSON received from GitHub.") from exc

        return data

    def _ensure_success_status(self, response: requests.Response) -> None:
        if response.status_code == 200:
            return

        detail = f"GitHub returned HTTP {response.status_code}"
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            message = payload.get("message")
            if message:
                detail = f"{detail}: {message}"
        raise UpdateFetchError(detail)

    def _extract_version_info(self, data: dict[str, Any]) -> tuple[str, str]:
        tag_name = str(data.get("tag_name") or "").strip()
        fallback_name = str(data.get("name") or "").strip()
        normalized_version = self._normalize_version(tag_name) or self._normalize_version(fallback_name)
        if not normalized_version:
            raise UpdateFetchError("Release tag is missing a version number.")
        return normalized_version, tag_name or fallback_name or normalized_version

    def _extract_asset_info(self, assets: Any) -> tuple[Optional[str], Optional[str]]:
        if not isinstance(assets, list):
            return None, None
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            download_url = asset.get("browser_download_url")
            if download_url:
                asset_url = str(download_url)
                asset_name = str(asset.get("name") or "")
                return asset_url, asset_name
        return None, None

    def _extract_body(self, body: Any) -> Optional[str]:
        if body is None:
            return None
        return str(body)

    def _build_dialog_content(self, result: UpdateResult) -> tuple[str, str]:
        if result.status is UpdateStatus.ERROR:
            return "Update Check Failed", self._format_error_message(result.error)

        release = result.release
        if result.status is UpdateStatus.AVAILABLE and release:
            if self._context.runtime.mode is RuntimeMode.SOURCE:
                return "Update Available", self._format_source_update_message(release)
            return "Update Available", self._format_frozen_update_message(release)

        # Up to date
        return "Up to Date", self._format_up_to_date_message(release)

    def _format_source_update_message(self, release: ReleaseInfo) -> str:
        message = (
            f"A new version <b>{html.escape(release.display_version)}</b> is available on GitHub.<br>"
            f"You are currently running <b>{html.escape(self._context.current_version)}</b>.<br><br>"
            "To update your local checkout, open a terminal in the project directory and run:<br>"
            "<code>git pull</code><br><br>"
            f"View the full release details on "
            f"<a href=\"{html.escape(release.html_url)}\">GitHub</a>."
        )
        notes = self._format_release_notes(release.body, release.html_url)
        if notes:
            message += notes
        return message

    def _format_frozen_update_message(self, release: ReleaseInfo) -> str:
        target_url = release.asset_url or release.html_url
        link_label = release.asset_name or "GitHub Releases"
        message = (
            f"A new packaged build <b>{html.escape(release.display_version)}</b> is available.<br>"
            f"You are currently running <b>{html.escape(self._context.current_version)}</b>.<br><br>"
            f"Download the latest installer from "
            f"<a href=\"{html.escape(target_url)}\">{html.escape(link_label)}</a>."
        )
        if release.asset_url and release.asset_url != release.html_url:
            message += (
                "<br><br>"
                f"You can also review the release notes on "
                f"<a href=\"{html.escape(release.html_url)}\">GitHub</a>."
            )
        else:
            message += (
                "<br><br>"
                f"As an alternative mirror, builds are available on "
                f"<a href=\"{html.escape(self._context.download_url)}\">SourceForge</a>."
            )

        notes = self._format_release_notes(release.body, release.html_url)
        if notes:
            message += notes
        return message

    def _format_up_to_date_message(self, release: Optional[ReleaseInfo]) -> str:
        latest_display = release.display_version if release else self._context.current_version
        message = (
            f"You are already running the latest available version "
            f"(<b>{html.escape(self._context.current_version)}</b>).<br>"
        )
        message += (
            f"The most recent GitHub release is <b>{html.escape(latest_display)}</b>."
            f"<br><br>Visit the "
            f"<a href=\"{html.escape(release.html_url if release else GITHUB_RELEASES_PAGE_URL)}\">"
            f"GitHub releases page</a> for details."
        )
        return message

    def _format_error_message(self, error_text: Optional[str]) -> str:
        detail = html.escape(error_text or "Unable to reach GitHub.")
        return (
            "The application could not determine whether a newer version is available right now.<br>"
            f"Reason: {detail}<br><br>"
            f"You can still check manually on "
            f"<a href=\"{html.escape(GITHUB_RELEASES_PAGE_URL)}\">GitHub</a> or "
            f"<a href=\"{html.escape(self._context.download_url)}\">SourceForge</a>."
        )

    def _format_release_notes(self, body: Optional[str], link: str) -> str:
        if not body:
            return ""
        snippet = body.strip()
        if not snippet:
            return ""
        max_chars = 600
        truncated = snippet if len(snippet) <= max_chars else snippet[: max_chars - 3] + "..."
        escaped = html.escape(truncated).replace("\r\n", "\n").replace("\r", "\n")
        escaped = escaped.replace("\n", "<br>")
        return (
            "<br><br><b>Release notes (excerpt)</b><br>"
            f"{escaped}<br><br>"
            f"Read the full notes on <a href=\"{html.escape(link)}\">GitHub</a>."
        )

    def _normalize_version(self, value: str) -> str:
        stripped = value.strip()
        if stripped.lower().startswith("v"):
            stripped = stripped[1:]
        return stripped

    def _is_remote_newer(self, remote: str, local: str) -> bool:
        return self._version_tuple(remote) > self._version_tuple(local)

    def _version_tuple(self, value: str) -> tuple[int, ...]:
        sanitized = self._normalize_version(value)
        if not sanitized:
            return (0,)
        parts = []
        for token in re.split(r"[.\-]", sanitized):
            if not token:
                continue
            if token.isdigit():
                parts.append(int(token))
            else:
                match = re.match(r"(\d+)", token)
                if match:
                    parts.append(int(match.group(1)))
                else:
                    parts.append(0)
        return tuple(parts) if parts else (0,)
