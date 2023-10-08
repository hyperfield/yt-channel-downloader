from PySide6 import QtWidgets
from PySide6.QtCore import Qt, QEvent, QPoint, QRect, Signal
from PySide6 import QtCore, QtGui


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
        checked = bool(index.model().data(index, Qt.DisplayRole))
        check_box_style_option = QtWidgets.QStyleOptionButton()
        if (index.flags() & Qt.ItemIsEditable):
            check_box_style_option.state |= QtWidgets.QStyle.State_Enabled
        else:
            check_box_style_option.state |= QtWidgets.QStyle.State_ReadOnly
        if checked:
            check_box_style_option.state |= QtWidgets.QStyle.State_On
        else:
            check_box_style_option.state |= QtWidgets.QStyle.State_Off
        check_box_style_option.rect = self.getCheckBoxRect(option)
        QtWidgets.QApplication.style().drawControl(
            QtWidgets.QStyle.CE_CheckBox, check_box_style_option, painter)

    def editorEvent(self, event, model, option, index):
        if not (index.flags() & Qt.ItemIsEditable):
            return False
        # Do not change the checkbox-state
        if event.type() == QEvent.MouseButtonRelease or event.type() == QEvent.MouseButtonDblClick:
            if event.button() != Qt.LeftButton or not self.getCheckBoxRect(option).contains(event.pos()):
                return False
            if event.type() == QEvent.MouseButtonDblClick:
                return True
        elif event.type() == QEvent.KeyPress:
            if event.key() != Qt.Key_Space and event.key() != Qt.Key_Select:
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
            QtWidgets.QStyle.SE_CheckBoxIndicator,
            check_box_style_option, None)
        check_box_point = QPoint(option.rect.x() +
                                 option.rect.width() / 2 -
                                 check_box_rect.width() / 2,
                                 option.rect.y() +
                                 option.rect.height() / 2 -
                                 check_box_rect.height() / 2)
        return QRect(check_box_point, check_box_rect.size())

    def setModelData(self, editor, model, index):
        newValue = not bool(index.model().data(index, Qt.DisplayRole))
        model.setData(index, newValue, Qt.EditRole)
        newCheckState = 2 if newValue else 0
        model.setData(index, newCheckState, Qt.CheckStateRole)


class ProgressBarDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        QtWidgets.QStyledItemDelegate.__init__(self, parent)

    def paint(self, painter, option, index):
        # Get the data for the item
        progress = index.data(QtCore.Qt.ItemDataRole.UserRole)

        # Draw the progress bar
        painter.save()
        rect = option.rect
        rect.setWidth(int(rect.width() * progress))
        painter.fillRect(rect, QtGui.QColor("#00c0ff"))
        painter.restore()
