from PyQt6 import QtCore

from .updater import Updater
from .logger import get_logger


logger = get_logger("AutoUpdateWorker")


class AutoUpdateWorker(QtCore.QObject):
    """Background worker to check for updates without blocking the UI."""

    finished = QtCore.pyqtSignal(object)

    def __init__(self, updater: Updater):
        super().__init__()
        self.updater = updater

    @QtCore.pyqtSlot()
    def run(self):
        result = None
        try:
            result = self.updater._check_for_updates()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Auto update check failed: %s", exc)
        self.finished.emit(result)
