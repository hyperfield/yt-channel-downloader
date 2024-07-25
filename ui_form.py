# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'form.ui'
##
## Created by: Qt User Interface Compiler version 6.7.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QAbstractScrollArea, QApplication, QGridLayout, QGroupBox,
    QHeaderView, QLayout, QLineEdit, QMainWindow,
    QMenu, QMenuBar, QPushButton, QSizePolicy,
    QStatusBar, QTreeView, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(781, 638)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        self.actionFile = QAction(MainWindow)
        self.actionFile.setObjectName(u"actionFile")
        self.actionFile.setMenuRole(QAction.ApplicationSpecificRole)
        self.actionExit = QAction(MainWindow)
        self.actionExit.setObjectName(u"actionExit")
        icon = QIcon(QIcon.fromTheme(u"system-log-out"))
        self.actionExit.setIcon(icon)
        self.actionExit.setMenuRole(QAction.QuitRole)
        self.actionSettings = QAction(MainWindow)
        self.actionSettings.setObjectName(u"actionSettings")
        icon1 = QIcon(QIcon.fromTheme(u"preferences-desktop-multimedia"))
        self.actionSettings.setIcon(icon1)
        self.actionSettings.setMenuRole(QAction.ApplicationSpecificRole)
        self.actionAbout = QAction(MainWindow)
        self.actionAbout.setObjectName(u"actionAbout")
        self.actionAbout.setMenuRole(QAction.ApplicationSpecificRole)
        self.actionYoutube_login = QAction(MainWindow)
        self.actionYoutube_login.setObjectName(u"actionYoutube_login")
        icon2 = QIcon()
        icon2.addFile(u"youtube-icon.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionYoutube_login.setIcon(icon2)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.gridGroupBox = QGroupBox(self.centralwidget)
        self.gridGroupBox.setObjectName(u"gridGroupBox")
        self.gridLayout = QGridLayout(self.gridGroupBox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setSizeConstraint(QLayout.SetFixedSize)
        self.chanUrlEdit = QLineEdit(self.gridGroupBox)
        self.chanUrlEdit.setObjectName(u"chanUrlEdit")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.chanUrlEdit.sizePolicy().hasHeightForWidth())
        self.chanUrlEdit.setSizePolicy(sizePolicy1)
        self.chanUrlEdit.setMinimumSize(QSize(500, 0))
        self.chanUrlEdit.setMaximumSize(QSize(700, 16777215))
        self.chanUrlEdit.setFocusPolicy(Qt.ClickFocus)

        self.gridLayout.addWidget(self.chanUrlEdit, 0, 0, 1, 1)

        self.getVidListButton = QPushButton(self.gridGroupBox)
        self.getVidListButton.setObjectName(u"getVidListButton")
        sizePolicy1.setHeightForWidth(self.getVidListButton.sizePolicy().hasHeightForWidth())
        self.getVidListButton.setSizePolicy(sizePolicy1)

        self.gridLayout.addWidget(self.getVidListButton, 0, 1, 1, 1)

        self.downloadSelectedVidsButton = QPushButton(self.gridGroupBox)
        self.downloadSelectedVidsButton.setObjectName(u"downloadSelectedVidsButton")
        sizePolicy1.setHeightForWidth(self.downloadSelectedVidsButton.sizePolicy().hasHeightForWidth())
        self.downloadSelectedVidsButton.setSizePolicy(sizePolicy1)

        self.gridLayout.addWidget(self.downloadSelectedVidsButton, 0, 2, 1, 1)


        self.verticalLayout.addWidget(self.gridGroupBox)

        self.treeView = QTreeView(self.centralwidget)
        self.treeView.setObjectName(u"treeView")
        sizePolicy.setHeightForWidth(self.treeView.sizePolicy().hasHeightForWidth())
        self.treeView.setSizePolicy(sizePolicy)
        self.treeView.setInputMethodHints(Qt.ImhNone)
        self.treeView.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

        self.verticalLayout.addWidget(self.treeView)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 781, 24))
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setObjectName(u"menuFile")
        self.menuHelp = QMenu(self.menubar)
        self.menuHelp.setObjectName(u"menuHelp")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())
        self.menuFile.addAction(self.actionSettings)
        self.menuFile.addAction(self.actionYoutube_login)
        self.menuFile.addAction(self.actionExit)
        self.menuHelp.addAction(self.actionAbout)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"YT Channel Downloader", None))
        self.actionFile.setText(QCoreApplication.translate("MainWindow", u"&File", None))
#if QT_CONFIG(tooltip)
        self.actionFile.setToolTip(QCoreApplication.translate("MainWindow", u"File", None))
#endif // QT_CONFIG(tooltip)
        self.actionExit.setText(QCoreApplication.translate("MainWindow", u"&Exit", None))
#if QT_CONFIG(shortcut)
        self.actionExit.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Q", None))
#endif // QT_CONFIG(shortcut)
        self.actionSettings.setText(QCoreApplication.translate("MainWindow", u"&Settings", None))
#if QT_CONFIG(tooltip)
        self.actionSettings.setToolTip(QCoreApplication.translate("MainWindow", u"Settings", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionSettings.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
        self.actionAbout.setText(QCoreApplication.translate("MainWindow", u"About", None))
        self.actionYoutube_login.setText(QCoreApplication.translate("MainWindow", u"Youtube &login", None))
#if QT_CONFIG(shortcut)
        self.actionYoutube_login.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Shift+L", None))
#endif // QT_CONFIG(shortcut)
#if QT_CONFIG(tooltip)
        self.chanUrlEdit.setToolTip("")
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(whatsthis)
        self.chanUrlEdit.setWhatsThis(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Youtube video, playlist or channel URL</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.chanUrlEdit.setText("")
        self.chanUrlEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Youtube video, playlist or channel URL", None))
        self.getVidListButton.setText(QCoreApplication.translate("MainWindow", u"Fetch", None))
        self.downloadSelectedVidsButton.setText(QCoreApplication.translate("MainWindow", u"Download", None))
        self.menuFile.setTitle(QCoreApplication.translate("MainWindow", u"File", None))
        self.menuHelp.setTitle(QCoreApplication.translate("MainWindow", u"Help", None))
    # retranslateUi

