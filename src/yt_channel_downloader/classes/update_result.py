from dataclasses import dataclass
from typing import Optional

from .release_info import ReleaseInfo
from .update_status import UpdateStatus


@dataclass(frozen=True)
class UpdateResult:
    status: UpdateStatus
    release: Optional[ReleaseInfo] = None
    error: Optional[str] = None
