import http.cookiejar
import time
import os

from PySide6.QtWidgets import QMainWindow, QDialog, QDialogButtonBox, QVBoxLayout, QLabel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtCore import QUrl, QDateTime, QTimer, QDateTime
from PySide6.QtNetwork import QNetworkCookie
from PySide6.QtCore import Signal

from .settings_manager import SettingsManager

URL_LOGIN = "https://accounts.google.com/ServiceLogin?service=youtube"
URL_YOUTUBE = "https://www.youtube.com/"


class CustomDialog(QDialog):
    def __init__(self, title, message):
        super().__init__()
        self.setWindowTitle(title)
        QBtn = QDialogButtonBox.Ok
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.layout = QVBoxLayout()
        dlg_message = QLabel(message)
        self.layout.addWidget(dlg_message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


class YoutubeLoginDialog(QMainWindow):
    logged_in_signal = Signal()

    def __init__(self, cookie_jar_path):
        super().__init__()
        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)

        self.settings_manager = SettingsManager()
        self.cookie_jar_path = cookie_jar_path
        self.cookie_jar = http.cookiejar.MozillaCookieJar(self.cookie_jar_path)
        
        self.cookies_loaded = False
        self.logged_in = False
        self.cookie_expirations = {}

        self.profile = QWebEngineProfile.defaultProfile()
        self.cookie_store = self.profile.cookieStore()

        self.load_cookies()

        if self.cookies_loaded:
            self.logged_in = True
            self.logged_in_signal.emit()
            self.browser.load(QUrl(URL_YOUTUBE))
        else:
            self.browser.load(QUrl(URL_LOGIN))

        self.cookie_store.cookieAdded.connect(self.process_cookie)

        QTimer.singleShot(60000, self.check_cookie_expiry)

    def process_cookie(self, cookie):
        py_cookie = http.cookiejar.Cookie(
            version=0,
            name=cookie.name().data().decode('utf-8'),
            value=cookie.value().data().decode('utf-8'),
            port=None,
            port_specified=False,
            domain=cookie.domain(),
            domain_specified=bool(cookie.domain()),
            domain_initial_dot=cookie.domain().startswith('.'),
            path=cookie.path(),
            path_specified=bool(cookie.path()),
            secure=cookie.isSecure(),
            expires=cookie.expirationDate().toSecsSinceEpoch() if cookie.expirationDate().isValid() else None,
            discard=False,
            comment=None,
            comment_url=None,
            rest={},
            rfc2109=False
        )
        self.cookie_jar.set_cookie(py_cookie)
        self.cookie_jar.save(ignore_discard=True)

        if py_cookie.expires:
            self.cookie_expirations[py_cookie.name] = py_cookie.expires

        if cookie.name().data().decode('utf-8') in ["SID", "HSID", "SSID"]:
            self.logged_in = True
            QTimer.singleShot(2000, self.emit_logged_in_signal)

    def load_cookies(self):
        try:
            self.cookie_jar.load(ignore_discard=True)
            logged_in_cookies = ["SID", "HSID", "SSID"]
            found_logged_in_cookies = set()

            for cookie in self.cookie_jar:
                q_cookie = QNetworkCookie(
                    cookie.name.encode('utf-8'),
                    cookie.value.encode('utf-8')
                )
                q_cookie.setDomain(cookie.domain)
                q_cookie.setPath(cookie.path)
                q_cookie.setSecure(cookie.secure)
                if cookie.expires:
                    q_cookie.setExpirationDate(QDateTime.fromSecsSinceEpoch(cookie.expires))
                    self.cookie_expirations[cookie.name] = cookie.expires

                QWebEngineProfile.defaultProfile().cookieStore().setCookie(
                    q_cookie)
                # Check if the loaded cookie is one of the logged-in cookies
                if cookie.name in logged_in_cookies:
                    found_logged_in_cookies.add(cookie.name)

            # Set cookies_loaded to True only if all logged-in cookies are found
            self.cookies_loaded = all(cookie in found_logged_in_cookies
                                      for cookie in logged_in_cookies)
            self.logged_in = self.cookies_loaded
        except FileNotFoundError:
            pass

    def clear_cookies(self):
        self.cookie_jar.clear()
        self.cookie_jar.save(ignore_discard=True)
        self.cookies_loaded = False
        self.profile = self.browser.page().profile()
        self.profile.cookieStore().deleteAllCookies()

    def logout(self):
        self.clear_cookies()
        self.profile.clearHttpCache()
        self.browser.page().triggerAction(QWebEnginePage.ReloadAndBypassCache)
        self.browser.load(QUrl("https://accounts.google.com/signin"))
        self.logged_in = False

    def check_cookie_expiry(self):
        current_time = time.time()
        for cookie_name, expiry in list(self.cookie_expirations.items()):
            if expiry < current_time:
                self.load_cookies()
                break
        QTimer.singleShot(60000, self.check_cookie_expiry)

    def emit_logged_in_signal(self):
        if self.logged_in:
            self.logged_in_signal.emit()
            self.close()

    def close_window(self):
        if self.logged_in:
            self.close()
