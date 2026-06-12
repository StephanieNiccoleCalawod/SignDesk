from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from theme.themes import c
from theme.typography import SIZE_XS, SIZE_MD
from components.indicators.status_pill import StatusPill
from components.indicators.confidence_meter import ConfidenceMeter
from core.theme import ThemeSignal

class DetectionStatusWidget(QWidget):
    """
    Groups the system status pill and match confidence meters.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(14)
        
        # System Status
        status_box = QWidget()
        status_layout = QVBoxLayout(status_box)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)
        
        self.lbl_status = QLabel("SYSTEM STATUS")
        self.status_pill = StatusPill("Idle", "idle")
        
        status_layout.addWidget(self.lbl_status)
        status_layout.addWidget(self.status_pill)
        
        # Match Confidence
        conf_box = QWidget()
        conf_layout = QVBoxLayout(conf_box)
        conf_layout.setContentsMargins(0, 0, 0, 0)
        conf_layout.setSpacing(8)
        
        self.lbl_conf = QLabel("MATCH CONFIDENCE")
        self.current_conf = ConfidenceMeter("Current")
        self.hold_conf = ConfidenceMeter("Hold to confirm")
        
        conf_layout.addWidget(self.lbl_conf)
        conf_layout.addWidget(self.current_conf)
        conf_layout.addSpacing(4)
        conf_layout.addWidget(self.hold_conf)
        
        self.layout.addWidget(status_box)
        self.layout.addWidget(conf_box)
        
        self._apply_style()
        
        try:
            ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass
            
    def _apply_style(self):
        if hasattr(self, 'lbl_status') and self.lbl_status:
            self.lbl_status.setStyleSheet(f"color: {c('text_secondary')}; font-size: {SIZE_XS}px; font-weight: bold; letter-spacing: 0.8px;")
        if hasattr(self, 'lbl_conf') and self.lbl_conf:
            self.lbl_conf.setStyleSheet(f"color: {c('text_secondary')}; font-size: {SIZE_XS}px; font-weight: bold; letter-spacing: 0.8px;")
        if hasattr(self, 'hold_conf') and self.hold_conf:
            self.hold_conf.title_lbl.setStyleSheet(f"color: {c('text_secondary')}; font-size: 11px;")
            
    def _on_theme_changed(self, is_dark: bool):
        self._apply_style()
