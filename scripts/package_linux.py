"""Package a Linux x86_64 cx_Freeze folder as AppImage, DEB, and RPM."""

import argparse
from pathlib import Path
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

from desktop_release import (
    APP_NAME, PACKAGE, ROOT, architecture, github_download, release_version,
    write_build_info, write_checksums,
)


DEB_DEPENDENCIES = (
    "libc6 (>= 2.35)", "libstdc++6", "libgcc-s1", "zlib1g", "libglib2.0-0",
    "libdbus-1-3", "libfontconfig1", "libfreetype6", "libegl1", "libgl1", "libopengl0",
    "libx11-6", "libx11-xcb1", "libxcb1", "libxcb-cursor0", "libxcb-icccm4",
    "libxcb-keysyms1", "libxcb-shape0", "libxkbcommon0",
    "libxkbcommon-x11-0", "ffmpeg",
)
RPM_DEPENDENCIES = (
    "glibc >= 2.35", "libstdc++", "libgcc", "zlib", "glib2", "dbus-libs",
    "fontconfig", "freetype", "mesa-libEGL", "mesa-libGL", "libglvnd-opengl",
    "libX11", "libX11-xcb", "libxcb", "xcb-util-cursor", "xcb-util-wm", "xcb-util-keysyms", "libxkbcommon",
    "libxkbcommon-x11", "/usr/bin/ffmpeg", "/usr/bin/ffprobe",
)


def stage_payload(bundle, destination):
    """Keep the freezer layout intact and add standard desktop integration."""
    bundle = bundle.resolve(strict=True)
    if not (bundle / PACKAGE).is_file() or not (bundle / "lib").is_dir():
        raise ValueError("Build the Linux cx_Freeze folder before packaging")
    for path in bundle.rglob("*"):
        if path.is_symlink() and not path.resolve().is_relative_to(bundle):
            raise ValueError(f"Bundle symlink escapes its directory: {path}")
    shutil.copytree(bundle, destination / "usr/lib" / PACKAGE, symlinks=True)
    launcher = destination / "usr/bin" / PACKAGE
    launcher.parent.mkdir(parents=True)
    launcher.write_text(
        '#!/bin/sh\nset -eu\n'
        'binary_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
        f'exec "$binary_dir/../lib/{PACKAGE}/{PACKAGE}" "$@"\n', encoding="utf-8",
    )
    launcher.chmod(0o755)
    desktop = destination / "usr/share/applications" / (PACKAGE + ".desktop")
    desktop.parent.mkdir(parents=True)
    desktop.write_text(
        "[Desktop Entry]\nType=Application\n"
        f"Name={APP_NAME}\nComment=Download video channels and playlists\n"
        f"Exec={PACKAGE}\nIcon={PACKAGE}\nTerminal=false\n"
        "Categories=Network;AudioVideo;\nStartupNotify=true\n", encoding="utf-8",
    )
    icon = destination / "usr/share/pixmaps" / (PACKAGE + ".png")
    icon.parent.mkdir(parents=True)
    shutil.copy2(ROOT / "packaging/icons/icon.png", icon)
    license_dir = destination / "usr/share/licenses" / PACKAGE
    license_dir.mkdir(parents=True)
    shutil.copy2(ROOT / "LICENSE", license_dir / "LICENSE")
    return desktop, icon


def deb_control(version, size_kib, minimum_glibc="2.35"):
    dependencies = (f"libc6 (>= {minimum_glibc})", *DEB_DEPENDENCIES[1:])
    return (
        f"Package: {PACKAGE}\nVersion: {version}\nArchitecture: amd64\n"
        "Maintainer: hyperfield <info@quicknode.net>\nSection: video\nPriority: optional\n"
        f"Installed-Size: {size_kib}\nDepends: {', '.join(dependencies)}\n"
        "Recommends: deno (>= 2.3.0) | nodejs (>= 22.0.0)\n"
        "Homepage: https://github.com/hyperfield/yt-channel-downloader\n"
        f"Description: {APP_NAME}\n"
        " Desktop application for downloading channels and playlists via yt-dlp.\n"
        " Includes Python and Qt. Full YouTube support needs Deno 2.3+ or Node.js 22+.\n"
    )


