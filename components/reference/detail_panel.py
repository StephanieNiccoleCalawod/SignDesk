import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QPixmap
from core.theme import c, ThemeSignal
from core.ui_helpers import _set_font, _add_shadow

class DetailPanel(QFrame):
    """
    A side detail panel displaying full information about a selected letter:
    its large handshape image, detailed step-by-step description, and tips.
    Supports a placeholder empty state when no letter is selected.
    """
    close_requested = pyqtSignal()
    practice_requested = pyqtSignal(str) # Emits selected letter when practice is clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("detailPanel")
        self.setMinimumWidth(300)
        
        self.current_letter = None
        self.image_path = None
        self.description = ""
        self.tip = ""

        self._build_ui()
        self._update_styles()
        
        try:
            ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

    def _build_ui(self):
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(16)

        # 1. Placeholder Widget (shown when no letter selected)
        self.placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout(self.placeholder_widget)
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.setSpacing(12)
        
        self.placeholder_icon = QLabel("👋")
        self.placeholder_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_font(self.placeholder_icon, size=40)
        
        self.placeholder_text = QLabel("Select a letter card\nto view ASL details")
        self.placeholder_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_text.setWordWrap(True)
        
        placeholder_layout.addWidget(self.placeholder_icon)
        placeholder_layout.addWidget(self.placeholder_text)
        self.main_layout.addWidget(self.placeholder_widget, stretch=1)

        # 2. Content Container (shown when letter is selected)
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)

        # Header: Title and Close button
        header_layout = QHBoxLayout()
        self.title_label = QLabel("")
        self.title_label.setStyleSheet("background: transparent; border: none;")
        _set_font(self.title_label, size=20, bold=True)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_btn.clicked.connect(self.clear_selection)
        header_layout.addWidget(self.close_btn)
        content_layout.addLayout(header_layout)

        # Image Label (Scrollable/Centered)
        self.image_frame = QFrame()
        self.image_frame.setObjectName("imageFrame")
        self.image_frame.setFixedSize(268, 240)
        image_frame_layout = QVBoxLayout(self.image_frame)
        image_frame_layout.setContentsMargins(4, 4, 4, 4)
        image_frame_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setFixedSize(260, 230)
        image_frame_layout.addWidget(self.img_label)
        content_layout.addWidget(self.image_frame, alignment=Qt.AlignmentFlag.AlignCenter)

        # Scrollable content for text details
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background: transparent;")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(14)

        # Description Card
        self.desc_box = QFrame()
        self.desc_box.setObjectName("descBox")
        desc_box_layout = QVBoxLayout(self.desc_box)
        desc_box_layout.setContentsMargins(12, 12, 12, 12)
        desc_box_layout.setSpacing(6)
        
        self.desc_header = QLabel("HOW TO FORM")
        _set_font(self.desc_header, size=10, bold=True)
        self.desc_text = QLabel()
        self.desc_text.setWordWrap(True)
        _set_font(self.desc_text, size=12)
        
        desc_box_layout.addWidget(self.desc_header)
        desc_box_layout.addWidget(self.desc_text)
        scroll_layout.addWidget(self.desc_box)

        # Tips Card
        self.tip_box = QFrame()
        self.tip_box.setObjectName("tipBox")
        tip_box_layout = QVBoxLayout(self.tip_box)
        tip_box_layout.setContentsMargins(12, 12, 12, 12)
        tip_box_layout.setSpacing(6)
        
        self.tip_header = QLabel("PRACTICE TIP")
        _set_font(self.tip_header, size=10, bold=True)
        self.tip_text = QLabel()
        self.tip_text.setWordWrap(True)
        _set_font(self.tip_text, size=12)
        
        tip_box_layout.addWidget(self.tip_header)
        tip_box_layout.addWidget(self.tip_text)
        scroll_layout.addWidget(self.tip_box)
        
        scroll_area.setWidget(scroll_content)
        content_layout.addWidget(scroll_area, stretch=1)

        # Practice Button
        self.practice_btn = QPushButton("Practice This")
        self.practice_btn.setFixedHeight(40)
        self.practice_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.practice_btn.clicked.connect(self._on_practice_clicked)
        content_layout.addWidget(self.practice_btn)
        
        self.main_layout.addWidget(self.content_widget, stretch=1)
        self.content_widget.setVisible(False)

    def _update_styles(self):
        bg_color = c("bg_primary")
        border_color = c("border")
        text_primary = c("text_primary")
        text_muted = c("text_muted")
        
        self.setStyleSheet(f"""
            QFrame#detailPanel {{
                background-color: {bg_color};
                border-left: 1px solid {border_color};
            }}
            QFrame#imageFrame {{
                background-color: {c('input_bg')};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            QFrame#descBox {{
                background-color: {c('input_bg')};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            QFrame#tipBox {{
                background-color: {c('info_bg')};
                border: 1px solid {c('border')};
                border-radius: 8px;
            }}
        """)
        
        self.placeholder_text.setStyleSheet(f"color: {text_muted}; background: transparent;")
        _set_font(self.placeholder_text, size=13)
        
        self.title_label.setStyleSheet(f"color: {text_primary}; background: transparent; border: none;")
        
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {c('text_secondary')};
                border: none;
                font-size: 20px;
                font-weight: bold;
                border-radius: 14px;
            }}
            QPushButton:hover {{
                background-color: {c('input_bg')};
                color: {c('error')};
            }}
        """)
        
        self.desc_header.setStyleSheet(f"color: {c('accent')}; background: transparent; border: none;")
        self.desc_text.setStyleSheet(f"color: {text_primary}; background: transparent; border: none;")

        self.tip_header.setStyleSheet(f"color: {c('info')}; background: transparent; border: none;")
        self.tip_text.setStyleSheet(f"color: {text_primary}; background: transparent; border: none;")

        self.practice_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c('accent')};
                color: #FFFFFF;
                border: none;
                border-radius: 20px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {c('accent_hover')};
            }}
        """)
        _set_font(self.practice_btn, size=13, bold=True)

    def _on_theme_changed(self, is_dark: bool):
        self._update_styles()
        if self.current_letter:
            self._render_image()

    def set_letter_details(self, letter: str, image_path: str | None, description: str, tip: str):
        """Displays details for the selected letter."""
        self.current_letter = letter.upper().strip()
        self.image_path = image_path
        self.description = description
        self.tip = tip
        
        self.title_label.setText(f"Letter {self.current_letter}")
        self.desc_text.setText(self.description)
        self.tip_text.setText(self.tip)
        
        self._render_image()
        
        self.placeholder_widget.setVisible(False)
        self.content_widget.setVisible(True)

    def _on_practice_clicked(self):
        if self.current_letter:
            self.practice_requested.emit(self.current_letter)

    def _render_image(self):
        # Clear previous contents
        self.img_label.setPixmap(QPixmap())
        self.img_label.setText("")
        
        # Load local image if it exists
        if self.image_path and os.path.exists(self.image_path):
            pixmap = QPixmap(self.image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    250, 220,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.img_label.setPixmap(scaled_pixmap)
                self.img_label.setStyleSheet("background: transparent; border: none;")
                return

        # Modern vector fallback
        self.img_label.setText(self.current_letter)
        _set_font(self.img_label, size=96, bold=True)
        accent_color = c('accent')
        cyan_color = c('cyan')
        self.img_label.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {accent_color}, stop:1 {cyan_color});
                color: #FFFFFF;
                border-radius: 6px;
                border: none;
            }}
        """)

    def clear_selection(self):
        """Resets the detail panel back to the placeholder empty state."""
        self.current_letter = None
        self.image_path = None
        self.description = ""
        self.tip = ""
        
        self.content_widget.setVisible(False)
        self.placeholder_widget.setVisible(True)
        self.close_requested.emit()
