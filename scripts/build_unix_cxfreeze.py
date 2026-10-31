"""Freeze on Linux with build_exe or on macOS with bdist_mac."""

import os
from pathlib import Path
import sys

from desktop_release import APP_NAME, PACKAGE, ROOT, architecture, release_version


def main():
    if sys.platform not in ("linux", "darwin"):
        raise SystemExit("Run this helper on Linux or macOS using that platform's Python")
    from cx_Freeze import Executable, setup

    os.chdir(ROOT)
    sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
    system = "macos" if sys.platform == "darwin" else "linux"
    build = ROOT / "build" / system / "cxfreeze" / architecture()
    version = release_version()
    options = {
        "build": {"build_base": str(build)},
        "build_exe": {
            "build_exe": str(build / "app"),
            "include_path": [str(ROOT / "src"), str(ROOT / "scripts")],
            "packages": [
                "yt_channel_downloader", "yt_dlp", "yt_dlp_ejs",
                "requests", "urllib3", "websockets", "Cryptodome", "mutagen",
            ],
            "includes": ["brotli", "certifi", "socks", "verify_frozen_bundle"],
            "excludes": ["yt_dlp.__pyinstaller", "PyInstaller", "cx_Freeze", "tkinter"],
            "include_files": [(str(ROOT / "LICENSE"), "LICENSE.txt")],
            "zip_exclude_packages": ["*"],
            "silent": True,
        },
    }
    if system == "macos":
        options["bdist_mac"] = {
            "bundle_name": APP_NAME,
            "iconfile": str(ROOT / "packaging/icons/icon.icns"),
            "plist_items": [
                ("CFBundleIdentifier", "net.quicknode.yt-channel-downloader"),
                ("CFBundleShortVersionString", version), ("CFBundleVersion", version),
                ("NSHighResolutionCapable", True), ("LSMinimumSystemVersion", "15.0"),
            ],
        }
    setup(
        name=PACKAGE, version=version, description=APP_NAME, options=options,
        executables=[Executable(
            str(ROOT / "scripts/frozen_unix_entry.py"), base="gui", target_name=PACKAGE,
            icon=str(ROOT / "packaging/icons/icon.png") if system == "linux" else None,
        )],
    )


if __name__ == "__main__":
    main()
