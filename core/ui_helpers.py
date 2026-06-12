"""
core/ui_helpers.py - Reusable UI Components
PyQt6 migration — CustomTkinter dependency fully removed.
"""

from PyQt6.QtWidgets import (QWidget, QFrame, QLabel, QHBoxLayout, QVBoxLayout,
                             QGraphicsDropShadowEffect, QSizePolicy)
from PyQt6.QtCore import Qt, QPropertyAnimation, QRectF, pyqtProperty, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QCursor, QFont, QColor, QPainter, QPen

from core.theme import c


class ToggleSwitch(QWidget):
    """Custom painted toggle switch with a sliding white knob."""
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None, checked=False, track_w=46, track_h=24):
        super().__init__(parent)
        self._track_w = track_w
        self._track_h = track_h
        self._knob_margin = 3
        self._knob_d = track_h - 2 * self._knob_margin
        self._checked = checked
        self._knob_x = float(self._on_x() if checked else self._off_x())

        self.setFixedSize(track_w, track_h)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self._anim = QPropertyAnimation(self, b"knob_x")
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def _off_x(self):
        return float(self._knob_margin)

    def _on_x(self):
        return float(self._track_w - self._knob_d - self._knob_margin)

    @pyqtProperty(float)
    def knob_x(self):
        return self._knob_x

    @knob_x.setter
    def knob_x(self, val):
        self._knob_x = val
        self.update()

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        self._checked = checked
        self._knob_x = float(self._on_x() if checked else self._off_x())
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self._anim.stop()
            self._anim.setStartValue(self._knob_x)
            self._anim.setEndValue(float(self._on_x() if self._checked else self._off_x()))
            self._anim.start()
            self.toggled.emit(self._checked)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Track
        track_color = QColor(c('accent')) if self._checked else QColor(c('border'))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track_color)
        radius = self._track_h / 2.0
        p.drawRoundedRect(QRectF(0, 0, self._track_w, self._track_h), radius, radius)

        # Knob (white circle)
        p.setBrush(QColor("#FFFFFF"))
        knob_y = float(self._knob_margin)
        p.drawEllipse(QRectF(self._knob_x, knob_y, self._knob_d, self._knob_d))

        p.end()


def _add_shadow(widget: QWidget, blur: int = 3, opacity: int = 30, offset_y: int = 1):
    """Attach a tight drop shadow to any QWidget/QFrame card.
    Small blur + small offset = shadow hugs the box edge cleanly."""
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setColor(QColor(0, 0, 0, opacity))
    shadow.setOffset(0, offset_y)
    widget.setGraphicsEffect(shadow)


def resolve_color(color, dark: bool = False):
    if isinstance(color, tuple):
        return color[1] if dark else color[0]
    return color


def _set_font(widget: QWidget, size: int = 13, bold: bool = False, family: str = "Segoe UI"):
    """Apply font via QFont — does NOT touch the stylesheet so colors/borders are preserved."""
    f = QFont(family, size)
    f.setBold(bold)
    widget.setFont(f)


