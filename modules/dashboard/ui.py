

import os
from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout,
    QScrollArea, QLineEdit, QMessageBox, QGridLayout, QSizePolicy, QPushButton
)
from PyQt6.QtCore import Qt, QSize, QTimer, QRect, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QLinearGradient, QColor, QCursor

from core.theme import c, is_dark
from core.ui_helpers import build_steps_panel, _set_font, _add_shadow
from modules.dashboard.dashboard_service import get_dashboard_summary, search_dashboard


class SearchDropdown(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("searchDropdown")
        self.setStyleSheet(f"""
            QFrame#searchDropdown {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 8px;
            }}
        """)
        self.hide()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 4, 0, 4)
        self.layout.setSpacing(0)
        _add_shadow(self)

    def update_results(self, results, on_click):
        # Clear previous
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not results:
            lbl = QLabel("No results found")
            lbl.setStyleSheet(f"color: {c('text_muted')}; padding: 8px 16px;")
            _set_font(lbl, size=11)
            self.layout.addWidget(lbl)
            self.setFixedHeight(40)
            return

        for r in results:
            item_widget = QWidget()
            item_widget.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(16, 8, 16, 8)
            item_layout.setSpacing(2)
            
            t_lbl = QLabel(r["title"])
            t_lbl.setStyleSheet(f"color: {c('text_primary')}; font-weight: bold;")
            
            d_lbl = QLabel(f"{r['type']} - {r['desc']}")
            d_lbl.setStyleSheet(f"color: {c('text_muted')};")
            _set_font(d_lbl, size=10)
            
            item_layout.addWidget(t_lbl)
            item_layout.addWidget(d_lbl)
            
            # Hover styling
            def enter(e, w=item_widget): w.setStyleSheet(f"background-color: {c('input_bg')};")
            def leave(e, w=item_widget): w.setStyleSheet("background-color: transparent;")
            def press(e, r_action=r["action"]): on_click(r_action)
            item_widget.enterEvent = enter
            item_widget.leaveEvent = leave
            item_widget.mousePressEvent = press
            
            self.layout.addWidget(item_widget)
            
        self.adjustSize()
        # Cap height
        if self.height() > 300:
            self.setFixedHeight(300)

class ProfileDropdown(QFrame):
    def __init__(self, parent, user_data, on_action):
        super().__init__(parent)
        self.setObjectName("profileDropdown")
        self.setStyleSheet(f"""
            QFrame#profileDropdown {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 8px;
            }}
        """)
        self.hide()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 8, 0, 8)
        self.layout.setSpacing(0)
        _add_shadow(self)

        # Header
        header = QWidget()
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(16, 8, 16, 12)
        h_layout.setSpacing(2)
        
        n_lbl = QLabel(user_data.display_name)
        n_lbl.setStyleSheet(f"color: {c('text_primary')}; font-weight: bold; font-size: 14px;")
        
        e_lbl = QLabel(user_data.email)
        e_lbl.setStyleSheet(f"color: {c('text_muted')}; font-size: 11px;")
        
        r_lbl = QLabel(f"Role: {user_data.role}")
        r_lbl.setStyleSheet(f"color: {c('info')}; font-size: 11px;")
        
        h_layout.addWidget(n_lbl)
        h_layout.addWidget(e_lbl)
        h_layout.addWidget(r_lbl)
        self.layout.addWidget(header)
        
        # Div
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background-color: {c('border')}; border: none;")
        self.layout.addWidget(div)
        
        # Actions
        actions = [
            ("Profile", "settings"),
            ("Settings", "settings"),
            ("Privacy Settings", "privacy"),
            ("Logout", "logout")
        ]
        
        for text, action in actions:
            btn = QLabel(text)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            if action == "logout":
                btn.setStyleSheet(f"color: #FF8A80; padding: 10px 16px; font-weight: bold;")
            else:
                btn.setStyleSheet(f"color: {c('text_primary')}; padding: 10px 16px;")
            
            def enter(e, w=btn, act=action): 
                w.setStyleSheet(f"background-color: {c('input_bg')}; color: {'#FF8A80' if act == 'logout' else c('text_primary')}; padding: 10px 16px; font-weight: {'bold' if act == 'logout' else 'normal'};")
            def leave(e, w=btn, act=action): 
                w.setStyleSheet(f"background-color: transparent; color: {'#FF8A80' if act == 'logout' else c('text_primary')}; padding: 10px 16px; font-weight: {'bold' if act == 'logout' else 'normal'};")
            def press(e, a=action): 
                self.hide()
                on_action(a)
                
            btn.enterEvent = enter
            btn.leaveEvent = leave
            btn.mousePressEvent = press
            
            self.layout.addWidget(btn)
            
        self.adjustSize()

