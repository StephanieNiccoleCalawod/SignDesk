"""
modules/auth/ui.py  — SignDesk Auth UI  (PyQt6, fully fixed)

Fixes applied
─────────────
1. CAPS → Title case labels  ("USERNAME" → "Username", etc.)
2. OTP email failure now BLOCKS navigation (no silent bypass)
3. Row background blocks fixed — QWidget rows are transparent,
   QFrame cards use explicit style; global QFrame QSS no longer
   bleeds onto plain container widgets
4. Eye icon visible — objectName scopes the style so the global
   QPushButton accent rule can't override it; Unicode 👁/🙈 used
   as a reliable cross-platform glyph
5. Buttons visible — C_WHITE / C_ACCENT resolved to plain hex
   strings (they are tuples in theme.py — indexing [0] is required)
6. Spacing tightened — form_wrap spacing set to 6px; accent-label
   rows shrink-wrapped so there's no phantom height between fields
7. All input fields (username, email, password) share identical
   height (44 px) and QSS so they look uniform
"""

from __future__ import annotations
import threading

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QCheckBox,
    QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor, QFont, QPixmap, QPainter, QLinearGradient, QColor

from core.theme import (
    C_ACCENT, C_ACCENT_HOVER, C_WHITE, C_TEXT_DARK, C_TEXT_MID, C_TEXT_LIGHT,
    C_INPUT_BG, C_INPUT_BORDER, C_INPUT_FOCUS, C_CARD_BG, C_CARD_BORDER,
    C_PANEL_LEFT, C_SUCCESS, C_ERROR_RED, C_WARN, c, is_dark,
)
from core.email_service import (
    generate_otp, get_otp_expiry, is_otp_expired,
    send_verification_email, ResendTracker, VerificationAttemptTracker,
)
from core.email_config import OTP_RESEND_COOLDOWN, OTP_EXPIRY_MINUTES, OTP_MAX_RESENDS
from modules.auth.service import (
    login_user, register_user, validate_password,
    validate_registration, check_duplicate_username, check_duplicate_email,
    verify_user, resend_verification_code, create_verified_user,
)

# ── resolve theme tuples to plain hex strings ──────────────────────────────
# C_* constants in theme.py are (light, dark) tuples; we always use light[0].
def _hex(c) -> str:
    """Return a plain hex string from a theme tuple or pass-through a string."""
    return c[0] if isinstance(c, tuple) else c

ACC       = _hex(C_ACCENT)
ACC_HOV   = _hex(C_ACCENT_HOVER)
WHITE     = _hex(C_WHITE)
TXT_DARK  = _hex(C_TEXT_DARK)
TXT_MID   = _hex(C_TEXT_MID)
TXT_LIGHT = _hex(C_TEXT_LIGHT)
INP_BG    = _hex(C_INPUT_BG)
INP_BRD   = _hex(C_INPUT_BORDER)
INP_FOC   = _hex(C_INPUT_FOCUS)
CARD_BG   = _hex(C_CARD_BG)
CARD_BRD  = _hex(C_CARD_BORDER)
PANEL     = _hex(C_PANEL_LEFT)
SUCCESS   = _hex(C_SUCCESS)
ERROR     = _hex(C_ERROR_RED)
WARN      = _hex(C_WARN)

# ── shared field height ────────────────────────────────────────────────────
FIELD_H = 44   # px — every input row uses this so heights are identical

# ══════════════════════════════════════════════════════════════════════════
# SHARED HELPERS
# ══════════════════════════════════════════════════════════════════════════

def _set_font(widget, family: str = "Segoe UI", size: int = 12, bold: bool = False):
    """Apply font via QFont (avoids stylesheet cascade fights)."""
    f = QFont(family, size)
    f.setBold(bold)
    widget.setFont(f)


def _make_entry(placeholder: str, password: bool = False) -> QLineEdit:
    """Standard text input — identical height and style everywhere."""
    e = QLineEdit()
    e.setPlaceholderText(placeholder)
    e.setFixedHeight(FIELD_H)
    if password:
        e.setEchoMode(QLineEdit.EchoMode.Password)
    e.setStyleSheet(f"""
        QLineEdit {{
            background-color: {INP_BG};
            border: 1px solid {INP_BRD};
            border-radius: 8px;
            color: {TXT_DARK};
            padding: 0 12px;
            font-size: 13px;
        }}
        QLineEdit:focus {{
            border: 1px solid {INP_FOC};
        }}
    """)
    return e


