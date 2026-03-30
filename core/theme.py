"""
theme.py - SignDesk Theme Configuration
Controls colors, fonts, and appearance modes across the app.
"""

import customtkinter as ctk
import re

def apply_theme():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

# Palette
C_BG           = "#F0F4FF"
C_PANEL_LEFT   = "#1A237E"
C_PANEL_LEFT2  = "#283593"
C_ACCENT       = "#00BCD4"
C_ACCENT_HOVER = "#0097A7"
C_WHITE        = "#FFFFFF"
C_TEXT_DARK    = "#1A1A2E"
C_TEXT_MID     = "#4A5568"
C_TEXT_LIGHT   = "#A0AEC0"
C_INPUT_BG     = "#EEF2FF"
C_INPUT_BORDER = "#C5CAE9"
C_DASH_BG      = "#EEF2FF"
C_CARD_BG      = "#FFFFFF"
C_SUCCESS      = "#38A169"
C_ERROR_RED    = "#E53E3E"
C_WARN         = "#D97706"

# Fonts
FONT_TITLE     = ("Georgia", 32, "bold")
FONT_SUBTITLE  = ("Georgia", 15, "italic")
FONT_HEADING   = ("Trebuchet MS", 22, "bold")
FONT_SUBHEAD   = ("Trebuchet MS", 12)
FONT_LABEL     = ("Trebuchet MS", 12, "bold")
FONT_INPUT     = ("Trebuchet MS", 13)
FONT_BTN       = ("Trebuchet MS", 13, "bold")
FONT_SMALL     = ("Trebuchet MS", 11)
FONT_FEAT      = ("Trebuchet MS", 13)
FONT_NAV       = ("Trebuchet MS", 11, "bold")
FONT_REQ       = ("Trebuchet MS", 10)

# Password Rules Config
PASSWORD_RULES = [
    ("length",    "At least 8 characters",              lambda p: len(p) >= 8),
    ("uppercase", "At least 1 uppercase letter (A–Z)",  lambda p: bool(re.search(r"[A-Z]", p))),
    ("lowercase", "At least 1 lowercase letter (a–z)",  lambda p: bool(re.search(r"[a-z]", p))),
    ("digit",     "At least 1 number (0–9)",             lambda p: bool(re.search(r"[0-9]", p))),
    ("special",   "At least 1 special character (!@#$%^&* etc.)",
                                                         lambda p: bool(re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", p))),
]
