"""Shared metadata and verified downloads for desktop release builds."""

import argparse
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import runpy
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "YT Channel Downloader"
PACKAGE = "yt-channel-downloader"


def release_version(tag=""):
    version = runpy.run_path(str(ROOT / "src/yt_channel_downloader/_release.py"))["__version__"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Desktop releases require an X.Y.Z version in _release.py")
    if tag and tag != "v" + version:
        raise ValueError(f"Release tag {tag!r} does not match v{version}")
    return version


def architecture():
    machine = platform.machine().lower()
    names = {"amd64": "x86_64", "x86_64": "x86_64", "arm64": "arm64", "aarch64": "arm64"}
    if machine not in names:
        raise ValueError(f"Unsupported desktop architecture: {machine}")
    return names[machine]


def github_download(repository, asset_name, destination):
    """Require GitHub's SHA-256 digest before executing a downloaded build tool."""
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/releases/latest",
        headers={"User-Agent": PACKAGE + "-build", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        release = json.load(response)
    asset = next(asset for asset in release["assets"] if asset["name"] == asset_name)
    digest = asset.get("digest", "")
    if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
        raise ValueError(f"No SHA-256 digest published for {repository}/{asset_name}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(asset["browser_download_url"], timeout=180) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest().lower() != digest.split(":")[1].lower():
        raise ValueError(f"Checksum mismatch for {asset_name}")
    destination.write_bytes(data)
    destination.chmod(0o755)
    return {"repository": repository, "tag": release["tag_name"], "asset": asset_name, "digest": digest}


def write_build_info(path, **extra):
    packages = {}
    for name in (PACKAGE, "cx-Freeze", "PyQt6", "PyQt6-Qt6", "yt-dlp", "yt-dlp-ejs"):
        packages[name] = metadata.version(name)
    info = {
        "version": release_version(), "architecture": architecture(),
        "python": platform.python_version(), "system": platform.platform(),
        "commit": os.environ.get("GITHUB_SHA", ""), "packages": packages, **extra,
    }
    path.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")


def write_checksums(paths, destination):
    lines = []
    for path in sorted(paths):
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        lines.append(f"{digest}  {path.name}\n")
    destination.write_text("".join(lines), encoding="ascii")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="")
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--expect-arch", choices=("x86_64", "arm64"))
    args = parser.parse_args()
    version, arch = release_version(args.tag), architecture()
    if args.expect_arch and arch != args.expect_arch:
        parser.error(f"Expected {args.expect_arch}, running on {arch}")
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as stream:
            stream.write(f"version={version}\narch={arch}\n")
    print(json.dumps({"version": version, "arch": arch}))


if __name__ == "__main__":
    main()
