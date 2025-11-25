from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt, QEvent, QPoint, QRect, pyqtSignal as Signal


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
        model.setData(index, newCheckState,
                      Qt.ItemDataRole.CheckStateRole)
