"""
core/theme.py - SignDesk Theme Configuration
PyQt6 migration — CustomTkinter dependency fully removed.

What changed:
  - Removed: import customtkinter as ctk
  - Removed: apply_theme() (called ctk.set_appearance_mode)
  - Added:   ThemeSignal  — singleton QObject that broadcasts dark/light changes
  - Added:   c()          — resolves any COLORS tuple to a hex string for the
                            current mode; use everywhere instead of COLORS[key][0]
  - Added:   build_qss()  — generates a global QSS string for QApplication
  - Everything else (COLORS, C_ constants, fonts, PASSWORD_RULES,
    ThemeManager) is 100% unchanged so all existing imports keep working.
"""

from __future__ import annotations
import re
from typing import Optional

# ── PyQt6 signal bus (lazy-imported to keep theme.py importable even in
#    environments that don't have Qt — e.g. unit-test runners) ─────────────
try:
    from PyQt6.QtCore import QObject, pyqtSignal

    class _ThemeSignal(QObject):
        """
        Singleton signal bus for theme changes.

        Usage
        -----
        # Emit when the user toggles dark mode:
        ThemeSignal.instance().theme_changed.emit(True)   # True = dark

        # Subscribe in any QWidget:
        ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        """

        theme_changed = pyqtSignal(bool)   # True → dark, False → light
        _inst: Optional["_ThemeSignal"] = None

        @classmethod
        def instance(cls) -> "_ThemeSignal":
            if cls._inst is None:
                cls._inst = cls()
            return cls._inst

    ThemeSignal = _ThemeSignal

except ImportError:
    # Fallback stub so non-Qt code can still import theme.py safely
    class ThemeSignal:  # type: ignore[no-redef]
        @classmethod
        def instance(cls):
            return cls()
        def theme_changed(self, *_):
            pass
        def connect(self, *_):
            pass
        def emit(self, *_):
            pass


# ── Color Palette Dictionary ───────────────────────────────────────────────
# Each value is a (light, dark) tuple.
# Index 0 = light mode   |   Index 1 = dark mode
COLORS = {
    "bg_primary":    ("#FFFFFF", "#141416"),   # Main cards & panels
    "bg_secondary":  ("#F3F1F8", "#0A0A0B"),   # Window background

    "panel_left":     ("#DDD9F2", "#1A1A1E"),  # Sidebar bg
    "panel_left_end": ("#C9C4E8", "#282836"),  # Sidebar gradient end

    "text_primary":   ("#1F1F1F", "#F1F1F5"),  # Headings, active text
    "text_secondary": ("#6B7280", "#9CA3AF"),   # Subtitles
    "text_muted":     ("#A0AEC0", "#6B7280"),   # Placeholders

    "accent":       ("#6C63FF", "#6C63FF"),     # Primary buttons (same both modes)
    "accent_hover": ("#5A52E0", "#5A52E0"),
    "cyan":         ("#A78BFA", "#A78BFA"),     # Secondary highlight

    "border":       ("#EDE9F3", "#272730"),     # Card borders
    "input_bg":     ("#F7F8FA", "#1C1C24"),     # Input field background
    "input_border": ("#D4D0E6", "#3A3A4A"),     # Input border

    # Semantic
    "success":    ("#1D9E75", "#22C55E"),
    "success_bg": ("#E1F5EE", "#163325"),
    "error":      ("#E24B4A", "#F87171"),
    "error_bg":   ("#FCEBEB", "#3C1D1D"),
    "warn":       ("#BA7517", "#FBBF24"),
    "warn_bg":    ("#FAEEDA", "#3A2A0D"),
    "info":       ("#5E35B1", "#A78BFA"),
    "info_bg":    ("#EDE7F6", "#2C2245"),

    # Badge shades
    "badge_gray_bg": ("#F0F0F0", "#272730"),
    "badge_gray_fg": ("#888888", "#9CA3AF"),
}


