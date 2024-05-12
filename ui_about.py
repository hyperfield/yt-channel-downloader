# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'about.ui'
##
## Created by: Qt User Interface Compiler version 6.6.0
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
from PySide6.QtWidgets import (QApplication, QDialog, QLabel, QPushButton,
    QSizePolicy, QWidget)

class Ui_aboutDialog(object):
    def setupUi(self, aboutDialog):
        if not aboutDialog.objectName():
            aboutDialog.setObjectName(u"aboutDialog")
        aboutDialog.resize(362, 324)
        self.aboutLabel = QLabel(aboutDialog)
        self.aboutLabel.setObjectName(u"aboutLabel")
        self.aboutLabel.setGeometry(QRect(110, 10, 211, 261))
        self.aboutOkButton = QPushButton(aboutDialog)
        self.aboutOkButton.setObjectName(u"aboutOkButton")
        self.aboutOkButton.setGeometry(QRect(220, 270, 89, 25))
        self.label = QLabel(aboutDialog)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(20, 30, 81, 91))

        self.retranslateUi(aboutDialog)

        QMetaObject.connectSlotsByName(aboutDialog)
    # setupUi

    def retranslateUi(self, aboutDialog):
        aboutDialog.setWindowTitle(QCoreApplication.translate("aboutDialog", u"About", None))
        self.aboutLabel.setText(QCoreApplication.translate("aboutDialog", u"<html><head><title>About</title></head><body><h3 style=\" margin-top:14px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:large; font-weight:700;\">YT Channel Downloader</span></h3><p><span style=\" font-weight:700;\">Version:</span> 0.3.3</p><p><span style=\" font-weight:700;\">Year: </span>2024 </p><p><span style=\" font-weight:700;\">License: </span>MIT </p><p><span style=\" font-weight:700;\">Github: </span><a href=\"https://github.com/hyperfield/yt-channel-downloader\"><span style=\" text-decoration: underline; color:#0000ff;\">View on Github</span></a></p><p><span style=\" font-weight:700;\">Author: </span><a href=\"mailto:info@quicknode.net\"><span style=\" text-decoration: underline; color:#0000ff;\">hyperfield</span></a></p></body></html>", None))
        self.aboutOkButton.setText(QCoreApplication.translate("aboutDialog", u"OK", None))
        self.label.setText(QCoreApplication.translate("aboutDialog", u"<html><head/><body><p><img src=\":/images/icon.png\" width=\"64\" height=\"64\"/></p></body></html>\n"
"", None))
    # retranslateUi

