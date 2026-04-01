"""
modules/dashboard/ui.py - Dashboard UI
"""

import customtkinter as ctk
from tkinter import messagebox
import os
from PIL import Image
from core.theme import *


class DashboardPage(ctk.CTkFrame):
    def __init__(self, parent, app, username: str):
        super().__init__(parent, fg_color=C_DASH_BG, corner_radius=0)
        self._app      = app
        self._username = username
        self._build()

    def _launch_gesture_detection(self):
        self._app.show_gesture_detection(self._username)

    def _on_logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to log out?"):
            self._app.show_login()

    def _build(self):
        self._build_navbar()
        body = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        body.pack(fill="both", expand=True, padx=36, pady=28)
        self._build_welcome(body)
        self._build_stats(body)
        self._build_modules(body)
        self._build_footer(body)

    def _build_navbar(self):
        navbar = ctk.CTkFrame(self, height=60, fg_color=C_PANEL_LEFT, corner_radius=0)
        navbar.pack(fill="x", side="top")
        navbar.pack_propagate(False)

        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "assets", "logo.png"
        )
        if os.path.exists(logo_path):
            try:
                logo_img = ctk.CTkImage(Image.open(logo_path), size=(36, 36))
                ctk.CTkLabel(navbar, image=logo_img, text="").pack(
                    side="left", padx=(20, 10))
            except Exception:
                pass

        ctk.CTkLabel(
            navbar, text="SignDesk",
            font=("Georgia", 18, "bold"),
            text_color=C_WHITE, fg_color="transparent"
        ).pack(side="left", padx=24 if not os.path.exists(logo_path) else 0)

        ctk.CTkButton(
            navbar, text="Logout  →",
            command=self._on_logout, font=FONT_NAV,
            fg_color=C_ERROR_RED, hover_color="#C73D3C",
            text_color=C_WHITE, width=100, height=32, corner_radius=6
        ).pack(side="right", padx=20, pady=14)

    def _build_welcome(self, parent):
        card = ctk.CTkFrame(
            parent, fg_color=C_INFO_BG, corner_radius=12,
            border_width=1, border_color="#B5D4F4"
        )
        card.pack(fill="x", pady=(0, 20))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=24, pady=18, anchor="w")
        ctk.CTkLabel(
            inner, text=f"Good day, {self._username} 👋",
            font=("Georgia", 18, "bold"),
            text_color="#042C53", fg_color="transparent"
        ).pack(anchor="w")
        ctk.CTkLabel(
            inner,
            text="You're successfully signed in to SignDesk. Your dashboard is ready.",
            font=FONT_SUBHEAD, text_color=C_INFO_TEXT, fg_color="transparent"
        ).pack(anchor="w", pady=(4, 0))

    def _build_stats(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 20))
        frame.columnconfigure((0, 1, 2), weight=1)

        for col, (label, value) in enumerate([
            ("Sessions today", "3"),
            ("Avg. accuracy",  "91%"),
            ("Signs learned",  "24"),
        ]):
            card = ctk.CTkFrame(
                frame, fg_color=C_CARD_BG, corner_radius=8,
                border_width=1, border_color=C_CARD_BORDER
            )
            card.grid(row=0, column=col,
                      padx=(0, 10) if col < 2 else 0,
                      sticky="nsew")
            ctk.CTkLabel(card, text=label, font=FONT_SMALL,
                         text_color=C_TEXT_LIGHT, fg_color="transparent"
                         ).pack(anchor="w", padx=16, pady=(14, 2))
            ctk.CTkLabel(card, text=value,
                         font=(FONT_PRIMARY, 22, "bold"),
                         text_color=C_TEXT_DARK, fg_color="transparent"
                         ).pack(anchor="w", padx=16, pady=(0, 14))

    def _build_modules(self, parent):
        ctk.CTkLabel(
            parent, text="Modules",
            font=(FONT_PRIMARY, 13, "bold"),
            text_color=C_TEXT_DARK, fg_color="transparent", anchor="w"
        ).pack(fill="x", pady=(0, 10))

        modules = [
            ("🖐️", "Gesture Recognition",
             "Detect and interpret hand signs in real time using your camera.",
             True,  self._launch_gesture_detection,
             C_BADGE_BLUE_BG,  C_BADGE_BLUE_FG),

            ("🔊", "Speech Output",
             "Convert recognized signs to spoken audio instantly.",
             False, None,
             C_BADGE_TEAL_BG,  C_BADGE_TEAL_FG),

            ("📖", "Sign Dictionary",
             "Browse and learn the full supported sign language vocabulary.",
             False, None,
             C_BADGE_AMBER_BG, C_BADGE_AMBER_FG),

            ("📊", "Session History",
             "Review your past sessions, accuracy scores, and progress.",
             False, None,
             C_BADGE_GRAY_BG,  C_BADGE_GRAY_FG),
        ]

        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        for i, (icon, title, desc, is_active, cb, icon_bg, icon_fg) in enumerate(modules):
            card = ctk.CTkFrame(
                grid, fg_color=C_CARD_BG, corner_radius=12,
                border_width=1,
                border_color=C_ACCENT if is_active else C_CARD_BORDER
            )
            card.grid(
                row=i // 2, column=i % 2,
                padx=(0, 10) if i % 2 == 0 else 0,
                pady=6, sticky="nsew"
            )
            pad = ctk.CTkFrame(card, fg_color="transparent")
            pad.pack(padx=20, pady=18, anchor="w", fill="x")

            # Colored icon badge
            badge = ctk.CTkFrame(pad, width=40, height=40,
                                 fg_color=icon_bg, corner_radius=10)
            badge.pack_propagate(False)
            badge.pack(anchor="w", pady=(0, 10))
            ctk.CTkLabel(badge, text=icon, font=("Segoe UI Emoji", 18),
                         fg_color="transparent"
                         ).place(relx=0.5, rely=0.5, anchor="center")

            ctk.CTkLabel(pad, text=title,
                         font=(FONT_PRIMARY, 13, "bold"),
                         text_color=C_TEXT_DARK, fg_color="transparent",
                         anchor="w").pack(fill="x")
            ctk.CTkLabel(pad, text=desc,
                         font=(FONT_PRIMARY, 11), text_color=C_TEXT_MID,
                         fg_color="transparent", anchor="w",
                         wraplength=300, justify="left"
                         ).pack(fill="x", pady=(4, 0))

            # Status badge
            badge_text  = "Launch  →" if is_active else "Coming soon"
            badge_bg    = icon_bg if is_active else C_BADGE_GRAY_BG
            badge_fg    = icon_fg if is_active else C_BADGE_GRAY_FG

            status_frame = ctk.CTkFrame(pad, fg_color=badge_bg, corner_radius=6)
            status_frame.pack(anchor="w", pady=(12, 0))
            status_lbl = ctk.CTkLabel(
                status_frame, text=badge_text,
                font=(FONT_PRIMARY, 11, "bold"),
                text_color=badge_fg, fg_color="transparent"
            )
            status_lbl.pack(padx=10, pady=4)

            if is_active and cb:
                status_frame.configure(cursor="hand2")
                status_frame.bind("<Button-1>", lambda e, f=cb: f())
                status_lbl.bind("<Button-1>",   lambda e, f=cb: f())

    def _build_footer(self, parent):
        ctk.CTkLabel(
            parent,
            text="SignDesk v1.0.0  •  © 2025 SignDesk Project  •  All rights reserved",
            font=FONT_SMALL, text_color=C_TEXT_LIGHT, fg_color="transparent"
        ).pack(pady=(28, 4))