# ── Global dark-mode state ─────────────────────────────────────────────────
_CURRENT_DARK: bool = False

def set_dark_mode(dark: bool) -> None:
    global _CURRENT_DARK
    _CURRENT_DARK = dark

def is_dark() -> bool:
    return _CURRENT_DARK

# ── Primary color resolver ─────────────────────────────────────────────────

def c(key: str, dark=None) -> str:
    """Resolve a COLORS key. Uses global dark-mode state if dark is None."""
    pair = COLORS.get(key, ("#FFFFFF", "#FFFFFF"))
    use_dark = _CURRENT_DARK if dark is None else dark
    return pair[1] if use_dark else pair[0]


# ── Legacy C_ constants ────────────────────────────────────────────────────
# Kept as (light, dark) tuples so every existing `from core.theme import C_*`
# import continues to work.  Resolve them with c() when you need a plain hex.

C_BG           = COLORS["bg_secondary"]
C_PANEL_LEFT   = COLORS["panel_left"]
C_PANEL_LEFT2  = COLORS["panel_left_end"]
C_ACCENT       = COLORS["accent"]
C_ACCENT_HOVER = COLORS["accent_hover"]
C_CYAN         = COLORS["cyan"]
C_WHITE        = ("#FFFFFF", "#FFFFFF")
C_TEXT_DARK    = COLORS["text_primary"]
C_TEXT_MID     = COLORS["text_secondary"]
C_TEXT_LIGHT   = COLORS["text_muted"]
C_INPUT_BG     = COLORS["input_bg"]
C_INPUT_BORDER = COLORS["input_border"]
C_INPUT_FOCUS  = COLORS["accent"]
C_DASH_BG      = COLORS["bg_secondary"]
C_CARD_BG      = COLORS["bg_primary"]
C_CARD_BORDER  = COLORS["border"]

# Semantic
C_SUCCESS    = COLORS["success"]
C_SUCCESS_BG = COLORS["success_bg"]
C_ERROR_RED  = COLORS["error"]
C_ERROR_BG   = COLORS["error_bg"]
C_WARN       = COLORS["warn"]
C_WARN_BG    = COLORS["warn_bg"]
C_INFO_BG    = COLORS["info_bg"]
C_INFO_TEXT  = COLORS["info"]

# Badges
C_BADGE_BLUE_BG  = COLORS["info_bg"]
C_BADGE_BLUE_FG  = COLORS["info"]
C_BADGE_TEAL_BG  = COLORS["success_bg"]
C_BADGE_TEAL_FG  = COLORS["success"]
C_BADGE_AMBER_BG = COLORS["warn_bg"]
C_BADGE_AMBER_FG = COLORS["warn"]
C_BADGE_GRAY_BG  = COLORS["badge_gray_bg"]
C_BADGE_GRAY_FG  = COLORS["badge_gray_fg"]

# Sidebar
C_SIDEBAR_START  = COLORS["panel_left"]
C_SIDEBAR_END    = COLORS["panel_left_end"]
C_SIDEBAR_ACTIVE = ("#495086", "#2D2D3D")
C_NAV_TEXT       = ("#B8B5D0", "#84849E")
C_NAV_ACTIVE     = ("#FFFFFF", "#FFFFFF")


# ── Fonts ──────────────────────────────────────────────────────────────────
# Still defined as tuples so existing code that unpacks them keeps working.
# PyQt6 widgets call _set_font(widget, size, bold) from ui_helpers instead.

