"""
core/toast.py - Toast Notifications
Lightweight popup notifications for PyQt6.
"""

from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QFrame, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QRect
from PyQt6.QtGui import QColor

from core.theme import c, is_dark

class Toast(QFrame):
    """
    A non-blocking sliding notification widget.
    Shows temporarily at the top-right of its parent.
    """
    def __init__(self, parent, message: str, kind: str = "info", duration_ms: int = 3000):
        super().__init__(parent)
        self.parent_widget = parent
        self.message = message
        self.duration_ms = duration_ms
        self.kind = kind
        
        self.setObjectName("toastFrame")
        
        # Colors based on kind
        colors = {
            "info": (c('info_bg'), c('info')),
            "success": (c('success_bg'), c('success')),
            "error": (c('error_bg'), c('error')),
            "warning": (c('warn_bg'), c('warn')),
        }
        bg_col, fg_col = colors.get(kind, colors["info"])
        
        self.setStyleSheet(f"""
            QFrame#toastFrame {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-left: 4px solid {fg_col};
                border-radius: 6px;
            }}
        """)
        
        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 40 if is_dark() else 20))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        
        lbl = QLabel(self.message)
        lbl.setStyleSheet(f"color: {c('text_primary')}; border: none; background: transparent; font-size: 13px; font-weight: bold;")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        
        self.adjustSize()
        self.setFixedWidth(min(max(self.width(), 200), 350))
        
        # Setup position (off-screen top-right initially)
        self._target_x = 0
        self._target_y = 0
        self._update_position(offscreen=True)
        
        # Setup animations
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(300)
        
        # Auto-dismiss timer
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide_toast)
        
    def _update_position(self, offscreen=False):
        if not self.parent_widget:
            return
            
        parent_rect = self.parent_widget.rect()
        width = self.width()
        height = self.height()
        
        margin_right = 24
        margin_top = 24
        
        self._target_x = parent_rect.width() - width - margin_right
        self._target_y = margin_top
        
        if offscreen:
            # Start off-screen to the right
            self.setGeometry(QRect(parent_rect.width(), self._target_y, width, height))

    def show_toast(self):
        self.raise_()
        self.show()
        self._update_position(offscreen=True)
        
        self._anim.setStartValue(self.geometry())
        self._anim.setEndValue(QRect(self._target_x, self._target_y, self.width(), self.height()))
        self._anim.start()
        
        if self.duration_ms > 0:
            self._timer.start(self.duration_ms)
            
    def hide_toast(self):
        self._anim.setStartValue(self.geometry())
        self._anim.setEndValue(QRect(self.parent_widget.width(), self._target_y, self.width(), self.height()))
        
        # Disconnect any previous connections to avoid multiple calls
        try:
            self._anim.finished.disconnect()
        except TypeError:
            pass
            
        self._anim.finished.connect(self.deleteLater)
        self._anim.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Update target X in case parent resized while showing
        if self.isVisible() and not self._anim.state() == QPropertyAnimation.State.Running:
            self._update_position()
            self.setGeometry(QRect(self._target_x, self._target_y, self.width(), self.height()))

def show_toast(parent, message: str, kind: str = "info", duration_ms: int = 3000):
    toast = Toast(parent, message, kind, duration_ms)
    toast.show_toast()
    return toast
