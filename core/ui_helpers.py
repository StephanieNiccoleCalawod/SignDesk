"""
core/ui_helpers.py - Reusable UI Components
PyQt6 migration — CustomTkinter dependency fully removed.
"""

from PyQt6.QtWidgets import QWidget, QFrame, QLabel, QHBoxLayout, QVBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor

from core.theme import c

def resolve_color(color, dark: bool = False):
    """Resolve a (light, dark) tuple based on the current mode, or return as-is."""
    if isinstance(color, tuple):
        return color[1] if dark else color[0]
    return color

def _set_font(widget: QWidget, size: int = 13, bold: bool = False):
    """Utility to apply font family, size, and weight via inline style."""
    weight = "bold" if bold else "normal"
    widget.setStyleSheet(f"font-family: 'Segoe UI'; font-size: {size}px; font-weight: {weight};")

class HoverNavWidget(QWidget):
    """Internal widget for create_nav_item to handle hover events."""
    def __init__(self, bg_normal, bg_hover, command):
        super().__init__()
        self.bg_normal = bg_normal
        self.bg_hover = bg_hover
        self.command = command
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {self.bg_normal}; border-radius: 10px;")
        if self.command:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def enterEvent(self, event):
        if self.command:
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
    """
    Reusable sidebar navigation item.
    dark=None means follow the global theme state.
    """
    from core.theme import is_dark as _is_dark
    if dark is None:
        dark = _is_dark()

    if is_active:
        bg_normal = "#2D2D3D" if dark else "#495086"
        bg_hover = bg_normal
    else:
        bg_normal = "transparent"
        bg_hover = "#3D4470" if dark else "#D6D3E8"

    text_color = "#FFFFFF" if is_active else ("#84849E" if dark else "#2C3358")

    frame = HoverNavWidget(bg_normal, bg_hover, command)
    frame.setFixedHeight(38)
    
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(12, 0, 12, 0)
    layout.setSpacing(8)

    icon_lbl = QLabel(icon)
    icon_lbl.setStyleSheet(f"color: {text_color}; font-family: 'Segoe UI Emoji'; font-size: 14px; background: transparent;")
    icon_lbl.setFixedWidth(24)
    icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

    text_lbl = QLabel(label)
    text_lbl.setStyleSheet(f"color: {text_color}; background: transparent;")
    _set_font(text_lbl, size=12, bold=is_active)

    layout.addWidget(icon_lbl)
    layout.addWidget(text_lbl)
    layout.addStretch()

    return frame

def create_step_card(parent: QWidget, step_number: int, title: str,
                     description: str, card_width: int = 155,
                     dark: bool = False) -> QFrame:
    """
    Reusable step-card component (frame-based).
    """
    card = QFrame(parent)
    card.setFixedWidth(card_width)
    card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    
    # Card styling
    bg = c("bg_primary", dark)
    border = c("border", dark)
    card.setStyleSheet(f"""
        QFrame {{
            background-color: {bg};
            border: 1px solid {border};
            border-radius: 14px;
        }}
    """)

    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 18, 14, 18)
    layout.setSpacing(6)
    layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

    accent = c("accent", dark)

    # Badge
    badge = QLabel(str(step_number))
    badge.setFixedSize(40, 40)
    badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setStyleSheet(f"""
        QLabel {{
            background-color: {accent};
            color: #FFFFFF;
            border-radius: 20px;
            font-family: 'Segoe UI';
            font-size: 12px;
            font-weight: bold;
            border: none;
        }}
    """)
    
    # Title
    title_lbl = QLabel(title)
    title_lbl.setWordWrap(True)
    title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title_lbl.setStyleSheet(f"color: {accent}; border: none; background: transparent;")
    _set_font(title_lbl, size=11, bold=True)

    # Description
    desc_lbl = QLabel(description)
    desc_lbl.setWordWrap(True)
    desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    text_mid = c("text_secondary", dark)
    desc_lbl.setStyleSheet(f"color: {text_mid}; border: none; background: transparent;")
    _set_font(desc_lbl, size=10, bold=False)

    layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignHCenter)
    layout.addSpacing(6)
    layout.addWidget(title_lbl)
    layout.addWidget(desc_lbl)

    return card

def build_steps_panel(parent: QWidget, steps: list[tuple[str, str]],
                      card_width: int = 155, dark: bool = False) -> QWidget:
    """Lay out N step cards in a single responsive horizontal row."""
    container = QWidget(parent)
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)

    section_label = QLabel("How to Use SignDesk")
    section_label.setStyleSheet(f"color: {c('text_primary', dark)}; background: transparent;")
    _set_font(section_label, size=13, bold=True)
    
    layout.addWidget(section_label)
    layout.addSpacing(10)

    row_widget = QWidget()
    row_layout = QHBoxLayout(row_widget)
    row_layout.setContentsMargins(0, 0, 0, 0)
    row_layout.setSpacing(8)

    for i, (title, desc) in enumerate(steps):
        card = create_step_card(
            row_widget, step_number=i + 1,
            title=title, description=desc,
            card_width=card_width,
            dark=dark
        )
        row_layout.addWidget(card)

    row_layout.addStretch()

    layout.addWidget(row_widget)

    return container