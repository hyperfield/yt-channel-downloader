from PyQt6 import QtWidgets, QtCore, QtGui


class ProgressBarDelegate(QtWidgets.QStyledItemDelegate):
    """Delegate rendering a gradient progress bar inside table cells."""

    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        raw_progress = index.data(QtCore.Qt.ItemDataRole.UserRole)
        text = index.data(QtCore.Qt.ItemDataRole.DisplayRole)

        progress = None
        if raw_progress is not None:
            try:
                progress = float(raw_progress)
            except (TypeError, ValueError):
                progress = None

        if progress is None:
            view_option = QtWidgets.QStyleOptionViewItem(option)
            self.initStyleOption(view_option, index)
            QtWidgets.QStyledItemDelegate.paint(self, painter, view_option, index)
            return

        bar_rect = option.rect.adjusted(4, 8, -4, -8)
        if bar_rect.height() <= 0 or bar_rect.width() <= 0:
            bar_rect = option.rect

        painter.save()
        # Draw background
        painter.setPen(QtGui.QPen(QtGui.QColor('#a0a0a0')))
        painter.setBrush(QtGui.QBrush(QtGui.QColor('#f0f0f0')))
        painter.drawRoundedRect(bar_rect, 4, 4)

        # Draw filled portion
        clamped = min(max(progress, 0.0), 100.0)
        chunk_width = max(0, int(bar_rect.width() * clamped / 100))
        if chunk_width > 0:
            chunk_rect = QtCore.QRect(bar_rect.left(), bar_rect.top(), chunk_width, bar_rect.height())
            gradient = QtGui.QLinearGradient(chunk_rect.topLeft(), chunk_rect.bottomRight())
            gradient.setColorAt(0.0, QtGui.QColor('#3a7bd5'))
            gradient.setColorAt(1.0, QtGui.QColor('#00d2ff'))
            painter.setBrush(QtGui.QBrush(gradient))
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.drawRoundedRect(chunk_rect, 4, 4)
        painter.restore()

        if text:
            painter.save()
            painter.setPen(QtGui.QPen(QtGui.QColor('#000000')))
            painter.drawText(bar_rect, QtCore.Qt.AlignmentFlag.AlignCenter, text)
            painter.restore()
