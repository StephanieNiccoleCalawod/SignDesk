import os
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QPixmap
from core.theme import c, ThemeSignal
from core.ui_helpers import _set_font, _add_shadow

class LetterCard(QFrame):
    """
    A reusable card displaying a single ASL letter image or a stylized vector/gradient fallback.
    """
    clicked = pyqtSignal(str) # Emits the letter when clicked

    def __init__(self, letter: str, image_path: str = None, parent=None):
        super().__init__(parent)
        self.letter = letter.upper().strip()
        self.image_path = image_path
        self.setObjectName("letterCard")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedSize(140, 180)
        
        self._build_ui()
        self._update_styles()
        
        # Connect to theme changes to dynamically switch colors
        try:
            ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Image Container
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setFixedSize(120, 120)
        layout.addWidget(self.img_label)

        # Text Label
        self.txt_label = QLabel(self.letter)
        self.txt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.txt_label)

        self._load_image()
        _add_shadow(self, blur=8, opacity=15, offset_y=2)

    def _load_image(self):
        # Clear previous styles/pixmap
        self.img_label.setPixmap(QPixmap())
        self.img_label.setText("")
        
        # Load local image if it exists
        if self.image_path and os.path.exists(self.image_path):
            pixmap = QPixmap(self.image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    120, 120,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.img_label.setPixmap(scaled_pixmap)
                self.img_label.setStyleSheet("background: transparent; border: none;")
                return

        # Modern vector-like gradient fallback if image is missing or invalid
        self.img_label.setText(self.letter)
        _set_font(self.img_label, size=48, bold=True)
        # Use dynamic colors for gradient fallback
        accent_color = c('accent')
        cyan_color = c('cyan')
        self.img_label.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {accent_color}, stop:1 {cyan_color});
                color: #FFFFFF;
                border-radius: 8px;
                border: none;
            }}
        """)

    def _update_styles(self):
        bg_normal = c("bg_primary")
        border_color = c("border")
        text_color = c("text_primary")
        
        self.setStyleSheet(f"""
            QFrame#letterCard {{
                background-color: {bg_normal};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
        """)
        self.txt_label.setStyleSheet(f"color: {text_color}; background: transparent; border: none;")
        _set_font(self.txt_label, size=16, bold=True)

    def _on_theme_changed(self, is_dark: bool):
        self._update_styles()
        # Re-render fallback gradient to match updated theme colors if needed
        self._load_image()

    def enterEvent(self, event):
        bg_hover = c("input_bg")
        accent_color = c("accent")
        self.setStyleSheet(f"""
            QFrame#letterCard {{
                background-color: {bg_hover};
                border: 1.5px solid {accent_color};
                border-radius: 12px;
            }}
        """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._update_styles()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.letter)
        super().mousePressEvent(event)

    def set_image_path(self, path: str):
        """Allows dynamically updating the image path from outside."""
        self.image_path = path
        self._load_image()
