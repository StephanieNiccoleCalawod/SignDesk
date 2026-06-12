from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt
from theme.themes import c
from theme.typography import SIZE_SM

class LandmarkOverlay(QWidget):
    """
    Transparent overlay that displays detection state natively over the CameraFeed.
    Does not render dots (OpenCV handles that), but handles the UI elements 
    that float over the camera feed (like 'Hand detected').
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        self.detected_label = QLabel("Hand detected")
        self.detected_label.setStyleSheet(f"""
            background-color: rgba(74, 222, 128, 0.15);
            border: 1px solid rgba(74, 222, 128, 0.5);
            border-radius: 6px;
            padding: 3px 8px;
            font-size: {SIZE_SM}px;
            color: {c('success')};
        """)
        self.detected_label.hide()
        
        self.layout.addWidget(self.detected_label, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.layout.addStretch()
        
    def set_detected(self, is_detected: bool):
        self.detected_label.setVisible(is_detected)
