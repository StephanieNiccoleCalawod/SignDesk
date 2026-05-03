"""
otp_verification_window.py - OTP Verification UI (Password Reset)
Step 2 of the password reset flow: 6-digit OTP entry with auto-advance.
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
from core.email_service import ResendTracker, VerificationAttemptTracker
from core.email_config import OTP_MAX_RESENDS
from modules.auth.ui import make_left_panel, _primary_btn, _outline_btn, _set_font
from modules.auth.otp_manager import create_otp, verify_otp, PASSWORD_RESET_OTP_EXPIRY_MINUTES
from modules.auth.password_reset_email import send_password_reset_email


class ForgotPasswordOTPPage(QWidget):
    verify_signal = pyqtSignal(bool, str)
    resend_signal = pyqtSignal(bool, str)

    def __init__(self, parent_widget, app, email: str):
        super().__init__(parent_widget)
        self._app = app
        self._email = email
        self._resend_tracker = ResendTracker()
        self._resend_tracker.record_resend()
        self._attempt_tracker = VerificationAttemptTracker()

        self.verify_signal.connect(self._on_verify_result)
        self.resend_signal.connect(self._on_resend_complete)

        self._cooldown_timer = QTimer(self)
        self._cooldown_timer.timeout.connect(self._update_cooldown)

        self._build()
        self._start_cooldown_timer()

    def _build(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(make_left_panel())

        right = QFrame()
        right.setStyleSheet(f"background-color: {C_WHITE};")
        right_layout = QVBoxLayout(right)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        fw = QFrame()
        fw.setFixedWidth(420)
        fw.setStyleSheet("background: transparent;")
        fw_layout = QVBoxLayout(fw)
        fw_layout.setSpacing(8)

        heading = QLabel("Verify your identity")
        _set_font(heading, size=24, bold=True)
        heading.setStyleSheet(f"color: {C_TEXT_DARK};")
        fw_layout.addWidget(heading)

        sub = QLabel("We've sent a verification code to:")
        _set_font(sub, size=12)
        sub.setStyleSheet(f"color: {C_TEXT_MID};")
        fw_layout.addWidget(sub)

        email_lbl = QLabel(self._mask_email(self._email))
        _set_font(email_lbl, size=13, bold=True)
        email_lbl.setStyleSheet(f"color: {C_PANEL_LEFT};")
        fw_layout.addWidget(email_lbl)
        fw_layout.addSpacing(12)

        # OTP Card
        otp_card = QFrame()
        otp_card.setStyleSheet(
            f"background-color: {C_INPUT_BG}; border: 1px solid {C_CARD_BORDER}; border-radius: 10px;"
        )
        otp_layout = QVBoxLayout(otp_card)
        otp_layout.setContentsMargins(24, 20, 24, 20)

        code_lbl = QLabel("Enter the 6-digit verification code")
        _set_font(code_lbl, size=11, bold=True)
        code_lbl.setStyleSheet(f"color: {C_TEXT_MID}; border: none;")
        code_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        otp_layout.addWidget(code_lbl)

        # 6 individual digit boxes
        boxes_row = QWidget()
        boxes_row.setStyleSheet("background: transparent;")
        boxes_row.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        boxes_layout = QHBoxLayout(boxes_row)
        boxes_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        boxes_layout.setSpacing(8)

        self._otp_boxes = []
        for i in range(6):
            box = QLineEdit()
            box.setFixedSize(48, 56)
            box.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            box.setMaxLength(1)
            box.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {C_WHITE};
                    border: 1px solid {C_INPUT_BORDER};
                    border-radius: 8px;
                    font-family: 'Courier New';
                    font-size: 24px;
                    font-weight: bold;
                    color: {C_PANEL_LEFT};
                }}
                QLineEdit:focus {{
                    border: 1px solid {C_INPUT_FOCUS};
                }}
            """)
            box.textChanged.connect(lambda text, idx=i: self._on_box_changed(text, idx))
            box.keyPressEvent = lambda event, idx=i, orig=box.keyPressEvent: self._on_key_press(event, idx, orig)
            boxes_layout.addWidget(box)
            self._otp_boxes.append(box)

        otp_layout.addWidget(boxes_row)

        exp_lbl = QLabel(f"Code expires in {PASSWORD_RESET_OTP_EXPIRY_MINUTES} minutes")
        _set_font(exp_lbl, size=10)
        exp_lbl.setStyleSheet(f"color: {C_TEXT_LIGHT}; border: none;")
        exp_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        otp_layout.addWidget(exp_lbl)

        fw_layout.addWidget(otp_card)

        self._status_label = QLabel("")
        _set_font(self._status_label, size=11)
        self._status_label.setWordWrap(True)
        fw_layout.addWidget(self._status_label)

        self._verify_btn = _primary_btn("Verify Code", self._on_verify)
        fw_layout.addWidget(self._verify_btn)

        # Resend row
        resend_row = QWidget()
        resend_row.setStyleSheet("background: transparent;")
        resend_row.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        resend_layout = QHBoxLayout(resend_row)
        resend_layout.setContentsMargins(0, 0, 0, 0)

        resend_lbl = QLabel("Didn't receive the code?")
        resend_lbl.setStyleSheet(f"color: {C_TEXT_LIGHT};")
        self._resend_btn = QPushButton("Resend Code")
        self._resend_btn.setStyleSheet(
            f"color: {C_ACCENT}; font-weight: bold; border: none; background: transparent;"
        )
        self._resend_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._resend_btn.clicked.connect(self._on_resend)
        self._resend_btn.setEnabled(False)

        self._cooldown_label = QLabel("")
        self._cooldown_label.setStyleSheet(f"color: {C_TEXT_LIGHT};")

        resend_layout.addWidget(resend_lbl)
        resend_layout.addWidget(self._resend_btn)
        resend_layout.addWidget(self._cooldown_label)
        resend_layout.addStretch()
        fw_layout.addWidget(resend_row)

        fw_layout.addSpacing(6)
        fw_layout.addWidget(_outline_btn("Back", self._on_back))

        right_layout.addWidget(fw)
        main_layout.addWidget(right)

    # ── OTP box logic ──────────────────────────────────────

    def _on_box_changed(self, text, index):
        if text and text[-1].isdigit():
            if index < 5:
                self._otp_boxes[index + 1].setFocus()
        elif text:
            self._otp_boxes[index].clear()

    def _on_key_press(self, event, index, original_handler):
        from PyQt6.QtCore import Qt as _Qt
        if event.key() == _Qt.Key.Key_Backspace and not self._otp_boxes[index].text():
            if index > 0:
                self._otp_boxes[index - 1].setFocus()
                self._otp_boxes[index - 1].clear()
        else:
            original_handler(event)

    def _get_otp_code(self) -> str:
        return "".join(box.text().strip() for box in self._otp_boxes)

    def _clear_otp_boxes(self):
        for box in self._otp_boxes:
            box.clear()
        self._otp_boxes[0].setFocus()

    def _mask_email(self, email: str) -> str:
        try:
            local, domain = email.split("@")
            masked = local[0] + "***" + (local[-1] if len(local) > 2 else "")
            return f"{masked}@{domain}"
        except Exception:
            return email

    # ── Verify flow ────────────────────────────────────────

    def _on_verify(self):
        code = self._get_otp_code()
        if len(code) != 6 or not code.isdigit():
            self._status_label.setText("Please enter all 6 digits.")
            self._status_label.setStyleSheet(f"color: {C_WARN};")
            return

        can_try, reason = self._attempt_tracker.can_attempt()
        if not can_try:
            self._status_label.setText(reason)
            self._status_label.setStyleSheet(f"color: {C_ERROR_RED};")
            self._verify_btn.setEnabled(False)
            return

        self._verify_btn.setEnabled(False)
        self._verify_btn.setText("Verifying...")
        self._status_label.setText("Verifying code...")
        self._status_label.setStyleSheet(f"color: {C_ACCENT};")

        def run_verify():
            ok, msg = verify_otp(self._email, code)
            self.verify_signal.emit(ok, msg)

        threading.Thread(target=run_verify, daemon=True).start()

    def _on_verify_result(self, success: bool, msg: str):
        if success:
            self._status_label.setText("Code verified!")
            self._status_label.setStyleSheet(f"color: {C_SUCCESS};")
            self._app.show_reset_password(self._email)
        else:
            self._verify_btn.setEnabled(True)
            self._verify_btn.setText("Verify Code")
            self._attempt_tracker.record_attempt()
            remaining = self._attempt_tracker.attempts_remaining
            self._status_label.setText(f"{msg} ({remaining} attempts left)")
            self._status_label.setStyleSheet(f"color: {C_ERROR_RED};")
            self._clear_otp_boxes()

    # ── Resend flow ────────────────────────────────────────

    def _on_resend(self):
        can_resend, reason = self._resend_tracker.can_resend()
        if not can_resend:
            self._status_label.setText(reason)
            self._status_label.setStyleSheet(f"color: {C_WARN};")
            return

        self._resend_btn.setEnabled(False)
        self._status_label.setText("Sending new code...")
        self._status_label.setStyleSheet(f"color: {C_ACCENT};")

        def resend_task():
            otp_code = create_otp(self._email)
            email_ok, email_msg = send_password_reset_email(self._email, otp_code)
            self.resend_signal.emit(email_ok, email_msg)

        threading.Thread(target=resend_task, daemon=True).start()

    def _on_resend_complete(self, success: bool, message: str):
        if success:
            self._resend_tracker.record_resend()
            count = self._resend_tracker.resend_count
            self._status_label.setText(f"New code sent! ({count}/{OTP_MAX_RESENDS} resends used)")
            self._status_label.setStyleSheet(f"color: {C_SUCCESS};")
            self._clear_otp_boxes()
            self._start_cooldown_timer()
        else:
            self._status_label.setText(message)
            self._status_label.setStyleSheet(f"color: {C_ERROR_RED};")
            self._resend_btn.setEnabled(True)

    # ── Cooldown timer ─────────────────────────────────────

    def _start_cooldown_timer(self):
        self._resend_btn.setEnabled(False)
        self._update_cooldown()

    def _update_cooldown(self):
        remaining = self._resend_tracker.cooldown_remaining
        if remaining > 0:
            self._cooldown_label.setText(f"({remaining}s)")
            self._resend_btn.setEnabled(False)
            self._cooldown_timer.start(1000)
        else:
            self._cooldown_timer.stop()
            self._cooldown_label.setText("")
            can_resend, _ = self._resend_tracker.can_resend()
            if can_resend:
                self._resend_btn.setEnabled(True)
            else:
                if self._resend_tracker.resend_count >= OTP_MAX_RESENDS:
                    self._resend_btn.setEnabled(False)
                    self._cooldown_label.setText("(limit reached)")

    # ── Navigation ─────────────────────────────────────────

    def _on_back(self):
        self._cooldown_timer.stop()
        self._app.show_forgot_password()