class HoverNavWidget(QWidget):
    """Internal widget for create_nav_item to handle hover events."""
    def __init__(self, bg_normal, bg_hover, command):
        super().__init__()
        self.bg_normal = bg_normal
        self.bg_hover  = bg_hover
        self.command   = command
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {self.bg_normal}; border-radius: 10px;")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def enterEvent(self, event):
        self.setStyleSheet(f"background-color: {self.bg_hover}; border-radius: 10px;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(f"background-color: {self.bg_normal}; border-radius: 10px;")
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if self.command and event.button() == Qt.MouseButton.LeftButton:
            self.command()
        super().mousePressEvent(event)


def create_nav_item(parent: QWidget, icon: str, label: str,
                    is_active: bool = False, command=None,
                    dark: bool = None) -> QWidget:
    """Reusable sidebar navigation item — text only."""
    from core.theme import is_dark as _is_dark
    if dark is None:
        dark = _is_dark()

    if is_active:
        bg_normal = "#2D2D3D" if dark else "#495086"
        bg_hover  = "#353550" if dark else "#3F4678"
    else:
        bg_normal = "transparent"
        bg_hover  = "rgba(0,0,0,0.08)" if not dark else "rgba(255,255,255,0.08)"

    text_color = "#FFFFFF" if is_active else ("#84849E" if dark else "#2C3358")

    frame = HoverNavWidget(bg_normal, bg_hover, command)
    frame.setFixedHeight(38)

    layout = QHBoxLayout(frame)
    layout.setContentsMargins(16, 0, 12, 0)
    layout.setSpacing(0)

    text_lbl = QLabel(label)
    text_lbl.setStyleSheet(f"color: {text_color}; background: transparent; border: none;")
    _set_font(text_lbl, size=12, bold=is_active)

    layout.addWidget(text_lbl)
    layout.addStretch()

    return frame


def create_step_card(parent: QWidget, step_number: int, title: str,
                     description: str, card_width: int = 155,
                     dark: bool = False) -> QFrame:
    """Reusable step-card component."""
    card = QFrame(parent)
    card.setObjectName("stepCard")
    card.setMinimumWidth(120)
    card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    card_bg     = "#1E1E2E" if dark else "#FFFFFF"
    card_border = "#3D3D5C" if dark else "#E2E8F0"
    badge_color = "#4F46E5"
    title_color = "#C4B5FD" if dark else "#1E293B"   # darker = more readable
    desc_color  = "#94A3B8" if dark else "#475569"   # darker = more readable

    card.setStyleSheet(f"""
        QFrame#stepCard {{
            background-color: {card_bg};
            border: 1px solid {card_border};
            border-radius: 14px;
        }}
        QFrame#stepCard QLabel {{
            background: transparent;
            border: none;
        }}
    """)

    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 18, 14, 18)
    layout.setSpacing(8)
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    # Badge — use a QWidget container so QFrame global rules can't interfere
    badge_container = QWidget()
    badge_container.setFixedSize(36, 36)
    badge_container.setStyleSheet(f"""
        background-color: {badge_color};
        border-radius: 18px;
        border: none;
    """)
    badge_layout = QHBoxLayout(badge_container)
    badge_layout.setContentsMargins(0, 0, 0, 0)
    badge_lbl = QLabel(str(step_number))
    badge_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge_lbl.setStyleSheet(f"color: #FFFFFF; background: transparent; border: none;")
    _set_font(badge_lbl, size=13, bold=True)
    badge_layout.addWidget(badge_lbl)

    title_lbl = QLabel(title)
    title_lbl.setObjectName("stepTitle")
    title_lbl.setWordWrap(True)
    title_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
    title_lbl.setStyleSheet(f"color: {title_color};")
    _set_font(title_lbl, size=11, bold=True)

    divider = QFrame()
    divider.setObjectName("stepDivider")
    divider.setFixedHeight(1)
    divider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    divider.setStyleSheet(f"QFrame#stepDivider {{ background: {card_border}; border: none; border-radius: 0px; }}")

    desc_lbl = QLabel(description)
    desc_lbl.setObjectName("stepDesc")
    desc_lbl.setWordWrap(True)
    desc_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
    desc_lbl.setStyleSheet(f"color: {desc_color};")
    _set_font(desc_lbl, size=10)

    layout.addWidget(badge_container, 0, Qt.AlignmentFlag.AlignLeft)
    layout.addSpacing(2)
    layout.addWidget(title_lbl)
    layout.addWidget(divider)
    layout.addWidget(desc_lbl)

    _add_shadow(card)

    return card


def build_steps_panel(parent: QWidget, steps: list[tuple[str, str]],
                      card_width: int = 155, dark: bool = None) -> QWidget:
    """Lay out N step cards in a single responsive horizontal row."""
    from core.theme import is_dark as _is_dark
    if dark is None:
        dark = _is_dark()

    container = QWidget(parent)
    container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)

    section_label = QLabel("How to Use SignDesk")
    section_label.setStyleSheet(
        f"color: {c('text_primary', dark)}; background: transparent; border: none;")
    _set_font(section_label, size=13, bold=True)
    layout.addWidget(section_label)

    # Wrapper gives shadow exactly enough room — matches blur=5, offset_y=2
    wrapper = QWidget()
    wrapper.setStyleSheet("background: transparent;")
    wrapper_layout = QVBoxLayout(wrapper)
    wrapper_layout.setContentsMargins(6, 6, 6, 8)
    wrapper_layout.setSpacing(0)

    row_widget = QWidget()
    row_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
    row_layout = QHBoxLayout(row_widget)
    row_layout.setContentsMargins(0, 0, 0, 0)
    row_layout.setSpacing(12)
    row_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    for i, (title, desc) in enumerate(steps):
        card = create_step_card(
            row_widget, step_number=i + 1,
            title=title, description=desc,
            card_width=card_width,
            dark=dark
        )
        # Remove fixed width so card can expand with stretch
        card.setMinimumWidth(120)
        card.setMaximumWidth(9999)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row_layout.addWidget(card, stretch=1)

    wrapper_layout.addWidget(row_widget)
    layout.addWidget(wrapper)

    return container