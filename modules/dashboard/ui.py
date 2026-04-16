"""
modules/dashboard/ui.py - Dashboard UI
Modern soft-gradient SaaS dashboard with sidebar navigation.
"""

import customtkinter as ctk
from tkinter import Canvas, messagebox
import os
from PIL import Image
from core.theme import *
from core.ui_helpers import (
    build_steps_panel, create_gradient_canvas, create_nav_item,
    _lerp_color,
)


class DashboardPage(ctk.CTkFrame):
    SIDEBAR_W = 210

    def __init__(self, parent, app, username: str):
        super().__init__(parent, fg_color=C_DASH_BG, corner_radius=0)
        self._app      = app
        self._username = username
        self._sidebar_images = []       # prevent GC of logo image
        self._build()

    # ── Navigation callbacks ───────────────────────────────

    def _launch_gesture_detection(self):
        self._app.show_gesture_detection(self._username)

    def _launch_settings(self):
        if hasattr(self._app, 'show_settings'):
            self._app.show_settings(self._username)

    def _launch_speech_output(self):
        self._app.show_speech_output(self._username)

    def _on_logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to log out?"):
            self._app.show_login()

    # ── Main build ─────────────────────────────────────────

    def _build(self):
        # Two-column layout: sidebar | main content
        self.grid_columnconfigure(0, weight=0, minsize=self.SIDEBAR_W)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_area()

    # ══════════════════════════════════════════════════════════
    # SIDEBAR
    # ══════════════════════════════════════════════════════════

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(
            self, width=self.SIDEBAR_W, fg_color=C_SIDEBAR_START,
            corner_radius=0,
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        # Gradient background canvas
        gradient = create_gradient_canvas(
            sidebar, self.SIDEBAR_W, 700,
            color_start=C_SIDEBAR_START, color_end=C_SIDEBAR_END,
        )
        gradient.place(x=0, y=0, relwidth=1, relheight=1)

        # Content overlay (transparent, on top of gradient)
        content = ctk.CTkFrame(sidebar, fg_color="transparent")
        content.place(x=0, y=0, relwidth=1, relheight=1)

        # ── Logo + brand ──────────────────────────────────
        brand = ctk.CTkFrame(content, fg_color="transparent")
        brand.pack(fill="x", padx=16, pady=(20, 24))

        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "assets", "logo.png"
        )
        brand_row = ctk.CTkFrame(brand, fg_color="transparent")
        brand_row.pack(anchor="w")

        if os.path.exists(logo_path):
            try:
                logo_img = ctk.CTkImage(Image.open(logo_path), size=(36, 36))
                self._sidebar_images.append(logo_img)
                ctk.CTkLabel(
                    brand_row, image=logo_img, text="", fg_color="transparent"
                ).pack(side="left", padx=(0, 10))
            except Exception:
                pass

        ctk.CTkLabel(
            brand_row, text="SignDesk",
            font=(FONT_PRIMARY, 16, "bold"),
            text_color=C_WHITE, fg_color="transparent",
        ).pack(side="left")

        # Subtle divider
        ctk.CTkFrame(
            content, height=1, fg_color="#4A4590"
        ).pack(fill="x", padx=16, pady=(0, 16))

        # ── Navigation items ──────────────────────────────
        nav_frame = ctk.CTkFrame(content, fg_color="transparent")
        nav_frame.pack(fill="x", padx=12)

        create_nav_item(nav_frame, "📊", "Dashboard",
                        is_active=True, command=None)
        create_nav_item(nav_frame, "🖐️", "Gesture Translator",
                        is_active=False,
                        command=self._launch_gesture_detection)
        create_nav_item(nav_frame, "🔊", "Speech Output",
                        is_active=False, command=self._launch_speech_output)
        create_nav_item(nav_frame, "📖", "Sign Dictionary",
                        is_active=False, command=None)
        create_nav_item(nav_frame, "📈", "Session History",
                        is_active=False, command=None)

        # Spacer
        ctk.CTkFrame(content, fg_color="transparent").pack(
            fill="both", expand=True)

        # ── Bottom section — divider + logout ─────────────
        ctk.CTkFrame(
            content, height=1, fg_color="#4A4590"
        ).pack(fill="x", padx=16, pady=(0, 8))

        bottom = ctk.CTkFrame(content, fg_color="transparent")
        bottom.pack(fill="x", padx=12, pady=(0, 20))

        create_nav_item(bottom, "⚙️", "Settings",
                        is_active=False, command=self._launch_settings)

        logout_frame = ctk.CTkFrame(bottom, fg_color="transparent",
                                     corner_radius=10, height=38)
        logout_frame.pack(fill="x", pady=(2, 0))
        logout_frame.pack_propagate(False)

        logout_inner = ctk.CTkFrame(logout_frame, fg_color="transparent")
        logout_inner.pack(fill="x", padx=12, expand=True)

        lo_icon = ctk.CTkLabel(
            logout_inner, text="🚪", font=("Segoe UI Emoji", 14),
            text_color="#FF8A80", fg_color="transparent", width=24,
        )
        lo_icon.pack(side="left", padx=(0, 8))
        lo_text = ctk.CTkLabel(
            logout_inner, text="Logout", font=FONT_SIDEBAR,
            text_color="#FF8A80", fg_color="transparent", anchor="w",
        )
        lo_text.pack(side="left")

        for w in (logout_frame, logout_inner, lo_icon, lo_text):
            w.configure(cursor="hand2")
            w.bind("<Button-1>", lambda e: self._on_logout())

    # ══════════════════════════════════════════════════════════
    # MAIN CONTENT AREA
    # ══════════════════════════════════════════════════════════

    def _build_main_area(self):
        main = ctk.CTkFrame(self, fg_color=C_DASH_BG, corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")

        self._build_topbar(main)

        body = ctk.CTkScrollableFrame(
            main, fg_color=C_DASH_BG, corner_radius=0
        )
        body.pack(fill="both", expand=True, padx=28, pady=(8, 20))

        self._build_welcome(body)
        self._build_stats(body)
        self._build_modules(body)
        self._build_how_to_use(body)
        self._build_footer(body)

    # ── Top Bar ────────────────────────────────────────────

    def _build_topbar(self, parent):
        topbar = ctk.CTkFrame(parent, height=60, fg_color="transparent",
                               corner_radius=0)
        topbar.pack(fill="x", padx=28, pady=(16, 4))
        topbar.pack_propagate(False)

        # Left: greeting
        ctk.CTkLabel(
            topbar, text=f"Welcome back, {self._username} 👋",
            font=(FONT_PRIMARY, 16, "bold"),
            text_color=C_TEXT_DARK, fg_color="transparent",
        ).pack(side="left", pady=12)

        # Right: search bar
        search_frame = ctk.CTkFrame(
            topbar, fg_color=C_INPUT_BG, corner_radius=18,
            border_width=1, border_color=C_CARD_BORDER,
        )
        search_frame.pack(side="right", pady=12)

        ctk.CTkLabel(
            search_frame, text="🔍",
            font=("Segoe UI Emoji", 12),
            text_color=C_TEXT_LIGHT, fg_color="transparent",
        ).pack(side="left", padx=(12, 4))

        search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search...",
            font=(FONT_PRIMARY, 11),
            fg_color="transparent", border_width=0,
            text_color=C_TEXT_DARK,
            placeholder_text_color=C_TEXT_LIGHT,
            height=30, width=160,
        )
        search_entry.pack(side="left", padx=(0, 12))

        # Avatar circle
        avatar = ctk.CTkFrame(
            topbar, width=36, height=36,
            fg_color=C_ACCENT, corner_radius=18,
        )
        avatar.pack(side="right", padx=(12, 0), pady=12)
        avatar.pack_propagate(False)
        ctk.CTkLabel(
            avatar, text=self._username[0].upper(),
            font=(FONT_PRIMARY, 14, "bold"),
            text_color=C_WHITE, fg_color="transparent",
        ).place(relx=0.5, rely=0.5, anchor="center")

    # ── Welcome Banner ─────────────────────────────────────

    def _build_welcome(self, parent):
        card = ctk.CTkFrame(
            parent, fg_color=C_INFO_BG, corner_radius=14,
            border_width=1, border_color="#D1C4E9"
        )
        card.pack(fill="x", pady=(0, 20))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=24, pady=18, anchor="w")
        ctk.CTkLabel(
            inner, text=f"Good day, {self._username} 👋",
            font=(FONT_PRIMARY, 18, "bold"),
            text_color="#311B92", fg_color="transparent"
        ).pack(anchor="w")
        ctk.CTkLabel(
            inner,
            text="You're successfully signed in to SignDesk. Your dashboard is ready.",
            font=FONT_SUBHEAD, text_color=C_INFO_TEXT, fg_color="transparent"
        ).pack(anchor="w", pady=(4, 0))

    # ── Stats Row ──────────────────────────────────────────

    def _build_stats(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 20))
        frame.columnconfigure((0, 1, 2), weight=1)

        stats_data = [
            ("Sessions today", "3",  "📊"),
            ("Avg. accuracy",  "91%", "🎯"),
            ("Signs learned",  "24",  "✋"),
        ]

        for col, (label, value, icon) in enumerate(stats_data):
            card = ctk.CTkFrame(
                frame, fg_color=C_CARD_BG, corner_radius=12,
                border_width=1, border_color=C_CARD_BORDER
            )
            card.grid(row=0, column=col,
                      padx=(0, 10) if col < 2 else 0,
                      sticky="nsew")

            # Icon circle
            icon_circle = ctk.CTkFrame(
                card, width=32, height=32,
                fg_color="#EDE7F6", corner_radius=16,
            )
            icon_circle.pack(anchor="w", padx=16, pady=(14, 6))
            icon_circle.pack_propagate(False)
            ctk.CTkLabel(
                icon_circle, text=icon, font=("Segoe UI Emoji", 12),
                fg_color="transparent"
            ).place(relx=0.5, rely=0.5, anchor="center")

            ctk.CTkLabel(card, text=label, font=FONT_SMALL,
                         text_color=C_TEXT_LIGHT, fg_color="transparent"
                         ).pack(anchor="w", padx=16, pady=(0, 2))
            ctk.CTkLabel(card, text=value,
                         font=(FONT_PRIMARY, 22, "bold"),
                         text_color=C_TEXT_DARK, fg_color="transparent"
                         ).pack(anchor="w", padx=16, pady=(0, 14))

    # ── Module Cards ───────────────────────────────────────

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
             True, self._launch_speech_output,
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
                grid, fg_color=C_CARD_BG, corner_radius=14,
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
                                 fg_color=icon_bg, corner_radius=12)
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
                         wraplength=260, justify="left"
                         ).pack(fill="x", pady=(4, 0))

            # Status badge — pill style
            badge_text  = "Launch  →" if is_active else "Coming soon"
            badge_bg    = icon_bg if is_active else C_BADGE_GRAY_BG
            badge_fg    = icon_fg if is_active else C_BADGE_GRAY_FG

            status_frame = ctk.CTkFrame(pad, fg_color=badge_bg,
                                         corner_radius=12)
            status_frame.pack(anchor="w", pady=(12, 0))
            status_lbl = ctk.CTkLabel(
                status_frame, text=badge_text,
                font=(FONT_PRIMARY, 11, "bold"),
                text_color=badge_fg, fg_color="transparent"
            )
            status_lbl.pack(padx=12, pady=4)

            if is_active and cb:
                status_frame.configure(cursor="hand2")
                status_frame.bind("<Button-1>", lambda e, f=cb: f())
                status_lbl.bind("<Button-1>",   lambda e, f=cb: f())

    # ── How-to-Use Cards ───────────────────────────────────

    def _build_how_to_use(self, parent):
        """5-step instructional 'How to Use' card panel."""
        steps = [
            (
                "Open Gesture Translator",
                "Navigate to the \"Gesture Translator\" section from the main menu.",
            ),
            (
                "Allow Camera Access",
                "When prompted, allow the system to access your camera for real-time translation.",
            ),
            (
                "Start Recording",
                "Click the \"Start Recording\" button to begin capturing your gestures.",
            ),
            (
                "Perform Sign Language",
                "Make sure your hands are clearly visible in the frame as you sign.",
            ),
            (
                "View Translation",
                "The translation will appear in the result panel on the right.",
            ),
        ]
        build_steps_panel(parent, steps, card_width=120)

    # ── Footer ─────────────────────────────────────────────

    def _build_footer(self, parent):
        ctk.CTkLabel(
            parent,
            text="SignDesk v1.0.0  •  © 2025 SignDesk Project  •  All rights reserved",
            font=FONT_SMALL, text_color=C_TEXT_LIGHT, fg_color="transparent"
        ).pack(pady=(28, 4))
