from PyQt6.QtWidgets import QLabel
from theme.themes import c
from theme.typography import SIZE_SM
from core.theme import ThemeSignal

class FPSBadge(QLabel):
    """
    Badge for displaying the current FPS.
    """
    def __init__(self, parent=None):
        super().__init__("FPS: --", parent)
        self._apply_style()
        
        try:
            ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass
            
    def _apply_style(self):
        self.setStyleSheet(f"""
            background-color: {c('badge_bg')};
            color: {c('text_muted')};
            padding: 2px 8px;
            border-radius: 10px;
            font-size: {SIZE_SM}px;
        """)
        
    def _on_theme_changed(self, is_dark: bool):
        self._apply_style()
        
    def set_fps(self, fps: int):
        self.setText(f"FPS: {fps}")
