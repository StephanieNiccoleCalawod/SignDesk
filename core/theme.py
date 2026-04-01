"""
theme.py - SignDesk Theme Configuration
"""
import customtkinter as ctk
import re

def apply_theme():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

# ── Palette ────────────────────────────────────────────────
C_BG            = "#F0F4FF"
C_PANEL_LEFT    = "#1A2472"
C_PANEL_LEFT2   = "#1E2E8A"
C_ACCENT        = "#1A6EC7"
C_ACCENT_HOVER  = "#155BB0"
C_CYAN          = "#5BC8F5"
C_WHITE         = "#FFFFFF"
C_TEXT_DARK     = "#1A1A2E"
C_TEXT_MID      = "#4A5568"
C_TEXT_LIGHT    = "#A0AEC0"
C_INPUT_BG      = "#F7F8FA"
C_INPUT_BORDER  = "#CCCCCC"
C_INPUT_FOCUS   = "#1A6EC7"
C_DASH_BG       = "#F0F4FF"
C_CARD_BG       = "#FFFFFF"
C_CARD_BORDER   = "#E0E0E0"

# Semantic
C_SUCCESS       = "#1D9E75"
C_SUCCESS_BG    = "#E1F5EE"
C_ERROR_RED     = "#E24B4A"
C_ERROR_BG      = "#FCEBEB"
C_WARN          = "#BA7517"
C_WARN_BG       = "#FAEEDA"
C_INFO_BG       = "#E6F1FB"
C_INFO_TEXT     = "#185FA5"

# Module badge colors
C_BADGE_BLUE_BG  = "#E6F1FB"
C_BADGE_BLUE_FG  = "#185FA5"
C_BADGE_TEAL_BG  = "#E1F5EE"
C_BADGE_TEAL_FG  = "#0F6E56"
C_BADGE_AMBER_BG = "#FAEEDA"
C_BADGE_AMBER_FG = "#854F0B"
C_BADGE_GRAY_BG  = "#F0F0F0"
C_BADGE_GRAY_FG  = "#888888"

# ── Fonts ──────────────────────────────────────────────────
FONT_PRIMARY   = "Trebuchet MS"   # fixes FONT_PRIMARY NameError in vision/ui.py
FONT_TITLE     = ("Georgia", 32, "bold")
FONT_SUBTITLE  = ("Georgia", 15, "italic")
FONT_HEADING   = (FONT_PRIMARY, 22, "bold")
FONT_SUBHEAD   = (FONT_PRIMARY, 12)
FONT_LABEL     = (FONT_PRIMARY, 12, "bold")
FONT_LABEL_SM  = (FONT_PRIMARY, 11, "bold")
FONT_INPUT     = (FONT_PRIMARY, 13)
FONT_BTN       = (FONT_PRIMARY, 13, "bold")
FONT_SMALL     = (FONT_PRIMARY, 11)
FONT_FEAT      = (FONT_PRIMARY, 13)
FONT_NAV       = (FONT_PRIMARY, 11, "bold")
FONT_REQ       = (FONT_PRIMARY, 10)

# ── Password Rules ─────────────────────────────────────────
PASSWORD_RULES = [
    ("length",    "At least 8 characters",
                  lambda p: len(p) >= 8),
    ("uppercase", "At least 1 uppercase letter (A–Z)",
                  lambda p: bool(re.search(r"[A-Z]", p))),
    ("lowercase", "At least 1 lowercase letter (a–z)",
                  lambda p: bool(re.search(r"[a-z]", p))),
    ("digit",     "At least 1 number (0–9)",
                  lambda p: bool(re.search(r"[0-9]", p))),
    ("special",   "At least 1 special character (!@#$%^&* etc.)",
                  lambda p: bool(re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", p))),
]
