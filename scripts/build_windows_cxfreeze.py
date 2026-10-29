"""Build a Windows folder bundle or MSI with cx_Freeze.

Use ``build_exe`` or ``bdist_msi``. Add ``--probe`` to build_exe to include the
console diagnostic executable in a separate test build directory.
"""

import argparse
import os
from pathlib import Path
import runpy
import sys
import sysconfig
import uuid


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--probe", action="store_true")
    args, commands = parser.parse_known_args()
    if sys.platform != "win32":
        parser.error("Run this build on Windows using the build virtual environment.")
    if args.probe and "bdist_msi" in commands:
        parser.error("Use --probe with build_exe, not with bdist_msi.")
    sys.argv = [sys.argv[0], *commands]

    from cx_Freeze import Executable, setup
    from cx_Freeze.command.build_exe import build_exe
    from cx_Freeze.winversioninfo import VersionInfo

    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    sys.path.insert(0, str(root / "src"))
    release = runpy.run_path(str(root / "src/yt_channel_downloader/_release.py"))
    version = release["__version__"]
    app_name = "YT Channel Downloader"

    class WindowsBuildExe(build_exe):
        def run(self):
            super().run()
            # The project README is too large for a Windows version comment.
            # Stamp concise metadata after freezing and before MSI packaging.
            for executable in self.distribution.executables:
                VersionInfo(
                    version,
                    description=app_name,
                    product=app_name,
                    company=self.distribution.metadata.get_author(),
                    copyright=executable.copyright,
                    comments="Windows desktop application built with cx_Freeze.",
                    verbose=False,
                ).stamp(Path(self.build_exe) / executable.target_name)

    icon = str(root / "packaging/icons/icon.ico")
    build_dir = root / "build/windows/cxfreeze"
    dist_dir = root / "dist/windows/cxfreeze"
    target_dir = build_dir / "probe" if args.probe else dist_dir / app_name
    if not target_dir.resolve().is_relative_to(root):
        parser.error("The bundle output must stay inside the project directory.")
    executables = [
        Executable(
            str(root / "src/yt_channel_downloader/__main__.py"),
            base="gui",
            target_name=app_name + ".exe",
            icon=icon,
            shortcut_name=app_name,
            shortcut_dir="ProgramMenuFolder",
            copyright="Copyright (c) 2024 hyperfield",
        ),
    ]
    if args.probe:
        executables.append(Executable(
            str(root / "scripts/verify_frozen_bundle.py"),
            base="console",
            target_name="verify-bundle.exe",
        ))

    platform = sysconfig.get_platform()
    upgrade_id = uuid.uuid5(
        uuid.NAMESPACE_URL,
        "https://github.com/hyperfield/yt-channel-downloader/windows/" + platform,
    )
    setup(
        name="yt-channel-downloader",
        version=version,
        description="YT Channel Downloader",
        cmdclass={"build_exe": WindowsBuildExe},
        options={
            "build": {"build_base": str(build_dir / "work")},
            "build_exe": {
                "build_exe": str(target_dir),
                "include_path": [str(root / "src")],
                "packages": [
                    "yt_channel_downloader", "yt_dlp", "yt_dlp_ejs",
                    "requests", "urllib3", "websockets", "Cryptodome", "mutagen",
                ],
                "includes": ["brotli", "certifi", "socks"],
                "excludes": ["yt_dlp.__pyinstaller", "PyInstaller", "cx_Freeze", "tkinter"],
                "include_files": [
                    (str(root / "LICENSE"), "LICENSE.txt"),
                ],
                "include_msvcr": True,
                "zip_exclude_packages": ["*"],
                "silent": True,
            },
            "bdist_msi": {
                "bdist_dir": str(build_dir / "msi"),
                "dist_dir": str(dist_dir),
                "output_name": f"YT-Channel-Downloader-{version}-{platform}.msi",
                "product_name": app_name,
                "upgrade_code": "{" + str(upgrade_id).upper() + "}",
                "all_users": False,
                "add_to_path": False,
                "initial_target_dir": r"[LocalAppDataFolder]Programs\YT Channel Downloader",
                "install_icon": icon,
            },
        },
        executables=executables,
    )


if __name__ == "__main__":
    main()
