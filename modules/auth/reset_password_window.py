

import re
import threading
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QScrollArea, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor

from core.theme import *
from modules.auth.ui import make_left_panel, _primary_btn, _set_font
from modules.auth.service import validate_password
from modules.auth.otp_manager import update_password


PASSWORD_RULES = [
    ("length",    "At least 8 characters",              lambda p: len(p) >= 8),
    ("upper",     "At least 1 uppercase letter (A-Z)",  lambda p: bool(re.search(r"[A-Z]", p))),
    ("lower",     "At least 1 lowercase letter (a-z)",  lambda p: bool(re.search(r"[a-z]", p))),
    ("digit",     "At least 1 number (0-9)",            lambda p: bool(re.search(r"[0-9]", p))),
    ("special",   "At least 1 special character",       lambda p: bool(re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", p))),
]


class ResetPasswordPage(QWidget):
    update_signal = pyqtSignal(bool, str)

    def __init__(self, parent_widget, app, email: str):
        super().__init__(parent_widget)
        self._app = app
        self._email = email
        self.update_signal.connect(self._on_result)
        self._build()

    def _make_password_field(self, placeholder):
        wrap = QFrame()
        wrap.setStyleSheet(
            f"background-color: {C_INPUT_BG}; border: 1px solid {C_INPUT_BORDER}; border-radius: 8px;"
        )
        layout = QHBoxLayout(wrap)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(0)

        entry = QLineEdit()
        entry.setPlaceholderText(placeholder)
        entry.setEchoMode(QLineEdit.EchoMode.Password)
        entry.setStyleSheet("border: none; background: transparent; font-size: 14px; padding: 0 6px;")
        entry.setFixedHeight(40)

        toggle_btn = QPushButton("Show")
        toggle_btn.setFixedSize(48, 32)
        toggle_btn.setStyleSheet(
            f"border: none; background: transparent; color: {C_TEXT_LIGHT}; font-size: 11px; font-weight: bold;"
        )
        toggle_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        def toggle():
            if entry.echoMode() == QLineEdit.EchoMode.Password:
                entry.setEchoMode(QLineEdit.EchoMode.Normal)
                toggle_btn.setText("Hide")
            else:
                entry.setEchoMode(QLineEdit.EchoMode.Password)
                toggle_btn.setText("Show")

        toggle_btn.clicked.connect(toggle)
        layout.addWidget(entry)
        layout.addWidget(toggle_btn)
        return wrap, entry

    def _build(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(make_left_panel())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: white;")

        content = QWidget()
        content.setStyleSheet(f"background-color: {C_WHITE};")
        content_layout = QVBoxLayout(content)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        content_layout.setContentsMargins(60, 40, 60, 40)

        form_wrap = QFrame()
        form_wrap.setFixedWidth(400)
        form_wrap.setStyleSheet("background: transparent;")
        form_layout = QVBoxLayout(form_wrap)
        form_layout.setSpacing(6)

        heading = QLabel("Create new password")
        _set_font(heading, size=24, bold=True)
        heading.setStyleSheet(f"color: {C_TEXT_DARK};")
        form_layout.addWidget(heading)

        sub = QLabel("Your new password must meet the requirements below.")
        _set_font(sub, size=12)
        sub.setStyleSheet(f"color: {C_TEXT_MID};")
        sub.setWordWrap(True)
        form_layout.addWidget(sub)
        form_layout.addSpacing(16)

        # New password
        new_lbl = QLabel("New Password")
        _set_font(new_lbl, size=10, bold=True)
        new_lbl.setStyleSheet(f"color: {C_TEXT_LIGHT};")
        form_layout.addWidget(new_lbl)

        pw_wrap, self._pass_entry = self._make_password_field("Min. 8 characters")
        form_layout.addWidget(pw_wrap)
        self._pass_entry.textChanged.connect(self._on_password_type)

        # Strength bar
        self._strength_bar = QProgressBar()
        self._strength_bar.setFixedHeight(6)
        self._strength_bar.setRange(0, 5)
        self._strength_bar.setValue(0)
        self._strength_bar.setTextVisible(False)
        self._strength_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {C_INPUT_BORDER};
                border-radius: 3px;
                border: none;
            }}
            QProgressBar::chunk {{
                border-radius: 3px;
                background-color: {C_TEXT_LIGHT};
            }}
        """)
        form_layout.addWidget(self._strength_bar)

        self._strength_label = QLabel("")
        _set_font(self._strength_label, size=10)
        self._strength_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.addWidget(self._strength_label)

        # Requirements box
        req_box = QFrame()
        req_box.setStyleSheet(
            f"background-color: #F8FAFF; border: 1px solid {C_INPUT_BORDER}; border-radius: 8px;"
        )
        req_layout = QVBoxLayout(req_box)
        req_layout.setContentsMargins(14, 10, 14, 10)
        req_layout.setSpacing(4)

        req_title = QLabel("Password must contain:")
        _set_font(req_title, size=10, bold=True)
        req_title.setStyleSheet(f"color: {C_TEXT_MID}; border: none;")
        req_layout.addWidget(req_title)

        self._req_labels = {}
        for key, text, _ in PASSWORD_RULES:
            row = QWidget()
            row.setStyleSheet("background: transparent;")
            row.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            icon = QLabel("-")
            icon.setFixedWidth(14)
            icon.setStyleSheet(f"color: {C_TEXT_LIGHT}; border: none; font-size: 11px;")

            text_lbl = QLabel(text)
            _set_font(text_lbl, size=11)
            text_lbl.setStyleSheet(f"color: {C_TEXT_LIGHT}; border: none;")

            row_layout.addWidget(icon)
            row_layout.addWidget(text_lbl)
            row_layout.addStretch()
            req_layout.addWidget(row)
            self._req_labels[key] = (icon, text_lbl)

        form_layout.addWidget(req_box)
        form_layout.addSpacing(8)

        # Confirm password
        cf_lbl = QLabel("Confirm Password")
        _set_font(cf_lbl, size=10, bold=True)
        cf_lbl.setStyleSheet(f"color: {C_TEXT_LIGHT};")
        form_layout.addWidget(cf_lbl)

        cf_wrap, self._confirm_entry = self._make_password_field("Repeat your new password")
        form_layout.addWidget(cf_wrap)

        self._status_label = QLabel("")
        _set_font(self._status_label, size=11)
        self._status_label.setWordWrap(True)
        form_layout.addWidget(self._status_label)

        self._update_btn = _primary_btn("Update Password", self._on_update)
        form_layout.addWidget(self._update_btn)

        content_layout.addWidget(form_wrap)
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _on_password_type(self):
        password = self._pass_entry.text()
        passed = 0
        for key, _, rule_fn in PASSWORD_RULES:
            icon_lbl, text_lbl = self._req_labels[key]
            if rule_fn(password):
                icon_lbl.setText("✓")
                icon_lbl.setStyleSheet(f"color: {C_SUCCESS}; border: none; font-size: 11px;")
                text_lbl.setStyleSheet(f"color: {C_SUCCESS}; border: none;")
                passed += 1
            else:
                icon_lbl.setText("-")
                icon_lbl.setStyleSheet(f"color: {C_TEXT_LIGHT}; border: none; font-size: 11px;")
                text_lbl.setStyleSheet(f"color: {C_TEXT_LIGHT}; border: none;")

        self._strength_bar.setValue(passed)

        colors = {0: C_TEXT_LIGHT, 1: C_ERROR_RED, 2: C_ERROR_RED, 3: C_WARN, 4: C_ACCENT, 5: C_SUCCESS}
        labels = {0: "", 1: "Weak", 2: "Weak", 3: "Fair", 4: "Good", 5: "Strong"}
        color = colors.get(passed, C_TEXT_LIGHT)
        label = labels.get(passed, "")

        self._strength_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {C_INPUT_BORDER};
                border-radius: 3px;
                border: none;
            }}
            QProgressBar::chunk {{
                border-radius: 3px;
                background-color: {color};
            }}
        """)
        self._strength_label.setText(label)
        self._strength_label.setStyleSheet(f"color: {color};")

    def _on_update(self):
        password = self._pass_entry.text().strip()
        confirm = self._confirm_entry.text().strip()

        if not password or not confirm:
            self._status_label.setText("Please fill in both password fields.")
            self._status_label.setStyleSheet(f"color: {C_WARN};")
            return

        errors = validate_password(password)
        if errors:
            self._status_label.setText("Password does not meet all requirements.")
            self._status_label.setStyleSheet(f"color: {C_ERROR_RED};")
            return

        if password != confirm:
            self._status_label.setText("Passwords do not match.")
            self._status_label.setStyleSheet(f"color: {C_ERROR_RED};")
            return

        self._update_btn.setEnabled(False)
        self._update_btn.setText("Updating...")
        self._status_label.setText("Updating your password...")
        self._status_label.setStyleSheet(f"color: {C_ACCENT};")

        def bg_task():
            ok, msg = update_password(self._email, password)
            self.update_signal.emit(ok, msg)

        threading.Thread(target=bg_task, daemon=True).start()

    def _on_result(self, success: bool, msg: str):
        if success:
            self._status_label.setText("")
            try:
                from core.database import get_connection
                with get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT username FROM users WHERE email = ?", (self._email,))
                    row = cursor.fetchone()
                username_hint = row[0] if row else None
            except Exception:
                username_hint = None

            detail = f"\n\nSign in with your username: {username_hint}" if username_hint else ""
            QMessageBox.information(self, "Password Updated",
                f"Your password has been updated successfully.{detail}")
            self._app.show_login()
        else:
            self._update_btn.setEnabled(True)
            self._update_btn.setText("Update Password")
            self._status_label.setText(msg)
            self._status_label.setStyleSheet(f"color: {C_ERROR_RED};")
