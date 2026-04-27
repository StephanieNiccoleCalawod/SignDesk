"""
modules/gesture_history/page.py
Full-page wrapper for GestureHistorySection.
Follows the same pattern as GestureDetectionPage, SettingsPage, etc.
"""

import os
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image

from core.theme import COLORS, FONT_NAV, FONT_PRIMARY, C_WHITE
from modules.gesture_history.ui import GestureHistorySection
from modules.gesture_history.backend import init_history_db


class GestureHistoryPage(ctk.CTkFrame):

    def __init__(self, parent, app, username: str):
        super().__init__(parent, fg_color=COLORS["bg_secondary"], corner_radius=0)
        self._app      = app
        self._username = username
        init_history_db()
        self._build()

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build(self):
        self._build_navbar()
        self._build_body()

    def _build_navbar(self):
        navbar = ctk.CTkFrame(self, height=60,
                              fg_color=COLORS["panel_left"], corner_radius=0)
        navbar.pack(fill="x", side="top")
        navbar.pack_propagate(False)

        # Logo
        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "assets", "logo.png"
        )
        if os.path.exists(logo_path):
            try:
                logo_img = ctk.CTkImage(Image.open(logo_path), size=(36, 36))
                ctk.CTkLabel(navbar, image=logo_img, text="").pack(
                    side="left", padx=(20, 10))
                self._logo_img = logo_img   # prevent GC
            except Exception:
                pass

        ctk.CTkLabel(
            navbar, text="SignDesk",
            font=("Georgia", 18, "bold"),
            text_color=COLORS["text_primary"], fg_color="transparent"
        ).pack(side="left", padx=24)

        # Right buttons
        ctk.CTkButton(
            navbar, text="Logout  →",
            command=self._on_logout, font=FONT_NAV,
            fg_color=COLORS["error"], hover_color=COLORS["error"],
            text_color=("#FFFFFF", "#FFFFFF"),
            width=90, height=32, corner_radius=6
        ).pack(side="right", padx=(0, 20), pady=14)

        ctk.CTkButton(
            navbar, text="← Dashboard",
            command=self._on_back, font=FONT_NAV,
            fg_color="transparent", hover_color=COLORS["panel_left_end"],
            text_color=("#FFFFFF", "#FFFFFF"),
            border_width=1, border_color=("#FFFFFF", "#FFFFFF"),
            width=120, height=32, corner_radius=6
        ).pack(side="right", padx=(0, 8), pady=14)

    def _build_body(self):
        body = ctk.CTkScrollableFrame(
            self, fg_color=COLORS["bg_secondary"], corner_radius=0
        )
        body.pack(fill="both", expand=True, padx=24, pady=20)

        # Page title
        ctk.CTkLabel(
            body, text="Gesture History",
            font=(FONT_PRIMARY, 18, "bold"),
            text_color=COLORS["text_primary"], fg_color="transparent", anchor="w"
        ).pack(fill="x", pady=(0, 16))

        # The 2×2 section widget — scoped to current user
        user_id = getattr(self._app, 'current_user_id', None)
        section = GestureHistorySection(body, user_id=user_id)
        section.pack(fill="both", expand=True)

    # ── Navigation ─────────────────────────────────────────────────────────────

    def _on_back(self):
        self._app.show_dashboard(self._username)

    def _on_logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to log out?"):
            self._app.show_login()
