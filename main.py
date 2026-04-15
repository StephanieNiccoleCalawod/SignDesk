"""
SignDesk - Sign Language to Speech System
Main Application Entry Point
"""

import customtkinter as ctk
from core.theme import apply_theme, C_BG
from modules.auth.ui import LoginPage, RegisterPage, VerificationPage
from modules.dashboard.ui import DashboardPage
from modules.vision.ui import GestureDetectionPage

class SignDeskApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SignDesk")
        self.geometry("950x680")
        self.minsize(950, 680)
        self.resizable(False, False)
        
        # Apply theme globally
        apply_theme()
        
        from core.config import config
        config.load()
        
        self.configure(fg_color=C_BG)

        self.update_idletasks()
        x = (self.winfo_screenwidth()  - 900) // 2
        y = (self.winfo_screenheight() - 650) // 2
        self.geometry(f"900x650+{x}+{y}")

        self._current_page = None
        self._current_user = None
        self.show_login()

    def _clear(self):
        if self._current_page:
            self._current_page.destroy()
            self._current_page = None

    def show_login(self):
        self._clear()
        self.resizable(False, False)
        self._set_size(900, 650)
        self._current_page = LoginPage(self, self)
        self._current_page.pack(fill="both", expand=True)

    def show_register(self):
        self._clear()
        self.resizable(False, False)
        self._set_size(900, 650)
        self._current_page = RegisterPage(self, self)
        self._current_page.pack(fill="both", expand=True)

    def show_verification(self, pending_data: dict):
        """Navigate to the email verification page."""
        self._clear()
        self.resizable(False, False)
        self._set_size(900, 650)
        self._current_page = VerificationPage(self, self, pending_data)
        self._current_page.pack(fill="both", expand=True)

    def show_forgot_password(self):
        """Navigate to the Forgot Password page (Step 1)."""
        self._clear()
        self.resizable(False, False)
        self._set_size(900, 650)
        from modules.auth.forgot_password_window import ForgotPasswordPage
        self._current_page = ForgotPasswordPage(self, self)
        self._current_page.pack(fill="both", expand=True)

    def show_otp_verification(self, email: str):
        """Navigate to the OTP Verification page (Step 2)."""
        self._clear()
        self.resizable(False, False)
        self._set_size(900, 650)
        from modules.auth.otp_verification_window import ForgotPasswordOTPPage
        self._current_page = ForgotPasswordOTPPage(self, self, email)
        self._current_page.pack(fill="both", expand=True)

    def show_reset_password(self, email: str):
        """Navigate to the Reset Password page (Step 3)."""
        self._clear()
        self.resizable(False, False)
        self._set_size(900, 650)
        from modules.auth.reset_password_window import ResetPasswordPage
        self._current_page = ResetPasswordPage(self, self, email)
        self._current_page.pack(fill="both", expand=True)

    def show_settings(self, username: str):
        self._current_user = username
        self._clear()
        self.resizable(True, True)
        self._set_size(950, 680)
        from modules.settings.ui import SettingsPage
        self._current_page = SettingsPage(self, self, username)
        self._current_page.pack(fill="both", expand=True)

    def show_speech_output(self, username: str):
        self._current_user = username
        self._clear()
        self.resizable(True, True)
        self._set_size(950, 680)
        from modules.speech.ui import SpeechOutputPage
        self._current_page = SpeechOutputPage(self, self, username)
        self._current_page.pack(fill="both", expand=True)

    def show_dashboard(self, username: str):
        self._current_user = username
        self._clear()
        self.resizable(True, True)
        self._set_size(950, 680)
        self._current_page = DashboardPage(self, self, username)
        self._current_page.pack(fill="both", expand=True)

    def show_gesture_detection(self, username: str):
        """Navigate to the Gesture Detection page (Module 2)."""
        self._current_user = username
        self._clear()
        self.resizable(True, True)
        self._set_size(950, 680)
        self._current_page = GestureDetectionPage(self, self, username)
        self._current_page.pack(fill="both", expand=True)

    def _set_size(self, width: int, height: int):
        """Resize and re-center the window."""
        x = (self.winfo_screenwidth() - width) // 2
        y = (self.winfo_screenheight() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

if __name__ == "__main__":
    from core.database import update_database_schema
    update_database_schema()
    
    app = SignDeskApp()
    app.mainloop()