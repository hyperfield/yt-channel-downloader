"""Unix bundle entry point, including an explicit diagnostic mode for CI."""

import os
from pathlib import Path
import sys


def configure_tool_path():
    # Finder does not inherit a terminal's Homebrew or Deno PATH settings.
    candidates = [Path.home() / ".deno/bin"]
    if sys.platform == "darwin":
        candidates.extend((Path("/opt/homebrew/bin"), Path("/usr/local/bin")))
    entries = os.environ.get("PATH", os.defpath).split(os.pathsep)
    entries.extend(str(path) for path in candidates if path.is_dir() and str(path) not in entries)
    os.environ["PATH"] = os.pathsep.join(entries)


if __name__ == "__main__":
    configure_tool_path()
    if sys.argv[1:] == ["--verify-bundle"]:
        from verify_frozen_bundle import main
    else:
        from yt_channel_downloader.__main__ import main
    main()
