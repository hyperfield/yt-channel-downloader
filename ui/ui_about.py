# Form implementation generated from reading ui file 'about.ui'
#
# Created by: PyQt6 UI code generator 6.8.1
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_aboutDialog(object):
    def setupUi(self, aboutDialog):
        aboutDialog.setObjectName("aboutDialog")
        aboutDialog.resize(489, 328)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(12)
        aboutDialog.setFont(font)
        self.aboutLabel = QtWidgets.QLabel(parent=aboutDialog)
        self.aboutLabel.setGeometry(QtCore.QRect(110, 10, 361, 261))
        self.aboutLabel.setObjectName("aboutLabel")
        self.aboutOkButton = QtWidgets.QPushButton(parent=aboutDialog)
        self.aboutOkButton.setGeometry(QtCore.QRect(220, 270, 89, 25))
        self.aboutOkButton.setObjectName("aboutOkButton")
        self.label = QtWidgets.QLabel(parent=aboutDialog)
        self.label.setGeometry(QtCore.QRect(20, 30, 81, 91))
        self.label.setObjectName("label")

        self.retranslateUi(aboutDialog)
        QtCore.QMetaObject.connectSlotsByName(aboutDialog)

    def retranslateUi(self, aboutDialog):
        _translate = QtCore.QCoreApplication.translate
        aboutDialog.setWindowTitle(_translate("aboutDialog", "About"))
        self.aboutLabel.setText(_translate("aboutDialog", "<html><head><title>About</title></head><body><h3 style=\" margin-top:14px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:large; font-weight:700;\">YT Channel Downloader</span></h3><p><span style=\" font-weight:700;\">Version:</span> 0.4.10</p><p><span style=\" font-weight:700;\">Years: </span>2023-2025</p><p><span style=\" font-weight:700;\">License: </span>MIT </p><p><span style=\" font-weight:700;\">Github: </span><a href=\"https://github.com/hyperfield/yt-channel-downloader\"><span style=\" text-decoration: underline; color:#0000ff;\">View on Github</span></a></p><p><span style=\" font-weight:700;\">Author: </span><a href=\"mailto:info@quicknode.net\"><span style=\" text-decoration: underline; color:#0000ff;\">hyperfield</span></a></p><p><span style=\" font-weight:700;\">Contributors: </span><p>\n"
"  <a href=\"https://github.com/dsasmblr\" style=\"text-decoration: underline; color: #0000ff;\">dsasmblr</a>, \n"
"  <a href=\"https://github.com/djfm\" style=\"text-decoration: underline; color: #0000ff;\">djfm</a>, \n"
"  <a href=\"https://github.com/arvinnick\" style=\"text-decoration: underline; color: #0000ff;\">arvinnick</a>, \n"
"  <a href=\"https://github.com/quelilon\" style=\"text-decoration: underline; color: #0000ff;\">quelilon</a>\n"
"</p></body></html>"))
        self.aboutOkButton.setText(_translate("aboutDialog", "OK"))
        self.label.setText(_translate("aboutDialog", "<html><head/><body><p><img src=\":/images/icon.png\" width=\"64\" height=\"64\"/></p></body></html>\n"
""))
