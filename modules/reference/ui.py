

import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QGridLayout, QFrame, QMessageBox, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor

from components.layout.sidebar import Sidebar
from components.reference import LetterCard, FilterPill, DetailPanel
from core.theme import c, ThemeSignal
from core.ui_helpers import _set_font
from modules.reference.repository import get_all_letters

class ReferencePage(QWidget):
    """
    The ASL manual alphabet reference chart page.
    Combines search, filter groups, grid of letter cards, and a side detail panel.
    """

    def __init__(self, parent, app, username: str):
        super().__init__(parent)
        self._app = app
        self._username = username
        self.setObjectName("referencePage")

        # Load letter metadata from repository
        self.all_letters = get_all_letters()

        self._build()
        self._update_styles()

        # Connect to theme changes to dynamically update styles
        try:
            ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

    def _build(self):
        # Main Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top Bar: Heading & User profile avatar
        topbar = QWidget()
        tb_layout = QHBoxLayout(topbar)
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
        
        self.greeting = QLabel("ASL Alphabet Reference")
        self.greeting.setStyleSheet(f"color: {c('welcome_title')}; font-family: 'Segoe UI'; font-size: 26px; font-weight: bold;")
        
        card_layout.addWidget(self.greeting, 0, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        tb_layout.addWidget(card, stretch=1)

        self.avatar = QLabel(self._username[0].upper() if self._username else "?")
        self.avatar.setFixedSize(36, 36)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tb_layout.addWidget(self.avatar, 0, Qt.AlignmentFlag.AlignVCenter)
        
        layout.addWidget(topbar)

        # Toolbar: Filter Pills (Left) & Search Bar (Right)
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(28, 8, 28, 12)
        toolbar_layout.setSpacing(16)

        # Filter Pills Layout container
        pills_container = QWidget()
        pills_layout = QHBoxLayout(pills_container)
        pills_layout.setContentsMargins(0, 0, 0, 0)
        pills_layout.setSpacing(8)

        self.filter_pills = {}
        filter_names = ["All", "A-M", "N-Z", "Vowels", "Consonants"]
        for f in filter_names:
            pill = FilterPill(f, is_active=(f == "All"))
            pill.selected.connect(self._on_filter_selected)
            pills_layout.addWidget(pill)
            self.filter_pills[f] = pill

        toolbar_layout.addWidget(pills_container)
        toolbar_layout.addStretch()

        # Search Bar removed

        layout.addWidget(toolbar)

        # Content Split Layout: Grid scroll area (Left) & Detail Panel (Right)
        content_split = QWidget()
        content_split_layout = QHBoxLayout(content_split)
        content_split_layout.setContentsMargins(0, 0, 0, 0)
        content_split_layout.setSpacing(0)

        # Scrollable letter grid (Left)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        grid_container = QWidget()
        grid_container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(grid_container)
        self.grid_layout.setContentsMargins(28, 12, 28, 24)
        self.grid_layout.setSpacing(20)

        # Pre-set column sizing for 4-column layout
        for col_idx in range(4):
            self.grid_layout.setColumnStretch(col_idx, 1)

        scroll.setWidget(grid_container)
        content_split_layout.addWidget(scroll, stretch=1)

        # Detail Panel (Right)
        self.detail_panel = DetailPanel(self)
        self.detail_panel.practice_requested.connect(self._on_practice_requested)
        content_split_layout.addWidget(self.detail_panel)

        layout.addWidget(content_split, stretch=1)

    def _update_styles(self):
        self.setStyleSheet(f"QWidget#referencePage {{ background-color: {c('bg_secondary')}; }}")
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

    def _on_theme_changed(self, is_dark: bool):
        self._update_styles()

    def showEvent(self, event):
        super().showEvent(event)
        self._filter_and_search()

    def _on_filter_selected(self, selected_filter: str):
        # Update active filter states
        for name, pill in self.filter_pills.items():
            pill.set_active(name == selected_filter)
        self._filter_and_search()

    def _filter_and_search(self):
        # Retrieve values
        active_filter = "All"
        for name, pill in self.filter_pills.items():
            if pill.is_active():
                active_filter = name
                break

        # Match criteria
        filtered = []
        for letter_obj in self.all_letters:
            letter_char = letter_obj.letter
            
            # 1. Check filter boundaries
            matches_filter = False
            if active_filter == "All":
                matches_filter = True
            elif active_filter == "A-M":
                matches_filter = "A" <= letter_char <= "M"
            elif active_filter == "N-Z":
                matches_filter = "N" <= letter_char <= "Z"
            elif active_filter == "Vowels":
                matches_filter = letter_char in ["A", "E", "I", "O", "U"]
            elif active_filter == "Consonants":
                matches_filter = letter_char not in ["A", "E", "I", "O", "U"]

            if matches_filter:
                filtered.append(letter_obj)

        self._render_grid(filtered)

    def _clear_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

    def _render_grid(self, letters):
        self._clear_grid()

        if not letters:
            empty_lbl = QLabel("No letters match search or filter settings.")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet(f"color: {c('text_muted')}; margin-top: 50px;")
            _set_font(empty_lbl, size=13)
            self.grid_layout.addWidget(empty_lbl, 0, 0, 1, 4)
            return

        cols = 4
        for i, letter_obj in enumerate(letters):
            card = LetterCard(letter_obj.letter, letter_obj.image_path, parent=self)
            card.clicked.connect(self._on_card_clicked)
            
            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(card, row, col)

        # Set stretch on subsequent row to force grid to top alignment
        self.grid_layout.setRowStretch(self.grid_layout.rowCount(), 1)

    def _on_card_clicked(self, letter: str):
        # Load details into details side panel
        match = None
        for letter_obj in self.all_letters:
            if letter_obj.letter == letter:
                match = letter_obj
                break

        if match:
            self.detail_panel.set_letter_details(
                letter=match.letter,
                image_path=match.image_path,
                description=match.description,
                tip=match.tip
            )

    def _on_practice_requested(self, letter: str):
        # Transition context to Camera Practice
        if hasattr(self._app, "show_gesture_detection"):
            self._app.show_gesture_detection(self._username, target_letter=letter)

    def _on_navigation_requested(self, key: str):
        if key == "dashboard":
            self._app.show_dashboard(self._username)
        elif key == "camera":
            self._app.show_gesture_detection(self._username)
        elif key == "flashcards":
            self._app.show_flashcard_quiz(self._username)
        elif key == "reference":
            pass # Already here
        elif key == "settings":
            self._app.show_settings(self._username)
        elif key == "history":
            self._app.show_gesture_history(self._username)

    def _on_logout(self):
        reply = QMessageBox.question(
            self, "Logout", "Are you sure you want to log out?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._app.show_login()
