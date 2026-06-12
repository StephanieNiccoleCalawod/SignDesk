from PyQt6.QtWidgets import QFrame, QVBoxLayout
from theme.themes import c
from core.theme import ThemeSignal

class BaseCard(QFrame):
    """
    Standard reusable card matching the unified design system.
    Features a clean white (or dark) background and subtle border.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 14, 14, 14)
        self.layout.setSpacing(10)
        
        self._apply_style()
        
        try:
            ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass
            
    def _apply_style(self):
        self.setStyleSheet(f"""
            BaseCard {{
                background-color: {c('card_bg')};
                border: 1px solid {c('card_border')};
                border-radius: 12px;
            }}
        """)
        
    def _on_theme_changed(self, is_dark: bool):
        self._apply_style()
