"""
theme.py - SignDesk Theme Configuration
Modern dashboard aesthetic with Dark Mode support via (light, dark) tuples.
"""
import customtkinter as ctk
import re

def apply_theme():
    ctk.set_appearance_mode("dark")  # Defaulting to dark as requested
    ctk.set_default_color_theme("blue")

# ── Color Palette Dictionary (New standard) ────────────────
COLORS = {
    "bg_primary": ("#FFFFFF", "#141416"),          # Main cards & panels
    "bg_secondary": ("#F3F1F8", "#0A0A0B"),        # Window background
    "panel_left": ("#2C3358", "#1A1A1E"),          # Sidebar
    "panel_left_end": ("#6C63FF", "#282836"),      # Sidebar gradient if any
    
    "text_primary": ("#1F1F1F", "#F1F1F5"),        # Headings, active text
    "text_secondary": ("#6B7280", "#9CA3AF"),      # Subtitles
    "text_muted": ("#A0AEC0", "#6B7280"),          # Placeholders

    "accent": ("#6C63FF", "#6C63FF"),              # Primary buttons
    "accent_hover": ("#5A52E0", "#5A52E0"),        
    "cyan": ("#A78BFA", "#A78BFA"),                # Secondary highlight

    "border": ("#EDE9F3", "#272730"),              # Card borders
    "input_bg": ("#F7F8FA", "#1C1C24"),            # Input fields
    "input_border": ("#D4D0E6", "#3A3A4A"),

    # Semantic Colors
    "success": ("#1D9E75", "#22C55E"),
    "success_bg": ("#E1F5EE", "#163325"),
    "error": ("#E24B4A", "#F87171"),
    "error_bg": ("#FCEBEB", "#3C1D1D"),
    "warn": ("#BA7517", "#FBBF24"),
    "warn_bg": ("#FAEEDA", "#3A2A0D"),
    "info": ("#5E35B1", "#A78BFA"),
    "info_bg": ("#EDE7F6", "#2C2245"),

    # Badge Colors
    "badge_gray_bg": ("#F0F0F0", "#272730"),
    "badge_gray_fg": ("#888888", "#9CA3AF"),
}

# ── Legacy Constants (Mapped to Tuples for Backwards Comp.) ──
C_BG            = COLORS["bg_secondary"]
C_PANEL_LEFT    = COLORS["panel_left"]
C_PANEL_LEFT2   = COLORS["panel_left_end"]
C_ACCENT        = COLORS["accent"]
C_ACCENT_HOVER  = COLORS["accent_hover"]
C_CYAN          = COLORS["cyan"]
C_WHITE         = ("#FFFFFF", "#FFFFFF")
C_TEXT_DARK     = COLORS["text_primary"]
C_TEXT_MID      = COLORS["text_secondary"]
C_TEXT_LIGHT    = COLORS["text_muted"]
C_INPUT_BG      = COLORS["input_bg"]
C_INPUT_BORDER  = COLORS["input_border"]
C_INPUT_FOCUS   = COLORS["accent"]
C_DASH_BG       = COLORS["bg_secondary"]
C_CARD_BG       = COLORS["bg_primary"]
C_CARD_BORDER   = COLORS["border"]

# Semantic
C_SUCCESS       = COLORS["success"]
C_SUCCESS_BG    = COLORS["success_bg"]
C_ERROR_RED     = COLORS["error"]
C_ERROR_BG      = COLORS["error_bg"]
C_WARN          = COLORS["warn"]
C_WARN_BG       = COLORS["warn_bg"]
C_INFO_BG       = COLORS["info_bg"]
C_INFO_TEXT     = COLORS["info"]

# Badges
C_BADGE_BLUE_BG  = COLORS["info_bg"]
C_BADGE_BLUE_FG  = COLORS["info"]
C_BADGE_TEAL_BG  = COLORS["success_bg"]
C_BADGE_TEAL_FG  = COLORS["success"]
C_BADGE_AMBER_BG = COLORS["warn_bg"]
C_BADGE_AMBER_FG = COLORS["warn"]
C_BADGE_GRAY_BG  = COLORS["badge_gray_bg"]
C_BADGE_GRAY_FG  = COLORS["badge_gray_fg"]

# Sidebar specific
C_SIDEBAR_START  = COLORS["panel_left"]
C_SIDEBAR_END    = COLORS["panel_left_end"]
C_SIDEBAR_ACTIVE = ("#495086", "#2D2D3D")
C_NAV_TEXT       = ("#B8B5D0", "#84849E")
C_NAV_ACTIVE     = ("#FFFFFF", "#FFFFFF")

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