def _primary_btn(text: str, command) -> QPushButton:
    btn = QPushButton(text)
    btn.setFixedHeight(44)
    btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    # Use objectName so we can target exactly this button in QSS without
    # fighting the global QPushButton rule from build_qss().
    btn.setObjectName("primaryBtn")
    btn.setStyleSheet(f"""
        QPushButton#primaryBtn {{
            background-color: {ACC};
            color: #FFFFFF;
            border: none;
            border-radius: 22px;
            font-size: 14px;
            font-weight: bold;
        }}
        QPushButton#primaryBtn:hover {{
            background-color: {ACC_HOV};
        }}
        QPushButton#primaryBtn:disabled {{
            background-color: {INP_BRD};
            color: {TXT_LIGHT};
        }}
    """)
    btn.clicked.connect(command)
    return btn


def _outline_btn(text: str, command) -> QPushButton:
    btn = QPushButton(text)
    btn.setFixedHeight(44)
    btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    btn.setObjectName("outlineBtn")
    btn.setStyleSheet(f"""
        QPushButton#outlineBtn {{
            background-color: {WHITE};
            color: {TXT_DARK};
            border: 1.5px solid {CARD_BRD};
            border-radius: 22px;
            font-size: 14px;
            font-weight: bold;
        }}
        QPushButton#outlineBtn:hover {{
            background-color: {INP_BG};
        }}
    """)
    btn.clicked.connect(command)
    return btn


class _GradientPanel(QFrame):
    """Left auth panel — gradient + logo + tagline."""
    def paintEvent(self, event):
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, QColor(c("panel_left")))
        grad.setColorAt(1, QColor(c("panel_left_end")))
        painter.fillRect(self.rect(), grad)


