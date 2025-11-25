from dataclasses import dataclass

from .runtime_info import RuntimeInfo


@dataclass(frozen=True)
class UpdateContext:
    runtime: RuntimeInfo
    current_version: str
    download_url: str
