from PyQt6.QtWidgets import QProgressBar
from theme.themes import c
from core.theme import ThemeSignal

class ProgressBar(QProgressBar):
    """
    Standard progress bar matching the track and fill design.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextVisible(False)
        self.setFixedHeight(6)
        self._apply_style()
        
        try:
            ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass
            
    def _apply_style(self):
        self.setStyleSheet(f"""
            QProgressBar {{
                background-color: {c('progress_bg')};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {c('progress_fill')};
                border-radius: 3px;
            }}
        """)
        
    def _on_theme_changed(self, is_dark: bool):
        self._apply_style()
