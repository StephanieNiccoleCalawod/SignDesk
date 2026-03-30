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
        self.geometry("960x620")
        self.resizable(False, False)
        
        # Apply theme globally
        apply_theme()
        self.configure(fg_color=C_BG)

        self.update_idletasks()
        x = (self.winfo_screenwidth()  - 960) // 2
        y = (self.winfo_screenheight() - 620) // 2
        self.geometry(f"960x620+{x}+{y}")

        self._current_page = None
        self._current_user = None
        self.show_login()

    def _clear(self):
        if self._current_page:
            self._current_page.destroy()
            self._current_page = None

    def show_login(self):
        self._clear()
        self._set_size(960, 620)
        self._current_page = LoginPage(self, self)
        self._current_page.pack(fill="both", expand=True)

    def show_register(self):
        self._clear()
        self._set_size(960, 620)
        self._current_page = RegisterPage(self, self)
        self._current_page.pack(fill="both", expand=True)

    def show_verification(self, pending_data: dict):
        """Navigate to the email verification page."""
        self._clear()
        self._set_size(960, 620)
        self._current_page = VerificationPage(self, self, pending_data)
        self._current_page.pack(fill="both", expand=True)

    def show_dashboard(self, username: str):
        self._current_user = username
        self._clear()
        self._set_size(960, 620)
        self._current_page = DashboardPage(self, self, username)
        self._current_page.pack(fill="both", expand=True)

    def show_gesture_detection(self, username: str):
        """Navigate to the Gesture Detection page (Module 2)."""
        self._current_user = username
        self._clear()
        self._set_size(1200, 720)
        self._current_page = GestureDetectionPage(self, self, username)
        self._current_page.pack(fill="both", expand=True)

    def _set_size(self, width: int, height: int):
        """Resize and re-center the window."""
        x = (self.winfo_screenwidth() - width) // 2
        y = (self.winfo_screenheight() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

if __name__ == "__main__":
    app = SignDeskApp()
    app.mainloop()