"""
core/ui_helpers.py - Reusable UI Components
Contains common UI widgets used across different modules.
"""

import customtkinter as ctk
import os
from PIL import Image
from core.theme import (
    C_PANEL_LEFT, C_PANEL_LEFT2, C_ACCENT, C_CYAN, C_WHITE,
    C_TEXT_DARK, C_TEXT_MID, C_TEXT_LIGHT,
    C_INPUT_BG, C_INPUT_BORDER, C_INPUT_FOCUS,
    C_CARD_BORDER, C_ACCENT_HOVER,
    FONT_PRIMARY, FONT_TITLE, FONT_SUBTITLE, FONT_FEAT,
    FONT_SMALL, FONT_LABEL, FONT_INPUT, FONT_BTN,
)


def make_left_panel(parent: ctk.CTkFrame) -> ctk.CTkFrame:
    """
    Brand sidebar used on Login, Register, and Verify screens.
    Navy background, logo, tagline, feature list, copyright.
    """
    panel = ctk.CTkFrame(parent, width=340, fg_color=C_PANEL_LEFT, corner_radius=0)
    panel.pack_propagate(False)

    inner = ctk.CTkFrame(panel, fg_color="transparent")
    inner.place(relx=0.5, rely=0.5, anchor="center")

    # ── Logo ───────────────────────────────────────────────
    logo_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "assets", "logo.png"
    )
    if os.path.exists(logo_path):
        try:
            logo_img = ctk.CTkImage(Image.open(logo_path), size=(160, 160))
            ctk.CTkLabel(
                inner, image=logo_img, text="", fg_color="transparent"
            ).pack(pady=(0, 10))
        except Exception:
            _fallback_logo(inner)
    else:
        _fallback_logo(inner)

    # ── App name + tagline ─────────────────────────────────
    ctk.CTkLabel(
        inner, text="SignDesk",
        font=FONT_TITLE, text_color=C_WHITE, fg_color="transparent"
    ).pack()
    ctk.CTkLabel(
        inner, text="Sign Language to Speech",
        font=FONT_SUBTITLE, text_color=C_CYAN, fg_color="transparent"
    ).pack(pady=(6, 28))

    # Subtle divider
    ctk.CTkFrame(
        inner, height=1, width=200, fg_color=C_PANEL_LEFT2
    ).pack(pady=(0, 24))

    # ── Feature list ───────────────────────────────────────
    features = [
        "Real-time gesture recognition",
        "Instant speech output",
        "Accessible & inclusive",
    ]
    for feat in features:
        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(anchor="w", pady=6)

        # Cyan dot instead of arrow — cleaner at small sizes
        dot = ctk.CTkFrame(row, width=6, height=6,
                           fg_color=C_CYAN, corner_radius=3)
        dot.pack_propagate(False)
        dot.pack(side="left", padx=(0, 10), pady=2)

        ctk.CTkLabel(
            row, text=feat, font=FONT_FEAT,
            text_color="#B0BEC5", fg_color="transparent"
        ).pack(side="left")

    # ── Copyright ──────────────────────────────────────────
    ctk.CTkLabel(
        panel, text="© 2025 SignDesk Project",
        font=FONT_SMALL, text_color="#546E7A", fg_color="transparent"
    ).place(relx=0.5, rely=0.97, anchor="s")

    return panel


def _fallback_logo(parent):
    """Rendered when logo.png is missing."""
    ctk.CTkLabel(
        parent, text="🤟",
        font=("Segoe UI Emoji", 56), text_color=C_CYAN,
        fg_color="transparent"
    ).pack(pady=(0, 12))


def make_field(parent, label: str, placeholder: str,
               show: str = "", optional: bool = False) -> ctk.CTkEntry:
    """
    Labeled input field with focus-ring highlight.
    Label is small uppercase; entry gets a 1px brand-blue border on focus.
    """
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

    # Focus ring — 1px brand-blue border on focus
    entry.bind("<FocusIn>",
               lambda e: entry.configure(border_color=C_INPUT_FOCUS))
    entry.bind("<FocusOut>",
               lambda e: entry.configure(border_color=C_INPUT_BORDER))

    return entry


def make_primary_button(parent, text: str, command) -> ctk.CTkButton:
    """Solid blue primary action button."""
    return ctk.CTkButton(
        parent, text=text, command=command,
        font=FONT_BTN,
        fg_color=C_ACCENT, hover_color=C_ACCENT_HOVER,
        text_color=C_WHITE,
        height=42, corner_radius=8
    )


def make_ghost_button(parent, text: str, command) -> ctk.CTkButton:
    """
    Outline secondary button — white bg, 0.5px border, dark text.
    Replaces the old transparent/mid-text ghost that was hard to read.
    """
    return ctk.CTkButton(
        parent, text=text, command=command,
        font=FONT_BTN,
        fg_color="#FFFFFF", hover_color=C_INPUT_BG,
        text_color=C_TEXT_DARK,
        border_width=1, border_color=C_CARD_BORDER,
        height=42, corner_radius=8
    )