def rpm_spec(version, minimum_glibc="2.35"):
    dependencies = (f"glibc >= {minimum_glibc}", *RPM_DEPENDENCIES[1:])
    requirements = "\n".join("Requires: " + item for item in dependencies)
    return f"""%global debug_package %{{nil}}
%global __os_install_post %{{nil}}
Name: {PACKAGE}
Version: {version}
Release: 1
Summary: {APP_NAME}
License: MIT
URL: https://github.com/hyperfield/yt-channel-downloader
Source0: payload.tar.gz
BuildArch: x86_64
AutoReqProv: no
{requirements}
Recommends: (deno >= 2.3.0 or nodejs >= 22.0.0)

%description
Desktop application for downloading channels and playlists via yt-dlp.
Includes Python and Qt. Full YouTube support needs Deno 2.3+ or Node.js 22+.

%prep
%setup -q -n payload

%build

%install
mkdir -p %{{buildroot}}/usr
cp -a usr/. %{{buildroot}}/usr/

%files
/usr/bin/{PACKAGE}
/usr/lib/{PACKAGE}
/usr/share/applications/{PACKAGE}.desktop
/usr/share/pixmaps/{PACKAGE}.png
%dir /usr/share/licenses/{PACKAGE}
%license /usr/share/licenses/{PACKAGE}/LICENSE
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=ROOT / "build/linux/cxfreeze/x86_64/app")
    parser.add_argument("--format", choices=("all", "appimage", "deb", "rpm"), default="all")
    args = parser.parse_args()
    if sys.platform != "linux" or architecture() != "x86_64":
        parser.error("Build Linux x86_64 packages on Linux x86_64")
    libc, minimum_glibc = platform.libc_ver()
    if libc != "glibc" or not re.fullmatch(r"\d+\.\d+", minimum_glibc):
        parser.error("Native packages require a glibc-based build environment")
    version = release_version()
    output = ROOT / "dist/linux"
    output.mkdir(parents=True, exist_ok=True)
    work = ROOT / "build/linux/packages"
    work.mkdir(parents=True, exist_ok=True)
    artifacts, tools = [], []
    formats = {"appimage", "deb", "rpm"} if args.format == "all" else {args.format}
    with tempfile.TemporaryDirectory(prefix="package-", dir=work) as temporary:
        stage = Path(temporary) / "payload"
        desktop, icon = stage_payload(args.bundle, stage)
        subprocess.run(["desktop-file-validate", str(desktop)], check=True)
        if "rpm" in formats:
            rpm_root = Path(temporary) / "rpm"
            for name in ("BUILD", "BUILDROOT", "RPMS", "SOURCES", "SPECS", "SRPMS"):
                (rpm_root / name).mkdir(parents=True)
            with tarfile.open(rpm_root / "SOURCES/payload.tar.gz", "w:gz") as archive:
                archive.add(stage, arcname="payload")
            spec = rpm_root / "SPECS/package.spec"
            spec.write_text(rpm_spec(version, minimum_glibc), encoding="utf-8")
            subprocess.run(["rpmbuild", "-bb", "--define", f"_topdir {rpm_root}", str(spec)], check=True)
            packages = list((rpm_root / "RPMS").rglob("*.rpm"))
            if len(packages) != 1:
                raise ValueError("Expected exactly one RPM")
            target = output / packages[0].name
            shutil.copy2(packages[0], target)
            artifacts.append(target)
        if "deb" in formats:
            control = stage / "DEBIAN/control"
            control.parent.mkdir()
            size = sum(path.stat().st_size for path in stage.rglob("*") if path.is_file())
            control.write_text(deb_control(version, (size + 1023) // 1024, minimum_glibc), encoding="utf-8")
            target = output / f"{PACKAGE}_{version}_amd64.deb"
            subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(stage), str(target)], check=True)
            artifacts.append(target)
            control.unlink()
            control.parent.rmdir()
        if "appimage" in formats:
            shutil.copy2(desktop, stage / desktop.name)
            shutil.copy2(icon, stage / icon.name)
            (stage / ".DirIcon").symlink_to(icon.name)
            app_run = stage / "AppRun"
            app_run.write_text(
                '#!/bin/sh\nset -eu\n'
                'app_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
                f'exec "$app_dir/usr/bin/{PACKAGE}" "$@"\n', encoding="utf-8",
            )
            app_run.chmod(0o755)
            appimagetool = Path(temporary) / "appimagetool.AppImage"
            runtime = Path(temporary) / "runtime-x86_64"
            tools.append(github_download("AppImage/appimagetool", "appimagetool-x86_64.AppImage", appimagetool))
            tools.append(github_download("AppImage/type2-runtime", "runtime-x86_64", runtime))
            target = output / f"YT-Channel-Downloader-{version}-linux-x86_64.AppImage"
            subprocess.run(
                [str(appimagetool), "--runtime-file", str(runtime), str(stage), str(target)],
                env={**os.environ, "ARCH": "x86_64", "APPIMAGE_EXTRACT_AND_RUN": "1"}, check=True,
            )
            artifacts.append(target)
    info = output / f"BUILD-INFO-linux-x86_64-{version}.json"
    write_build_info(info, glibc_baseline=minimum_glibc, build_tools=tools)
    write_checksums([*artifacts, info], output / "SHA256SUMS-linux-x86_64.txt")
    for artifact in artifacts:
        print(artifact)


if __name__ == "__main__":
    main()
