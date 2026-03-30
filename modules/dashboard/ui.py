"""
ui.py - Dashboard UI Pages
Contains the dashboard main page.
"""

import customtkinter as ctk
from tkinter import messagebox
from core.theme import *

class DashboardPage(ctk.CTkFrame):
    def __init__(self, parent, app, username: str):
        super().__init__(parent, fg_color=C_DASH_BG, corner_radius=0)
        self._app      = app
        self._username = username
        self._build()

    def _launch_gesture_detection(self):
        """Navigate to the Gesture Detection page."""
        self._app.show_gesture_detection(self._username)

    def _build(self):
        navbar = ctk.CTkFrame(self, height=60, fg_color=C_PANEL_LEFT, corner_radius=0)
        navbar.pack(fill="x", side="top")
        navbar.pack_propagate(False)

        ctk.CTkLabel(navbar, text="🤟  SignDesk", font=("Georgia", 18, "bold"),
                     text_color=C_WHITE, fg_color="transparent").pack(side="left", padx=28)
        ctk.CTkButton(navbar, text="Logout  →", command=self._on_logout, font=FONT_NAV,
                      fg_color=C_ACCENT, hover_color=C_ACCENT_HOVER, text_color=C_WHITE,
                      width=110, height=34, corner_radius=6).pack(side="right", padx=24, pady=13)

        body = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        body.pack(fill="both", expand=True, padx=36, pady=28)

        welcome_card = ctk.CTkFrame(body, fg_color=C_CARD_BG, corner_radius=12)
        welcome_card.pack(fill="x", pady=(0, 24))
        inner = ctk.CTkFrame(welcome_card, fg_color="transparent")
        inner.pack(padx=28, pady=22, anchor="w")

        ctk.CTkLabel(inner, text=f"Good day, {self._username} 👋",
                     font=("Georgia", 20, "bold"), text_color=C_TEXT_DARK,
                     fg_color="transparent").pack(anchor="w")
        ctk.CTkLabel(inner, text="You're successfully signed in to SignDesk. Your dashboard is ready.",
                     font=FONT_SUBHEAD, text_color=C_TEXT_MID,
                     fg_color="transparent").pack(anchor="w", pady=(6, 0))

        ctk.CTkLabel(body, text="Modules", font=("Trebuchet MS", 14, "bold"),
                     text_color=C_TEXT_DARK, fg_color="transparent",
                     anchor="w").pack(fill="x", pady=(0, 12))

        # Module definitions: (icon, title, description, is_active, callback)
        modules = [
            ("🖐️", "Gesture Recognition", "Detect and interpret hand signs in real time using your camera.", True, self._launch_gesture_detection),
            ("🔊", "Speech Output",        "Convert recognized signs to spoken audio instantly.", False, None),
            ("📖", "Sign Dictionary",      "Browse and learn the full supported sign language vocabulary.", False, None),
            ("📊", "Session History",      "Review your past sessions, accuracy scores, and progress.", False, None),
        ]

        grid = ctk.CTkFrame(body, fg_color="transparent")
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        for i, (icon, title, desc, is_active, callback) in enumerate(modules):
            card = ctk.CTkFrame(grid, fg_color=C_CARD_BG, corner_radius=12)
            card.grid(row=i // 2, column=i % 2,
                      padx=(0, 12) if i % 2 == 0 else (0, 0),
                      pady=6, sticky="nsew")
            pad = ctk.CTkFrame(card, fg_color="transparent")
            pad.pack(padx=20, pady=18, anchor="w", fill="x")

            badge = ctk.CTkFrame(pad, width=44, height=44, fg_color=C_PANEL_LEFT, corner_radius=10)
            badge.pack_propagate(False)
            badge.pack(anchor="w", pady=(0, 10))
            ctk.CTkLabel(badge, text=icon, font=("Segoe UI Emoji", 20),
                         fg_color="transparent").place(relx=0.5, rely=0.5, anchor="center")

            ctk.CTkLabel(pad, text=title, font=("Trebuchet MS", 13, "bold"),
                         text_color=C_TEXT_DARK, fg_color="transparent", anchor="w").pack(fill="x")
            ctk.CTkLabel(pad, text=desc, font=("Trebuchet MS", 10), text_color=C_TEXT_MID,
                         fg_color="transparent", anchor="w",
                         wraplength=280, justify="left").pack(fill="x", pady=(4, 0))

            if is_active and callback:
                ctk.CTkButton(pad, text="Launch  →", command=callback,
                              font=("Trebuchet MS", 10, "bold"), fg_color=C_ACCENT,
                              hover_color=C_ACCENT_HOVER, text_color=C_WHITE, height=28,
                              corner_radius=6).pack(anchor="w", pady=(12, 0))
            else:
                ctk.CTkButton(pad, text="Coming Soon", state="disabled",
                              font=("Trebuchet MS", 10, "bold"), fg_color=C_INPUT_BG,
                              text_color=C_TEXT_LIGHT, hover_color=C_INPUT_BG, height=28,
                              corner_radius=6, border_width=1,
                              border_color=C_INPUT_BORDER).pack(anchor="w", pady=(12, 0))

        ctk.CTkLabel(body,
                     text="SignDesk v1.0.0  •  © 2025 SignDesk Project  •  All rights reserved",
                     font=FONT_SMALL, text_color=C_TEXT_LIGHT,
                     fg_color="transparent").pack(pady=(28, 4))

    def _on_logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to log out?"):
            self._app.show_login()
