"""
core/ui_helpers.py - Reusable UI Components
Contains common UI widgets used across different modules.
"""

import customtkinter as ctk
import os
from tkinter import Canvas
from PIL import Image
from core.theme import (
    C_PANEL_LEFT, C_PANEL_LEFT2, C_ACCENT, C_CYAN, C_WHITE,
    C_TEXT_DARK, C_TEXT_MID, C_TEXT_LIGHT,
    C_INPUT_BG, C_INPUT_BORDER, C_INPUT_FOCUS,
    C_CARD_BG, C_CARD_BORDER, C_ACCENT_HOVER,
    C_DASH_BG,
    C_SIDEBAR_START, C_SIDEBAR_END, C_SIDEBAR_ACTIVE,
    C_NAV_TEXT, C_NAV_ACTIVE,
    FONT_PRIMARY, FONT_TITLE, FONT_SUBTITLE, FONT_FEAT,
    FONT_SMALL, FONT_LABEL, FONT_INPUT, FONT_BTN,
    FONT_SIDEBAR, FONT_SIDEBAR_ACTIVE,
)


# ══════════════════════════════════════════════════════════════
# SIDEBAR COMPONENTS (Dashboard)
# ══════════════════════════════════════════════════════════════

def _hex_to_rgb(hex_color: str):
    """Convert '#RRGGBB' to (r, g, b) tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _rgb_to_hex(r, g, b):
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def _lerp_color(c1: str, c2: str, t: float) -> str:
    """Linearly interpolate between two hex colors. t=0 → c1, t=1 → c2."""
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    return _rgb_to_hex(
        r1 + (r2 - r1) * t,
        g1 + (g2 - g1) * t,
        b1 + (b2 - b1) * t,
    )


def create_gradient_canvas(parent, width, height,
                           color_start=C_SIDEBAR_START,
                           color_end=C_SIDEBAR_END,
                           steps=64):
    """
    Create a Canvas filled with a vertical gradient (top → bottom).
    Returns the canvas widget — caller should place/pack/grid it.
    """
    canvas = Canvas(
        parent, width=width, height=height,
        highlightthickness=0, bd=0,
    )
    for i in range(steps):
        y0 = int(height * i / steps)
        y1 = int(height * (i + 1) / steps) + 1
        color = _lerp_color(color_start, color_end, i / max(steps - 1, 1))
        canvas.create_rectangle(0, y0, width, y1, fill=color, outline=color)
    return canvas


def create_nav_item(parent, icon: str, label: str,
                    is_active: bool = False, command=None):
    """
    Reusable sidebar navigation item.

    Parameters
    ----------
    parent    : container widget
    icon      : emoji or text icon
    label     : nav label text
    is_active : whether this is the currently active page
    command   : callback for click
    """
    bg = C_SIDEBAR_ACTIVE if is_active else "transparent"
    text_color = C_NAV_ACTIVE if is_active else C_NAV_TEXT
    font = FONT_SIDEBAR_ACTIVE if is_active else FONT_SIDEBAR

    frame = ctk.CTkFrame(parent, fg_color=bg, corner_radius=10, height=38)
    frame.pack(fill="x", pady=2)
    frame.pack_propagate(False)

    inner = ctk.CTkFrame(frame, fg_color="transparent")
    inner.pack(fill="x", padx=12, expand=True)

    icon_lbl = ctk.CTkLabel(
        inner, text=icon, font=("Segoe UI Emoji", 14),
        text_color=text_color, fg_color="transparent", width=24,
    )
    icon_lbl.pack(side="left", padx=(0, 8))

    text_lbl = ctk.CTkLabel(
        inner, text=label, font=font,
        text_color=text_color, fg_color="transparent", anchor="w",
    )
    text_lbl.pack(side="left", fill="x", expand=True)

    if command:
        for w in (frame, inner, icon_lbl, text_lbl):
            w.configure(cursor="hand2")
            w.bind("<Button-1>", lambda e, cmd=command: cmd())

    # Hover effect (only for inactive items)
    if not is_active and command:
        hover_bg = "#3D4470"
        def _enter(e):
            frame.configure(fg_color=hover_bg)
        def _leave(e):
            frame.configure(fg_color="transparent")
        for w in (frame, inner, icon_lbl, text_lbl):
            w.bind("<Enter>", _enter)
            w.bind("<Leave>", _leave)

    return frame


# ══════════════════════════════════════════════════════════════
# STEP-CARD COMPONENTS (How-To Section)
# ══════════════════════════════════════════════════════════════

_STEP_CARD_ACCENT = "#6C63FF"       # matches new purple accent
_STEP_BADGE_R     = 20
_STEP_BADGE_SIZE  = _STEP_BADGE_R * 2 + 4


def create_step_card(parent, step_number: int, title: str,
                     description: str, card_width: int = 155,
                     pad_top: int = 18, badge_gap: int = 12,
                     title_gap: int = 6, pad_bottom: int = 18,
                     pad_x: int = 14):
    """
    Reusable step-card component (frame-based).

    Uses a CTkFrame with corner_radius for the rounded card background,
    a small Canvas only for the numbered circle badge, and separate
    CTkLabel widgets for title and description.
    """
    wrap_width = card_width - pad_x * 2

    card = ctk.CTkFrame(
        parent,
        width=card_width,
        fg_color=C_CARD_BG,
        corner_radius=14,
        border_width=1,
        border_color=C_CARD_BORDER,
    )

    inner = ctk.CTkFrame(card, fg_color="transparent")
    inner.pack(fill="x", padx=pad_x, pady=(pad_top, pad_bottom))

    # Numbered circle badge
    badge_canvas = Canvas(
        inner, width=_STEP_BADGE_SIZE, height=_STEP_BADGE_SIZE,
        highlightthickness=0, bd=0, bg=C_CARD_BG,
    )
    cx = _STEP_BADGE_SIZE // 2
    cy = _STEP_BADGE_SIZE // 2
    r  = _STEP_BADGE_R
    badge_canvas.create_oval(
        cx - r, cy - r, cx + r, cy + r,
        fill=_STEP_CARD_ACCENT, outline=_STEP_CARD_ACCENT,
    )
    badge_canvas.create_text(
        cx, cy, text=str(step_number), fill=C_WHITE,
        font=(FONT_PRIMARY, 12, "bold"),
    )
    badge_canvas.pack(anchor="center", pady=(0, badge_gap))

    # Title
    ctk.CTkLabel(
        inner, text=title,
        font=(FONT_PRIMARY, 11, "bold"),
        text_color=_STEP_CARD_ACCENT,
        fg_color="transparent",
        wraplength=wrap_width,
        justify="center", anchor="center",
    ).pack(fill="x", pady=(0, title_gap))

    # Description
    ctk.CTkLabel(
        inner, text=description,
        font=(FONT_PRIMARY, 10),
        text_color=C_TEXT_MID,
        fg_color="transparent",
        wraplength=wrap_width,
        justify="center", anchor="center",
    ).pack(fill="x")

    return card


def build_steps_panel(parent, steps: list[tuple[str, str]],
                      card_width: int = 155):
    """Lay out N step cards in a single responsive horizontal row."""
    section_label = ctk.CTkLabel(
        parent, text="How to Use SignDesk",
        font=(FONT_PRIMARY, 13, "bold"),
        text_color=C_TEXT_DARK, fg_color="transparent", anchor="w",
    )
    section_label.pack(fill="x", pady=(24, 10))

    grid = ctk.CTkFrame(parent, fg_color="transparent")
    grid.pack(fill="x")

    for col_idx in range(len(steps)):
        grid.columnconfigure(col_idx, weight=1)

    for i, (title, desc) in enumerate(steps):
        card = create_step_card(
            grid, step_number=i + 1,
            title=title, description=desc,
            card_width=card_width,
        )
        card.grid(
            row=0, column=i,
            padx=(0, 8) if i < len(steps) - 1 else 0,
            pady=4, sticky="nsew",
        )

    return grid


# ══════════════════════════════════════════════════════════════
# AUTH PAGE COMPONENTS (Login / Register / Verify)
# ══════════════════════════════════════════════════════════════

def make_left_panel(parent: ctk.CTkFrame) -> ctk.CTkFrame:
    """
    Brand sidebar used on Login, Register, and Verify screens.
    Gradient background (dark blue → violet), logo, tagline, feature list.
    Properly structured with vertical pack layout for consistent alignment.
    """
    panel = ctk.CTkFrame(parent, width=300, fg_color=C_PANEL_LEFT, corner_radius=0)
    panel.pack_propagate(False)

    # Gradient canvas as background — use relwidth/relheight for dynamic sizing
    gradient = create_gradient_canvas(panel, 300, 700,
                                       color_start=C_SIDEBAR_START,
                                       color_end=C_SIDEBAR_END)
    gradient.place(x=0, y=0, relwidth=1, relheight=1)

    # ── Content overlay ────────────────────────────────────
    # Use a full-height transparent frame with pack layout
    # instead of center-placed inner (which misaligns)
    content = ctk.CTkFrame(panel, fg_color="transparent")
    content.place(x=0, y=0, relwidth=1, relheight=1)

    # ── Top spacer (pushes content toward vertical center) ─
    ctk.CTkFrame(content, fg_color="transparent", height=1).pack(
        fill="x", expand=True)

    # ── Logo ───────────────────────────────────────────────
    logo_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "assets", "logo.png"
    )
    if os.path.exists(logo_path):
        try:
            logo_img = ctk.CTkImage(Image.open(logo_path), size=(110, 110))
            lbl = ctk.CTkLabel(
                content, image=logo_img, text="", fg_color="transparent"
            )
            lbl.pack(pady=(0, 14))
            lbl._img_ref = logo_img   # prevent GC
        except Exception:
            _fallback_logo(content)
    else:
        _fallback_logo(content)

    # ── App name + tagline ─────────────────────────────────
    ctk.CTkLabel(
        content, text="SignDesk",
        font=(FONT_PRIMARY, 26, "bold"),
        text_color=C_WHITE, fg_color="transparent"
    ).pack()
    ctk.CTkLabel(
        content, text="Sign Language to Speech",
        font=(FONT_PRIMARY, 12), text_color="#C4B5FD", fg_color="transparent"
    ).pack(pady=(4, 30))

    # Subtle divider
    ctk.CTkFrame(
        content, height=1, width=180, fg_color="#4A4590"
    ).pack(pady=(0, 24))

    # ── Feature list ───────────────────────────────────────
    feat_frame = ctk.CTkFrame(content, fg_color="transparent")
    feat_frame.pack(padx=36)

    features = [
        "Real-time gesture recognition",
        "Instant speech output",
        "Accessible & inclusive",
    ]
    for feat in features:
        row = ctk.CTkFrame(feat_frame, fg_color="transparent")
        row.pack(anchor="w", pady=7)

        dot = ctk.CTkFrame(row, width=6, height=6,
                           fg_color="#A78BFA", corner_radius=3)
        dot.pack_propagate(False)
        dot.pack(side="left", padx=(0, 10), pady=2)

        ctk.CTkLabel(
            row, text=feat, font=(FONT_PRIMARY, 12),
            text_color="#C4B5FD", fg_color="transparent"
        ).pack(side="left")

    # ── Bottom spacer (balances top spacer — centers content) ─
    ctk.CTkFrame(content, fg_color="transparent", height=1).pack(
        fill="x", expand=True)

    # ── Copyright at bottom ────────────────────────────────
    ctk.CTkLabel(
        content, text="© 2025 SignDesk Project",
        font=(FONT_PRIMARY, 10), text_color="#7C7AAA", fg_color="transparent"
    ).pack(pady=(0, 16))

    return panel


def _fallback_logo(parent):
    """Rendered when logo.png is missing."""
    ctk.CTkLabel(
        parent, text="🤟",
        font=("Segoe UI Emoji", 56), text_color="#A78BFA",
        fg_color="transparent"
    ).pack(pady=(0, 12))


def make_field(parent, label: str, placeholder: str,
               show: str = "", optional: bool = False) -> ctk.CTkEntry:
    """Labeled input field with focus-ring highlight."""
    lrow = ctk.CTkFrame(parent, fg_color="transparent")
    lrow.pack(fill="x", pady=(0, 4))

    ctk.CTkLabel(
        lrow, text=label.upper(),
        font=(FONT_PRIMARY, 10, "bold"),
        text_color="#A0AEC0", fg_color="transparent", anchor="w"
    ).pack(side="left")

    if optional:
        ctk.CTkLabel(
            lrow, text="  optional",
            font=(FONT_PRIMARY, 10),
            text_color=C_TEXT_LIGHT, fg_color="transparent"
        ).pack(side="left")

    entry = ctk.CTkEntry(
        parent,
        placeholder_text=placeholder,
        font=FONT_INPUT,
        fg_color=C_INPUT_BG,
        border_color=C_INPUT_BORDER, border_width=1,
        text_color=C_TEXT_DARK,
        placeholder_text_color=C_TEXT_LIGHT,
        height=42, corner_radius=8,
        show=show,
    )
    entry.pack(fill="x", pady=(0, 14))

    entry.bind("<FocusIn>",
               lambda e: entry.configure(border_color=C_INPUT_FOCUS))
    entry.bind("<FocusOut>",
               lambda e: entry.configure(border_color=C_INPUT_BORDER))

    return entry


def make_primary_button(parent, text: str, command) -> ctk.CTkButton:
    """Solid purple primary action button."""
    return ctk.CTkButton(
        parent, text=text, command=command,
        font=FONT_BTN,
        fg_color=C_ACCENT, hover_color=C_ACCENT_HOVER,
        text_color=C_WHITE,
        height=42, corner_radius=21   # pill style
    )


def make_ghost_button(parent, text: str, command) -> ctk.CTkButton:
    """Outline secondary button — white bg, subtle border."""
    return ctk.CTkButton(
        parent, text=text, command=command,
        font=FONT_BTN,
        fg_color="#FFFFFF", hover_color=C_INPUT_BG,
        text_color=C_TEXT_DARK,
        border_width=1, border_color=C_CARD_BORDER,
        height=42, corner_radius=21   # pill style
    )
