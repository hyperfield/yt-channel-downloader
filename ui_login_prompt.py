# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'login_prompt.ui'
##
## Created by: Qt User Interface Compiler version 6.7.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QDialog,
    QDialogButtonBox, QLabel, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_LoginPromptDialog(object):
    def setupUi(self, LoginPromptDialog):
        if not LoginPromptDialog.objectName():
            LoginPromptDialog.setObjectName(u"LoginPromptDialog")
        LoginPromptDialog.resize(400, 200)
        self.verticalLayout = QVBoxLayout(LoginPromptDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label = QLabel(LoginPromptDialog)
        self.label.setObjectName(u"label")
        self.label.setWordWrap(True)

        self.verticalLayout.addWidget(self.label)

        self.checkBox = QCheckBox(LoginPromptDialog)
        self.checkBox.setObjectName(u"checkBox")

        self.verticalLayout.addWidget(self.checkBox)

        self.buttonBox = QDialogButtonBox(LoginPromptDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Ok)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(LoginPromptDialog)

        QMetaObject.connectSlotsByName(LoginPromptDialog)
    # setupUi

    def retranslateUi(self, LoginPromptDialog):
        LoginPromptDialog.setWindowTitle(QCoreApplication.translate("LoginPromptDialog", u"Login Prompt", None))
        self.label.setText(QCoreApplication.translate("LoginPromptDialog", u"This login process will allow you to download private, age-restricted or premium content using your YouTube account. When you log in, this app will download media on behalf of your account. You can log out with a single click from the same menu.", None))
        self.checkBox.setText(QCoreApplication.translate("LoginPromptDialog", u"Do not show this message again", None))
    # retranslateUi

