from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from theme.themes import c
from theme.typography import SIZE_MD
from core.theme import ThemeSignal

class StatusPill(QWidget):
    """
    Status indicator with an icon/dot and text (e.g. "Detecting...")
    """
    
    STATES = {
        "idle": {"bg": "badge_bg", "fg": "text_muted", "dot": "text_muted"},
        "detecting": {"bg": "warning_dark", "fg": "warning_dark", "dot": "warning_dark"},
        "error": {"bg": "danger_light", "fg": "danger_dark", "dot": "danger_dark"},
        "success": {"bg": "score_pill_bg", "fg": "success_dark", "dot": "success_dark"}
    }
    
    def __init__(self, text: str = "Idle", state: str = "idle", parent=None):
        super().__init__(parent)
        
        self.current_state = state
        self.current_text = text
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 5, 10, 5)
        self.layout.setSpacing(5)
        
        self.dot = QLabel("●")
        self.dot.setStyleSheet("border: none; background: transparent; font-size: 8px;")
        
        self.label = QLabel(text)
        self.label.setStyleSheet(f"border: none; background: transparent; font-size: {SIZE_MD}px; font-weight: bold;")
        
        self.layout.addWidget(self.dot)
        self.layout.addWidget(self.label)
        
        self.set_state(state, text)
        
        try:
            ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass
        
    def set_state(self, state: str, text: str = None):
        self.current_state = state
        if text is not None:
            self.current_text = text
            self.label.setText(text)
            
        colors = self.STATES.get(state, self.STATES["idle"])
        
        if state == "detecting":
            self.setStyleSheet(f"background-color: #FEF3C7; border-radius: 20px;")
            self.label.setStyleSheet(f"color: #92400E; font-size: {SIZE_MD}px; font-weight: bold; border: none; background: transparent;")
            self.dot.setStyleSheet(f"color: #92400E; font-size: 10px; border: none; background: transparent;")
        elif state == "idle":
            self.setStyleSheet(f"background-color: {c('badge_bg')}; border-radius: 20px;")
            self.label.setStyleSheet(f"color: {c('text_muted')}; font-size: {SIZE_MD}px; font-weight: bold; border: none; background: transparent;")
            self.dot.setStyleSheet(f"color: {c('text_muted')}; font-size: 10px; border: none; background: transparent;")
        elif state == "success":
            self.setStyleSheet(f"background-color: {c('score_pill_bg')}; border-radius: 20px;")
            self.label.setStyleSheet(f"color: {c('success_dark')}; font-size: {SIZE_MD}px; font-weight: bold; border: none; background: transparent;")
            self.dot.setStyleSheet(f"color: {c('success_dark')}; font-size: 10px; border: none; background: transparent;")
        else:
            self.setStyleSheet(f"background-color: {c('danger_light')}; border-radius: 20px;")
            self.label.setStyleSheet(f"color: {c('danger_dark')}; font-size: {SIZE_MD}px; font-weight: bold; border: none; background: transparent;")
            self.dot.setStyleSheet(f"color: {c('danger_dark')}; font-size: 10px; border: none; background: transparent;")

    def _on_theme_changed(self, is_dark: bool):
        self.set_state(self.current_state)
