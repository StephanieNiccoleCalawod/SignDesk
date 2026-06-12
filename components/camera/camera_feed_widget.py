from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from theme.themes import c
import cv2

class CameraFeedWidget(QWidget):
    """
    Independent widget for displaying OpenCV frames natively in PyQt.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.feed_label = QLabel()
        self.feed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feed_label.setStyleSheet(f"""
            background-color: {c('camera_bg')};
            border-radius: 8px;
            border: none;
        """)
        self.feed_label.setMinimumSize(320, 240)
        
        self.layout.addWidget(self.feed_label)
        self._current_frame = None
        
    def set_frame(self, frame):
        """Convert cv2 BGR frame to QPixmap and display."""
        if frame is None:
            return
            
        self._current_frame = frame
        
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        
        qt_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        scaled_pixmap = QPixmap.fromImage(qt_img).scaled(
            self.feed_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.feed_label.setPixmap(scaled_pixmap)
        
    def clear(self):
        """Clear the current frame."""
        self.feed_label.clear()
        self._current_frame = None
        
    def resizeEvent(self, event):
        """Re-scale the current frame if the widget is resized."""
        super().resizeEvent(event)
        if self._current_frame is not None:
            self.set_frame(self._current_frame)
