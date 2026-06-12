from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from core.theme import c, ThemeSignal
from core.ui_helpers import _set_font

class FilterPill(QPushButton):
    """
    A rounded filter pill component used to select categories or filter criteria.
    Features active/inactive states and theme-aware colors.
    """
    selected = pyqtSignal(str) # Emits label text when selected

    def __init__(self, text: str, is_active: bool = False, parent=None):
        super().__init__(text, parent)
        self.pill_text = text
        self._is_active = is_active
        self.setObjectName("filterPill")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(32)
        
        self._update_styles()
        
        try:
            ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

    def _update_styles(self):
        accent_color = c("accent")
        
        if self._is_active:
            bg_color = accent_color
            text_color = "#FFFFFF"
            border_style = "none"
        else:
            bg_color = c("bg_primary")
            text_color = c("text_secondary")
            border_style = f"1px solid {c('border')}"

        self.setStyleSheet(f"""
            QPushButton#filterPill {{
                background-color: {bg_color};
                color: {text_color};
                border: {border_style};
                border-radius: 16px;
                padding: 4px 16px;
            }}
        """)
        _set_font(self, size=12, bold=self._is_active)

    def _on_theme_changed(self, is_dark: bool):
        self._update_styles()

    def set_active(self, active: bool):
        self._is_active = active
        self._update_styles()

    def is_active(self) -> bool:
        return self._is_active

    def text(self) -> str:
        return self.pill_text

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.pill_text)
        super().mousePressEvent(event)
