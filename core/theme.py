"""
theme.py - SignDesk Theme Configuration
Modern soft-gradient SaaS dashboard aesthetic.
"""
import customtkinter as ctk
import re

def apply_theme():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

# ── Palette ────────────────────────────────────────────────
C_BG            = "#F3F1F8"        # soft lavender-gray main bg
C_PANEL_LEFT    = "#2C3358"        # sidebar / auth panel dark
C_PANEL_LEFT2   = "#6C63FF"        # sidebar gradient end (violet)
C_ACCENT        = "#6C63FF"        # primary accent — soft purple
C_ACCENT_HOVER  = "#5A52E0"        # accent hover state
C_CYAN          = "#A78BFA"        # secondary highlight — soft violet
C_WHITE         = "#FFFFFF"
C_TEXT_DARK     = "#1F1F1F"        # titles
C_TEXT_MID      = "#6B7280"        # secondary text — gray
C_TEXT_LIGHT    = "#A0AEC0"        # muted placeholders
C_INPUT_BG      = "#F7F8FA"
C_INPUT_BORDER  = "#D4D0E6"        # purple-tinted input border
C_INPUT_FOCUS   = "#6C63FF"        # focus ring — purple
C_DASH_BG       = "#F3F1F8"        # dashboard content area
C_CARD_BG       = "#FFFFFF"
C_CARD_BORDER   = "#EDE9F3"        # soft purple-tinted border

# Semantic
C_SUCCESS       = "#1D9E75"
C_SUCCESS_BG    = "#E1F5EE"
C_ERROR_RED     = "#E24B4A"
C_ERROR_BG      = "#FCEBEB"
C_WARN          = "#BA7517"
C_WARN_BG       = "#FAEEDA"
C_INFO_BG       = "#EDE7F6"        # light purple welcome banner
C_INFO_TEXT     = "#5E35B1"        # deep purple welcome text

# Module badge colors — purple-tinted
C_BADGE_BLUE_BG  = "#EDE7F6"
C_BADGE_BLUE_FG  = "#5E35B1"
C_BADGE_TEAL_BG  = "#E1F5EE"
C_BADGE_TEAL_FG  = "#0F6E56"
C_BADGE_AMBER_BG = "#FAEEDA"
C_BADGE_AMBER_FG = "#854F0B"
C_BADGE_GRAY_BG  = "#F0F0F0"
C_BADGE_GRAY_FG  = "#888888"

# Sidebar specific
C_SIDEBAR_START  = "#2C3358"       # gradient dark end
C_SIDEBAR_END    = "#6C63FF"       # gradient light end
C_SIDEBAR_ACTIVE = "#495086"       # active nav item bg (translucent white sim)
C_NAV_TEXT       = "#B8B5D0"       # muted lavender nav labels
C_NAV_ACTIVE     = "#FFFFFF"       # active nav item text

# ── Fonts ──────────────────────────────────────────────────
FONT_PRIMARY   = "Segoe UI"
FONT_TITLE     = ("Segoe UI", 28, "bold")
FONT_SUBTITLE  = ("Segoe UI", 13)
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
FONT_SIDEBAR   = (FONT_PRIMARY, 12)
FONT_SIDEBAR_ACTIVE = (FONT_PRIMARY, 12, "bold")

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
    ("special",   "At least 1 special character (!@#$%^& etc.)",
                  lambda p: bool(re.search(r"[!@#$%^&*()\+\-=\[\]{};':\"\\|,.<>\/?]", p))),
]
