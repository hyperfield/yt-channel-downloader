# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'about.ui'
##
## Created by: Qt User Interface Compiler version 6.5.3
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
        self.aboutLabel.setText(QCoreApplication.translate("aboutDialog", u"<html>\n"
"<head>\n"
"    <title>About</title>\n"
"</head>\n"
"<body>\n"
"    <h3>YT Channel Downloader</h3>\n"
"    <p><strong>Version:</strong> 0.1.0</p>\n"
"    <p><strong>Year: </strong>2023</p>\n"
"    <p><strong>License: </strong>MIT</p>\n"
"    <p><strong>Github: </strong><a href=\"https://github.com/hyperfield/yt-channel-downloader\">View on Github</a></p>\n"
"    <p><strong>Author: </strong><a href=\"mailto:pzarva@quicknode.net\">Pavel Zarva</p>\n"
"</body>\n"
"</html>", None))
        self.aboutOkButton.setText(QCoreApplication.translate("aboutDialog", u"OK", None))
        self.label.setText(QCoreApplication.translate("aboutDialog", u"<html><head/><body><p><img src=\":/images/icon.png\" width=\"64\" height=\"64\"/></p></body></html>\n"
"", None))
    # retranslateUi