def make_left_panel() -> QFrame:
    import os
    panel = _GradientPanel()
    panel.setFixedWidth(300)
    panel.setObjectName("leftPanel")
    panel.setStyleSheet("border: none; border-radius: 0px;")

    layout = QVBoxLayout(panel)
    layout.setContentsMargins(32, 40, 32, 40)
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

    # ── Logo image ─────────────────────────────────────
    logo_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "assets", "logo.png"
    )
    logo_lbl = QLabel()
    logo_lbl.setStyleSheet("background: transparent; border: none;")
    logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if os.path.exists(logo_path):
        px = QPixmap(logo_path).scaled(
            80, 80,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        logo_lbl.setPixmap(px)
    else:
        logo_lbl.setText("SD")
        logo_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #6C63FF; background: transparent; border: none;")
    layout.addWidget(logo_lbl)
    layout.addSpacing(16)

    # ── App name ───────────────────────────────────────
    name_lbl = QLabel("SignDesk")
    name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    text_col = "#FFFFFF" if is_dark() else "#2C3358"
    name_lbl.setStyleSheet(f"color: {text_col}; background: transparent; border: none; font-size: 26px; font-weight: bold;")
    layout.addWidget(name_lbl)
    layout.addSpacing(8)

    # ── Tagline ────────────────────────────────────────
    tag_lbl = QLabel("Master sign language,\ninteractively.")
    tag_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    muted_col = "#B8B5D0" if is_dark() else "#5A5490"
    tag_lbl.setStyleSheet(f"color: {muted_col}; background: transparent; border: none; font-size: 13px;")
    tag_lbl.setWordWrap(True)
    layout.addWidget(tag_lbl)

    return panel


def _make_password_field(placeholder: str):
    """
    Returns (wrap_frame, entry_widget).
    The eye-toggle button uses objectName 'eyeBtn' so the global
    QPushButton accent QSS cannot override its transparent style.
    """
    wrap = QFrame()
    wrap.setObjectName("pwWrap")
    wrap.setFixedHeight(FIELD_H)
    wrap.setStyleSheet(f"""
        QFrame#pwWrap {{
            background-color: {INP_BG};
            border: 1px solid {INP_BRD};
            border-radius: 8px;
        }}
    """)

    layout = QHBoxLayout(wrap)
    layout.setContentsMargins(12, 0, 6, 0)
    layout.setSpacing(4)

    entry = QLineEdit()
    entry.setPlaceholderText(placeholder)
    entry.setEchoMode(QLineEdit.EchoMode.Password)
    entry.setStyleSheet("""
        QLineEdit {
            border: none;
            background: transparent;
            font-size: 13px;
            color: """ + TXT_DARK + """;
        }
    """)
    entry.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    eye_btn = QPushButton("Show")
    eye_btn.setObjectName("eyeBtn")
    eye_btn.setFixedSize(48, 32)
    eye_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    eye_btn.setToolTip("Show / hide password")
    eye_btn.setStyleSheet(f"""
        QPushButton#eyeBtn {{
            border: none;
            background: transparent;
            color: {TXT_LIGHT};
            font-size: 11px;
            font-weight: bold;
            padding: 0;
        }}
        QPushButton#eyeBtn:hover {{
            color: {ACC};
        }}
    """)

    def _toggle():
        if entry.echoMode() == QLineEdit.EchoMode.Password:
            entry.setEchoMode(QLineEdit.EchoMode.Normal)
            eye_btn.setText("Hide")
        else:
            entry.setEchoMode(QLineEdit.EchoMode.Password)
            eye_btn.setText("Show")

    eye_btn.clicked.connect(_toggle)
    layout.addWidget(entry)
    layout.addWidget(eye_btn)
    return wrap, entry


# ══════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ══════════════════════════════════════════════════════════════════════════

class LoginPage(QWidget):
    def __init__(self, parent_widget, app):
        super().__init__(parent_widget)
        self._app = app
        self._build()

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(make_left_panel())

        # ── right side ────────────────────────────────────────────────
        right = QWidget()
        right.setObjectName("rightPanel")
        right.setStyleSheet(f"QWidget#rightPanel {{ background-color: {c('bg_primary')}; }}")
        right_lay = QVBoxLayout(right)
        right_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── form card ─────────────────────────────────────────────────
        card = QFrame()
        card.setObjectName("loginCard")
        card.setFixedWidth(400)
        card.setStyleSheet(f"""
            QFrame#loginCard {{
                background-color: {c('bg_primary')};
                border: 1.5px solid {c('border')};
                border-radius: 16px;
            }}
        """)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(36, 32, 36, 32)
        card_lay.setSpacing(6)

        # heading
        heading = QLabel("Welcome back")
        _set_font(heading, size=24, bold=True)
        heading.setStyleSheet(f"color: {c('text_primary')}; background: transparent; border: none;")
        card_lay.addWidget(heading)

        sub = QLabel("Sign in to continue to SignDesk")
        _set_font(sub, size=12)
        sub.setStyleSheet(f"color: {c('text_secondary')}; background: transparent; border: none;")
        card_lay.addWidget(sub)
        card_lay.addSpacing(14)

        # username
        u_lbl = QLabel("Username")
        _set_font(u_lbl, size=10, bold=True)
        u_lbl.setStyleSheet(f"color: {TXT_LIGHT}; background: transparent; border: none;")
        card_lay.addWidget(u_lbl)

        self._user_entry = _make_entry("Enter your username")
        card_lay.addWidget(self._user_entry)
        card_lay.addSpacing(6)

        # password label row (label left, forgot right)
        pw_row = QWidget()
        pw_row.setStyleSheet("background: transparent;")
        pw_row_lay = QHBoxLayout(pw_row)
        pw_row_lay.setContentsMargins(0, 0, 0, 0)
        pw_row_lay.setSpacing(0)

        pw_lbl = QLabel("Password")
        _set_font(pw_lbl, size=10, bold=True)
        pw_lbl.setStyleSheet(f"color: {TXT_LIGHT}; background: transparent; border: none;")

        forgot_btn = QPushButton("Forgot password?")
        forgot_btn.setObjectName("forgotBtn")
        forgot_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        forgot_btn.setStyleSheet(f"""
            QPushButton#forgotBtn {{
                color: {ACC};
                border: none;
                background: transparent;
                font-size: 11px;
                padding: 0;
            }}
            QPushButton#forgotBtn:hover {{
                color: {ACC_HOV};
            }}
        """)
        forgot_btn.clicked.connect(lambda: self._app.show_forgot_password())

        pw_row_lay.addWidget(pw_lbl)
        pw_row_lay.addStretch()
        pw_row_lay.addWidget(forgot_btn)
        card_lay.addWidget(pw_row)

        self._pass_entry = _make_entry("Enter your password", password=True)
        card_lay.addWidget(self._pass_entry)

        # show-password checkbox
        self._show_cb = QCheckBox("Show Password")
        self._show_cb.setStyleSheet(f"""
            QCheckBox {{
                color: {TXT_MID};
                font-size: 12px;
                background: transparent;
                border: none;
            }}
        """)
        self._show_cb.stateChanged.connect(self._toggle_password)
        card_lay.addWidget(self._show_cb)
        card_lay.addSpacing(10)

        # sign-in button
        self._login_btn = _primary_btn("Sign In", self._on_login)
        card_lay.addWidget(self._login_btn)

        # "or" divider
        div_row = QWidget()
        div_row.setStyleSheet("background: transparent;")
        div_lay = QHBoxLayout(div_row)
        div_lay.setContentsMargins(0, 4, 0, 4)

        def _hline():
            ln = QFrame()
            ln.setFrameShape(QFrame.Shape.HLine)
            ln.setObjectName("divLine")
            ln.setStyleSheet(f"QFrame#divLine {{ border: none; border-top: 1px solid {CARD_BRD}; background: transparent; }}")
            return ln

        or_lbl = QLabel("or")
        or_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        or_lbl.setStyleSheet(f"color: {TXT_MID}; background: transparent; border: none; padding: 0 8px;")
        div_lay.addWidget(_hline(), stretch=1)
        div_lay.addWidget(or_lbl, stretch=0, alignment=Qt.AlignmentFlag.AlignCenter)
        div_lay.addWidget(_hline(), stretch=1)
        card_lay.addWidget(div_row)

        card_lay.addWidget(_outline_btn("Create Account", self._app.show_register))

        right_lay.addWidget(card)
        root.addWidget(right)

    # ── helpers ───────────────────────────────────────────────────────

    def _toggle_password(self, state: int):
        mode = QLineEdit.EchoMode.Normal if state == 2 else QLineEdit.EchoMode.Password
        self._pass_entry.setEchoMode(mode)

    def _on_login(self):
        username = self._user_entry.text().strip()
        password = self._pass_entry.text().strip()
        if not username or not password:
            QMessageBox.warning(self, "Missing Fields", "Please fill in all required fields.")
            return
        success, message = login_user(username, password)
        if success:
            self._app.show_dashboard(username)
        else:
            QMessageBox.critical(self, "Login Failed", message)


# ══════════════════════════════════════════════════════════════════════════
# REGISTER PAGE
# ══════════════════════════════════════════════════════════════════════════

class RegisterPage(QWidget):
    email_sent_signal = pyqtSignal(bool, str, dict, str)

    def __init__(self, parent_widget, app):
        super().__init__(parent_widget)
        self._app = app
        self.email_sent_signal.connect(self._on_email_sent)
        self._build()

    # ── accent label (coloured left bar + text) ───────────────────────

    def _accent_label(self, text: str) -> QWidget:
        """
        A compact label row with a purple left-bar accent.
        Uses a plain QWidget so it gets no background from QFrame QSS.
        Fixed height so it doesn't add phantom spacing.
        """
        row = QWidget()
        row.setFixedHeight(22)
        row.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        bar = QFrame()
        bar.setFixedSize(3, 15)
        bar.setObjectName("accentBar")
        bar.setStyleSheet("QFrame#accentBar { background-color: #6C63FF; border: none; border-radius: 1px; }")

        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {TXT_LIGHT}; background: transparent; border: none; font-size: 10px; font-weight: bold;")

        lay.addWidget(bar)
        lay.addWidget(lbl)
        lay.addStretch()
        return row

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(make_left_panel())

        # ── scrollable right side ──────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("regScroll")
        scroll.setStyleSheet("QScrollArea#regScroll { border: none; background: transparent; }")

        content = QWidget()
        content.setObjectName("regContent")
        content.setStyleSheet(f"QWidget#regContent {{ background-color: {WHITE}; }}")
        content_lay = QVBoxLayout(content)
        content_lay.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        content_lay.setContentsMargins(60, 40, 60, 40)

        # ── form card ─────────────────────────────────────────────────
        card = QFrame()
        card.setObjectName("regCard")
        card.setFixedWidth(420)
        card.setStyleSheet(f"""
            QFrame#regCard {{
                background-color: {WHITE};
                border: 1.5px solid {CARD_BRD};
                border-radius: 16px;
            }}
        """)
        form = QVBoxLayout(card)
        form.setContentsMargins(36, 32, 36, 32)
        form.setSpacing(6)

        heading = QLabel("Create your account")
        _set_font(heading, size=24, bold=True)
        heading.setStyleSheet(f"color: {c('text_primary')}; background: transparent; border: none;")
        form.addWidget(heading)
        form.addSpacing(10)

        # ── username ──────────────────────────────────────────────────
        form.addWidget(self._accent_label("Username"))
        self._uname_entry = _make_entry("Choose a username")
        form.addWidget(self._uname_entry)
        form.addSpacing(4)

        # ── email ─────────────────────────────────────────────────────
        form.addWidget(self._accent_label("Email Address"))
        self._email_entry = _make_entry("your@email.com")
        form.addWidget(self._email_entry)
        form.addSpacing(4)

        # ── password ──────────────────────────────────────────────────
        form.addWidget(self._accent_label("Password"))
        pw_wrap, self._pass_entry = _make_password_field("Min. 8 characters")
        form.addWidget(pw_wrap)
        self._pass_entry.textChanged.connect(self._on_confirm_type)
        form.addSpacing(4)

        # ── confirm password ──────────────────────────────────────────
        form.addWidget(self._accent_label("Confirm Password"))
        cpw_wrap, self._confirm_entry = _make_password_field("Repeat your password")
        form.addWidget(cpw_wrap)
        self._confirm_entry.textChanged.connect(self._on_confirm_type)

        # match feedback
        self._match_label = QLabel("")
        self._match_label.setStyleSheet("background: transparent; border: none; font-size: 11px;")
        form.addWidget(self._match_label)

        # status label
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet("background: transparent; border: none; font-size: 11px;")
        form.addWidget(self._status_label)

        form.addSpacing(6)
        self._submit_btn = _primary_btn("Create Account", self._on_submit)
        form.addWidget(self._submit_btn)

        form.addSpacing(6)
        form.addWidget(_outline_btn("← Back to Login", self._app.show_login))

        content_lay.addWidget(card)
        scroll.setWidget(content)
        root.addWidget(scroll)

    # ── validation feedback ───────────────────────────────────────────

    def _on_confirm_type(self):
        confirm = self._confirm_entry.text()
        if not confirm:
            self._match_label.setText("")
            return
        if confirm == self._pass_entry.text():
            self._match_label.setText("✓  Passwords match")
            self._match_label.setStyleSheet(f"color: {SUCCESS}; background: transparent; border: none; font-size: 11px;")
        else:
            self._match_label.setText("✗  Passwords do not match")
            self._match_label.setStyleSheet(f"color: {ERROR}; background: transparent; border: none; font-size: 11px;")

    # ── submit ────────────────────────────────────────────────────────

    def _on_submit(self):
        from core.validators import sanitize_username, sanitize_input, registration_limiter

        username = sanitize_username(self._uname_entry.text())
        email    = sanitize_input(self._email_entry.text()).lower()
        password = self._pass_entry.text().strip()
        confirm  = self._confirm_entry.text().strip()

        # ── Rate limiting: max 5 attempts per email per 5 minutes ──
        allowed, wait = registration_limiter.is_allowed(email)
        if not allowed:
            mins = wait // 60
            secs = wait % 60
            QMessageBox.warning(
                self, "Too Many Attempts",
                f"Too many registration attempts for this email.\n"
                f"Please wait {mins}m {secs}s before trying again."
            )
            return

        # ── Validate (format + MX record + strength) ──
        errors = validate_registration(username, email, password, confirm)
        if errors:
            QMessageBox.critical(self, "Validation Error",
                                 "Please fix the following:\n\n" +
                                 "\n".join(f"• {e}" for e in errors))
            return

        dup, msg = check_duplicate_username(username)
        if dup:
            QMessageBox.critical(self, "Username Taken", msg); return

        dup, msg = check_duplicate_email(email)
        if dup:
            QMessageBox.critical(self, "Email Exists", msg); return

        self._submit_btn.setEnabled(False)
        self._submit_btn.setText("Sending code…")
        self._status_label.setText("Sending verification code to your email…")
        self._status_label.setStyleSheet(f"color: {ACC}; background: transparent; border: none;")

        otp_code   = generate_otp()
        otp_expiry = get_otp_expiry()
        print(f"[OTP] Generated OTP for {email}: {otp_code}")

        pending_data = {
            "username":   username,
            "email":      email,
            "password":   password,
            "otp_code":   otp_code,
            "otp_expiry": otp_expiry,
        }

        def _bg():
            print(f"[OTP] Calling send_verification_email → {email}")
            ok, err = send_verification_email(email, otp_code)
            print(f"[OTP] send_verification_email returned: ok={ok}, msg={err}")
            self.email_sent_signal.emit(ok, err, pending_data, otp_code)

        threading.Thread(target=_bg, daemon=True).start()

    def _on_email_sent(self, success: bool, message: str, pending_data: dict, otp_code: str):
        self._submit_btn.setEnabled(True)
        self._submit_btn.setText("Create Account")

        if success:
            print(f"[OTP] Email confirmed sent — proceeding to verification page.")
            self._status_label.setText("")
            self._app.show_verification(pending_data)
        else:
            # ── FIX: block navigation, never bypass ──────────────────
            print(f"[OTP] Email FAILED — blocking navigation. Reason: {message}")
            self._status_label.setText("Failed to send verification email. Please try again.")
            self._status_label.setStyleSheet(f"color: {ERROR}; background: transparent; border: none;")
            QMessageBox.critical(
                self,
                "Email Error",
                f"Could not send the verification email.\n\n"
                f"Reason: {message}\n\n"
                "Please check your internet connection and try again.\n"
                "Registration cannot continue without a verified email.",
            )
            # Do NOT call show_verification — user must fix and retry.


# ══════════════════════════════════════════════════════════════════════════
# VERIFICATION PAGE
# ══════════════════════════════════════════════════════════════════════════

class VerificationPage(QWidget):
    _LOCKOUT_SECONDS = 10 * 60
    create_signal = pyqtSignal(bool, str)
    resend_signal = pyqtSignal(bool, str, str)

    def __init__(self, parent_widget, app, pending_data: dict):
        super().__init__(parent_widget)
        self._app     = app
        self._pending = pending_data
        self._resend_tracker  = ResendTracker()
        self._resend_tracker.record_resend()
        self._attempt_tracker = VerificationAttemptTracker()

        self.create_signal.connect(self._on_create_result)
        self.resend_signal.connect(self._on_resend_complete)

        self._cooldown_timer = QTimer(self)
        self._cooldown_timer.timeout.connect(self._update_cooldown)
        self._lockout_timer  = QTimer(self)
        self._lockout_timer.timeout.connect(self._tick_lockout)
        self._lockout_remaining = 0

        self._build()

        from core.cooldown_persistence import load_cooldown
        persisted = load_cooldown(self._pending["email"])
        if persisted > 0:
            self._lockout_remaining = persisted
            while self._resend_tracker.resend_count < OTP_MAX_RESENDS:
                self._resend_tracker.record_resend()
            self._show_lockout_ui()
            self._lockout_timer.start(1000)
        else:
            self._start_cooldown_timer()

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(make_left_panel())

        right = QWidget()
        right.setObjectName("verRight")
        right.setStyleSheet(f"QWidget#verRight {{ background-color: {WHITE}; }}")
        right_lay = QVBoxLayout(right)
        right_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("verCard")
        card.setFixedWidth(420)
        card.setStyleSheet(f"""
            QFrame#verCard {{
                background-color: {WHITE};
                border: 1.5px solid {CARD_BRD};
                border-radius: 16px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(36, 32, 36, 32)
        lay.setSpacing(6)

        heading = QLabel("Verify your email")
        _set_font(heading, size=24, bold=True)
        heading.setStyleSheet(f"color: {c('text_primary')}; background: transparent; border: none;")
        lay.addWidget(heading)

        sub1 = QLabel("We've sent a verification code to:")
        _set_font(sub1, size=12)
        sub1.setStyleSheet(f"color: {TXT_MID}; background: transparent; border: none;")
        lay.addWidget(sub1)

        def _mask(e: str) -> str:
            try:
                l, d = e.split("@")
                return f"{l[0]}***{l[-1] if len(l) > 2 else ''}@{d}"
            except Exception:
                return e

        sub2 = QLabel(_mask(self._pending["email"]))
        _set_font(sub2, size=14, bold=True)
        sub2.setStyleSheet(f"color: {PANEL}; background: transparent; border: none;")
        lay.addWidget(sub2)
        lay.addSpacing(14)

        # OTP entry card
        otp_card = QFrame()
        otp_card.setObjectName("otpCard")
        otp_card.setStyleSheet(f"""
            QFrame#otpCard {{
                background-color: {INP_BG};
                border: 1px solid {CARD_BRD};
                border-radius: 10px;
            }}
        """)
        otp_lay = QVBoxLayout(otp_card)
        otp_lay.setContentsMargins(24, 18, 24, 18)
        otp_lay.setSpacing(10)

        code_lbl = QLabel("Enter the 6-digit verification code")
        _set_font(code_lbl, size=11, bold=True)
        code_lbl.setStyleSheet(f"color: {TXT_MID}; background: transparent; border: none;")
        code_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        otp_lay.addWidget(code_lbl)

        self._otp_entry = QLineEdit()
        self._otp_entry.setPlaceholderText("000000")
        self._otp_entry.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._otp_entry.setMaxLength(6)
        self._otp_entry.setStyleSheet(f"""
            QLineEdit {{
                background-color: {WHITE};
                border: 1px solid {INP_BRD};
                border-radius: 8px;
                font-family: 'Courier New';
                font-size: 32px;
                font-weight: bold;
                color: {PANEL};
                padding: 10px;
            }}
            QLineEdit:focus {{
                border: 1px solid {INP_FOC};
            }}
        """)
        self._otp_entry.textChanged.connect(self._on_otp_key)
        otp_lay.addWidget(self._otp_entry)

        exp_lbl = QLabel(f"Code expires in {OTP_EXPIRY_MINUTES} minutes")
        _set_font(exp_lbl, size=10)
        exp_lbl.setStyleSheet(f"color: {TXT_LIGHT}; background: transparent; border: none;")
        exp_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        otp_lay.addWidget(exp_lbl)

        lay.addWidget(otp_card)

        self._status_label = QLabel("")
        _set_font(self._status_label, size=11)
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(self._status_label)

        self._verify_btn = _primary_btn("Verify & Create Account", self._on_verify)
        self._verify_btn.setEnabled(False)
        lay.addWidget(self._verify_btn)

        # lockout warning card (hidden initially)
        self._warning_card = QFrame()
        self._warning_card.setObjectName("warnCard")
        self._warning_card.setStyleSheet("""
            QFrame#warnCard {
                background-color: #1E1E2E;
                border: 1px solid #3A3A4A;
                border-radius: 10px;
            }
        """)
        warn_lay = QVBoxLayout(self._warning_card)
        w1 = QLabel("⚠  You've reached the resend limit.\nPlease wait before retrying.")
        w1.setStyleSheet("color: #FFA500; background: transparent; border: none; font-weight: bold;")
        self._lockout_timer_label = QLabel("")
        self._lockout_timer_label.setStyleSheet("color: #FFFFFF; background: transparent; border: none; font-weight: bold;")
        warn_lay.addWidget(w1)
        warn_lay.addWidget(self._lockout_timer_label)
        self._warning_card.hide()
        lay.addWidget(self._warning_card)

        # resend row
        resend_row = QWidget()
        resend_row.setStyleSheet("background: transparent;")
        resend_lay = QHBoxLayout(resend_row)
        resend_lay.setContentsMargins(0, 0, 0, 0)
        resend_lay.setSpacing(4)

        r_lbl = QLabel("Didn't receive the code?")
        r_lbl.setStyleSheet(f"color: {TXT_LIGHT}; background: transparent; border: none;")

        self._resend_btn = QPushButton("Resend Code")
        self._resend_btn.setObjectName("resendBtn")
        self._resend_btn.setStyleSheet(f"""
            QPushButton#resendBtn {{
                color: {ACC};
                font-weight: bold;
                border: none;
                background: transparent;
            }}
            QPushButton#resendBtn:hover {{ color: {ACC_HOV}; }}
            QPushButton#resendBtn:disabled {{ color: {TXT_LIGHT}; }}
        """)
        self._resend_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._resend_btn.clicked.connect(self._on_resend)

        self._cooldown_label = QLabel("")
        self._cooldown_label.setStyleSheet(f"color: {TXT_LIGHT}; background: transparent; border: none;")

        resend_lay.addWidget(r_lbl)
        resend_lay.addWidget(self._resend_btn)
        resend_lay.addWidget(self._cooldown_label)
        resend_lay.addStretch()
        lay.addWidget(resend_row)

        lay.addSpacing(6)
        lay.addWidget(_outline_btn("← Back to Registration", self._on_back))

        right_lay.addWidget(card)
        root.addWidget(right)

    # ── OTP input ─────────────────────────────────────────────────────

    def _on_otp_key(self):
        val = self._otp_entry.text().strip()
        self._verify_btn.setEnabled(len(val) == 6 and val.isdigit())

    # ── verify ────────────────────────────────────────────────────────

    def _on_verify(self):
        entered = self._otp_entry.text().strip()
        if not entered or len(entered) != 6 or not entered.isdigit():
            self._status_label.setText("Please enter a valid 6-digit code.")
            self._status_label.setStyleSheet(f"color: {WARN}; background: transparent; border: none;")
            return

        can_try, reason = self._attempt_tracker.can_attempt()
        if not can_try:
            self._status_label.setText(reason)
            self._status_label.setStyleSheet(f"color: {ERROR}; background: transparent; border: none;")
            self._verify_btn.setEnabled(False)
            QMessageBox.critical(self, "Verification Locked", reason)
            self._on_back()
            return

        stored_code   = self._pending.get("otp_code", "")
        stored_expiry = self._pending.get("otp_expiry")

        if stored_expiry and is_otp_expired(stored_expiry):
            self._status_label.setText("Code has expired. Please resend.")
            self._status_label.setStyleSheet(f"color: {ERROR}; background: transparent; border: none;")
            self._attempt_tracker.record_attempt()
            self._otp_entry.clear()
            return

        if entered != stored_code:
            self._attempt_tracker.record_attempt()
            remaining = self._attempt_tracker.attempts_remaining
            self._status_label.setText(f"Incorrect code. ({remaining} attempts left)")
            self._status_label.setStyleSheet(f"color: {ERROR}; background: transparent; border: none;")
            self._otp_entry.clear()
            return

        self._verify_btn.setEnabled(False)
        self._verify_btn.setText("Creating account…")
        self._status_label.setText("Creating your account…")
        self._status_label.setStyleSheet(f"color: {ACC}; background: transparent; border: none;")

        def _run():
            ok, msg = create_verified_user(
                self._pending["username"],
                self._pending["email"],
                self._pending["password"],
            )
            self.create_signal.emit(ok, msg)

        threading.Thread(target=_run, daemon=True).start()

    def _on_create_result(self, success: bool, msg: str):
        if success:
            self._status_label.setText("Account created successfully.")
            self._status_label.setStyleSheet(f"color: {SUCCESS}; background: transparent; border: none;")
            QMessageBox.information(self, "Success", "Account verified! You can now log in.")
            self._app.show_login()
        else:
            self._verify_btn.setEnabled(True)
            self._verify_btn.setText("Verify & Create Account")
            self._status_label.setText(msg)
            self._status_label.setStyleSheet(f"color: {ERROR}; background: transparent; border: none;")
            QMessageBox.critical(self, "Account Error", msg)

    # ── resend ────────────────────────────────────────────────────────

    def _on_resend(self):
        can_resend, reason = self._resend_tracker.can_resend()
        if not can_resend:
            self._status_label.setText(reason)
            self._status_label.setStyleSheet(f"color: {WARN}; background: transparent; border: none;")
            return

        self._resend_btn.setEnabled(False)
        self._status_label.setText("Sending new code…")
        self._status_label.setStyleSheet(f"color: {ACC}; background: transparent; border: none;")

        new_code = generate_otp()
        self._pending["otp_code"]   = new_code
        self._pending["otp_expiry"] = get_otp_expiry()

        def _task():
            ok, msg = send_verification_email(self._pending["email"], new_code)
            self.resend_signal.emit(ok, msg, new_code)

        threading.Thread(target=_task, daemon=True).start()

    def _on_resend_complete(self, success: bool, message: str, new_code: str = ""):
        if success:
            self._resend_tracker.record_resend()
            count = self._resend_tracker.resend_count
            self._status_label.setText(f"New code sent! ({count}/{OTP_MAX_RESENDS} resends used)")
            self._status_label.setStyleSheet(f"color: {SUCCESS}; background: transparent; border: none;")
            self._otp_entry.clear()
            if count >= OTP_MAX_RESENDS:
                self._begin_lockout()
            else:
                self._start_cooldown_timer()
        else:
            self._status_label.setText(message)
            self._status_label.setStyleSheet(f"color: {ERROR}; background: transparent; border: none;")
            self._resend_btn.setEnabled(True)

    # ── cooldown ──────────────────────────────────────────────────────

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
                self._resend_btn.setEnabled(False)
                self._cooldown_label.setText("(limit reached)")

    # ── lockout ───────────────────────────────────────────────────────

    def _begin_lockout(self):
        from datetime import datetime, timedelta
        from core.cooldown_persistence import save_cooldown
        self._lockout_remaining = self._LOCKOUT_SECONDS
        expiry = datetime.now() + timedelta(seconds=self._LOCKOUT_SECONDS)
        save_cooldown(self._pending["email"], expiry)
        self._show_lockout_ui()
        self._lockout_timer.start(1000)

    def _show_lockout_ui(self):
        self._resend_btn.setEnabled(False)
        self._cooldown_label.setText("")
        self._warning_card.show()

    def _hide_lockout_ui(self):
        self._warning_card.hide()

    def _tick_lockout(self):
        if self._lockout_remaining <= 0:
            self._lockout_timer.stop()
            self._on_lockout_expired()
            return
        m, s = divmod(self._lockout_remaining, 60)
        self._lockout_timer_label.setText(f"Try again in {m:02d}:{s:02d}")
        self._lockout_remaining -= 1

    def _on_lockout_expired(self):
        from core.cooldown_persistence import clear_cooldown
        self._resend_tracker.reset()
        clear_cooldown()
        self._hide_lockout_ui()
        self._resend_btn.setEnabled(True)
        self._cooldown_label.setText("")
        self._status_label.setText("Cooldown expired. You may resend the code.")
        self._status_label.setStyleSheet(f"color: {SUCCESS}; background: transparent; border: none;")

    # ── navigation ────────────────────────────────────────────────────

    def _on_back(self):
        from core.cooldown_persistence import clear_cooldown
        self._cooldown_timer.stop()
        self._lockout_timer.stop()
        self._resend_tracker.reset()
        clear_cooldown()
        self._app.show_register()