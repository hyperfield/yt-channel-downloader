from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from .runtime_mode import RuntimeMode


@dataclass(frozen=True)
class RuntimeInfo:
    mode: RuntimeMode
    root_path: Path
    executable: Path

    @property
    def is_frozen(self) -> bool:
        return self.mode is RuntimeMode.FROZEN

    @property
    def is_source(self) -> bool:
        return self.mode is RuntimeMode.SOURCE


def detect_runtime() -> RuntimeInfo:
    """
    Detect whether the application is running from source (python -m yt_channel_downloader)
    or from a frozen/packaged bundle (e.g. PyInstaller).
    """
    if getattr(sys, "frozen", False):
        executable = Path(getattr(sys, "executable"))
        base_dir = Path(getattr(sys, "_MEIPASS", executable.parent))
        return RuntimeInfo(RuntimeMode.FROZEN, base_dir, executable)

    executable = Path(sys.argv[0]).resolve()
    root_path = Path(__file__).resolve().parent.parent
    return RuntimeInfo(RuntimeMode.SOURCE, root_path, executable)
