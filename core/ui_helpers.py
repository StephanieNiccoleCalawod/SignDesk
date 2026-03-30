"""
ui_helpers.py - Reusable UI Components
Contains common UI widgets used across different modules.
"""

import customtkinter as ctk
from core.theme import (
    C_PANEL_LEFT, C_PANEL_LEFT2, C_ACCENT, C_WHITE, FONT_TITLE, FONT_SUBTITLE, 
    FONT_FEAT, FONT_SMALL, C_TEXT_DARK, C_TEXT_LIGHT, C_TEXT_MID,
    C_INPUT_BG, C_INPUT_BORDER, FONT_LABEL, FONT_INPUT, FONT_BTN, C_ACCENT_HOVER
)

def make_left_panel(parent: ctk.CTkFrame) -> ctk.CTkFrame:
    panel = ctk.CTkFrame(parent, width=340, fg_color=C_PANEL_LEFT, corner_radius=0)
    panel.pack_propagate(False)

    inner = ctk.CTkFrame(panel, fg_color="transparent")
    inner.place(relx=0.5, rely=0.5, anchor="center")

    ctk.CTkLabel(inner, text="🤟", font=("Segoe UI Emoji", 64),
                 text_color=C_ACCENT, fg_color="transparent").pack(pady=(0, 16))
    ctk.CTkLabel(inner, text="SignDesk", font=FONT_TITLE,
                 text_color=C_WHITE, fg_color="transparent").pack()
    ctk.CTkLabel(inner, text="Sign Language to Speech", font=FONT_SUBTITLE,
                 text_color=C_ACCENT, fg_color="transparent").pack(pady=(6, 32))

    ctk.CTkFrame(inner, height=2, width=210, fg_color=C_PANEL_LEFT2).pack(pady=(0, 28))

    for feat in ["Real-time gesture recognition", "Instant speech output", "Accessible & inclusive"]:
        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(anchor="w", pady=8)
        ctk.CTkLabel(row, text="▸", font=("Trebuchet MS", 14, "bold"),
                     text_color=C_ACCENT, fg_color="transparent").pack(side="left", padx=(0, 10))
        ctk.CTkLabel(row, text=feat, font=FONT_FEAT,
                     text_color="#B0BEC5", fg_color="transparent").pack(side="left")

    ctk.CTkLabel(panel, text="© 2025 SignDesk Project", font=FONT_SMALL,
                 text_color="#546E7A", fg_color="transparent").place(relx=0.5, rely=0.97, anchor="s")

    return panel


def make_field(parent, label: str, placeholder: str,
               show: str = "", optional: bool = False) -> ctk.CTkEntry:
    lrow = ctk.CTkFrame(parent, fg_color="transparent")
    lrow.pack(fill="x", pady=(0, 4))
    ctk.CTkLabel(lrow, text=label, font=FONT_LABEL,
                 text_color=C_TEXT_DARK, fg_color="transparent", anchor="w").pack(side="left")
    if optional:
        ctk.CTkLabel(lrow, text="  (optional)", font=("Trebuchet MS", 10),
                     text_color=C_TEXT_LIGHT, fg_color="transparent").pack(side="left")
    entry = ctk.CTkEntry(parent, placeholder_text=placeholder, font=FONT_INPUT,
                         fg_color=C_INPUT_BG, border_color=C_INPUT_BORDER, border_width=1,
                         text_color=C_TEXT_DARK, placeholder_text_color=C_TEXT_LIGHT,
                         height=42, corner_radius=8, show=show)
    entry.pack(fill="x", pady=(0, 16))
    return entry


def make_primary_button(parent, text: str, command) -> ctk.CTkButton:
    return ctk.CTkButton(parent, text=text, command=command, font=FONT_BTN,
                         fg_color=C_ACCENT, hover_color=C_ACCENT_HOVER,
                         text_color=C_WHITE, height=44, corner_radius=8)


def make_ghost_button(parent, text: str, command) -> ctk.CTkButton:
    return ctk.CTkButton(parent, text=text, command=command, font=FONT_BTN,
                         fg_color="transparent", hover_color=C_INPUT_BG, text_color=C_TEXT_MID,
                         border_width=1, border_color=C_INPUT_BORDER, height=44, corner_radius=8)
