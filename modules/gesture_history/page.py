

import os
from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout,
    QScrollArea, QPushButton, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QCursor, QPainter, QLinearGradient, QColor

from core.theme import c, ThemeSignal
from core.ui_helpers import _set_font
from modules.gesture_history.ui import GestureHistorySection
from modules.gesture_history.backend import init_history_db




class GestureHistoryPage(QWidget):

    def __init__(self, parent, app, username: str):
        super().__init__(parent)
        self._app      = app
        self._username = username
        self.setStyleSheet(f"background-color: {c('bg_secondary')};")
        init_history_db()
        self._build()

        try:
            ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top bar
        self.topbar = QWidget()
        tb_layout = QHBoxLayout(self.topbar)
        tb_layout.setContentsMargins(28, 16, 28, 8)
        tb_layout.setSpacing(24)

        card = QFrame()
        card.setObjectName("welcomeCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        card.setStyleSheet(f"""
            QFrame#welcomeCard {{
                background-color: {c('info_bg')};
                border: 1px solid {c('welcome_border')};
                border-radius: 14px;
            }}
            QFrame#welcomeCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 18, 24, 18)

        self.greeting = QLabel("Gesture History")
        self.greeting.setStyleSheet(f"color: {c('welcome_title')}; font-family: 'Segoe UI'; font-size: 26px; font-weight: bold;")
        card_layout.addWidget(self.greeting, 0, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        
        tb_layout.addWidget(card, stretch=1)

        # Avatar circle
        self.avatar = QLabel(self._username[0].upper())
        self.avatar.setFixedSize(36, 36)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar.setStyleSheet(f"""
            QLabel {{
                background-color: {c('accent')};
                color: #FFFFFF;
                border-radius: 18px;
                font-family: 'Segoe UI';
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        tb_layout.addWidget(self.avatar, 0, Qt.AlignmentFlag.AlignVCenter)

        main_layout.addWidget(self.topbar)

        # Scrollable body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        scroll.setWidget(body)

        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(28, 12, 28, 24)
        body_layout.setSpacing(16)

        # Section — scoped by username, no user_id needed
        section = GestureHistorySection(body, username=self._username)
        body_layout.addWidget(section, stretch=1)

        main_layout.addWidget(scroll, stretch=1)

    # ── Navigation ─────────────────────────────────────────────────────────────

    def _on_back(self):
        self._app.show_dashboard(self._username)

    def _on_logout(self):
        reply = QMessageBox.question(
            self, "Logout", "Are you sure you want to log out?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._app.show_login()

    def _on_theme_changed(self, is_dark: bool):
        self._update_styles()

    def _update_styles(self):
        self.setStyleSheet(f"background-color: {c('bg_secondary')};")
        if hasattr(self, 'topbar') and self.topbar:
            self.topbar.setStyleSheet("background: transparent; border: none;")
        if hasattr(self, 'greeting') and self.greeting:
            self.greeting.setStyleSheet(f"color: {c('welcome_title')}; font-family: 'Segoe UI'; font-size: 26px; font-weight: bold;")
            for welcome_card in self.findChildren(QFrame, "welcomeCard"):
                welcome_card.setStyleSheet(f"""
                    QFrame#welcomeCard {{
                        background-color: {c('info_bg')};
                        border: 1px solid {c('welcome_border')};
                        border-radius: 14px;
                    }}
                    QFrame#welcomeCard QLabel {{
                        background: transparent;
                        border: none;
                    }}
                """)
        if hasattr(self, 'avatar') and self.avatar:
            self.avatar.setStyleSheet(f"""
                QLabel {{
                    background-color: {c('accent')};
                    color: #FFFFFF;
                    border-radius: 18px;
                    font-family: 'Segoe UI';
                    font-size: 14px;
                    font-weight: bold;
                }}
            """)