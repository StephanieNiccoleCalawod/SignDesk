from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QLabel, QFrame
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from core.theme import c, ThemeSignal
from core.ui_helpers import _set_font

class SearchBar(QWidget):
    """
    A reusable search bar component with a clean interface, search icon,
    and a dynamic clear button.
    """
    text_changed = pyqtSignal(str)
    cleared = pyqtSignal()

    def __init__(self, placeholder: str = "Search letters, descriptions, tips...", parent=None):
        super().__init__(parent)
        self.placeholder = placeholder
        self.setObjectName("searchBarContainer")
        
        self._build_ui()
        self._update_styles()
        
        try:
            ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # Search wrapper to group icon + input + clear button
        self.wrapper = QFrame()
        self.wrapper.setObjectName("searchWrapper")
        self.wrapper.setFixedHeight(36)
        
        wrapper_layout = QHBoxLayout(self.wrapper)
        wrapper_layout.setContentsMargins(14, 0, 14, 0)
        wrapper_layout.setSpacing(8)
        
        # Magnifying glass / Search icon
        self.search_icon = QLabel("🔍")
        self.search_icon.setStyleSheet("background: transparent; border: none;")
        _set_font(self.search_icon, size=12)
        wrapper_layout.addWidget(self.search_icon)
        
        # Line Edit Input
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(self.placeholder)
        self.input_field.setFrame(False)
        self.input_field.setObjectName("searchInput")
        self.input_field.textChanged.connect(self._on_text_changed)
        wrapper_layout.addWidget(self.input_field, stretch=1)
        
        # Clear button (visible only when there is text)
        self.clear_btn = QPushButton("×")
        self.clear_btn.setFixedSize(20, 20)
        self.clear_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.clear_btn.setVisible(False)
        self.clear_btn.clicked.connect(self.clear_search)
        wrapper_layout.addWidget(self.clear_btn)
        
        layout.addWidget(self.wrapper)

    def _update_styles(self):
        bg_color = c("input_bg")
        border_color = c("input_border")
        focus_color = c("accent")
        text_color = c("text_primary")
        muted_color = c("text_muted")
        
        self.wrapper.setStyleSheet(f"""
            QFrame#searchWrapper {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 18px;
            }}
            QFrame#searchWrapper:focus-within {{
                border: 1px solid {focus_color};
            }}
        """)
        
        self.input_field.setStyleSheet(f"""
            QLineEdit#searchInput {{
                color: {text_color};
                background: transparent;
                border: none;
                padding: 4px 0px;
            }}
        """)
        _set_font(self.input_field, size=13)
        
        self.search_icon.setStyleSheet(f"color: {muted_color}; background: transparent; border: none;")
        
        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {muted_color};
                border: none;
                font-size: 16px;
                font-weight: bold;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {c('border')};
                color: {c('error')};
            }}
        """)

    def _on_theme_changed(self, is_dark: bool):
        self._update_styles()

    def _on_text_changed(self, text: str):
        self.clear_btn.setVisible(len(text) > 0)
        self.text_changed.emit(text)

    def text(self) -> str:
        return self.input_field.text()

    def set_text(self, text: str):
        self.input_field.setText(text)

    def clear_search(self):
        self.input_field.clear()
        self.input_field.setFocus()
        self.cleared.emit()
