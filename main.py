"""
SignDesk - Sign Language to Speech System
Main Application Entry Point
PyQt6 migration
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt

from core.theme import build_qss, c
from modules.auth.ui import LoginPage, RegisterPage, VerificationPage
from modules.dashboard.ui import DashboardPage
from modules.vision.ui import GestureDetectionPage

class SignDeskApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SignDesk")
        
        # Central widget to hold pages
        self._central_widget = QWidget()
        self._layout = QVBoxLayout(self._central_widget)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(self._central_widget)
        
        from modules.settings.account_backend import init_account_db
        init_account_db()

        self._current_page = None
        self._current_user = None
        self._current_user_id = None
        self.show_login()

    def _clear(self):
        if self._current_page:
            self._layout.removeWidget(self._current_page)
            self._current_page.deleteLater()
            self._current_page = None

    def _set_size(self, width: int, height: int, resizable: bool = True):
        """Resize and re-center the window."""
        if resizable:
            self.setMinimumSize(width, height)
            self.setMaximumSize(16777215, 16777215)
            self.resize(width, height)
        else:
            self.setMinimumSize(width, height)
            self.setMaximumSize(16777215, 16777215)
            self.resize(width, height)

        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - width) // 2
        y = (screen.height() - height) // 2
        self.setGeometry(x, y, width, height)

    def show_login(self):
        if self._current_user:
            from core.audit_log import log_event
            log_event("LOGOUT", self._current_user)
        self._current_user = None
        self._current_user_id = None
        self._clear()
        self._set_size(900, 650, resizable=False)
        self._current_page = LoginPage(self._central_widget, self)
        self._layout.addWidget(self._current_page)

    def show_register(self):
        self._clear()
        self._set_size(900, 650, resizable=False)
        self._current_page = RegisterPage(self._central_widget, self)
        self._layout.addWidget(self._current_page)

    def show_verification(self, pending_data: dict):
        """Navigate to the email verification page."""
        self._clear()
        self._set_size(900, 650, resizable=False)
        self._current_page = VerificationPage(self._central_widget, self, pending_data)
        self._layout.addWidget(self._current_page)

    def show_forgot_password(self):
        """Navigate to the Forgot Password page (Step 1)."""
        self._clear()
        self._set_size(900, 650, resizable=False)
        from modules.auth.forgot_password_window import ForgotPasswordPage
        self._current_page = ForgotPasswordPage(self._central_widget, self)
        self._layout.addWidget(self._current_page)

    def show_otp_verification(self, email: str):
        """Navigate to the OTP Verification page (Step 2)."""
        self._clear()
        self._set_size(900, 650, resizable=False)
        from modules.auth.otp_verification_window import ForgotPasswordOTPPage
        self._current_page = ForgotPasswordOTPPage(self._central_widget, self, email)
        self._layout.addWidget(self._current_page)

    def show_reset_password(self, email: str):
        """Navigate to the Reset Password page (Step 3)."""
        self._clear()
        self._set_size(900, 650, resizable=False)
        from modules.auth.reset_password_window import ResetPasswordPage
        self._current_page = ResetPasswordPage(self._central_widget, self, email)
        self._layout.addWidget(self._current_page)

    def show_settings(self, username: str):
        self._current_user = username
        self._resolve_user_id(username)
        self._clear()
        self._set_size(950, 680, resizable=True)
        from modules.settings.ui import SettingsPage
        self._current_page = SettingsPage(self._central_widget, self, username)
        self._layout.addWidget(self._current_page)

    def show_dashboard(self, username: str):
        self._current_user = username
        self._resolve_user_id(username)
        self._clear()
        self._set_size(950, 680, resizable=True)
        self._current_page = DashboardPage(self._central_widget, self, username)
        self._layout.addWidget(self._current_page)

    @property
    def current_user_id(self) -> int | None:
        """Returns the database user_id for the currently logged-in user."""
        return self._current_user_id

    def _resolve_user_id(self, username: str):
        """Resolves user_id from the database. Always performs a fresh lookup."""
        try:
            from modules.settings.account_backend import get_user_by_username
            user = get_user_by_username(username)
            self._current_user_id = user["id"] if user else None
        except Exception:
            self._current_user_id = None

    def show_gesture_detection(self, username: str):
        """Navigate to the Gesture Detection page (Module 2)."""
        self._current_user = username
        self._resolve_user_id(username)
        self._clear()
        self._set_size(950, 680, resizable=True)
        self._current_page = GestureDetectionPage(self._central_widget, self, username)
        self._layout.addWidget(self._current_page)

    def show_gesture_history(self, username: str):
        self._current_user = username
        self._resolve_user_id(username)
        self._clear()
        self._set_size(950, 680, resizable=True)
        from modules.gesture_history.page import GestureHistoryPage
        self._current_page = GestureHistoryPage(self._central_widget, self, username)
        self._layout.addWidget(self._current_page)

    def show_gesture_log_viewer(self, username: str):
        self._current_user = username
        self._resolve_user_id(username)
        self._clear()
        self._set_size(950, 680, resizable=True)
        from modules.gesture_history.log_viewer import GestureLogViewerPage
        self._current_page = GestureLogViewerPage(self._central_widget, self, username)
        self._layout.addWidget(self._current_page)

def _resolve_dark_mode(theme_value: str) -> bool:
    """Determine whether dark mode should be active based on the saved theme preference."""
    if theme_value == "dark" or theme_value == "high-contrast":
        return True
    if theme_value == "system":
        try:
            import platform
            if platform.system() == "Windows":
                import winreg
                reg_key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                val, _ = winreg.QueryValueEx(reg_key, "AppsUseLightTheme")
                return val == 0
        except Exception:
            pass
        return False
    return False  # "light" or unknown


if __name__ == "__main__":
    from core.database import update_database_schema
    update_database_schema()
    
    app = QApplication(sys.argv)
    
    # Load config BEFORE building QSS so saved theme preference is respected
    from core.config import config
    config.load()

    from core.theme import set_dark_mode
    dark = _resolve_dark_mode(config.get("appearance.theme", "system"))
    set_dark_mode(dark)
    app.setStyleSheet(build_qss(dark=dark))
    
    window = SignDeskApp()
    window.show()
    sys.exit(app.exec())