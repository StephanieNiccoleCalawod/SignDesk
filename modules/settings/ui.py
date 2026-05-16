"""
modules/settings/ui.py — Full Settings Page
Two-column layout: sidebar navigation + scrollable content panels.
PyQt6 migration.
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout,
    QScrollArea, QStackedWidget, QPushButton, QCheckBox,
    QComboBox, QSlider, QLineEdit, QDialog, QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QCursor, QColor

from core.theme import c
from core.config import config
from core.ui_helpers import _set_font

# ══════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════

SIDEBAR_W   = 220
SECTION_IDS = [
    ("account",       "Account",              "👤"),
    ("appearance",    "Appearance",            "🎨"),
    ("gesture",       "Gesture Recognition",   "🤟"),
    ("speech",        "Speech Output",         "🔊"),
    ("privacy",       "Privacy & Data",        "🔒"),
    ("accessibility", "Accessibility",         "♿"),
    ("webcam",        "Webcam",                "📷"),
    ("about",         "About & Support",       "ℹ️"),
]

# Consistent dark-card colours
_ROW_BORDER  = ("#F1F5F9", "#1E1E28")

class SettingsPage(QWidget):
    def __init__(self, parent, app, username: str):
        super().__init__(parent)
        self._app = app
        self._username = username
        self._active_section = "account"
        self._nav_buttons = {}
        self._save_labels = {}
        self.setStyleSheet(f"background-color: {c('bg_secondary')};")
        self._build()

    # ──────────────────────────────────────────────────────
    # TOP-LEVEL LAYOUT
    # ──────────────────────────────────────────────────────

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._build_sidebar(layout)
        self._build_content_area(layout)

    # ──────────────────────────────────────────────────────
    # SIDEBAR
    # ──────────────────────────────────────────────────────

    def _build_sidebar(self, parent_layout):
        sidebar = QFrame()
        sidebar.setFixedWidth(SIDEBAR_W)
        sidebar.setStyleSheet(f"background-color: {c('bg_primary')}; border-right: 1px solid {c('border')};")
        parent_layout.addWidget(sidebar)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 24, 0, 20)
        layout.setSpacing(0)

        # Brand
        brand_layout = QHBoxLayout()
        brand_layout.setContentsMargins(16, 0, 16, 4)
        brand_layout.setSpacing(8)

        icon_lbl = QLabel("🤟")
        icon_lbl.setStyleSheet("font-family: 'Segoe UI Emoji'; font-size: 20px; border: none;")
        brand_layout.addWidget(icon_lbl)

        title_lbl = QLabel("SignDesk")
        title_lbl.setStyleSheet(f"color: {c('accent')}; border: none;")
        _set_font(title_lbl, size=16, bold=True)
        brand_layout.addWidget(title_lbl)
        brand_layout.addStretch()

        layout.addLayout(brand_layout)

        subtitle = QLabel("Settings")
        subtitle.setStyleSheet(f"color: {c('text_muted')}; border: none; padding-left: 16px;")
        _set_font(subtitle, size=12)
        layout.addWidget(subtitle)
        
        layout.addSpacing(12)

        # Back to Dashboard
        btn_back = QPushButton("← Dashboard")
        btn_back.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_back.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {c('accent')};
                border: none;
                text-align: left;
                padding-left: 16px;
                font-family: 'Segoe UI';
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {c('input_bg')};
            }}
        """)
        btn_back.setFixedHeight(28)
        btn_back.clicked.connect(self._on_back)
        layout.addWidget(btn_back)

        layout.addSpacing(20)

        # Nav items
        nav_widget = QWidget()
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(12, 0, 12, 0)
        nav_layout.setSpacing(1)

        for sid, label, icon in SECTION_IDS:
            btn = QPushButton()
            btn.setFixedHeight(38)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet("background: transparent; border: none; border-radius: 8px;")
            
            b_layout = QHBoxLayout(btn)
            b_layout.setContentsMargins(4, 0, 4, 0)
            b_layout.setSpacing(8)
            
            bar = QFrame()
            bar.setFixedSize(3, 20)
            bar.setStyleSheet("background: transparent; border-radius: 1px;")
            
            i_lbl = QLabel(icon)
            i_lbl.setStyleSheet("font-family: 'Segoe UI Emoji'; font-size: 14px; border: none; background: transparent;")
            i_lbl.setFixedWidth(24)
            
            t_lbl = QLabel(label)
            t_lbl.setStyleSheet(f"color: {c('text_secondary')}; border: none; background: transparent;")
            _set_font(t_lbl, size=13)
            
            b_layout.addWidget(bar)
            b_layout.addWidget(i_lbl)
            b_layout.addWidget(t_lbl)
            b_layout.addStretch()

            def make_click(s):
                return lambda: self._show_section(s)
            
            btn.clicked.connect(make_click(sid))
            
            nav_layout.addWidget(btn)
            self._nav_buttons[sid] = (btn, bar, t_lbl)

        layout.addWidget(nav_widget)
        layout.addStretch()

    # ──────────────────────────────────────────────────────
    # CONTENT AREA
    # ──────────────────────────────────────────────────────

    def _build_content_area(self, parent_layout):
        self._stacked = QStackedWidget()
        self._stacked.setStyleSheet("background: transparent; border: none;")
        parent_layout.addWidget(self._stacked, stretch=1)

        self._section_indices = {}

        builders = {
            "account":       self._build_account,
            "appearance":    self._build_appearance,
            "gesture":       self._build_gesture,
            "speech":        self._build_speech,
            "privacy":       self._build_privacy,
            "accessibility": self._build_accessibility,
            "webcam":        self._build_webcam,
            "about":         self._build_about,
        }

        for i, (sid, builder) in enumerate(builders.items()):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setStyleSheet("background: transparent;")
            
            wrap = QWidget()
            wrap.setStyleSheet("background: transparent;")
            w_layout = QVBoxLayout(wrap)
            w_layout.setContentsMargins(24, 24, 24, 24)
            w_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            # Optional width constraint: Old code set width=620 but allowed expansion. 
            # We'll just let it expand but set a max width on the content block if desired, 
            # or just use horizontal margins.
            inner_wrap = QWidget()
            inner_wrap.setMaximumWidth(620)
            inner_layout = QVBoxLayout(inner_wrap)
            inner_layout.setContentsMargins(0, 0, 0, 0)
            inner_layout.setSpacing(0)
            
            builder(inner_layout)
            
            if sid != "about":
                self._build_save_bar(inner_layout, sid)

            w_layout.addWidget(inner_wrap, 0, Qt.AlignmentFlag.AlignHCenter)

            scroll.setWidget(wrap)
            self._stacked.addWidget(scroll)
            self._section_indices[sid] = i

        self._show_section("account")

    def _show_section(self, section_id: str):
        self._active_section = section_id
        idx = self._section_indices.get(section_id, 0)
        self._stacked.setCurrentIndex(idx)

        # Update nav highlight
        for sid, (btn, bar, t_lbl) in self._nav_buttons.items():
            is_active = (sid == section_id)
            # using dark mode fallback #1C1C28 since we don't know dark mode here exactly
            bg_color = c("input_bg") if is_active else "transparent"
            bar_color = c("accent") if is_active else "transparent"
            text_color = c("accent") if is_active else c("text_secondary")
            
            btn.setStyleSheet(f"background-color: {bg_color}; border: none; border-radius: 8px;")
            bar.setStyleSheet(f"background-color: {bar_color}; border-radius: 1px;")
            t_lbl.setStyleSheet(f"color: {text_color}; border: none; background: transparent;")
            _set_font(t_lbl, size=13, bold=is_active)

    # ══════════════════════════════════════════════════════
    # WIDGET HELPERS
    # ══════════════════════════════════════════════════════

    def _section_title(self, parent_layout, text):
        lbl = QLabel(text.upper())
        lbl.setStyleSheet(f"color: {c('text_muted')}; border: none; background: transparent;")
        _set_font(lbl, size=11, bold=True)
        parent_layout.addWidget(lbl)
        parent_layout.addSpacing(8)

    def _card(self, parent_layout) -> QVBoxLayout:
        c_frame = QFrame()
        c_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 14px;
            }}
        """)
        layout = QVBoxLayout(c_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        parent_layout.addWidget(c_frame)
        parent_layout.addSpacing(20)
        return layout

    def _row_divider(self, parent_layout):
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background-color: {c('border')}; border: none;")
        parent_layout.addWidget(div)

    def _row(self, parent_layout, label, desc=None, danger=False):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(20, 14, 20, 14)
        
        left = QWidget()
        l_layout = QVBoxLayout(left)
        l_layout.setContentsMargins(0, 0, 0, 0)
        l_layout.setSpacing(2)
        
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {c('error') if danger else c('text_primary')}; border: none; background: transparent;")
        _set_font(lbl, size=13)
        l_layout.addWidget(lbl)
        
        if desc:
            dlbl = QLabel(desc)
            dlbl.setStyleSheet(f"color: {c('text_muted')}; border: none; background: transparent;")
            _set_font(dlbl, size=11)
            l_layout.addWidget(dlbl)
            
        row_layout.addWidget(left, stretch=1)
        
        right = QWidget()
        r_layout = QHBoxLayout(right)
        r_layout.setContentsMargins(0, 0, 0, 0)
        r_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row_layout.addWidget(right)
        
        parent_layout.addWidget(row_widget)
        return r_layout

    def _toggle_row(self, parent_layout, label, desc, key, disabled=False, on_change=None):
        right_layout = self._row(parent_layout, label, desc)

        cb = QCheckBox()
        cb.setChecked(config.get(key, False))
        cb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # Style like a toggle switch
        cb.setStyleSheet(f"""
            QCheckBox::indicator {{ width: 44px; height: 22px; }}
            QCheckBox::indicator:unchecked {{ background-color: {c('border')}; border-radius: 11px; }}
            QCheckBox::indicator:checked {{ background-color: {c('accent')}; border-radius: 11px; }}
        """)
        if disabled:
            cb.setEnabled(False)
            
        def _on_toggle(state):
            config.set(key, bool(state))
            if on_change:
                on_change(bool(state))
            
        cb.stateChanged.connect(_on_toggle)
        right_layout.addWidget(cb)
        
        self._row_divider(parent_layout)

    def _select_row(self, parent_layout, label, desc, key, options, on_change=None):
        right_layout = self._row(parent_layout, label, desc)

        current = config.get(key, options[0][0])
        labels = [o[1] for o in options]
        values = [o[0] for o in options]

        combo = QComboBox()
        combo.addItems(labels)
        try:
            combo.setCurrentIndex(values.index(current))
        except ValueError:
            combo.setCurrentIndex(0)
            
        combo.setFixedWidth(180)
        combo.setFixedHeight(32)
        combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {c('input_bg')};
                color: {c('text_primary')};
                border: 1px solid {c('border')};
                border-radius: 8px;
                padding-left: 10px;
                font-family: 'Segoe UI';
                font-size: 12px;
            }}
            QComboBox::drop-down {{ border: none; }}
        """)
        
        def _on_change(idx):
            config.set(key, values[idx])
            if on_change:
                on_change(values[idx])
            
        combo.currentIndexChanged.connect(_on_change)
        right_layout.addWidget(combo)

        self._row_divider(parent_layout)

    def _slider_row(self, parent_layout, label, desc, key, min_val, max_val, step, fmt_fn):
        outer = QWidget()
        o_layout = QVBoxLayout(outer)
        o_layout.setContentsMargins(20, 14, 20, 14)
        
        top = QHBoxLayout()
        
        left = QVBoxLayout()
        left.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {c('text_primary')}; border: none; background: transparent;")
        _set_font(lbl, size=13)
        left.addWidget(lbl)
        
        if desc:
            dlbl = QLabel(desc)
            dlbl.setStyleSheet(f"color: {c('text_muted')}; border: none; background: transparent;")
            _set_font(dlbl, size=11)
            left.addWidget(dlbl)
            
        top.addLayout(left, stretch=1)
        
        current_val = config.get(key, min_val)
        val_label = QLabel(fmt_fn(current_val))
        val_label.setFixedWidth(56)
        val_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        val_label.setStyleSheet(f"color: {c('accent')}; border: none; background: transparent;")
        _set_font(val_label, size=13, bold=True)
        top.addWidget(val_label)
        
        o_layout.addLayout(top)
        
        slider = QSlider(Qt.Orientation.Horizontal)
        # Scale float values to int by multiplying by 100 or appropriately
        scale = 100 if isinstance(step, float) else 1
        slider.setRange(int(min_val * scale), int(max_val * scale))
        slider.setSingleStep(int(step * scale))
        slider.setValue(int(current_val * scale))
        
        slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border-radius: 4px;
                height: 8px;
                background: {c('border')};
            }}
            QSlider::sub-page:horizontal {{
                background: {c('accent')};
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {c('accent')};
                width: 16px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 8px;
            }}
        """)
        
        def _on_slide(val):
            real_val = val / scale
            snapped = round(round(real_val / step) * step, 4)
            config.set(key, snapped)
            val_label.setText(fmt_fn(snapped))
            
        slider.valueChanged.connect(_on_slide)
        o_layout.addWidget(slider)
        o_layout.addSpacing(8)
        
        parent_layout.addWidget(outer)
        self._row_divider(parent_layout)

    def _badge(self, parent_layout, text, color="blue"):
        # map color string to theme bg/fg roughly
        bg = "#EFF6FF"
        fg = "#2563EB"
        if color == "amber":
            bg = "#FFFBEB"
            fg = "#B45309"
        elif color == "green":
            bg = "#F0FDF4"
            fg = "#15803D"
        elif color == "purple":
            bg = "#F5F3FF"
            fg = "#7C3AED"
            
        lbl = QLabel(text)
        lbl.setStyleSheet(f"background-color: {bg}; color: {fg}; border-radius: 6px; padding: 2px 8px; font-family: 'Segoe UI'; font-size: 10px; font-weight: bold;")
        parent_layout.addWidget(lbl)
        return lbl

    # ══════════════════════════════════════════════════════
    # SECTION: ACCOUNT
    # ══════════════════════════════════════════════════════

    def _build_account(self, parent_layout):
        self._section_title(parent_layout, "Account")
        card = self._card(parent_layout)

        from modules.settings.account_backend import Session
        self._session = Session()
        self._session.load_by_username(self._username)

        if self._session.is_logged_in:
            self._display_name = self._session.user["name"]
            self._user_email = self._session.user["email"]
        else:
            self._display_name = self._username
            self._user_email = ""

        # Header
        header = QWidget()
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 18, 20, 18)
        
        initials = self._display_name[0].upper() if self._display_name else "?"
        
        avatar = QLabel(initials)
        avatar.setFixedSize(52, 52)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(f"background-color: {c('accent')}; color: #FFFFFF; border-radius: 26px; font-family: 'Segoe UI'; font-size: 18px; font-weight: bold;")
        h_layout.addWidget(avatar)
        h_layout.addSpacing(14)
        
        info = QVBoxLayout()
        info.setSpacing(2)
        
        self._acct_name_label = QLabel(self._display_name)
        self._acct_name_label.setStyleSheet(f"color: {c('text_primary')}; border: none; background: transparent;")
        _set_font(self._acct_name_label, size=16, bold=True)
        info.addWidget(self._acct_name_label)
        
        self._acct_email_label = QLabel(self._user_email)
        self._acct_email_label.setStyleSheet(f"color: {c('text_secondary')}; border: none; background: transparent;")
        _set_font(self._acct_email_label, size=12)
        info.addWidget(self._acct_email_label)
        
        h_layout.addLayout(info, stretch=1)
        card.addWidget(header)
        
        self._row_divider(card)

        # Inline edit rows
        self._build_editable_row(card, "Change email address", "Update your registered email", self._user_email, self._save_email)
        self._build_editable_row(card, "Display name", "How your name appears in the app", self._display_name, self._save_display_name)

        # Change password
        pw_right = self._row(card, "Change password", "Keep your account secure")
        pw_btn = QPushButton("Change")
        pw_btn.setFixedSize(80, 30)
        pw_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        pw_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c('input_bg')};
                color: {c('accent')};
                border: none;
                border-radius: 8px;
                font-family: 'Segoe UI';
                font-size: 12px;
                font-weight: bold;
            }}
        """)
        pw_btn.clicked.connect(self._on_change_password)
        pw_right.addWidget(pw_btn)

    def _build_editable_row(self, parent_layout, label, desc, current_value, on_save):
        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(0)
        
        top = QWidget()
        t_layout = QHBoxLayout(top)
        t_layout.setContentsMargins(20, 14, 20, 0)
        
        left = QVBoxLayout()
        left.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {c('text_primary')}; border: none; background: transparent;")
        _set_font(lbl, size=13)
        left.addWidget(lbl)
        dlbl = QLabel(desc)
        dlbl.setStyleSheet(f"color: {c('text_muted')}; border: none; background: transparent;")
        _set_font(dlbl, size=11)
        left.addWidget(dlbl)
        t_layout.addLayout(left, stretch=1)
        
        edit_btn = QPushButton("Edit")
        edit_btn.setFixedSize(70, 30)
        edit_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        edit_btn.setStyleSheet(f"background-color: {c('input_bg')}; color: {c('accent')}; border: none; border-radius: 8px; font-weight: bold;")
        t_layout.addWidget(edit_btn)
        
        c_layout.addWidget(top)
        
        edit_frame = QWidget()
        e_layout = QHBoxLayout(edit_frame)
        e_layout.setContentsMargins(20, 8, 20, 14)
        
        entry = QLineEdit(current_value)
        entry.setFixedHeight(36)
        entry.setStyleSheet(f"""
            QLineEdit {{
                background-color: {c('input_bg')};
                color: {c('text_primary')};
                border: 1px solid {c('accent')};
                border-radius: 8px;
                padding-left: 10px;
            }}
        """)
        e_layout.addWidget(entry, stretch=1)
        
        save_btn = QPushButton("Save")
        save_btn.setFixedSize(70, 36)
        save_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        save_btn.setStyleSheet(f"background-color: {c('accent')}; color: #FFFFFF; border: none; border-radius: 8px; font-weight: bold;")
        e_layout.addWidget(save_btn)
        
        c_layout.addWidget(edit_frame)
        edit_frame.hide()
        
        is_editing = [False]
        
        def _do_save():
            new_val = entry.text().strip()
            if new_val:
                on_save(new_val)
            _toggle_edit()
            
        save_btn.clicked.connect(_do_save)
        
        def _toggle_edit():
            is_editing[0] = not is_editing[0]
            if is_editing[0]:
                edit_btn.setText("Cancel")
                edit_frame.show()
                entry.setFocus()
            else:
                edit_btn.setText("Edit")
                edit_frame.hide()
                entry.setText(current_value)
                
        edit_btn.clicked.connect(_toggle_edit)
        
        parent_layout.addWidget(container)
        self._row_divider(parent_layout)

    def _save_email(self, new_email):
        from modules.settings.account_backend import update_email
        if not hasattr(self, '_session') or not self._session.is_logged_in:
            QMessageBox.critical(self, "Error", "Session not available.")
            return

        password, ok = QInputDialog.getText(self, "Verify Identity", "Enter your current password to verify:", QLineEdit.EchoMode.Password)
        if not ok or not password:
            return

        success, msg = update_email(self._session.user_id, new_email, password)
        if success:
            self._session.refresh()
            self._user_email = self._session.user["email"]
            self._acct_email_label.setText(self._user_email)
        else:
            QMessageBox.critical(self, "Email Update", msg)

    def _save_display_name(self, new_name):
        from modules.settings.account_backend import update_display_name
        if not hasattr(self, '_session') or not self._session.is_logged_in:
            QMessageBox.critical(self, "Error", "Session not available.")
            return

        success, msg = update_display_name(self._session.user_id, new_name)
        if success:
            self._session.refresh()
            self._display_name = self._session.user["name"]
            self._acct_name_label.setText(self._display_name)
        else:
            QMessageBox.critical(self, "Display Name", msg)

    def _on_change_password(self):
        from modules.settings.account_backend import update_password, verify_password
        from modules.auth.otp_manager import create_otp, verify_otp, invalidate_otp
        from core.email_service import send_verification_email, ResendTracker

        if not hasattr(self, '_session') or not self._session.is_logged_in:
            QMessageBox.critical(self, "Error", "Session not available.")
            return

        user_email = self._user_email
        if not user_email:
            QMessageBox.critical(self, "Error", "No email address on file.")
            return

        parts = user_email.split("@")
        masked_email = parts[0][0] + "***@" + parts[1] if len(parts) == 2 and len(parts[0]) > 1 else user_email

        resend_tracker = ResendTracker()
        otp_attempts = [0]
        max_otp_attempts = 5

        dlg = QDialog(self)
        dlg.setWindowTitle("Change Password")
        dlg.setFixedSize(430, 520)
        dlg.setStyleSheet(f"background-color: {c('bg_primary')};")

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 20, 24, 20)
        
        title = QLabel("Change Password")
        title.setStyleSheet(f"color: {c('text_primary')}; border: none; background: transparent;")
        _set_font(title, size=16, bold=True)
        layout.addWidget(title)
        
        step1 = QLabel("Step 1: Verify your identity")
        step1.setStyleSheet(f"color: {c('text_muted')}; border: none; background: transparent;")
        layout.addWidget(step1)
        layout.addSpacing(12)

        fields = {}
        for lbl, key in [("Current password", "current"), ("New password", "new"), ("Confirm new password", "confirm")]:
            field_lbl = QLabel(lbl)
            field_lbl.setStyleSheet(f"color: {c('text_muted')}; border: none; background: transparent;")
            layout.addWidget(field_lbl)
            entry = QLineEdit()
            entry.setEchoMode(QLineEdit.EchoMode.Password)
            entry.setFixedHeight(38)
            entry.setStyleSheet(f"background-color: {c('input_bg')}; color: {c('text_primary')}; border: 1px solid {c('border')}; border-radius: 8px;")
            layout.addWidget(entry)
            layout.addSpacing(8)
            fields[key] = entry
            
        hint = QLabel("Min 8 chars · 1 uppercase · 1 number")
        hint.setStyleSheet(f"color: {c('text_muted')}; border: none; background: transparent;")
        layout.addWidget(hint)
        
        status_label = QLabel("")
        status_label.setStyleSheet(f"color: {c('error')}; border: none; background: transparent;")
        status_label.setWordWrap(True)
        layout.addWidget(status_label)

        def _set_status(msg, is_error=True):
            status_label.setStyleSheet(f"color: {c('error') if is_error else c('success')}; border: none; background: transparent;")
            status_label.setText(msg)

        otp_frame = QWidget()
        o_layout = QVBoxLayout(otp_frame)
        o_layout.setContentsMargins(0, 8, 0, 0)
        
        step2 = QLabel("Step 2: Enter verification code")
        step2.setStyleSheet(f"color: {c('accent')}; border: none; background: transparent;")
        _set_font(step2, size=11, bold=True)
        o_layout.addWidget(step2)
        
        otp_hint = QLabel(f"A 6-digit code was sent to {masked_email}")
        otp_hint.setStyleSheet(f"color: {c('text_muted')}; border: none; background: transparent;")
        o_layout.addWidget(otp_hint)
        
        otp_entry = QLineEdit()
        otp_entry.setPlaceholderText("Enter 6-digit code")
        otp_entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        otp_entry.setFixedHeight(42)
        otp_entry.setStyleSheet(f"background-color: {c('input_bg')}; color: {c('text_primary')}; border: 1px solid {c('accent')}; border-radius: 8px; font-size: 16px;")
        o_layout.addWidget(otp_entry)
        
        layout.addWidget(otp_frame)
        otp_frame.hide()

        btn_row = QHBoxLayout()
        layout.addStretch()
        layout.addLayout(btn_row)

        phase1_buttons = QWidget()
        p1_layout = QHBoxLayout(phase1_buttons)
        p1_layout.setContentsMargins(0, 0, 0, 0)
        
        p1_layout.addStretch()
        cancel1 = QPushButton("Cancel")
        cancel1.setFixedSize(80, 36)
        cancel1.clicked.connect(dlg.reject)
        cancel1.setStyleSheet(f"background: transparent; color: {c('text_secondary')}; border: none;")
        p1_layout.addWidget(cancel1)
        
        send_btn = QPushButton("✉ Send OTP")
        send_btn.setFixedSize(130, 36)
        send_btn.setStyleSheet(f"background-color: {c('accent')}; color: #FFFFFF; border: none; border-radius: 8px; font-weight: bold;")
        p1_layout.addWidget(send_btn)

        phase2_buttons = QWidget()
        p2_layout = QHBoxLayout(phase2_buttons)
        p2_layout.setContentsMargins(0, 0, 0, 0)
        
        resend_btn = QPushButton("Resend code")
        resend_btn.setStyleSheet(f"background: transparent; color: {c('accent')}; border: none;")
        p2_layout.addWidget(resend_btn)
        p2_layout.addStretch()
        
        cancel2 = QPushButton("Cancel")
        cancel2.setFixedSize(80, 36)
        cancel2.clicked.connect(dlg.reject)
        cancel2.setStyleSheet(f"background: transparent; color: {c('text_secondary')}; border: none;")
        p2_layout.addWidget(cancel2)
        
        verify_btn = QPushButton("✓ Verify & Save")
        verify_btn.setFixedSize(130, 36)
        verify_btn.setStyleSheet(f"background-color: {c('accent')}; color: #FFFFFF; border: none; border-radius: 8px; font-weight: bold;")
        p2_layout.addWidget(verify_btn)

        btn_row.addWidget(phase1_buttons)
        btn_row.addWidget(phase2_buttons)
        phase2_buttons.hide()

        def _send_otp():
            current_pw = fields["current"].text()
            new_pw = fields["new"].text()
            confirm_pw = fields["confirm"].text()
            if not current_pw or not new_pw or not confirm_pw:
                _set_status("⚠ All password fields are required.")
                return
            ok, msg = update_password(self._session.user_id, current_pw, new_pw, confirm_pw, dry_run=True)
            if not ok:
                _set_status(f"⚠ {msg}")
                return
            _set_status("Sending verification code...", False)
            try:
                otp_code = create_otp(user_email)
                email_ok, email_msg = send_verification_email(user_email, otp_code)
            except Exception as e:
                _set_status(f"⚠ Failed to send code: {e}")
                return
            if not email_ok:
                _set_status(f"⚠ {email_msg}")
                return
            resend_tracker.record_resend()
            for entry in fields.values():
                entry.setEnabled(False)
            otp_frame.show()
            otp_entry.setFocus()
            phase1_buttons.hide()
            phase2_buttons.show()
            _set_status(f"✉ Code sent to {masked_email}", False)

        send_btn.clicked.connect(_send_otp)

        def _resend_otp():
            can, reason = resend_tracker.can_resend()
            if not can:
                _set_status(f"⚠ {reason}")
                return
            _set_status("Resending code...", False)
            try:
                otp_code = create_otp(user_email)
                email_ok, email_msg = send_verification_email(user_email, otp_code)
            except Exception as e:
                _set_status(f"⚠ Failed to resend: {e}")
                return
            if not email_ok:
                _set_status(f"⚠ {email_msg}")
                return
            resend_tracker.record_resend()
            _set_status(f"✉ New code sent to {masked_email}", False)

        resend_btn.clicked.connect(_resend_otp)

        def _verify_and_save():
            code = otp_entry.text().strip()
            if not code or len(code) != 6 or not code.isdigit():
                _set_status("⚠ Please enter a valid 6-digit code.")
                return
            otp_attempts[0] += 1
            if otp_attempts[0] > max_otp_attempts:
                _set_status(f"⚠ Too many attempts. Please close and try again.")
                return
            ok, msg = verify_otp(user_email, code)
            if not ok:
                remaining = max_otp_attempts - otp_attempts[0]
                _set_status(f"⚠ {msg} ({remaining} attempt{'s' if remaining != 1 else ''} left)")
                otp_entry.clear()
                return
            pw_ok, pw_msg = update_password(self._session.user_id, fields["current"].text(), fields["new"].text(), fields["confirm"].text())
            invalidate_otp(user_email)
            if not pw_ok:
                _set_status(f"⚠ {pw_msg}")
                return
            dlg.accept()
            QMessageBox.information(self, "Password Changed", "Your password has been updated successfully.")

        verify_btn.clicked.connect(_verify_and_save)

        dlg.exec()

    # ══════════════════════════════════════════════════════
    # SECTION: APPEARANCE
    # ══════════════════════════════════════════════════════

    def _apply_theme(self, theme_value: str):
        """Apply the selected theme and rebuild the settings page to pick up new colours."""
        from core.theme import apply_qt_theme
        import platform

        if theme_value == "dark":
            apply_qt_theme(dark=True)
        elif theme_value == "high-contrast":
            apply_qt_theme(dark=True)
        elif theme_value == "system":
            try:
                if platform.system() == "Windows":
                    import winreg
                    reg_key = winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                    val, _ = winreg.QueryValueEx(reg_key, "AppsUseLightTheme")
                    apply_qt_theme(dark=(val == 0))
                else:
                    apply_qt_theme(dark=False)
            except Exception:
                apply_qt_theme(dark=False)
        else:
            apply_qt_theme(dark=False)

        # Rebuild the entire settings UI so every widget re-calls c() with the new mode
        self._rebuild_all()

    def _rebuild_all(self):
        """Tear down and rebuild every section so colour tokens reflect the current theme."""
        # Remember where we were
        current_section = self._active_section

        # Remove the stacked widget from the main layout
        layout = self.layout()
        old_stacked = self._stacked
        layout.removeWidget(old_stacked)
        old_stacked.deleteLater()

        # Reset tracking dicts
        self._nav_buttons = {}
        self._save_labels = {}

        # Re-apply sidebar colours (the sidebar is the first widget in layout)
        sidebar = layout.itemAt(0).widget() if layout.count() > 0 else None
        if sidebar:
            layout.removeWidget(sidebar)
            sidebar.deleteLater()

        # Rebuild everything from scratch into the existing layout
        self.setStyleSheet(f"background-color: {c('bg_secondary')};")
        self._build_sidebar(layout)
        self._build_content_area(layout)
        self._show_section(current_section)

    def _apply_font_size(self, size_value: str):
        """Apply the selected font size globally."""
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont
        size_map = {"small": 11, "medium": 13, "large": 15, "xl": 17}
        pt = size_map.get(size_value, 13)
        app = QApplication.instance()
        if app:
            font = QFont("Segoe UI", pt)
            app.setFont(font)

    def _build_appearance(self, parent_layout):
        self._section_title(parent_layout, "Appearance")
        card = self._card(parent_layout)
        self._select_row(
            card, "Theme", "App color scheme",
            "appearance.theme",
            [("system", "System default"), ("light", "Light"), ("dark", "Dark"), ("high-contrast", "High contrast")],
            on_change=self._apply_theme,
        )
        self._select_row(
            card, "Font size", "Affects gesture text output",
            "appearance.font_size",
            [("small", "Small"), ("medium", "Medium"), ("large", "Large"), ("xl", "Extra large")],
            on_change=self._apply_font_size,
        )
        self._toggle_row(
            card, "Show landmark overlay", "Draw hand keypoints on webcam view",
            "appearance.show_landmark_overlay",
            on_change=self._apply_landmark_overlay,
        )

    def _apply_landmark_overlay(self, enabled: bool):
        """Notify the vision module (if running) to show/hide the hand keypoint overlay."""
        # The vision module reads config.get("appearance.show_landmark_overlay") on each frame,
        # so writing to config is sufficient — no explicit signal needed.
        pass

    # ══════════════════════════════════════════════════════
    # SECTION: GESTURE RECOGNITION
    # ══════════════════════════════════════════════════════

    def _build_gesture(self, parent_layout):
        self._section_title(parent_layout, "Gesture Recognition")
        card = self._card(parent_layout)
        self._slider_row(card, "Confidence threshold", "Minimum score to accept a gesture", "gesture.confidence_threshold", 40, 95, 5, lambda v: f"{int(v)}%")
        self._slider_row(card, "Gesture timeout window", "Pause before assembling a sentence", "gesture.timeout", 0.5, 5.0, 0.5, lambda v: f"{v:.1f}s")
        self._select_row(card, "Gesture library", "Active recognition dataset", "gesture.library", [("asl-standard", "ASL — Standard"), ("asl-fingerspell", "ASL — Fingerspelling"), ("custom", "Custom library")])
        self._toggle_row(card, "Show confidence indicator", "Display score badge on each gesture", "gesture.show_confidence_indicator")

    # ══════════════════════════════════════════════════════
    # SECTION: SPEECH OUTPUT
    # ══════════════════════════════════════════════════════

    def _build_speech(self, parent_layout):
        self._section_title(parent_layout, "Speech Output")
        card = self._card(parent_layout)
        self._toggle_row(card, "Text-to-speech", "Read out recognized sentences aloud", "speech.tts_enabled")
        self._select_row(card, "Voice", None, "speech.voice", [("default", "Default system voice"), ("female", "Voice 1 (Female)"), ("male", "Voice 2 (Male)")])
        self._slider_row(card, "Speech rate", None, "speech.rate", 0.5, 2.0, 0.1, lambda v: f"{v:.1f}×")
        self._slider_row(card, "Volume", None, "speech.volume", 0, 100, 5, lambda v: f"{int(v)}%")

    # ══════════════════════════════════════════════════════
    # SECTION: PRIVACY & DATA
    # ══════════════════════════════════════════════════════

    def _build_privacy(self, parent_layout):
        self._section_title(parent_layout, "Privacy & Data")
        card = self._card(parent_layout)

        right = self._row(card, "Gesture history log", "Save recognized text + timestamps locally")
        self._badge(right, "Off by default", "amber")
        var_hist = QCheckBox()
        var_hist.setChecked(config.get("privacy.gesture_history_log", False))
        var_hist.setStyleSheet(f"""
            QCheckBox::indicator {{ width: 44px; height: 22px; }}
            QCheckBox::indicator:unchecked {{ background-color: {c('border')}; border-radius: 11px; }}
            QCheckBox::indicator:checked {{ background-color: {c('accent')}; border-radius: 11px; }}
        """)
        from modules.gesture_history.backend import set_setting as _gh_set
        def _toggle_hist(state):
            b = bool(state)
            config.set("privacy.gesture_history_log", b)
            _gh_set("logging_enabled", "1" if b else "0")
        var_hist.stateChanged.connect(_toggle_hist)
        right.addWidget(var_hist)
        self._row_divider(card)

        right2 = self._row(card, "Local-only processing", "No data is ever sent to external servers")
        self._badge(right2, "Always on", "green")
        self._row_divider(card)

        right3 = self._row(card, "View saved gesture log", "Browse or export your local history")
        def _open_log_viewer(e):
            self._app.show_gesture_log_viewer(self._username)
        arrow = QLabel("›")
        arrow.setStyleSheet(f"color: {c('text_muted')}; border: none; font-size: 20px; background: transparent;")
        arrow.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        arrow.mousePressEvent = _open_log_viewer
        right3.addWidget(arrow)
        self._row_divider(card)

        clear_right = self._row(card, "Clear gesture history", "Permanently delete all local logs", danger=True)
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedSize(70, 30)
        clear_btn.setStyleSheet(f"background-color: {c('error_bg')}; color: {c('error')}; border: none; border-radius: 8px; font-weight: bold;")
        clear_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        def _confirm_clear():
            reply = QMessageBox.question(self, "Clear Gesture History", "This will permanently delete all saved gesture history. This cannot be undone. Continue?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                from modules.gesture_history.backend import clear_history as _gh_clear
                user_id = getattr(self._app, 'current_user_id', None)
                _gh_clear(user_id)
                clear_btn.hide()
                cleared = QLabel("✓ Cleared")
                cleared.setStyleSheet(f"background-color: {c('success_bg')}; color: {c('success')}; border-radius: 6px; padding: 2px 8px; font-family: 'Segoe UI'; font-size: 10px; font-weight: bold;")
                clear_right.addWidget(cleared)

        clear_btn.clicked.connect(_confirm_clear)
        clear_right.addWidget(clear_btn)

    # ══════════════════════════════════════════════════════
    # SECTION: ACCESSIBILITY
    # ══════════════════════════════════════════════════════

    def _build_accessibility(self, parent_layout):
        self._section_title(parent_layout, "Accessibility")
        card = self._card(parent_layout)
        self._toggle_row(card, "Screen reader support", "Optimize UI labels for assistive tools", "accessibility.screen_reader_support")
        self._toggle_row(card, "Reduce motion", "Minimize animations in the interface", "accessibility.reduce_motion")
        self._toggle_row(card, "Keyboard navigation", "Control app features without a mouse", "accessibility.keyboard_navigation")
        self._toggle_row(card, "Gesture feedback vibration", "Haptic pulse on successful recognition", "accessibility.haptic_feedback")

    # ══════════════════════════════════════════════════════
    # SECTION: WEBCAM
    # ══════════════════════════════════════════════════════

    def _build_webcam(self, parent_layout):
        self._section_title(parent_layout, "Webcam")
        card = self._card(parent_layout)
        self._toggle_row(card, "Enable webcam on launch", "Auto-start camera when app opens", "webcam.auto_start_on_launch")
        self._select_row(card, "Camera source", None, "webcam.camera_source", [("builtin", "Built-in webcam"), ("external", "External USB camera")])
        self._select_row(card, "Resolution", "Higher resolution may affect performance", "webcam.resolution", [("480p", "480p"), ("720p", "720p (recommended)"), ("1080p", "1080p")])

    # ══════════════════════════════════════════════════════
    # SECTION: ABOUT & SUPPORT
    # ══════════════════════════════════════════════════════

    def _build_about(self, parent_layout):
        self._section_title(parent_layout, "About & Support")
        card = self._card(parent_layout)

        right = self._row(card, "App version", "SignDesk v1.0.0")
        self._badge(right, "Latest", "purple")
        self._row_divider(card)

        right2 = self._row(card, "User guide & documentation")
        arrow2 = QLabel("›")
        arrow2.setStyleSheet(f"color: {c('text_muted')}; border: none; font-size: 18px; background: transparent;")
        right2.addWidget(arrow2)
        self._row_divider(card)

        right3 = self._row(card, "Send feedback")
        arrow3 = QLabel("›")
        arrow3.setStyleSheet(f"color: {c('text_muted')}; border: none; font-size: 18px; background: transparent;")
        right3.addWidget(arrow3)
        self._row_divider(card)

        right4 = self._row(card, "Sign out", danger=True)
        arrow4 = QLabel("›")
        arrow4.setStyleSheet("color: #FDA4AF; border: none; font-size: 18px; background: transparent;")
        arrow4.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        def _on_sign_out(e):
            reply = QMessageBox.question(self, "Sign Out", "Are you sure you want to sign out?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self._app.show_login()
        arrow4.mousePressEvent = _on_sign_out
        right4.addWidget(arrow4)

    # ══════════════════════════════════════════════════════
    # SAVE BAR
    # ══════════════════════════════════════════════════════

    def _build_save_bar(self, parent_layout, section_id=None):
        bar = QWidget()
        b_layout = QHBoxLayout(bar)
        b_layout.setContentsMargins(0, 8, 0, 24)
        b_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        saved_label = QLabel("")
        saved_label.setStyleSheet(f"color: {c('success')}; background-color: {c('success_bg')}; border-radius: 8px; font-family: 'Segoe UI'; font-size: 12px; padding: 0 10px;")
        saved_label.hide()
        if section_id:
            self._save_labels[section_id] = saved_label
        b_layout.addWidget(saved_label)
        b_layout.addSpacing(10)

        save_btn = QPushButton("Save changes")
        save_btn.setFixedSize(130, 40)
        save_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c('accent')};
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                font-family: 'Segoe UI';
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {c('accent_hover')};
            }}
        """)
        save_btn.clicked.connect(self._on_save)
        b_layout.addWidget(save_btn)

        parent_layout.addWidget(bar)

    def _on_save(self):
        config.save()

        # Re-apply live settings for the active section
        if self._active_section == "appearance":
            theme_val = config.get("appearance.theme", "system")
            font_val = config.get("appearance.font_size", "medium")
            self._apply_font_size(font_val)
            self._apply_theme(theme_val)  # rebuilds page last

        saved_label = self._save_labels.get(self._active_section)
        if not saved_label:
            return

        saved_label.setText("✓ Changes saved")
        saved_label.show()
        
        QTimer.singleShot(2500, saved_label.hide)

    # ══════════════════════════════════════════════════════
    # NAVIGATION
    # ══════════════════════════════════════════════════════

    def _on_back(self):
        self._app.show_dashboard(self._username)