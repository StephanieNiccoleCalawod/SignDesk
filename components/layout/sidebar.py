"""
components/layout/sidebar.py
Modernized sidebar with:
  - Purple gradient background (#f2e7ff → #e9d5ff)
  - Smooth animated slide-right via QPropertyAnimation on pill pos
  - Smooth color fade via QVariantAnimation on bg + text color
  - Active state: dark purple bg, white text, drop shadow
  - All existing routing/signal contracts preserved
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QPropertyAnimation, QVariantAnimation,
    QEasingCurve, QPoint,
)
from PyQt6.QtGui import QCursor, QPixmap, QPainter, QLinearGradient, QColor
from core.theme import c, is_dark, ThemeSignal
from core.ui_helpers import _set_font

# ── Purple palette ─────────────────────────────────────────────────────────
_P_LIGHTEST = "#f2e7ff"
_P_LIGHT    = "#e9d5ff"
_P_MID      = "#d9b6ff"
_P_STRONG   = "#c490ff"
_P_DARK     = "#7c3aed"
_P_DARKER   = "#6d28d9"
_TEXT_IDLE  = "#4c1d95"
_WHITE      = "#FFFFFF"

_SLIDE_PX   = 10
_ANIM_MS    = 220


def _lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
    """Linear interpolate between two QColors. t in [0, 1]."""
    return QColor(
        int(c1.red()   + (c2.red()   - c1.red())   * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue()  + (c2.blue()  - c1.blue())  * t),
        int(c1.alpha() + (c2.alpha() - c1.alpha()) * t),
    )


class _ColorAnimation:
    """
    Wraps two QVariantAnimations (bg + text) to fade between idle and
    hover/active colors. Plays forward on enter, backward on leave.
    """

    def __init__(
        self,
        on_bg_changed,
        on_text_changed,
        idle_bg:   QColor,
        target_bg: QColor,
        idle_text: QColor,
        target_text: QColor,
        duration: int = _ANIM_MS,
    ):
        self._idle_bg     = idle_bg
        self._target_bg   = target_bg
        self._idle_text   = idle_text
        self._target_text = target_text
        self._t           = 0.0          # current interpolation position 0→1

        self._anim = QVariantAnimation()
        self._anim.setDuration(duration)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_value)

        self._on_bg_changed   = on_bg_changed
        self._on_text_changed = on_text_changed

    def _on_value(self, val):
        t = val / 1000.0
        self._t = t
        bg   = _lerp_color(self._idle_bg,   self._target_bg,   t)
        text = _lerp_color(self._idle_text, self._target_text, t)
        self._on_bg_changed(bg)
        self._on_text_changed(text)

    def forward(self):
        self._anim.stop()
        self._anim.setStartValue(int(self._t * 1000))
        self._anim.setEndValue(1000)
        self._anim.start()

    def backward(self):
        self._anim.stop()
        self._anim.setStartValue(int(self._t * 1000))
        self._anim.setEndValue(0)
        self._anim.start()

    def snap_to(self, t: float):
        """Jump instantly to t without animation (used for active state)."""
        self._anim.stop()
        self._t = t
        bg   = _lerp_color(self._idle_bg,   self._target_bg,   t)
        text = _lerp_color(self._idle_text, self._target_text, t)
        self._on_bg_changed(bg)
        self._on_text_changed(text)


class NavItem(QWidget):
    clicked = pyqtSignal(str)

    # Color stops
    _IDLE_BG    = QColor(0,   0,   0,   0)    # transparent
    _HOVER_BG   = QColor(196, 144, 255, 255)  # #c490ff
    _ACTIVE_BG  = QColor(124,  58, 237, 255)  # #7c3aed
    _IDLE_TEXT  = QColor(76,   29, 149, 255)  # #4c1d95
    _WHITE_COL  = QColor(255, 255, 255, 255)

    def __init__(self, key: str, label: str, icon: str = "", parent=None):
        super().__init__(parent)
        self.key       = key
        self.is_active = False
        self._hovered  = False

        self.setFixedHeight(42)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setContentsMargins(0, 0, _SLIDE_PX, 0)

        # ── Pill ──────────────────────────────────────────────────────────
        self._pill = QFrame(self)
        self._pill.setObjectName("navPill")
        pill_layout = QHBoxLayout(self._pill)
        pill_layout.setContentsMargins(14, 0, 12, 0)
        pill_layout.setSpacing(10)

        self.text_lbl = QLabel(label)
        self.text_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.text_lbl.setStyleSheet("background: transparent; border: none;")
        _set_font(self.text_lbl, size=12, bold=False)
        pill_layout.addWidget(self.text_lbl)
        pill_layout.addStretch()

        self._pill.setGeometry(0, 2, 9999, 38)

        # ── Slide animation ────────────────────────────────────────────────
        self._slide = QPropertyAnimation(self._pill, b"pos")
        self._slide.setDuration(_ANIM_MS)
        self._slide.setEasingCurve(QEasingCurve.Type.OutCubic)

        # ── Drop shadow ────────────────────────────────────────────────────
        self._shadow = QGraphicsDropShadowEffect()
        self._shadow.setBlurRadius(0)
        self._shadow.setOffset(0, 3)
        self._shadow.setColor(QColor(124, 58, 237, 0))
        self._pill.setGraphicsEffect(self._shadow)

        # ── Hover color animation (idle ↔ hover) ──────────────────────────
        self._hover_anim = _ColorAnimation(
            on_bg_changed   = self._set_pill_bg,
            on_text_changed = self._set_text_color,
            idle_bg         = self._IDLE_BG,
            target_bg       = self._HOVER_BG,
            idle_text       = self._IDLE_TEXT,
            target_text     = self._WHITE_COL,
        )

        self._apply_style()

        try:
            ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

    # ── Geometry ───────────────────────────────────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        x = self._pill.pos().x()
        self._pill.setGeometry(x, 2, self.width() - _SLIDE_PX, 38)

    # ── Color setters (called by animation on each tick) ──────────────────

    def _set_pill_bg(self, color: QColor):
        self._pill.setStyleSheet(f"""
            QFrame#navPill {{
                background-color: rgba({color.red()},{color.green()},{color.blue()},{color.alpha()});
                border-radius: 12px;
            }}
        """)

    def _set_text_color(self, color: QColor):
        self.text_lbl.setStyleSheet(
            f"color: rgba({color.red()},{color.green()},{color.blue()},{color.alpha()});"
            f"background: transparent; border: none;"
        )

    # ── Apply full style (active / reset) ─────────────────────────────────

    def _apply_style(self):
        if self.is_active:
            # Snap directly to active colors (dark purple bg, white text)
            self._set_pill_bg(self._ACTIVE_BG)
            self._set_text_color(self._WHITE_COL)
            _set_font(self.text_lbl, size=12, bold=True)
            self._shadow.setBlurRadius(16)
            self._shadow.setColor(QColor(124, 58, 237, 90))
        else:
            # Let the hover animation handle intermediate states
            _set_font(self.text_lbl, size=12, bold=False)
            self._shadow.setBlurRadius(0)
            self._shadow.setColor(QColor(124, 58, 237, 0))

    # ── Slide helper ───────────────────────────────────────────────────────

    def _slide_to(self, x: int):
        self._slide.stop()
        self._slide.setStartValue(self._pill.pos())
        self._slide.setEndValue(QPoint(x, 2))
        self._slide.start()

    # ── Hover events ───────────────────────────────────────────────────────

    def enterEvent(self, event):
        self._hovered = True
        if not self.is_active:
            self._hover_anim.forward()
            self._slide_to(_SLIDE_PX)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        if not self.is_active:
            self._hover_anim.backward()
            self._slide_to(0)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)
        super().mousePressEvent(event)

    # ── Active state ───────────────────────────────────────────────────────

    def set_active(self, active: bool):
        was_active   = self.is_active
        self.is_active = active

        if active:
            # Stop hover animation, snap to active colors, slide in
            self._hover_anim.snap_to(0)
            self._apply_style()
            self._slide_to(_SLIDE_PX)
        else:
            # Deactivating: reset to idle unless currently hovered
            self._apply_style()
            if self._hovered:
                self._hover_anim.snap_to(1.0)
            else:
                self._hover_anim.snap_to(0.0)
                self._slide_to(0)

    # ── Theme ──────────────────────────────────────────────────────────────

    def _on_theme_changed(self, _):
        self._apply_style()


# ── Logout item ────────────────────────────────────────────────────────────

class LogoutItem(QWidget):
    clicked = pyqtSignal()

    _IDLE_BG   = QColor(0,   0,   0,   0)
    _HOVER_BG  = QColor(254, 226, 226, 255)  # #fee2e2
    _IDLE_TEXT = QColor(239,  68,  68, 255)  # #ef4444
    _HOV_TEXT  = QColor(185,  28,  28, 255)  # #b91c1c

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(42)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setContentsMargins(0, 0, _SLIDE_PX, 0)

        self._pill = QFrame(self)
        self._pill.setObjectName("logoutPill")
        pill_layout = QHBoxLayout(self._pill)
        pill_layout.setContentsMargins(14, 0, 12, 0)
        pill_layout.setSpacing(10)

        self.text_lbl = QLabel("Log Out")
        self.text_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        _set_font(self.text_lbl, size=12)
        pill_layout.addWidget(self.text_lbl)
        pill_layout.addStretch()
        self._pill.setGeometry(0, 2, 9999, 38)

        self._slide = QPropertyAnimation(self._pill, b"pos")
        self._slide.setDuration(_ANIM_MS)
        self._slide.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._color_anim = _ColorAnimation(
            on_bg_changed   = self._set_bg,
            on_text_changed = self._set_text,
            idle_bg         = self._IDLE_BG,
            target_bg       = self._HOVER_BG,
            idle_text       = self._IDLE_TEXT,
            target_text     = self._HOV_TEXT,
        )

        # Init idle state
        self._set_bg(self._IDLE_BG)
        self._set_text(self._IDLE_TEXT)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        x = self._pill.pos().x()
        self._pill.setGeometry(x, 2, self.width() - _SLIDE_PX, 38)

    def _set_bg(self, color: QColor):
        self._pill.setStyleSheet(f"""
            QFrame#logoutPill {{
                background-color: rgba({color.red()},{color.green()},{color.blue()},{color.alpha()});
                border-radius: 12px;
            }}
        """)

    def _set_text(self, color: QColor):
        self.text_lbl.setStyleSheet(
            f"color: rgba({color.red()},{color.green()},{color.blue()},{color.alpha()});"
            f"background: transparent; border: none;"
        )

    def _slide_to(self, x: int):
        self._slide.stop()
        self._slide.setStartValue(self._pill.pos())
        self._slide.setEndValue(QPoint(x, 2))
        self._slide.start()

    def enterEvent(self, event):
        self._color_anim.forward()
        self._slide_to(_SLIDE_PX)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._color_anim.backward()
        self._slide_to(0)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# ── Sidebar ────────────────────────────────────────────────────────────────

class Sidebar(QFrame):
    navigation_requested = pyqtSignal(str)
    logout_requested     = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(210)
        self.setObjectName("sidebarFrame")
        self.nav_items: dict[str, NavItem] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 28, 16, 20)
        layout.setSpacing(0)

        # ── Brand ──────────────────────────────────────────────────────────
        brand_layout = QHBoxLayout()
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(10)
        brand_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "assets", "logo.png",
        )
        if os.path.exists(logo_path):
            self.logo_lbl = QLabel()
            pixmap = QPixmap(logo_path).scaled(
                36, 36,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.logo_lbl.setPixmap(pixmap)
            self.logo_lbl.setStyleSheet("background: transparent;")
            brand_layout.addWidget(self.logo_lbl)
        else:
            placeholder = QWidget()
            placeholder.setFixedSize(32, 32)
            placeholder.setStyleSheet(f"background-color: {_P_DARK}; border-radius: 8px;")
            brand_layout.addWidget(placeholder)

        self.title_lbl = QLabel("SignDesk")
        self.title_lbl.setStyleSheet(f"color: {_P_DARK}; background: transparent;")
        _set_font(self.title_lbl, size=16, bold=True)
        brand_layout.addWidget(self.title_lbl)
        layout.addLayout(brand_layout)

        # ── Divider ────────────────────────────────────────────────────────
        layout.addSpacing(20)
        self.div1 = QFrame()
        self.div1.setFixedHeight(1)
        self.div1.setStyleSheet(f"background-color: {_P_MID}; border: none;")
        layout.addWidget(self.div1)
        layout.addSpacing(16)

        # ── Nav items ──────────────────────────────────────────────────────
        self.nav_layout = QVBoxLayout()
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(4)

        self._add_nav_item(self.nav_layout, "dashboard",  "Dashboard")
        self._add_nav_item(self.nav_layout, "camera",     "Camera Practice")
        self._add_nav_item(self.nav_layout, "flashcards", "Flashcard Quiz")
        self._add_nav_item(self.nav_layout, "reference",  "ASL Reference")
        self._add_nav_item(self.nav_layout, "history",    "Gesture History")

        layout.addLayout(self.nav_layout)
        layout.addStretch()

        # ── Bottom divider ─────────────────────────────────────────────────
        self.div2 = QFrame()
        self.div2.setFixedHeight(1)
        self.div2.setStyleSheet(f"background-color: {_P_MID}; border: none;")
        layout.addWidget(self.div2)
        layout.addSpacing(10)

        # ── Bottom items ───────────────────────────────────────────────────
        bottom_layout = QVBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(4)

        self._add_nav_item(bottom_layout, "settings", "Settings")

        self.logout_item = LogoutItem()
        self.logout_item.clicked.connect(self.logout_requested)
        bottom_layout.addWidget(self.logout_item)

        layout.addLayout(bottom_layout)

        try:
            ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

    # ── Paint ──────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(_P_LIGHTEST))
        grad.setColorAt(1.0, QColor(_P_LIGHT))
        painter.fillRect(self.rect(), grad)

    # ── Helpers ────────────────────────────────────────────────────────────

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

    def _on_theme_changed(self, _):
        self.update()
        self.title_lbl.setStyleSheet(f"color: {_P_DARK}; background: transparent;")