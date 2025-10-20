from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, QEvent, QPoint, QRect, pyqtSignal as Signal
from PyQt6 import QtCore, QtGui


class CheckBoxDelegate(QtWidgets.QStyledItemDelegate):
    """
    A delegate that places a fully functioning QCheckBox cell of
    the column to which it's applied.
    """
    checkBoxStateChanged = Signal()

    def __init__(self, parent=None):
        QtWidgets.QStyledItemDelegate.__init__(self, parent)

    def createEditor(self, parent, option, index):
        return None

    def paint(self, painter, option, index):
        checked = bool(index.model().data(index, Qt.ItemDataRole.DisplayRole))
        check_box_style_option = QtWidgets.QStyleOptionButton()

        if (index.flags() & Qt.ItemFlag.ItemIsEditable):
            check_box_style_option.state |= QtWidgets.QStyle.StateFlag.State_Enabled
        else:
            check_box_style_option.state |= QtWidgets.QStyle.StateFlag.State_ReadOnly

        if checked:
            check_box_style_option.state |= QtWidgets.QStyle.StateFlag.State_On
        else:
            check_box_style_option.state |= QtWidgets.QStyle.StateFlag.State_Off

        check_box_style_option.rect = self.getCheckBoxRect(option)
        QtWidgets.QApplication.style().drawControl(
            QtWidgets.QStyle.ControlElement.CE_CheckBox,
            check_box_style_option, painter)

    def editorEvent(self, event, model, option, index):
        if not (index.flags() & Qt.ItemFlag.ItemIsEditable):
            return False
        # Do not change the checkbox-state
        if event.type() == QEvent.Type.MouseButtonRelease or event.type() == QEvent.Type.MouseButtonDblClick:
            if event.button() != Qt.MouseButton.LeftButton or not self.getCheckBoxRect(option).contains(event.pos()):
                return False
            if event.type() == QEvent.Type.MouseButtonDblClick:
                return True
        elif event.type() == QEvent.Type.KeyPress:
            if event.key() != Qt.Key.Key_Space and event.key() != Qt.Key.Key_Select:
                return False
        else:
            return False
        # Change the checkbox-state
        self.setModelData(None, model, index)
        self.checkBoxStateChanged.emit()
        return True

    def getCheckBoxRect(self, option):
        check_box_style_option = QtWidgets.QStyleOptionButton()
        check_box_rect = QtWidgets.QApplication.style().subElementRect(
            QtWidgets.QStyle.SubElement.SE_CheckBoxIndicator,
            check_box_style_option, None)

        check_box_point = QPoint(
            int(option.rect.x() + option.rect.width() / 2
                - check_box_rect.width() / 2),
            int(option.rect.y() + option.rect.height() / 2
                - check_box_rect.height() / 2)
        )
        return QRect(check_box_point, check_box_rect.size())

    def setModelData(self, editor, model, index):
        newValue = not bool(index.model().data(
            index, Qt.ItemDataRole.DisplayRole))
        model.setData(index, newValue, Qt.ItemDataRole.EditRole)
        newCheckState = Qt.CheckState.Checked if newValue \
            else Qt.CheckState.Unchecked
        model.setData(index, newCheckState, Qt.ItemDataRole.CheckStateRole)


class ProgressBarDelegate(QtWidgets.QStyledItemDelegate):
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
            painter.drawText(bar_rect, Qt.AlignmentFlag.AlignCenter, text)
            painter.restore()
