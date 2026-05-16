"""
modules/dashboard/ui.py - Dashboard UI
PyQt6 migration — CustomTkinter dependency fully removed.
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout, 
    QScrollArea, QLineEdit, QMessageBox, QGridLayout
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QPainter, QLinearGradient, QColor, QCursor

from core.theme import c, is_dark
from core.ui_helpers import create_nav_item, build_steps_panel, _set_font

class GradientSidebar(QFrame):
    """Sidebar with vertical gradient background — respects current theme mode."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(210)

    def paintEvent(self, event):
        from core.theme import is_dark
        dark = is_dark()
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, QColor(c("panel_left", dark=dark)))
        grad.setColorAt(1, QColor(c("panel_left_end", dark=dark)))
        painter.fillRect(self.rect(), grad)

class DashboardPage(QWidget):
    def __init__(self, parent, app, username: str):
        super().__init__(parent)
        self._app = app
        self._username = username
        self.setStyleSheet(f"background-color: {c('bg_secondary')};")
        self._build()

    # ── Navigation callbacks ───────────────────────────────

    def _launch_gesture_detection(self):
        self._app.show_gesture_detection(self._username)

    def _launch_settings(self):
        if hasattr(self._app, 'show_settings'):
            self._app.show_settings(self._username)

    def _launch_gesture_history(self):
        self._app.show_gesture_history(self._username)

    def _on_logout(self):
        reply = QMessageBox.question(
            self, "Logout", "Are you sure you want to log out?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._app.show_login()

    # ── Main build ─────────────────────────────────────────

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._build_sidebar(layout)
        self._build_main_area(layout)

    # ══════════════════════════════════════════════════════════
    # SIDEBAR
    # ══════════════════════════════════════════════════════════

    def _build_sidebar(self, parent_layout):
        sidebar = GradientSidebar(self)
        parent_layout.addWidget(sidebar)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 24, 16, 20)
        layout.setSpacing(0)

        # ── Logo + brand ──────────────────────────────────
        brand_layout = QHBoxLayout()
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(10)
        brand_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "assets", "logo.png"
        )

        if os.path.exists(logo_path):
            logo_lbl = QLabel()
            pixmap = QPixmap(logo_path).scaled(
                36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            logo_lbl.setPixmap(pixmap)
            logo_lbl.setStyleSheet("background: transparent;")
            brand_layout.addWidget(logo_lbl)

        title_lbl = QLabel("SignDesk")
        title_lbl.setStyleSheet(f"color: {'#FFFFFF' if is_dark() else '#2C3358'}; background: transparent;")
        _set_font(title_lbl, size=16, bold=True)
        brand_layout.addWidget(title_lbl)

        layout.addLayout(brand_layout)
        
        # Subtle divider
        div1 = QFrame()
        div1.setFixedHeight(1)
        div1.setStyleSheet(f"background-color: {c('border')}; border: none;")
        layout.addSpacing(16)
        layout.addWidget(div1)
        layout.addSpacing(16)

        # ── Navigation items ──────────────────────────────
        nav_layout = QVBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(2)

        nav_layout.addWidget(create_nav_item(sidebar, "📊", "Dashboard", is_active=True))
        nav_layout.addWidget(create_nav_item(sidebar, "🖐️", "Gesture Translator", command=self._launch_gesture_detection))
        nav_layout.addWidget(create_nav_item(sidebar, "📖", "Sign Dictionary"))
        nav_layout.addWidget(create_nav_item(sidebar, "📈", "Gesture History", command=self._launch_gesture_history))

        layout.addLayout(nav_layout)
        layout.addStretch()

        # ── Bottom section — divider + logout ─────────────
        div2 = QFrame()
        div2.setFixedHeight(1)
        div2.setStyleSheet(f"background-color: {c('border')}; border: none;")
        layout.addWidget(div2)
        layout.addSpacing(8)

        bottom_layout = QVBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(2)

        bottom_layout.addWidget(create_nav_item(sidebar, "⚙️", "Settings", command=self._launch_settings))

        # Custom logout item with red text
        logout_btn = QWidget()
        logout_btn.setFixedHeight(38)
        logout_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        logout_btn.setStyleSheet("background: transparent; border-radius: 10px;")
        lo_layout = QHBoxLayout(logout_btn)
        lo_layout.setContentsMargins(12, 0, 12, 0)
        lo_layout.setSpacing(8)
        
        lo_icon = QLabel("🚪")
        lo_icon.setFixedWidth(24)
        lo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lo_icon.setStyleSheet("color: #FF8A80; font-family: 'Segoe UI Emoji'; font-size: 14px; background: transparent;")
        lo_text = QLabel("Logout")
        lo_text.setStyleSheet("color: #FF8A80; background: transparent;")
        _set_font(lo_text, size=12, bold=False)
        
        lo_layout.addWidget(lo_icon)
        lo_layout.addWidget(lo_text)
        lo_layout.addStretch()

        # Hover logic for logout
        def enterEvent(e): logout_btn.setStyleSheet(f"background-color: {c('input_bg')}; border-radius: 10px;")
        def leaveEvent(e): logout_btn.setStyleSheet("background-color: transparent; border-radius: 10px;")
        def mousePressEvent(e): 
            if e.button() == Qt.MouseButton.LeftButton:
                self._on_logout()
        logout_btn.enterEvent = enterEvent
        logout_btn.leaveEvent = leaveEvent
        logout_btn.mousePressEvent = mousePressEvent

        bottom_layout.addWidget(logout_btn)
        layout.addLayout(bottom_layout)

    # ══════════════════════════════════════════════════════════
    # MAIN CONTENT AREA
    # ══════════════════════════════════════════════════════════

    def _build_main_area(self, parent_layout):
        main = QWidget()
        main.setStyleSheet(f"background-color: {c('bg_secondary')};")
        parent_layout.addWidget(main, stretch=1)

        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._build_topbar(main_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        scroll.setWidget(body)

        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(28, 8, 28, 20)
        body_layout.setSpacing(20)

        self._build_welcome(body_layout)
        self._build_stats(body_layout)
        self._build_status(body_layout)
        self._build_how_to_use(body_layout)
        self._build_footer(body_layout)
        
        body_layout.addStretch()
        main_layout.addWidget(scroll)

    # ── Top Bar ────────────────────────────────────────────

    def _build_topbar(self, parent_layout):
        topbar = QWidget()
        topbar.setFixedHeight(60)
        parent_layout.addWidget(topbar)

        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(28, 16, 28, 4)
        
        # Left: greeting
        greeting = QLabel(f"Welcome back, {self._username} 👋")
        greeting.setStyleSheet(f"color: {c('text_primary')};")
        _set_font(greeting, size=16, bold=True)
        layout.addWidget(greeting)
        
        layout.addStretch()

        # Right: search bar
        search_frame = QFrame()
        search_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {c('input_bg')};
                border: 1px solid {c('border')};
                border-radius: 18px;
            }}
        """)
        search_frame.setFixedHeight(36)
        s_layout = QHBoxLayout(search_frame)
        s_layout.setContentsMargins(12, 0, 12, 0)
        
        s_icon = QLabel("🔍")
        s_icon.setStyleSheet(f"color: {c('text_muted')}; font-family: 'Segoe UI Emoji'; border: none; background: transparent;")
        
        s_entry = QLineEdit()
        s_entry.setPlaceholderText("Search...")
        s_entry.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                background: transparent;
                color: {c('text_primary')};
                font-family: 'Segoe UI';
                font-size: 11px;
            }}
        """)
        s_entry.setFixedWidth(160)
        
        s_layout.addWidget(s_icon)
        s_layout.addWidget(s_entry)
        
        layout.addWidget(search_frame)
        layout.addSpacing(12)

        # Avatar circle
        avatar = QLabel(self._username[0].upper())
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(f"""
            QLabel {{
                background-color: {c('accent')};
                color: #FFFFFF;
                border-radius: 18px;
                font-family: 'Segoe UI';
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(avatar)

    # ── Welcome Banner ─────────────────────────────────────

    def _build_welcome(self, parent_layout):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {c('info_bg')};
                border: 1px solid #D1C4E9;
                border-radius: 14px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 18, 24, 18)
        
        title = QLabel(f"Good day, {self._username} 👋")
        title.setStyleSheet("color: #311B92; border: none; background: transparent;")
        _set_font(title, size=18, bold=True)
        
        desc = QLabel("You're successfully signed in to SignDesk. Your dashboard is ready.")
        desc.setStyleSheet(f"color: {c('info')}; border: none; background: transparent;")
        _set_font(desc, size=12)
        
        layout.addWidget(title)
        layout.addWidget(desc)
        
        parent_layout.addWidget(card)

    # ── Stats Row ──────────────────────────────────────────

    def _build_stats(self, parent_layout):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        stats_data = [
            ("Sessions today", "3",  "📊"),
            ("Avg. accuracy",  "91%", "🎯"),
            ("Signs learned",  "24",  "✋"),
        ]

        for label, value, icon in stats_data:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {c('bg_primary')};
                    border: 1px solid {c('border')};
                    border-radius: 12px;
                }}
            """)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(16, 14, 16, 14)
            c_layout.setSpacing(0)
            
            # Icon circle
            icon_lbl = QLabel(icon)
            icon_lbl.setFixedSize(32, 32)
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_lbl.setStyleSheet("""
                QLabel {
                    background-color: #EDE7F6;
                    border-radius: 16px;
                    font-family: 'Segoe UI Emoji';
                    font-size: 12px;
                    border: none;
                }
            """)
            
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {c('text_muted')}; border: none; background: transparent;")
            _set_font(lbl, size=11)
            
            val = QLabel(value)
            val.setStyleSheet(f"color: {c('text_primary')}; border: none; background: transparent;")
            _set_font(val, size=22, bold=True)
            
            c_layout.addWidget(icon_lbl)
            c_layout.addSpacing(6)
            c_layout.addWidget(lbl)
            c_layout.addSpacing(2)
            c_layout.addWidget(val)
            
            layout.addWidget(card)
            
        parent_layout.addWidget(row)

    # ── Module Cards ───────────────────────────────────────

    def _build_status(self, parent_layout):
        lbl = QLabel("System Status")
        lbl.setStyleSheet(f"color: {c('text_primary')}; background: transparent;")
        _set_font(lbl, size=13, bold=True)
        parent_layout.addWidget(lbl)

        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Re-resolve colors using theme indices where possible, or fallback
        status_items = [
            ("📷", "Camera",       "Ready",         c('info_bg'),  c('info')),
            ("🔒", "Privacy Mode", "Local-only",    "#E8F5E9",        "#2E7D32"),
            ("📈", "History Log",  self._history_status(), c('badge_gray_bg'),  c('badge_gray_fg')),
        ]

        for icon, title, value, bg, fg in status_items:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {c('bg_primary')};
                    border: 1px solid {c('border')};
                    border-radius: 12px;
                }}
            """)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(16, 14, 16, 14)
            
            icon_lbl = QLabel(icon)
            icon_lbl.setFixedSize(32, 32)
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_lbl.setStyleSheet(f"background-color: {bg}; border-radius: 10px; font-family: 'Segoe UI Emoji'; font-size: 13px; border: none;")
            
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet(f"color: {c('text_muted')}; border: none; background: transparent;")
            _set_font(t_lbl, size=11)
            
            v_lbl = QLabel(value)
            v_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v_lbl.setStyleSheet(f"background-color: {bg}; color: {fg}; border-radius: 10px; padding: 3px 10px; font-weight: bold; font-family: 'Segoe UI'; font-size: 11px; border: none;")
            
            c_layout.addWidget(icon_lbl)
            c_layout.addWidget(t_lbl)
            c_layout.addWidget(v_lbl, 0, Qt.AlignmentFlag.AlignLeft)
            
            layout.addWidget(card)
            
        parent_layout.addWidget(row)

    def _history_status(self) -> str:
        """Returns a short label for history logging state."""
        try:
            from core.config import config
            enabled = config.get("privacy.gesture_history_log", False)
            return "Enabled" if enabled else "Disabled"
        except Exception:
            return "Unknown"

    # ── How-to-Use Cards ───────────────────────────────────

    def _build_how_to_use(self, parent_layout):
        steps = [
            (
                "Open Gesture Translator",
                "Navigate to the \"Gesture Translator\" section from the main menu.",
            ),
            (
                "Allow Camera Access",
                "When prompted, allow the system to access your camera for real-time translation.",
            ),
            (
                "Start Recording",
                "Click the \"Start Recording\" button to begin capturing your gestures.",
            ),
            (
                "Perform Sign Language",
                "Make sure your hands are clearly visible in the frame as you sign.",
            ),
            (
                "View Translation",
                "The translation will appear in the result panel on the right.",
            ),
        ]
        panel = build_steps_panel(self, steps, card_width=120)
        parent_layout.addWidget(panel)

    # ── Footer ─────────────────────────────────────────────

    def _build_footer(self, parent_layout):
        footer = QLabel("SignDesk v1.0.0  •  © 2025 SignDesk Project  •  All rights reserved")
        footer.setStyleSheet(f"color: {c('text_muted')}; background: transparent;")
        _set_font(footer, size=11)
        parent_layout.addWidget(footer, 0, Qt.AlignmentFlag.AlignHCenter)