FONT_PRIMARY        = "Segoe UI"
FONT_TITLE          = ("Segoe UI", 28, "bold")
FONT_SUBTITLE       = ("Segoe UI", 13)
FONT_HEADING        = (FONT_PRIMARY, 22, "bold")
FONT_SUBHEAD        = (FONT_PRIMARY, 12)
FONT_LABEL          = (FONT_PRIMARY, 12, "bold")
FONT_LABEL_SM       = (FONT_PRIMARY, 11, "bold")
FONT_INPUT          = (FONT_PRIMARY, 13)
FONT_BTN            = (FONT_PRIMARY, 13, "bold")
FONT_SMALL          = (FONT_PRIMARY, 11)
FONT_FEAT           = (FONT_PRIMARY, 13)
FONT_NAV            = (FONT_PRIMARY, 11, "bold")
FONT_REQ            = (FONT_PRIMARY, 10)
FONT_SIDEBAR        = (FONT_PRIMARY, 12)
FONT_SIDEBAR_ACTIVE = (FONT_PRIMARY, 12, "bold")


# ── Password Rules ─────────────────────────────────────────────────────────

PASSWORD_RULES = [
    ("length",    "At least 8 characters",
                  lambda p: len(p) >= 8),
    ("uppercase", "At least 1 uppercase letter (A–Z)",
                  lambda p: bool(re.search(r"[A-Z]", p))),
    ("lowercase", "At least 1 lowercase letter (a–z)",
                  lambda p: bool(re.search(r"[a-z]", p))),
    ("digit",     "At least 1 number (0–9)",
                  lambda p: bool(re.search(r"[0-9]", p))),
    ("special",   "At least 1 special character (!@#$%^& etc.)",
                  lambda p: bool(re.search(
                      r"[!@#$%^&*()\+\-=\[\]{};':\"\\|,.<>\/?]", p))),
]


# ── ThemeManager — unchanged public API ───────────────────────────────────

class ThemeManager:
    """
    Provides get_color(key) → (light_hex, dark_hex) tuple.
    Used by modules that call theme.get_color() directly.
    """

    def __init__(self) -> None:
        self._map = {
            "bg_main":        COLORS["bg_secondary"],
            "bg_card":        COLORS["bg_primary"],
            "bg_sidebar":     COLORS["panel_left"],
            "bg_input":       COLORS["input_bg"],
            "border":         COLORS["border"],
            "input_border":   COLORS["input_border"],
            "text_primary":   COLORS["text_primary"],
            "text_secondary": COLORS["text_secondary"],
            "text_muted":     COLORS["text_muted"],
            "primary":        COLORS["accent"],
            "accent":         COLORS["accent"],
            "accent_hover":   COLORS["accent_hover"],
            "cyan":           COLORS["cyan"],
            "success":        COLORS["success"],
            "success_bg":     COLORS["success_bg"],
            "error":          COLORS["error"],
            "error_bg":       COLORS["error_bg"],
            "warn":           COLORS["warn"],
            "warn_bg":        COLORS["warn_bg"],
            "info":           COLORS["info"],
            "info_bg":        COLORS["info_bg"],
        }

    def get_color(self, key: str) -> tuple[str, str]:
        return self._map.get(key, ("#FFFFFF", "#FFFFFF"))


theme = ThemeManager()


# ── Global QSS generator ───────────────────────────────────────────────────

