"""Build Windows bundles with version metadata from the application's release file."""

import argparse
import hashlib
from pathlib import Path
import runpy
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--layout",
        choices=("onefile", "onedir"),
        default="onefile",
        help="Bundle layout (default: onefile). Distribute the entire folder for onedir.",
    )
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Run this script on Windows using the build virtual environment.")

    import PyInstaller.__main__
    from packaging.version import Version
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo,
        StringFileInfo,
        StringStruct,
        StringTable,
        VarFileInfo,
        VarStruct,
        VSVersionInfo,
    )

    root = Path(__file__).resolve().parent.parent
    release = runpy.run_path(str(root / "src/yt_channel_downloader/_release.py"))
    version = release["__version__"]
    numbers = Version(version).release
    if len(numbers) > 4 or any(number > 65535 for number in numbers):
        parser.error("The release version must fit four 16-bit Windows version fields.")
    windows_version = numbers + (0,) * (4 - len(numbers))
    app_name = "YT Channel Downloader"
    build_dir = root / "build/windows" / args.layout
    dist_dir = root / "dist/windows" / args.layout
    build_dir.mkdir(parents=True, exist_ok=True)
    version_file = build_dir / "version_info.txt"
    version_info = VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=windows_version,
            prodvers=windows_version,
            mask=0x3F,
            flags=0,
            OS=0x40004,
            fileType=0x1,
            subtype=0,
            date=(0, 0),
        ),
        kids=[
            StringFileInfo([
                StringTable("040904B0", [
                    StringStruct("FileDescription", app_name),
                    StringStruct("FileVersion", version),
                    StringStruct("InternalName", "yt-channel-downloader"),
                    StringStruct("OriginalFilename", app_name + ".exe"),
                    StringStruct("ProductName", app_name),
                    StringStruct("ProductVersion", version),
                ]),
            ]),
            VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),
        ],
    )
    version_file.write_text(str(version_info), encoding="utf-8")
    PyInstaller.__main__.run([
        "--" + args.layout,
        "--noconsole",
        "--clean",
        "--noupx",
        "--name", app_name,
        "--paths", str(root / "src"),
        "--icon", str(root / "packaging/icons/icon.ico"),
        "--version-file", str(version_file),
        "--collect-all", "yt_channel_downloader",
        "--collect-all", "yt_dlp_ejs",
        "--recursive-copy-metadata", "yt-dlp",
        "--distpath", str(dist_dir),
        "--workpath", str(build_dir / "work"),
        "--specpath", str(build_dir),
        str(root / "src/yt_channel_downloader/__main__.py"),
    ])
    executable = dist_dir / (app_name + ".exe")
    if args.layout == "onedir":
        executable = dist_dir / app_name / (app_name + ".exe")
    with executable.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    print(f"Built: {executable}")
    print(f"SHA256: {digest}")


if __name__ == "__main__":
    main()
