"""
forgot_password_window.py - Forgot Password UI
Step 1 of the password reset flow: email input → send OTP.
PyQt6 implementation.
"""

import threading
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor

from core.theme import *
from modules.auth.ui import make_left_panel, _make_entry, _primary_btn, _outline_btn, _set_font
from modules.auth.otp_manager import check_email_exists, create_otp
from modules.auth.password_reset_email import send_password_reset_email


class ForgotPasswordPage(QWidget):
    check_fail_signal = pyqtSignal(str)
    otp_sent_signal = pyqtSignal(bool, str, str)

    def __init__(self, parent_widget, app):
        super().__init__(parent_widget)
        self._app = app
        self.check_fail_signal.connect(self._on_fail)
        self.otp_sent_signal.connect(self._on_result)
        self._build()

    def _build(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(make_left_panel())

        right = QFrame()
        right.setStyleSheet(f"background-color: {C_WHITE};")
        right_layout = QVBoxLayout(right)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form_wrap = QFrame()
        form_wrap.setFixedWidth(380)
        form_wrap.setStyleSheet("background: transparent;")
        form_layout = QVBoxLayout(form_wrap)
        form_layout.setSpacing(6)

        heading = QLabel("Forgot your password?")
        _set_font(heading, size=24, bold=True)
        heading.setStyleSheet(f"color: {C_TEXT_DARK};")

        sub = QLabel("Enter your email and we'll send you a verification code.")
        _set_font(sub, size=12)
        sub.setStyleSheet(f"color: {C_TEXT_MID};")
        sub.setWordWrap(True)

        form_layout.addWidget(heading)
        form_layout.addWidget(sub)
        form_layout.addSpacing(20)

        email_lbl = QLabel("Email Address")
        _set_font(email_lbl, size=10, bold=True)
        email_lbl.setStyleSheet(f"color: {C_TEXT_LIGHT};")
        self._email_entry = _make_entry("Enter your registered email")

        form_layout.addWidget(email_lbl)
        form_layout.addWidget(self._email_entry)

        self._status_label = QLabel("")
        _set_font(self._status_label, size=11)
        self._status_label.setWordWrap(True)
        form_layout.addWidget(self._status_label)

        self._send_btn = _primary_btn("Send Verification Code", self._on_send)
        form_layout.addWidget(self._send_btn)
        form_layout.addSpacing(6)
        form_layout.addWidget(_outline_btn("Back to Login", self._app.show_login))

        right_layout.addWidget(form_wrap)
        main_layout.addWidget(right)

    def _on_send(self):
        email = self._email_entry.text().strip()
        if not email:
            self._status_label.setText("Please enter your email address.")
            self._status_label.setStyleSheet(f"color: {C_WARN};")
            return

        self._send_btn.setEnabled(False)
        self._send_btn.setText("Checking...")
        self._status_label.setText("Verifying email...")
        self._status_label.setStyleSheet(f"color: {C_ACCENT};")

        def bg_task():
            exists, msg = check_email_exists(email)
            if not exists:
                self.check_fail_signal.emit(msg)
                return
            otp_code = create_otp(email)
            email_ok, email_msg = send_password_reset_email(email, otp_code)
            self.otp_sent_signal.emit(email_ok, email_msg, email)

        threading.Thread(target=bg_task, daemon=True).start()

    def _on_fail(self, message: str):
        self._send_btn.setEnabled(True)
        self._send_btn.setText("Send Verification Code")
        self._status_label.setText(message)
        self._status_label.setStyleSheet(f"color: {C_ERROR_RED};")

    def _on_result(self, success: bool, message: str, email: str):
        self._send_btn.setEnabled(True)
        self._send_btn.setText("Send Verification Code")
        if success:
            self._status_label.setText("")
            self._app.show_otp_verification(email)
        else:
            self._status_label.setText(f"Could not send email: {message}")
            self._status_label.setStyleSheet(f"color: {C_ERROR_RED};")
