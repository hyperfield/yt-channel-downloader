from PyQt6 import QtCore


class SelectionSizeWorker(QtCore.QObject):
    """Background worker to compute selection size totals without blocking UI."""

    finished = QtCore.pyqtSignal(object, object, bool, dict, int, int, bool)

    def __init__(self, rows_data, estimate_func, remaining_func, generation: int):
        super().__init__()
        self.rows_data = rows_data
        self.estimate_func = estimate_func
        self.remaining_func = remaining_func
        self.generation = generation
        self._cancelled = False

    def request_size_eta_cancellation(self):
        """Request cancellation of the current selection size estimation run."""
        self._cancelled = True

    @QtCore.pyqtSlot()
    def run(self):
        total_estimated = 0
        total_remaining = 0
        has_unknown = False
        per_row_estimates = {}
        cancelled = False

        for data in self.rows_data:
            if self._cancelled:
                cancelled = True
                break
            estimate = self.estimate_func(data["link"], data["duration"])
            per_row_estimates[data["row"]] = estimate
            if estimate is None:
                has_unknown = True
                continue

            total_estimated += estimate
            total_remaining += self.remaining_func(estimate, data["progress"])

        self.finished.emit(
            total_estimated,
            total_remaining,
            has_unknown,
            per_row_estimates,
            len(self.rows_data),
            self.generation,
            cancelled,
        )
