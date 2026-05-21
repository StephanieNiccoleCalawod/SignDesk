"""
modules/gesture_history/page.py
Full-page wrapper for GestureHistorySection.
PyQt6 migration — sidebar layout matching dashboard/gesture pages.
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout,
    QScrollArea, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QCursor, QPainter, QLinearGradient, QColor

from core.theme import c
from core.ui_helpers import _set_font
from modules.gesture_history.ui import GestureHistorySection
from modules.gesture_history.backend import init_history_db


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
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._build_sidebar(layout)
        self._build_body(layout)

    def _build_sidebar(self, parent_layout):
        from core.theme import is_dark
        dark = is_dark()

        title_col   = "#FFFFFF" if dark else "#2C3358"
        divider_col = "#4A4590" if dark else c("border")
        hover_col   = "#3D4470" if dark else "#D6D3E8"

        sidebar = GradientSidebar(self)
        parent_layout.addWidget(sidebar)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 24, 16, 20)
        layout.setSpacing(0)

        # ── Logo + brand ──────────────────────────────────
        brand = QHBoxLayout()
        brand.setSpacing(10)
        brand.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "assets", "logo.png"
        )
        if os.path.exists(logo_path):
            logo_lbl = QLabel()
            pixmap = QPixmap(logo_path).scaled(
                36, 36, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            logo_lbl.setPixmap(pixmap)
            logo_lbl.setStyleSheet("background: transparent;")
            brand.addWidget(logo_lbl)

        title = QLabel("SignDesk")
        title.setStyleSheet(f"color: {title_col}; background: transparent;")
        _set_font(title, 16, bold=True)
        brand.addWidget(title)
        layout.addLayout(brand)

        # Divider
        layout.addSpacing(16)
        div1 = QFrame()
        div1.setFixedHeight(1)
        div1.setStyleSheet(f"background-color: {divider_col}; border: none;")
        layout.addWidget(div1)
        layout.addSpacing(16)

        # ── Back to Dashboard — accent pill button ────────
        btn_back = QPushButton("←  Back to Dashboard")
        btn_back.setFixedHeight(36)
        btn_back.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_back.setStyleSheet(f"""
            QPushButton {{
                background-color: #495086;
                color: #FFFFFF;
                border: none;
                border-radius: 18px;
                font-family: 'Segoe UI';
                font-size: 12px;
                font-weight: bold;
                padding: 0px 16px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: #3F4678;
            }}
        """)
        btn_back.clicked.connect(self._on_back)
        layout.addWidget(btn_back)

        layout.addStretch()

        # ── Bottom: divider + logout ──────────────────────
        div2 = QFrame()
        div2.setFixedHeight(1)
        div2.setStyleSheet(f"background-color: {divider_col}; border: none;")
        layout.addWidget(div2)
        layout.addSpacing(8)

        logout_btn = QPushButton("→  Logout")
        logout_btn.setFixedHeight(38)
        logout_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        logout_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: #FF8A80; text-align: left;
                padding-left: 12px; border-radius: 10px;
                font-family: 'Segoe UI'; font-size: 13px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {hover_col}; }}
        """)
        logout_btn.clicked.connect(self._on_logout)
        layout.addWidget(logout_btn)

    def _build_body(self, parent_layout):
        main = QWidget()
        main.setStyleSheet(f"background-color: {c('bg_secondary')};")
        parent_layout.addWidget(main, stretch=1)

        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top bar
        topbar = QWidget()
        topbar.setFixedHeight(60)
        tb_layout = QHBoxLayout(topbar)
        tb_layout.setContentsMargins(28, 16, 28, 4)

        greeting = QLabel("Gesture History")
        greeting.setStyleSheet(f"color: {c('text_primary')};")
        _set_font(greeting, size=16, bold=True)
        tb_layout.addWidget(greeting)
        tb_layout.addStretch()

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
        tb_layout.addWidget(avatar)

        main_layout.addWidget(topbar)

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

        # Section
        user_id = getattr(self._app, 'current_user_id', None)
        section = GestureHistorySection(body, user_id=user_id)
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
