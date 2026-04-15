"""
modules/settings/ui.py - Settings Panel
Allows enabling/disabling webcam and TTS audio independently.
"""

import customtkinter as ctk
from core.theme import *
from core.config import config

class SettingsPage(ctk.CTkFrame):
    def __init__(self, parent, app, username: str):
        super().__init__(parent, fg_color=COLORS["bg_secondary"], corner_radius=0)
        self._app = app
        self._username = username
        self._build()

    def _build(self):
        # Navigation bar
        navbar = ctk.CTkFrame(self, height=60, fg_color=COLORS["panel_left"], corner_radius=0)
        navbar.pack(fill="x", side="top")
        navbar.pack_propagate(False)

        ctk.CTkLabel(
            navbar, text="⚙️ Settings",
            font=("Georgia", 18, "bold"),
            text_color=COLORS["text_primary"], fg_color="transparent"
        ).pack(side="left", padx=24)

        ctk.CTkButton(
            navbar, text="← Dashboard",
            command=self._on_back, font=FONT_NAV,
            fg_color="transparent", hover_color=COLORS["panel_left_end"],
            text_color=("#FFFFFF", "#FFFFFF"), border_width=1, border_color=("#FFFFFF", "#FFFFFF"),
            width=120, height=32, corner_radius=6
        ).pack(side="right", padx=(0, 20), pady=14)

        # Body container
        body = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        body.pack(fill="both", expand=True, padx=40, pady=40)

        # Settings Card
        card = ctk.CTkFrame(
            body, fg_color=COLORS["card_bg"], corner_radius=14,
            border_width=1, border_color=COLORS["card_border"]
        )
        card.pack(fill="x", anchor="n")

        ctk.CTkLabel(
            card, text="Hardware Controls",
            font=(FONT_PRIMARY, 16, "bold"),
            text_color=COLORS["text_primary"], anchor="w"
        ).pack(fill="x", padx=24, pady=(24, 8))

        ctk.CTkLabel(
            card, text="Manage permissions for external hardware components.",
            font=FONT_SUBHEAD, text_color=COLORS["text_muted"], anchor="w"
        ).pack(fill="x", padx=24, pady=(0, 24))

        # Webcam Toggle
        self._build_switch(
            parent=card,
            title="Webcam Access",
            description="Allow SignDesk to access your camera for real-time gesture recognition.",
            variable=config.webcam_enabled,
            command=self._toggle_webcam
        )

        divider = ctk.CTkFrame(card, height=1, fg_color=COLORS["border"])
        divider.pack(fill="x", padx=24, pady=16)

        # TTS Toggle
        self._build_switch(
            parent=card,
            title="Text-to-Speech Audio",
            description="Automatically speak completed sentences using system audio.",
            variable=config.tts_enabled,
            command=self._toggle_tts
        )
        
        # Add a bit of bottom padding
        ctk.CTkFrame(card, height=1, fg_color="transparent").pack(pady=12)

    def _build_switch(self, parent, title, description, variable, command):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=24)
        
        text_frame = ctk.CTkFrame(row, fg_color="transparent")
        text_frame.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            text_frame, text=title, font=(FONT_PRIMARY, 14, "bold"),
            text_color=COLORS["text_primary"], anchor="w"
        ).pack(fill="x")
        
        ctk.CTkLabel(
            text_frame, text=description, font=FONT_SMALL,
            text_color=COLORS["text_secondary"], anchor="w"
        ).pack(fill="x", pady=(4, 0))

        status_label = ctk.CTkLabel(
            text_frame, text="Enabled" if variable else "Disabled", 
            font=FONT_SMALL,
            text_color=COLORS["success"] if variable else COLORS["error"], 
            anchor="w"
        )
        status_label.pack(fill="x", pady=(2, 0))

        switch_var = ctk.BooleanVar(value=variable)
        
        def on_toggle():
            val = switch_var.get()
            status_label.configure(
                text="Enabled" if val else "Disabled",
                text_color=COLORS["success"] if val else COLORS["error"]
            )
            command(val)

        switch = ctk.CTkSwitch(
            row, text="", variable=switch_var,
            onvalue=True, offvalue=False,
            command=on_toggle
        )
        switch.pack(side="right", padx=(20, 0))

    def _toggle_webcam(self, value: bool):
        config.webcam_enabled = value
        config.save()

    def _toggle_tts(self, value: bool):
        config.tts_enabled = value
        config.save()

    def _on_back(self):
        self._app.show_dashboard(self._username)
