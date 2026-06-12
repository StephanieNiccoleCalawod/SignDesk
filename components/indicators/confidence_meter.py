from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from theme.themes import c
from theme.typography import SIZE_SM, SIZE_MD
from core.theme import ThemeSignal

class ConfidenceMeter(QWidget):
    """
    Meter displaying current percentage with color-coded fill bar
    (low: orange, mid: yellow, high: green)
    """
    def __init__(self, label_text: str = "Current", parent=None):
        super().__init__(parent)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(4)
        
        # Row: Label | %
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        
        self.title_lbl = QLabel(label_text)
        self.val_lbl = QLabel("0%")
        
        row.addWidget(self.title_lbl)
        row.addStretch()
        row.addWidget(self.val_lbl)
        
        self.layout.addLayout(row)
        
        # Track and Fill
        self.track = QFrame()
        self.track.setFixedHeight(8)
        
        self.fill = QFrame(self.track)
        self.fill.setFixedHeight(8)
        
        self.layout.addWidget(self.track)
        
        self.current_value = 0
        
        self._apply_style()
        
        try:
            ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass
        
    def _apply_style(self):
        if hasattr(self, 'title_lbl') and self.title_lbl:
            self.title_lbl.setStyleSheet(f"color: {c('text_secondary')}; font-size: {SIZE_SM}px; border: none; background: transparent;")
        if hasattr(self, 'val_lbl') and self.val_lbl:
            self.val_lbl.setStyleSheet(f"color: {c('text_primary')}; font-weight: bold; font-size: {SIZE_MD}px; border: none; background: transparent;")
        if hasattr(self, 'track') and self.track:
            self.track.setStyleSheet(f"background-color: {c('progress_bg')}; border-radius: 4px; border: none;")
        self.set_value(self.current_value)
            
    def _on_theme_changed(self, is_dark: bool):
        self._apply_style()
        
    def set_value(self, pct: int):
        self.current_value = max(0, min(100, pct))
        if hasattr(self, 'val_lbl') and self.val_lbl:
            self.val_lbl.setText(f"{self.current_value}%")
        
        # Color transition
        if self.current_value < 35:
            color = c('danger') # Orange
        elif self.current_value < 70:
            color = c('warning') # Yellow
        else:
            color = c('success') # Green
            
        if hasattr(self, 'fill') and self.fill:
            self.fill.setStyleSheet(f"background-color: {color}; border-radius: 4px; border: none;")
        
        # Update width based on track width
        self.resizeEvent(None)
        
    def resizeEvent(self, event):
        if hasattr(self, 'track') and hasattr(self, 'fill'):
            w = int((self.current_value / 100.0) * self.track.width())
            self.fill.setFixedWidth(w)
        super().resizeEvent(event)
