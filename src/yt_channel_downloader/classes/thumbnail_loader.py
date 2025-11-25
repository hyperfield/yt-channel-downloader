import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Optional, Iterable, Tuple

import requests
from PyQt6 import QtCore, QtGui

from .logger import get_logger


logger = get_logger("ThumbnailLoader")


class ThumbnailLoader(QtCore.QObject):
    """Fetch thumbnails asynchronously and emit scaled pixmaps."""

    DEFAULT_SIZE = (96, 54)

    thumbnail_ready = QtCore.pyqtSignal(int, QtGui.QPixmap)
    thumbnail_failed = QtCore.pyqtSignal(int)

    def __init__(self, parent=None, max_workers: int = 8):
        super().__init__(parent)
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="thumb")
        self._cache: Dict[str, QtGui.QPixmap] = {}
        self._lock = threading.Lock()

    def fetch(self, row_index: int, url: Optional[str], target_size=None):
        """Fetch thumbnail for a row; emit ready/failed on completion."""
        if not url:
            self.thumbnail_failed.emit(row_index)
            return
        target_size = target_size or self.DEFAULT_SIZE

        with self._lock:
            cached = self._cache.get(url)
        if cached:
            logger.info("Thumbnail cache hit: row=%s url=%s", row_index, url)
            self.thumbnail_ready.emit(row_index, cached)
            return

        future = self._executor.submit(self._download_and_scale, url, target_size)
        logger.info("Thumbnail fetch submitted: row=%s url=%s", row_index, url)
        future.add_done_callback(lambda f: self._handle_future(f, row_index, url))

    def _handle_future(self, future, row_index: int, url: str):
        try:
            pixmap = future.result()
        except Exception as exc:  # noqa: BLE001
            logger.info("Thumbnail fetch failed for %s: %s", url, exc)
            QtCore.QTimer.singleShot(0, lambda: self.thumbnail_failed.emit(row_index))
            return

        if pixmap is None or pixmap.isNull():
            logger.info("Thumbnail fetch produced null image for %s", url)
            QtCore.QTimer.singleShot(0, lambda: self.thumbnail_failed.emit(row_index))
            return

        with self._lock:
            self._cache[url] = pixmap
        logger.info("Thumbnail fetch completed: row=%s url=%s", row_index, url)
        QtCore.QTimer.singleShot(0, lambda: self.thumbnail_ready.emit(row_index, pixmap))

    @staticmethod
    def _download_and_scale(url: str, target_size) -> Optional[QtGui.QPixmap]:
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        data = resp.content
        image = QtGui.QImage.fromData(data)
        if image.isNull():
            return None
        pixmap = QtGui.QPixmap.fromImage(image)
        if target_size:
            pixmap = pixmap.scaled(
                target_size[0],
                target_size[1],
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
        return pixmap

    def shutdown(self):
        """Shutdown executor threads."""
        self._executor.shutdown(wait=False, cancel_futures=True)

    def preload_bulk(self, items: Iterable[Tuple[int, str]], target_size=None) -> Dict[int, QtGui.QPixmap]:
        """
        Prefetch a batch of thumbnails and return a map of row->pixmap.

        This method blocks until all downloads complete or fail.
        """
        target_size = target_size or self.DEFAULT_SIZE
        results: Dict[int, QtGui.QPixmap] = {}
        futures = {}
        for row_index, url in items:
            if not url:
                continue
            with self._lock:
                cached = self._cache.get(url)
            if cached:
                results[row_index] = cached
                continue
            fut = self._executor.submit(self._download_and_scale, url, target_size)
            futures[fut] = (row_index, url)

        for fut in as_completed(futures):
            row_index, url = futures[fut]
            try:
                pixmap = fut.result()
            except Exception as exc:  # noqa: BLE001
                logger.info("Thumbnail preload failed: row=%s url=%s error=%s", row_index, url, exc)
                continue
            if pixmap and not pixmap.isNull():
                with self._lock:
                    self._cache[url] = pixmap
                results[row_index] = pixmap
        return results