def build_qss(dark: bool = False) -> str:
    """
    Returns a global Qt Style Sheet string for QApplication.

    Apply at startup and whenever the user toggles dark/light mode:

        from PyQt6.QtWidgets import QApplication
        from core.theme import build_qss
        QApplication.instance().setStyleSheet(build_qss(dark=True))

    This sets sensible defaults for QWidget, QScrollArea, QScrollBar,
    QToolTip, and QDialog so individual widgets only need to override
    what differs from the base.
    """
    bg       = c("bg_secondary",  dark)
    card     = c("bg_primary",    dark)
    text     = c("text_primary",  dark)
    text_mid = c("text_secondary",dark)
    border   = c("border",        dark)
    input_bg = c("input_bg",      dark)
    accent   = c("accent",        dark)
    sb_bg    = c("badge_gray_bg", dark)
    sb_fg    = c("badge_gray_fg", dark)

    return f"""
        /* ── Base ── */
        QWidget {{
            background-color: {bg};
            color: {text};
            font-family: 'Segoe UI';
            font-size: 13px;
        }}

        /* ── NOTE: No global QFrame rule ──
         * QLabel inherits QFrame, so a blanket QFrame {{}} rule
         * gives every label a white background + border, hiding text.
         * Cards set their own styles via objectName selectors instead.
         */

        /* ── Inputs ── */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {input_bg};
            border: 1px solid {c("input_border", dark)};
            border-radius: 8px;
            padding: 4px 10px;
            color: {text};
            selection-background-color: {accent};
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 1px solid {accent};
        }}

        /* ── Buttons (base — pill shape; widget setStyleSheet overrides border-radius) ── */
        QPushButton {{
            background-color: {accent};
            color: #FFFFFF;
            border: none;
            border-radius: 9999px;
            padding: 6px 16px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {c("accent_hover", dark)};
        }}
        QPushButton:disabled {{
            background-color: {sb_bg};
            color: {sb_fg};
        }}

        /* ── ComboBox ── */
        QComboBox {{
            background-color: {input_bg};
            border: 1px solid {c("input_border", dark)};
            border-radius: 8px;
            padding: 4px 10px;
            color: {text};
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QComboBox QAbstractItemView {{
            background-color: {card};
            border: 1px solid {border};
            selection-background-color: {accent};
            color: {text};
        }}

        /* ── Checkboxes ── */
        QCheckBox {{
            color: {text_mid};
            spacing: 6px;
        }}
        QCheckBox::indicator {{
            width: 18px; height: 18px;
            border-radius: 4px;
            border: 1px solid {c("input_border", dark)};
            background: {input_bg};
        }}
        QCheckBox::indicator:checked {{
            background: {accent};
            border-color: {accent};
        }}

        /* ── Progress bars ── */
        QProgressBar {{
            background-color: {border};
            border: none;
            border-radius: 3px;
            height: 6px;
            text-align: center;
        }}
        QProgressBar::chunk {{
            background-color: {accent};
            border-radius: 3px;
        }}

        /* ── Scroll bars ── */
        QScrollBar:vertical {{
            background: {bg};
            width: 8px;
            margin: 0;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {border};
            border-radius: 4px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {accent};
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar:horizontal {{
            background: {bg};
            height: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal {{
            background: {border};
            border-radius: 4px;
            min-width: 30px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {accent};
        }}
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0;
        }}

        /* ── Scroll area ── */
        QScrollArea {{
            border: none;
            background-color: transparent;
        }}

        /* ── Dialogs ── */
        QDialog {{
            background-color: {card};
        }}

        /* ── Tooltips ── */
        QToolTip {{
            background-color: {card};
            color: {text};
            border: 1px solid {border};
            border-radius: 4px;
            padding: 4px 8px;
        }}

        /* ── Message boxes ── */
        QMessageBox {{
            background-color: {card};
        }}

        /* ── Sliders ── */
        QSlider::groove:horizontal {{
            height: 4px;
            background: {border};
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            background: {accent};
            border: none;
            width: 16px; height: 16px;
            border-radius: 8px;
            margin: -6px 0;
        }}
        QSlider::sub-page:horizontal {{
            background: {accent};
            border-radius: 2px;
        }}

        /* ── Labels ── */
        QLabel {{
            background: transparent;
            border: none;
        }}
    """


# ── Convenience: apply theme to a running QApplication ────────────────────

def apply_qt_theme(dark: bool = False) -> None:
    """
    Apply the global QSS + Fusion style to the running QApplication.

    Call once at startup:
        apply_qt_theme(dark=config.get("appearance.dark_mode", True))

    And again whenever the user toggles:
        ThemeSignal.instance().theme_changed.connect(apply_qt_theme)
    """
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            set_dark_mode(dark)
            app.setStyle("Fusion")
            app.setStyleSheet(build_qss(dark))
            # Broadcast so all subscribed widgets can update themselves
            ThemeSignal.instance().theme_changed.emit(dark)
    except Exception as e:
        print(f"[theme] apply_qt_theme failed: {e}")