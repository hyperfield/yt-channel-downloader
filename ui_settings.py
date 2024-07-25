# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'settings.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_Settings(object):
    def setupUi(self, Settings):
        if not Settings.objectName():
            Settings.setObjectName(u"Settings")
        Settings.resize(764, 512)
        self.save_button = QPushButton(Settings)
        self.save_button.setObjectName(u"save_button")
        self.save_button.setGeometry(QRect(570, 471, 80, 31))
        self.close_button = QPushButton(Settings)
        self.close_button.setObjectName(u"close_button")
        self.close_button.setGeometry(QRect(670, 471, 80, 31))
        self.layoutWidget = QWidget(Settings)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.layoutWidget.setGeometry(QRect(20, 180, 391, 51))
        self.vid_quality_hlayout = QHBoxLayout(self.layoutWidget)
        self.vid_quality_hlayout.setObjectName(u"vid_quality_hlayout")
        self.vid_quality_hlayout.setContentsMargins(0, 0, 0, 0)
        self.pref_vid_quality_label = QLabel(self.layoutWidget)
        self.pref_vid_quality_label.setObjectName(u"pref_vid_quality_label")

        self.vid_quality_hlayout.addWidget(self.pref_vid_quality_label)

        self.pref_vid_quality_dropdown = QComboBox(self.layoutWidget)
        self.pref_vid_quality_dropdown.addItem("")
        self.pref_vid_quality_dropdown.addItem("")
        self.pref_vid_quality_dropdown.addItem("")
        self.pref_vid_quality_dropdown.addItem("")
        self.pref_vid_quality_dropdown.addItem("")
        self.pref_vid_quality_dropdown.addItem("")
        self.pref_vid_quality_dropdown.addItem("")
        self.pref_vid_quality_dropdown.addItem("")
        self.pref_vid_quality_dropdown.addItem("")
        self.pref_vid_quality_dropdown.setObjectName(u"pref_vid_quality_dropdown")

        self.vid_quality_hlayout.addWidget(self.pref_vid_quality_dropdown)

        self.layoutWidget_2 = QWidget(Settings)
        self.layoutWidget_2.setObjectName(u"layoutWidget_2")
        self.layoutWidget_2.setGeometry(QRect(20, 110, 391, 51))
        self.pref_video_format_layout = QHBoxLayout(self.layoutWidget_2)
        self.pref_video_format_layout.setObjectName(u"pref_video_format_layout")
        self.pref_video_format_layout.setContentsMargins(0, 0, 0, 0)
        self.pref_vid_format = QLabel(self.layoutWidget_2)
        self.pref_vid_format.setObjectName(u"pref_vid_format")

        self.pref_video_format_layout.addWidget(self.pref_vid_format)

        self.pref_vid_format_dropdown = QComboBox(self.layoutWidget_2)
        self.pref_vid_format_dropdown.addItem("")
        self.pref_vid_format_dropdown.addItem("")
        self.pref_vid_format_dropdown.addItem("")
        self.pref_vid_format_dropdown.addItem("")
        self.pref_vid_format_dropdown.addItem("")
        self.pref_vid_format_dropdown.addItem("")
        self.pref_vid_format_dropdown.addItem("")
        self.pref_vid_format_dropdown.addItem("")
        self.pref_vid_format_dropdown.setObjectName(u"pref_vid_format_dropdown")

        self.pref_video_format_layout.addWidget(self.pref_vid_format_dropdown)

        self.layoutWidget_3 = QWidget(Settings)
        self.layoutWidget_3.setObjectName(u"layoutWidget_3")
        self.layoutWidget_3.setGeometry(QRect(20, 320, 391, 51))
        self.audio_quality_hlayout = QHBoxLayout(self.layoutWidget_3)
        self.audio_quality_hlayout.setObjectName(u"audio_quality_hlayout")
        self.audio_quality_hlayout.setContentsMargins(0, 0, 0, 0)
        self.audio_quality_label = QLabel(self.layoutWidget_3)
        self.audio_quality_label.setObjectName(u"audio_quality_label")

        self.audio_quality_hlayout.addWidget(self.audio_quality_label)

        self.pref_aud_quality_dropdown = QComboBox(self.layoutWidget_3)
        self.pref_aud_quality_dropdown.addItem("")
        self.pref_aud_quality_dropdown.addItem("")
        self.pref_aud_quality_dropdown.addItem("")
        self.pref_aud_quality_dropdown.addItem("")
        self.pref_aud_quality_dropdown.addItem("")
        self.pref_aud_quality_dropdown.addItem("")
        self.pref_aud_quality_dropdown.addItem("")
        self.pref_aud_quality_dropdown.addItem("")
        self.pref_aud_quality_dropdown.setObjectName(u"pref_aud_quality_dropdown")

        self.audio_quality_hlayout.addWidget(self.pref_aud_quality_dropdown)

        self.layoutWidget_4 = QWidget(Settings)
        self.layoutWidget_4.setObjectName(u"layoutWidget_4")
        self.layoutWidget_4.setGeometry(QRect(20, 250, 391, 51))
        self.pref_audio_format_layout = QHBoxLayout(self.layoutWidget_4)
        self.pref_audio_format_layout.setObjectName(u"pref_audio_format_layout")
        self.pref_audio_format_layout.setContentsMargins(0, 0, 0, 0)
        self.pref_aud_format = QLabel(self.layoutWidget_4)
        self.pref_aud_format.setObjectName(u"pref_aud_format")

        self.pref_audio_format_layout.addWidget(self.pref_aud_format)

        self.pref_aud_format_dropdown = QComboBox(self.layoutWidget_4)
        self.pref_aud_format_dropdown.addItem("")
        self.pref_aud_format_dropdown.addItem("")
        self.pref_aud_format_dropdown.addItem("")
        self.pref_aud_format_dropdown.addItem("")
        self.pref_aud_format_dropdown.addItem("")
        self.pref_aud_format_dropdown.addItem("")
        self.pref_aud_format_dropdown.addItem("")
        self.pref_aud_format_dropdown.addItem("")
        self.pref_aud_format_dropdown.setObjectName(u"pref_aud_format_dropdown")

        self.pref_audio_format_layout.addWidget(self.pref_aud_format_dropdown)

        self.layoutWidget_5 = QWidget(Settings)
        self.layoutWidget_5.setObjectName(u"layoutWidget_5")
        self.layoutWidget_5.setGeometry(QRect(20, 390, 601, 72))
        self.proxy_server_layout = QHBoxLayout(self.layoutWidget_5)
        self.proxy_server_layout.setObjectName(u"proxy_server_layout")
        self.proxy_server_layout.setContentsMargins(0, 0, 0, 0)
        self.proxy_label = QLabel(self.layoutWidget_5)
        self.proxy_label.setObjectName(u"proxy_label")

        self.proxy_server_layout.addWidget(self.proxy_label)

        self.proxy_server_type = QComboBox(self.layoutWidget_5)
        self.proxy_server_type.addItem("")
        self.proxy_server_type.addItem("")
        self.proxy_server_type.addItem("")
        self.proxy_server_type.addItem("")
        self.proxy_server_type.setObjectName(u"proxy_server_type")

        self.proxy_server_layout.addWidget(self.proxy_server_type)

        self.proxy_server_label = QLabel(self.layoutWidget_5)
        self.proxy_server_label.setObjectName(u"proxy_server_label")

        self.proxy_server_layout.addWidget(self.proxy_server_label)

        self.proxy_server_addr = QLineEdit(self.layoutWidget_5)
        self.proxy_server_addr.setObjectName(u"proxy_server_addr")

        self.proxy_server_layout.addWidget(self.proxy_server_addr)

        self.proxy_port_label = QLabel(self.layoutWidget_5)
        self.proxy_port_label.setObjectName(u"proxy_port_label")

        self.proxy_server_layout.addWidget(self.proxy_port_label)

        self.proxy_server_port = QLineEdit(self.layoutWidget_5)
        self.proxy_server_port.setObjectName(u"proxy_server_port")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.proxy_server_port.sizePolicy().hasHeightForWidth())
        self.proxy_server_port.setSizePolicy(sizePolicy)
        self.proxy_server_port.setMaximumSize(QSize(70, 16777215))

        self.proxy_server_layout.addWidget(self.proxy_server_port)

        self.layoutWidget_6 = QWidget(Settings)
        self.layoutWidget_6.setObjectName(u"layoutWidget_6")
        self.layoutWidget_6.setGeometry(QRect(20, 40, 601, 72))
        self.dl_dir_layout = QHBoxLayout(self.layoutWidget_6)
        self.dl_dir_layout.setObjectName(u"dl_dir_layout")
        self.dl_dir_layout.setContentsMargins(0, 0, 0, 0)
        self.save_downloads_label = QLabel(self.layoutWidget_6)
        self.save_downloads_label.setObjectName(u"save_downloads_label")

        self.dl_dir_layout.addWidget(self.save_downloads_label)

        self.save_downloads_edit = QLineEdit(self.layoutWidget_6)
        self.save_downloads_edit.setObjectName(u"save_downloads_edit")

        self.dl_dir_layout.addWidget(self.save_downloads_edit)

        self.browse_btn = QPushButton(self.layoutWidget_6)
        self.browse_btn.setObjectName(u"browse_btn")

        self.dl_dir_layout.addWidget(self.browse_btn)

        self.layoutWidget_7 = QWidget(Settings)
        self.layoutWidget_7.setObjectName(u"layoutWidget_7")
        self.layoutWidget_7.setGeometry(QRect(440, 120, 278, 94))
        self.verticalLayout = QVBoxLayout(self.layoutWidget_7)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.check_audio_only = QCheckBox(self.layoutWidget_7)
        self.check_audio_only.setObjectName(u"check_audio_only")

        self.verticalLayout.addWidget(self.check_audio_only)

        self.label = QLabel(self.layoutWidget_7)
        self.label.setObjectName(u"label")

        self.verticalLayout.addWidget(self.label)

        self.label_2 = QLabel(self.layoutWidget_7)
        self.label_2.setObjectName(u"label_2")

        self.verticalLayout.addWidget(self.label_2)

        self.label_3 = QLabel(self.layoutWidget_7)
        self.label_3.setObjectName(u"label_3")

        self.verticalLayout.addWidget(self.label_3)


        self.retranslateUi(Settings)

        QMetaObject.connectSlotsByName(Settings)
    # setupUi

    def retranslateUi(self, Settings):
        Settings.setWindowTitle(QCoreApplication.translate("Settings", u"Settings", None))
        self.save_button.setText(QCoreApplication.translate("Settings", u"Save", None))
        self.close_button.setText(QCoreApplication.translate("Settings", u"Close", None))
        self.pref_vid_quality_label.setText(QCoreApplication.translate("Settings", u"Preferred video quality:", None))
        self.pref_vid_quality_dropdown.setItemText(0, QCoreApplication.translate("Settings", u"144p", None))
        self.pref_vid_quality_dropdown.setItemText(1, QCoreApplication.translate("Settings", u"240p", None))
        self.pref_vid_quality_dropdown.setItemText(2, QCoreApplication.translate("Settings", u"360p", None))
        self.pref_vid_quality_dropdown.setItemText(3, QCoreApplication.translate("Settings", u"480p", None))
        self.pref_vid_quality_dropdown.setItemText(4, QCoreApplication.translate("Settings", u"720p (HD)", None))
        self.pref_vid_quality_dropdown.setItemText(5, QCoreApplication.translate("Settings", u"1080p (Full HD)", None))
        self.pref_vid_quality_dropdown.setItemText(6, QCoreApplication.translate("Settings", u"1440p (2K)", None))
        self.pref_vid_quality_dropdown.setItemText(7, QCoreApplication.translate("Settings", u"2160p (4K)", None))
        self.pref_vid_quality_dropdown.setItemText(8, QCoreApplication.translate("Settings", u"Best available", None))

        self.pref_vid_format.setText(QCoreApplication.translate("Settings", u"Preferred video format:", None))
        self.pref_vid_format_dropdown.setItemText(0, QCoreApplication.translate("Settings", u"Any", None))
        self.pref_vid_format_dropdown.setItemText(1, QCoreApplication.translate("Settings", u"mp4", None))
        self.pref_vid_format_dropdown.setItemText(2, QCoreApplication.translate("Settings", u"webm", None))
        self.pref_vid_format_dropdown.setItemText(3, QCoreApplication.translate("Settings", u"avi", None))
        self.pref_vid_format_dropdown.setItemText(4, QCoreApplication.translate("Settings", u"mov", None))
        self.pref_vid_format_dropdown.setItemText(5, QCoreApplication.translate("Settings", u"mkv", None))
        self.pref_vid_format_dropdown.setItemText(6, QCoreApplication.translate("Settings", u"flv", None))
        self.pref_vid_format_dropdown.setItemText(7, QCoreApplication.translate("Settings", u"3gp", None))

        self.audio_quality_label.setText(QCoreApplication.translate("Settings", u"Preferred audio quality:", None))
        self.pref_aud_quality_dropdown.setItemText(0, QCoreApplication.translate("Settings", u"32 kbps", None))
        self.pref_aud_quality_dropdown.setItemText(1, QCoreApplication.translate("Settings", u"64 kbps", None))
        self.pref_aud_quality_dropdown.setItemText(2, QCoreApplication.translate("Settings", u"128 kbps", None))
        self.pref_aud_quality_dropdown.setItemText(3, QCoreApplication.translate("Settings", u"160 kbps", None))
        self.pref_aud_quality_dropdown.setItemText(4, QCoreApplication.translate("Settings", u"192 kbps", None))
        self.pref_aud_quality_dropdown.setItemText(5, QCoreApplication.translate("Settings", u"256 kbps", None))
        self.pref_aud_quality_dropdown.setItemText(6, QCoreApplication.translate("Settings", u"320 kbps", None))
        self.pref_aud_quality_dropdown.setItemText(7, QCoreApplication.translate("Settings", u"Best available", None))

        self.pref_aud_format.setText(QCoreApplication.translate("Settings", u"Preferred audio format:", None))
        self.pref_aud_format_dropdown.setItemText(0, QCoreApplication.translate("Settings", u"Any", None))
        self.pref_aud_format_dropdown.setItemText(1, QCoreApplication.translate("Settings", u"mp3", None))
        self.pref_aud_format_dropdown.setItemText(2, QCoreApplication.translate("Settings", u"ogg / oga [Vorbis]", None))
        self.pref_aud_format_dropdown.setItemText(3, QCoreApplication.translate("Settings", u"m4a", None))
        self.pref_aud_format_dropdown.setItemText(4, QCoreApplication.translate("Settings", u"aac", None))
        self.pref_aud_format_dropdown.setItemText(5, QCoreApplication.translate("Settings", u"opus", None))
        self.pref_aud_format_dropdown.setItemText(6, QCoreApplication.translate("Settings", u"flac", None))
        self.pref_aud_format_dropdown.setItemText(7, QCoreApplication.translate("Settings", u"wav", None))

        self.proxy_label.setText(QCoreApplication.translate("Settings", u"SOCKS / proxy:", None))
        self.proxy_server_type.setItemText(0, QCoreApplication.translate("Settings", u"None", None))
        self.proxy_server_type.setItemText(1, QCoreApplication.translate("Settings", u"HTTPS", None))
        self.proxy_server_type.setItemText(2, QCoreApplication.translate("Settings", u"SOCKS4", None))
        self.proxy_server_type.setItemText(3, QCoreApplication.translate("Settings", u"SOCKS5", None))

        self.proxy_server_label.setText(QCoreApplication.translate("Settings", u"Server:", None))
        self.proxy_port_label.setText(QCoreApplication.translate("Settings", u"Port:", None))
        self.save_downloads_label.setText(QCoreApplication.translate("Settings", u"Save downloads to:", None))
        self.browse_btn.setText(QCoreApplication.translate("Settings", u"Browse", None))
        self.check_audio_only.setText(QCoreApplication.translate("Settings", u"Only the associated audio tracks", None))
        self.label.setText(QCoreApplication.translate("Settings", u"(Entire videos may be downloaded, then", None))
        self.label_2.setText(QCoreApplication.translate("Settings", u"audio would be extracted and the videos", None))
        self.label_3.setText(QCoreApplication.translate("Settings", u"will be deleted.)", None))
    # retranslateUi

