from PyQt6.QtWidgets import QLabel, QVBoxLayout
from PyQt6.QtCore import Qt
from theme.themes import c
from theme.typography import SIZE_XS, SIZE_XL

from .base_card import BaseCard

class StatCard(BaseCard):
    """
    Card specifically for displaying a single numerical statistic
    with a small uppercase label.
    """
    def __init__(self, title: str, value: str = "0", parent=None):
        # BaseCard.__init__ calls self._apply_style() and registers connection.
        # But during BaseCard.__init__, subclass fields like val_lbl and title_lbl do not exist yet.
        # Therefore, we call super().__init__ first, then build labels, and then call self._apply_style() again to style them.
        self.val_lbl = None
        self.title_lbl = None
        super().__init__(parent)
        
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(2)
        
        self.val_lbl = QLabel(value)
        self.val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.title_lbl = QLabel(title)
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.layout.addWidget(self.val_lbl)
        self.layout.addWidget(self.title_lbl)
        
        self._apply_style()
        
    def _apply_style(self):
        self.setStyleSheet(f"""
            StatCard {{
                background-color: {c('card_bg_secondary')};
                border: none;
                border-radius: 8px;
            }}
        """)
        if hasattr(self, 'val_lbl') and self.val_lbl:
            self.val_lbl.setStyleSheet(f"color: {c('text_primary')}; font-size: {SIZE_XL}px; font-weight: bold; border: none; background: transparent;")
        if hasattr(self, 'title_lbl') and self.title_lbl:
            self.title_lbl.setStyleSheet(f"color: {c('text_muted')}; font-size: {SIZE_XS}px; border: none; background: transparent;")
        
    def _on_theme_changed(self, is_dark: bool):
        self._apply_style()
        
    def set_value(self, value: str):
        if hasattr(self, 'val_lbl') and self.val_lbl:
            self.val_lbl.setText(value)
