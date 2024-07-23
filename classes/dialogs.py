import http.cookiejar
import time

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QLabel
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, QDateTime, QTimer, QDateTime
from PyQt6.QtNetwork import QNetworkCookie
from PyQt6.QtWebEngineCore import QWebEngineProfile

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
    def __init__(self):
        super().__init__()
        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)
        self.cookie_jar = http.cookiejar.MozillaCookieJar('youtube_cookies.txt')
        self.cookies_loaded = False
        self.logged_in = False
        self.cookie_expirations = {}

        self.load_cookies()

        # Load the appropriate URL based on whether cookies are loaded
        if self.cookies_loaded:
            self.browser.load(QUrl(URL_YOUTUBE))
        else:
            self.browser.load(QUrl(URL_LOGIN))

        self.browser.page().profile().cookieStore().cookieAdded.connect(self.process_cookie)

        # Check cookies after some time delay to ensure they are set properly
        QTimer.singleShot(10000, self.check_cookies)
        # Periodically check cookie expiry
        QTimer.singleShot(60000, self.check_cookie_expiry)  # Check every minute

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

        # Store the expiration time for tracking
        if py_cookie.expires:
            self.cookie_expirations[py_cookie.name] = py_cookie.expires

        # Check if the user is logged in by detecting specific cookies
        if cookie.name().data().decode('utf-8') in ["SID", "HSID", "SSID"]:
            self.logged_in = True
            QTimer.singleShot(2000, self.close_window)  # Close window after 2 seconds

    def load_cookies(self):
        try:
            self.cookie_jar.load(ignore_discard=True)
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

                QWebEngineProfile.defaultProfile().cookieStore().\
                    setCookie(q_cookie)
                self.cookies_loaded = True
                print("Loaded cookie:", q_cookie.name().data().decode('utf-8'))
        except FileNotFoundError:
            print("No cookies file found. Starting fresh.")

    def check_cookies(self):
        # Debug method to print all cookies
        self.browser.page().profile().cookieStore().cookieAdded.\
            connect(self.debug_print_cookie)

    def debug_print_cookie(self, cookie):
        print("Cookie Name:", cookie.name().data().decode('utf-8'))
        print("Cookie Value:", cookie.value().data().decode('utf-8'))
        print("Domain:", cookie.domain())
        print("Path:", cookie.path())
        print("Expires:", cookie.expirationDate().toString())
        print("Is Secure:", cookie.isSecure())

    def check_cookie_expiry(self):
        current_time = time.time()
        for cookie_name, expiry in list(self.cookie_expirations.items()):
            if expiry < current_time:
                print(f"Cookie {cookie_name} has expired, reloading cookies.")
                self.load_cookies()
                break
        # Recheck the expiry in another minute
        QTimer.singleShot(60000, self.check_cookie_expiry)

    def close_window(self):
        if self.logged_in:
            self.close()
