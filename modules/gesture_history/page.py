"""
modules/gesture_history/page.py
Full-page wrapper for GestureHistorySection.
PyQt6 migration.
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout,
    QScrollArea, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QCursor

from core.theme import c
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

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self._build_navbar(layout)
        self._build_body(layout)

    def _build_navbar(self, parent_layout):
        navbar = QFrame()
        navbar.setFixedHeight(60)
        navbar.setStyleSheet(f"background-color: {c('panel_left', dark=True)}; border: none;")
        
        layout = QHBoxLayout(navbar)
        layout.setContentsMargins(20, 0, 20, 0)
        
        # Logo
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
            layout.addWidget(logo_lbl)
            layout.addSpacing(10)

        title = QLabel("SignDesk")
        title.setStyleSheet(f"color: {c('text_primary', dark=True)}; background: transparent;")
        title.setStyleSheet("font-family: 'Georgia'; font-size: 18px; font-weight: bold; color: #FFFFFF; background: transparent;")
        layout.addWidget(title)

        layout.addStretch()

        # Buttons
        btn_back = QPushButton("← Dashboard")
        btn_back.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_back.setFixedSize(120, 32)
        btn_back.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: #FFFFFF;
                border: 1px solid #FFFFFF;
                border-radius: 6px;
                font-family: 'Segoe UI';
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {c('panel_left_end', dark=True)};
            }}
        """)
        btn_back.clicked.connect(self._on_back)
        layout.addWidget(btn_back)
        
        layout.addSpacing(8)
        
        btn_logout = QPushButton("Logout →")
        btn_logout.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_logout.setFixedSize(90, 32)
        btn_logout.setStyleSheet(f"""
            QPushButton {{
                background-color: {c('error')};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-family: 'Segoe UI';
                font-size: 13px;
            }}
        """)
        btn_logout.clicked.connect(self._on_logout)
        layout.addWidget(btn_logout)

        parent_layout.addWidget(navbar)

    def _build_body(self, parent_layout):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        scroll.setWidget(body)

        layout = QVBoxLayout(body)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Page title
        title = QLabel("Gesture History")
        title.setStyleSheet(f"color: {c('text_primary')}; background: transparent;")
        _set_font(title, size=18, bold=True)
        layout.addWidget(title)

        # Section
        user_id = getattr(self._app, 'current_user_id', None)
        section = GestureHistorySection(body, user_id=user_id)
        layout.addWidget(section, stretch=1)

        parent_layout.addWidget(scroll, stretch=1)

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
