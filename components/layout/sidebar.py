from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QPixmap, QPainter, QLinearGradient, QColor
from core.theme import c, is_dark, ThemeSignal
from core.ui_helpers import _set_font
import os

class NavItem(QWidget):
    clicked = pyqtSignal(str)
    
    def __init__(self, key: str, label: str, icon: str = "", parent=None):
        super().__init__(parent)
        self.key = key
        self.is_active = False
        
        self.setFixedHeight(38)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(0)
        
        self.text_lbl = QLabel(label)
        self.text_lbl.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.text_lbl)
        layout.addStretch()
        
        self._apply_style()
        
        # Connect to theme changes to dynamically update styles
        try:
            ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass
        
    def set_active(self, active: bool):
        self.is_active = active
        self._apply_style()
        
    def _apply_style(self):
        dark = is_dark()
        if self.is_active:
            bg = "#2D2D3D" if dark else "#495086"
            fg = "#FFFFFF"
            font_bold = True
        else:
            bg = "transparent"
            fg = "#84849E" if dark else "#2C3358"
            font_bold = False
            
        self.setStyleSheet(f"background-color: {bg}; border-radius: 10px;")
        self.text_lbl.setStyleSheet(f"color: {fg}; background: transparent; border: none;")
        _set_font(self.text_lbl, size=12, bold=font_bold)
        
    def _on_theme_changed(self, is_dark_mode: bool):
        self._apply_style()
        
    def enterEvent(self, event):
        dark = is_dark()
        if self.is_active:
            bg = "#353550" if dark else "#3F4678"
        else:
            bg = "rgba(255,255,255,0.08)" if dark else "rgba(0,0,0,0.08)"
        self.setStyleSheet(f"background-color: {bg}; border-radius: 10px;")
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._apply_style()
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)
        super().mousePressEvent(event)

class Sidebar(QFrame):
    navigation_requested = pyqtSignal(str)
    logout_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(210)
        self.setObjectName("sidebarFrame")
        
        self.nav_items = {}
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 24, 16, 20)
        layout.setSpacing(0)
        
        # Brand area (logo and name)
        brand_layout = QHBoxLayout()
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(10)
        brand_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "assets", "logo.png"
        )
        
        if os.path.exists(logo_path):
            self.logo_lbl = QLabel()
            pixmap = QPixmap(logo_path).scaled(
                36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.logo_lbl.setPixmap(pixmap)
            self.logo_lbl.setStyleSheet("background: transparent;")
            brand_layout.addWidget(self.logo_lbl)
        else:
            self.logo_icon = QWidget()
            self.logo_icon.setFixedSize(32, 32)
            self.logo_icon.setStyleSheet(f"background-color: {c('accent')}; border-radius: 8px;")
            brand_layout.addWidget(self.logo_icon)
            
        self.title_lbl = QLabel("SignDesk")
        _set_font(self.title_lbl, size=16, bold=True)
        brand_layout.addWidget(self.title_lbl)
        
        layout.addLayout(brand_layout)
        
        # Divider 1
        self.div1 = QFrame()
        self.div1.setFixedHeight(1)
        layout.addSpacing(16)
        layout.addWidget(self.div1)
        layout.addSpacing(16)
        
        # Navigation Items Area
        self.nav_layout = QVBoxLayout()
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(2)
        
        self._add_nav_item(self.nav_layout, "dashboard", "Dashboard")
        self._add_nav_item(self.nav_layout, "camera", "Camera Practice")
        self._add_nav_item(self.nav_layout, "flashcards", "Flashcard Quiz")
        self._add_nav_item(self.nav_layout, "reference", "ASL Reference")
        self._add_nav_item(self.nav_layout, "history", "Gesture History")
        
        layout.addLayout(self.nav_layout)
        layout.addStretch()
        
        # Divider 2
        self.div2 = QFrame()
        self.div2.setFixedHeight(1)
        layout.addWidget(self.div2)
        layout.addSpacing(8)
        
        # Bottom Area (Settings & Logout)
        bottom_layout = QVBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(2)
        
        self._add_nav_item(bottom_layout, "settings", "Settings")
        
        # Logout Button
        self.logout_btn = QWidget()
        self.logout_btn.setFixedHeight(38)
        self.logout_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.logout_btn.setStyleSheet("background: transparent; border-radius: 10px;")
        lo_layout = QHBoxLayout(self.logout_btn)
        lo_layout.setContentsMargins(16, 0, 12, 0)
        lo_layout.setSpacing(8)
        
        self.lo_text = QLabel("Logout")
        self.lo_text.setStyleSheet("color: #FF8A80; background: transparent; border: none;")
        _set_font(self.lo_text, size=12, bold=False)
        lo_layout.addWidget(self.lo_text)
        lo_layout.addStretch()
        
        def enterEvent(e): self.logout_btn.setStyleSheet(f"background-color: {c('input_bg')}; border-radius: 10px;")
        def leaveEvent(e): self.logout_btn.setStyleSheet("background-color: transparent; border-radius: 10px;")
        def mousePressEvent(e): 
            if e.button() == Qt.MouseButton.LeftButton:
                self.logout_requested.emit()
        self.logout_btn.enterEvent = enterEvent
        self.logout_btn.leaveEvent = leaveEvent
        self.logout_btn.mousePressEvent = mousePressEvent
        
        bottom_layout.addWidget(self.logout_btn)
        layout.addLayout(bottom_layout)
        
        # Apply initial styles
        self._apply_style()
        
        # Connect to Theme Changes
        try:
            ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

    def _apply_style(self):
        dark = is_dark()
        self.title_lbl.setStyleSheet(f"color: {'#FFFFFF' if dark else '#2C3358'}; background: transparent;")
        self.div1.setStyleSheet(f"background-color: {c('border')}; border: none;")
        self.div2.setStyleSheet(f"background-color: {c('border')}; border: none;")
        
        # Update all nav labels
        for label in self.findChildren(QLabel):
            if label.objectName() == "navLabel":
                label.setStyleSheet(f"color: {c('text_muted')}; background: transparent; border: none; padding: 8px 16px 4px;")
                
    def _on_theme_changed(self, is_dark_mode: bool):
        self._apply_style()
        self.update() # Refreshes gradient paint
        
    def paintEvent(self, event):
        dark = is_dark()
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, QColor(c("panel_left", dark=dark)))
        grad.setColorAt(1, QColor(c("panel_left_end", dark=dark)))
        painter.fillRect(self.rect(), grad)
        
    def _add_nav_label(self, layout, text: str):
        lbl = QLabel(text)
        lbl.setObjectName("navLabel")
        lbl.setText(text.upper())
        lbl.setStyleSheet(f"color: {c('text_muted')}; background: transparent; border: none; padding: 8px 16px 4px;")
        _set_font(lbl, size=10, bold=True)
        layout.addWidget(lbl)
        
    def _add_nav_item(self, layout, key: str, label: str, icon: str = ""):
        item = NavItem(key, label, icon)
        item.clicked.connect(self._on_nav_clicked)
        self.nav_items[key] = item
        layout.addWidget(item)
        
    def _on_nav_clicked(self, key: str):
        self.set_active_item(key)
        self.navigation_requested.emit(key)
        
    def set_active_item(self, key: str):
        for k, item in self.nav_items.items():
            item.set_active(k == key)