class DashboardPage(QWidget):
    def __init__(self, parent, app, username: str):
        super().__init__(parent)
        self._app = app
        self._username = username
        self.setStyleSheet(f"background-color: {c('bg_secondary')};")
        
        # We will keep references to labels to update them dynamically
        self._lbl_greeting_top = None
        self._lbl_greeting_card = None
        
        self._lbl_camera = None
        self._lbl_privacy = None
        self._lbl_history_log = None
        
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._execute_search)
        
        self._build()

        try:
            from core.theme import ThemeSignal
            ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

    def showEvent(self, event):
        self.refresh_dashboard()
        super().showEvent(event)

    def mousePressEvent(self, event):
        if hasattr(self, '_search_dropdown') and self._search_dropdown.isVisible():
            self._search_dropdown.hide()
        if hasattr(self, '_profile_dropdown') and self._profile_dropdown.isVisible():
            self._profile_dropdown.hide()
        super().mousePressEvent(event)

    def refresh_dashboard(self):
        summary = get_dashboard_summary(self._username)
        if not summary:
            return
            
        if self._lbl_greeting_top:
            self._lbl_greeting_top.setText(f"{summary.greeting}, {summary.display_name}")
        if self._lbl_greeting_card:
            self._lbl_greeting_card.setText(f"{summary.greeting}, {summary.display_name}")

        if self._lbl_camera:
            self._lbl_camera.setText(summary.camera_status)
            if summary.camera_status == "Ready":
                self._lbl_camera.parentWidget().setStyleSheet(f"background-color: {c('info_bg')}; border-radius: 8px; border: none;")
                self._lbl_camera.setStyleSheet(f"color: {c('info')}; background: transparent; border: none;")
            else:
                self._lbl_camera.parentWidget().setStyleSheet(f"background-color: {c('error_bg')}; border-radius: 8px; border: none;")
                self._lbl_camera.setStyleSheet(f"color: {c('error')}; background: transparent; border: none;")

        if self._lbl_privacy:
            self._lbl_privacy.setText(summary.privacy_mode)
            
        if self._lbl_history_log:
            self._lbl_history_log.setText("Enabled" if summary.history_logging_enabled else "Disabled")
            if summary.history_logging_enabled:
                self._lbl_history_log.parentWidget().setStyleSheet(f"background-color: {c('success_bg')}; border-radius: 8px; border: none;")
                self._lbl_history_log.setStyleSheet(f"color: {c('success')}; background: transparent; border: none;")
            else:
                self._lbl_history_log.parentWidget().setStyleSheet(f"background-color: {c('badge_gray_bg')}; border-radius: 8px; border: none;")
                self._lbl_history_log.setStyleSheet(f"color: {c('badge_gray_fg')}; background: transparent; border: none;")

    # ── Navigation callbacks ───────────────────────────────

    def _launch_gesture_detection(self):
        self._app.show_gesture_detection(self._username)

    def _launch_settings(self):
        if hasattr(self._app, 'show_settings'):
            self._app.show_settings(self._username)

    def _launch_gesture_history(self):
        self._app.show_gesture_history(self._username)

    def _launch_reference_chart(self):
        self._app.show_reference_chart(self._username)

    def _launch_flashcard_quiz(self):
        self._app.show_flashcard_quiz(self._username)

    def _show_dictionary_coming_soon(self):
        QMessageBox.information(self, "Coming Soon", "The Sign Dictionary feature is coming soon!")

    def _on_logout(self):
        reply = QMessageBox.question(
            self, "Logout", "Are you sure you want to log out?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._app.show_login()

    def _handle_action(self, action):
        if action == "dashboard":
            pass
        elif action == "gesture":
            self._launch_gesture_detection()
        elif action == "settings":
            self._launch_settings()
        elif action == "flashcards":
            self._launch_flashcard_quiz()
        elif action == "privacy":
            self._launch_settings() # settings handles privacy tab internally if needed
        elif action == "dictionary":
            self._show_dictionary_coming_soon()
        elif action == "history":
            self._launch_gesture_history()
        elif action == "logout":
            self._on_logout()

    def _on_search_text_changed(self, text):
        self._search_timer.start()
        if not text.strip() and hasattr(self, '_search_dropdown'):
            self._search_dropdown.hide()

    def _execute_search(self):
        text = self._search_entry.text().strip()
        if not text:
            if hasattr(self, '_search_dropdown'):
                self._search_dropdown.hide()
            return
            
        results = search_dashboard(text, self._username)
        
        # Position dropdown
        if not hasattr(self, '_search_dropdown'):
            self._search_dropdown = SearchDropdown(self)
            
        self._search_dropdown.update_results(results, self._handle_action)
        
        rect = self._search_frame.geometry()
        g_pos = self._search_frame.parentWidget().mapTo(self, rect.bottomLeft())
        
        self._search_dropdown.setFixedWidth(self._search_frame.width())
        self._search_dropdown.move(g_pos.x(), g_pos.y() + 4)
        self._search_dropdown.show()
        self._search_dropdown.raise_()

    def _show_profile_dropdown(self, pos):
        if not hasattr(self, '_profile_dropdown'):
            summary = get_dashboard_summary(self._username)
            if not summary:
                return
            self._profile_dropdown = ProfileDropdown(self, summary, self._handle_action)
            
        rect = self._avatar_widget.geometry()
        g_pos = self._avatar_widget.parentWidget().mapTo(self, rect.bottomLeft())
        
        self._profile_dropdown.adjustSize()
        x_pos = g_pos.x() + rect.width() - self._profile_dropdown.width()
        self._profile_dropdown.move(x_pos, g_pos.y() + 4)
        self._profile_dropdown.show()
        self._profile_dropdown.raise_()

    # ── Main build ─────────────────────────────────────────

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._build_main_area(layout)

    # ══════════════════════════════════════════════════════════
    # MAIN CONTENT AREA
    # ══════════════════════════════════════════════════════════

    def _build_main_area(self, parent_layout):
        self._main_content_widget = QWidget()
        self._main_content_widget.setStyleSheet(f"background-color: {c('bg_secondary')};")
        parent_layout.addWidget(self._main_content_widget, stretch=1)

        main_layout = QVBoxLayout(self._main_content_widget)
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
        body_layout.setContentsMargins(28, 12, 28, 24)
        body_layout.setSpacing(24)

        self._build_welcome(body_layout)
        self._build_status(body_layout)
        self._build_quizzes(body_layout)
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
        
        self._lbl_greeting_top = QLabel(f"Loading...")
        self._lbl_greeting_top.setStyleSheet(f"color: {c('text_primary')}; font-family: 'Segoe UI'; font-size: 22px; font-weight: bold;")
        layout.addWidget(self._lbl_greeting_top)
        
        layout.addStretch()

        self._search_frame = QFrame()
        self._search_frame.setObjectName("searchFrame")
        self._search_frame.setStyleSheet(f"""
            QFrame#searchFrame {{
                background-color: {c('input_bg')};
                border: 1px solid {c('border')};
                border-radius: 18px;
            }}
            QFrame#searchFrame QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        self._search_frame.setFixedHeight(36)
        self._search_frame.setMinimumWidth(200)
        self._search_frame.setMaximumWidth(280)
        s_layout = QHBoxLayout(self._search_frame)
        s_layout.setContentsMargins(14, 0, 14, 0)
        
        s_icon = QLabel("⌕")
        s_icon.setStyleSheet(f"color: {c('text_muted')}; border: none; background: transparent;")
        
        self._search_entry = QLineEdit()
        self._search_entry.setPlaceholderText("Search...")
        self._search_entry.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                background: transparent;
                color: {c('text_primary')};
                font-family: 'Segoe UI';
                font-size: 12px;
            }}
        """)
        self._search_entry.textChanged.connect(self._on_search_text_changed)
        
        s_layout.addWidget(s_icon)
        s_layout.addWidget(self._search_entry, stretch=1)
        
        layout.addWidget(self._search_frame)
        layout.addSpacing(12)

        self._avatar_widget = QLabel(self._username[0].upper())
        self._avatar_widget.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._avatar_widget.setFixedSize(36, 36)
        self._avatar_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._avatar_widget.setStyleSheet(f"""
            QLabel {{
                background-color: {c('accent')};
                color: #FFFFFF;
                border-radius: 18px;
                font-family: 'Segoe UI';
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        self._avatar_widget.mousePressEvent = self._show_profile_dropdown
        layout.addWidget(self._avatar_widget)

    # ── Welcome Banner ─────────────────────────────────────

    def _build_welcome(self, parent_layout):
        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(6, 6, 6, 8)
        wrapper_layout.setSpacing(0)

        card = QFrame()
        card.setObjectName("welcomeCard")
        card.setStyleSheet(f"""
            QFrame#welcomeCard {{
                background-color: {c('info_bg')};
                border: 1px solid #D1C4E9;
                border-radius: 14px;
            }}
            QFrame#welcomeCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 18, 24, 18)
        
        self._lbl_greeting_card = QLabel(f"Loading...")
        self._lbl_greeting_card.setStyleSheet("color: #311B92; font-family: 'Segoe UI'; font-size: 26px; font-weight: bold;")
        
        layout.addWidget(self._lbl_greeting_card)

        _add_shadow(card)
        wrapper_layout.addWidget(card)
        parent_layout.addWidget(wrapper)


    def _build_status(self, parent_layout):
        self._lbl_system_status_heading = QLabel("System Status")
        self._lbl_system_status_heading.setStyleSheet(f"color: {c('text_primary')}; background: transparent;")
        _set_font(self._lbl_system_status_heading, size=13, bold=True)
        parent_layout.addWidget(self._lbl_system_status_heading)

        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(6, 6, 6, 8)
        wrapper_layout.setSpacing(0)

        row = QWidget()
        row.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        self._lbl_camera = QLabel("Loading...")
        self._lbl_privacy = QLabel("Loading...")
        self._lbl_history_log = QLabel("Loading...")

        status_items = [
            ("Camera",       self._lbl_camera,      c('info_bg'),       c('info')),
            ("Privacy Mode", self._lbl_privacy,     "#E8F5E9",          "#2E7D32"),
            ("History Log",  self._lbl_history_log, c('badge_gray_bg'), c('badge_gray_fg')),
        ]

        for title, val_lbl, bg, fg in status_items:
            card = QFrame()
            card.setObjectName("statusCard")
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            card.setStyleSheet(f"""
                QFrame#statusCard {{
                    background-color: {c('bg_primary')};
                    border: 1px solid {c('border')};
                    border-radius: 12px;
                }}
                QFrame#statusCard QLabel {{
                    background: transparent;
                    border: none;
                }}
            """)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(20, 16, 20, 16)
            c_layout.setSpacing(6)

            t_lbl = QLabel(title)
            t_lbl.setStyleSheet(f"color: {c('text_primary')};")
            _set_font(t_lbl, size=11)

            badge_container = QWidget()
            badge_container.setFixedHeight(28)
            badge_container.setStyleSheet(f"""
                background-color: {bg};
                border-radius: 8px;
                border: none;
            """)
            badge_layout = QHBoxLayout(badge_container)
            badge_layout.setContentsMargins(14, 0, 14, 0)

            val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val_lbl.setStyleSheet(f"color: {fg}; background: transparent; border: none;")
            _set_font(val_lbl, size=11, bold=True)
            badge_layout.addWidget(val_lbl)

            c_layout.addWidget(t_lbl)
            c_layout.addWidget(badge_container, 0, Qt.AlignmentFlag.AlignLeft)

            _add_shadow(card)
            layout.addWidget(card, stretch=1)

        wrapper_layout.addWidget(row)
        parent_layout.addWidget(wrapper)

    def _build_how_to_use(self, parent_layout):
        steps = [
            (
                "Open Camera Practice",
                "Select \"Camera Practice\" from the sidebar to start a live gesture session.",
            ),
            (
                "Allow Camera Access",
                "Make sure your webcam is enabled in Settings so the live feed can start.",
            ),
            (
                "Pick a Letter Set",
                "Choose a set (e.g. Set 1 A–E) from the dropdown, then press Start.",
            ),
            (
                "Perform the Sign",
                "Hold the target letter sign clearly in front of the camera until the hold timer fills.",
            ),
            (
                "Review Your Score",
                "See your accuracy in the Session Score panel, then try the Flashcard Quiz to test yourself.",
            ),
        ]
        panel = build_steps_panel(self, steps, card_width=155)
        parent_layout.addWidget(panel)

    def _build_footer(self, parent_layout):
        self._lbl_footer = QLabel("SignDesk v1.0.0  •  © 2026 SignDesk Project  •  All rights reserved")
        self._lbl_footer.setStyleSheet(f"color: {c('text_muted')}; background: transparent;")
        _set_font(self._lbl_footer, size=11)
        parent_layout.addWidget(self._lbl_footer, 0, Qt.AlignmentFlag.AlignHCenter)

    def _build_quizzes(self, parent_layout):
        self._lbl_quiz_modes_heading = QLabel("Quiz Modes")
        self._lbl_quiz_modes_heading.setStyleSheet(f"color: {c('text_primary')}; background: transparent;")
        _set_font(self._lbl_quiz_modes_heading, size=13, bold=True)
        parent_layout.addWidget(self._lbl_quiz_modes_heading)

        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(6, 6, 6, 8)
        wrapper_layout.setSpacing(0)

        card = QFrame()
        card.setObjectName("quizCard")
        card.setStyleSheet(f"""
            QFrame#quizCard {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 12px;
            }}
            QFrame#quizCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        
        c_layout = QHBoxLayout(card)
        c_layout.setContentsMargins(20, 16, 20, 16)
        c_layout.setSpacing(14)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        title_lbl = QLabel("Flashcard Recognition Quiz")
        title_lbl.setStyleSheet(f"color: {c('text_primary')};")
        _set_font(title_lbl, size=14, bold=True)
        info_layout.addWidget(title_lbl)

        desc_lbl = QLabel("Test your memory! Identify ASL handshapes and build your scoring streak.")
        desc_lbl.setStyleSheet(f"color: {c('text_secondary')};")
        _set_font(desc_lbl, size=11)
        info_layout.addWidget(desc_lbl)

        c_layout.addLayout(info_layout, stretch=1)

        start_btn = QPushButton("Start Quiz")
        start_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        start_btn.setFixedSize(110, 32)
        start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c('accent')};
                color: #FFFFFF;
                border: none;
                border-radius: 16px;
                font-family: 'Segoe UI';
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {c('accent_hover')};
            }}
        """)
        start_btn.clicked.connect(self._launch_flashcard_quiz)
        c_layout.addWidget(start_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        _add_shadow(card)
        wrapper_layout.addWidget(card)
        parent_layout.addWidget(wrapper)

    def _on_theme_changed(self, is_dark: bool):
        self._update_styles()

    def _update_styles(self):
        dark = is_dark()
        self.setStyleSheet(f"background-color: {c('bg_secondary')};")
        if hasattr(self, '_main_content_widget') and self._main_content_widget:
            self._main_content_widget.setStyleSheet(f"background-color: {c('bg_secondary')};")
        
        if hasattr(self, '_lbl_greeting_top') and self._lbl_greeting_top:
            self._lbl_greeting_top.setStyleSheet(f"color: {c('text_primary')}; font-family: 'Segoe UI'; font-size: 22px; font-weight: bold;")
        if hasattr(self, '_search_frame') and self._search_frame:
            self._search_frame.setStyleSheet(f"""
                QFrame#searchFrame {{
                    background-color: {c('input_bg')};
                    border: 1px solid {c('border')};
                    border-radius: 18px;
                }}
                QFrame#searchFrame QLabel {{
                    background: transparent;
                    border: none;
                }}
            """)
        if hasattr(self, '_search_entry') and self._search_entry:
            self._search_entry.setStyleSheet(f"""
                QLineEdit {{
                    border: none;
                    background: transparent;
                    color: {c('text_primary')};
                    font-family: 'Segoe UI';
                    font-size: 12px;
                }}
            """)
        if hasattr(self, '_avatar_widget') and self._avatar_widget:
            self._avatar_widget.setStyleSheet(f"""
                QLabel {{
                    background-color: {c('accent')};
                    color: #FFFFFF;
                    border-radius: 18px;
                    font-family: 'Segoe UI';
                    font-size: 14px;
                    font-weight: bold;
                }}
            """)
            
        for card in self.findChildren(QFrame, "welcomeCard"):
            card.setStyleSheet(f"""
                QFrame#welcomeCard {{
                    background-color: {c('info_bg')};
                    border: 1px solid #D1C4E9;
                    border-radius: 14px;
                }}
                QFrame#welcomeCard QLabel {{
                    background: transparent;
                    border: none;
                }}
            """)
        for card in self.findChildren(QFrame, "statCard"):
            card.setStyleSheet(f"""
                QFrame#statCard {{
                    background-color: {c('bg_primary')};
                    border: 1px solid {c('border')};
                    border-radius: 12px;
                }}
                QFrame#statCard QLabel {{
                    background: transparent;
                    border: none;
                }}
            """)
        for card in self.findChildren(QFrame, "statusCard"):
            card.setStyleSheet(f"""
                QFrame#statusCard {{
                    background-color: {c('bg_primary')};
                    border: 1px solid {c('border')};
                    border-radius: 12px;
                }}
                QFrame#statusCard QLabel {{
                    background: transparent;
                    border: none;
                }}
            """)
        for card in self.findChildren(QFrame, "quizCard"):
            card.setStyleSheet(f"""
                QFrame#quizCard {{
                    background-color: {c('bg_primary')};
                    border: 1px solid {c('border')};
                    border-radius: 12px;
                }}
                QFrame#quizCard QLabel {{
                    background: transparent;
                    border: none;
                }}
            """)
            
        if hasattr(self, '_lbl_system_status_heading') and self._lbl_system_status_heading:
            self._lbl_system_status_heading.setStyleSheet(f"color: {c('text_primary')}; background: transparent;")
        # _lbl_how_to_use_heading removed; heading is now part of build_steps_panel
        if hasattr(self, '_lbl_quiz_modes_heading') and self._lbl_quiz_modes_heading:
            self._lbl_quiz_modes_heading.setStyleSheet(f"color: {c('text_primary')}; background: transparent;")
        if hasattr(self, '_lbl_footer') and self._lbl_footer:
            self._lbl_footer.setStyleSheet(f"color: {c('text_muted')}; background: transparent;")
            
        for card in self.findChildren(QFrame, "statCard") + self.findChildren(QFrame, "statusCard"):
            for lbl in card.findChildren(QLabel):
                if lbl not in [self._lbl_camera, self._lbl_privacy, self._lbl_history_log]:
                    lbl.setStyleSheet(f"color: {c('text_primary')}; background: transparent; border: none;")
                    
        for card in self.findChildren(QFrame, "quizCard"):
            for lbl in card.findChildren(QLabel):
                if lbl.text() == "Flashcard Recognition Quiz":
                    lbl.setStyleSheet(f"color: {c('text_primary')}; background: transparent; border: none;")
                elif "streak" in lbl.text().lower() or "test your memory" in lbl.text().lower():
                    lbl.setStyleSheet(f"color: {c('text_secondary')}; background: transparent; border: none;")
       
        card_bg     = "#1E1E2E" if dark else "#FFFFFF"
        card_border = "#3D3D5C" if dark else "#E2E8F0"
        title_color = "#C4B5FD" if dark else "#1E293B"
        desc_color  = "#94A3B8" if dark else "#475569"
        for card in self.findChildren(QFrame, "stepCard"):
            card.setStyleSheet(f"""
                QFrame#stepCard {{
                    background-color: {card_bg};
                    border: 1px solid {card_border};
                    border-radius: 14px;
                }}
                QFrame#stepCard QLabel {{
                    background: transparent;
                    border: none;
                }}
            """)
            for div in card.findChildren(QFrame, "stepDivider"):
                div.setStyleSheet(f"QFrame#stepDivider {{ background: {card_border}; border: none; border-radius: 0px; }}")
            for lbl in card.findChildren(QLabel, "stepTitle"):
                lbl.setStyleSheet(f"color: {title_color};")
            for lbl in card.findChildren(QLabel, "stepDesc"):
                lbl.setStyleSheet(f"color: {desc_color};")
               
        self.refresh_dashboard()