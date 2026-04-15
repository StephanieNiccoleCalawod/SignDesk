"""
ui.py - Speech Output Page
Displays the finalized sentences and provides TTS playback features.
"""

import customtkinter as ctk
from tkinter import messagebox
from core.theme import *
from modules.speech.tts import TTSEngine
from modules.speech.buffer import speech_buffer

class SpeechOutputPage(ctk.CTkFrame):
    def __init__(self, parent, app, username: str):
        super().__init__(parent, fg_color=COLORS["bg_secondary"], corner_radius=0)
        self._app = app
        self._username = username
        
        self.tts = TTSEngine(on_error=self._handle_tts_error)
        
        self._build()
        self._populate_sentences()
        
    def _build(self):
        # Navbar
        navbar = ctk.CTkFrame(self, height=60, fg_color=COLORS["panel_left"], corner_radius=0)
        navbar.pack(fill="x", side="top")
        navbar.pack_propagate(False)

        ctk.CTkLabel(
            navbar, text="🔊 Speech Output",
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
        body.pack(fill="both", expand=True, padx=40, pady=20)
        
        # Header controls
        hdr = ctk.CTkFrame(body, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(
            hdr, text="Finalized Sentences",
            font=(FONT_PRIMARY, 16, "bold"), text_color=COLORS["text_primary"]
        ).pack(side="left")

        # Status Pill
        self._status_pill = ctk.CTkFrame(hdr, fg_color=COLORS["badge_gray_bg"], corner_radius=12)
        self._status_pill.pack(side="left", padx=20)
        self._status_label = ctk.CTkLabel(
            self._status_pill, text="⏸ Idle",
            font=(FONT_PRIMARY, 12, "bold"), text_color=COLORS["badge_gray_fg"]
        )
        self._status_label.pack(padx=12, pady=4)
        
        if not self.tts._available:
            self._set_status("🔴 Unavailable", COLORS["error_bg"], COLORS["error"])
        
        ctk.CTkButton(
            hdr, text="▶ Play All", command=self._play_all,
            font=FONT_BTN, fg_color=COLORS["success"], hover_color=COLORS["success"],
            text_color=("#FFFFFF", "#FFFFFF"), width=100, height=32, corner_radius=6
        ).pack(side="right")

        # Scrollable container for sentences
        self._scroll_frame = ctk.CTkScrollableFrame(
            body, fg_color=COLORS["card_bg"], corner_radius=12,
            border_width=1, border_color=COLORS["card_border"]
        )
        self._scroll_frame.pack(fill="both", expand=True)

    def _set_status(self, text, bg, fg):
        self._status_pill.configure(fg_color=bg)
        self._status_label.configure(text=text, text_color=fg)

    def _populate_sentences(self):
        for widget in self._scroll_frame.winfo_children():
            widget.destroy()

        sentences = speech_buffer.get_all()
        
        if not sentences:
            ctk.CTkLabel(
                self._scroll_frame, text="No finalized sentences available in the buffer.",
                font=FONT_SUBHEAD, text_color=COLORS["text_muted"]
            ).pack(pady=40)
            return

        for i, sentence in enumerate(sentences):
            row = ctk.CTkFrame(self._scroll_frame, fg_color=COLORS["input_bg"], corner_radius=8)
            row.pack(fill="x", padx=16, pady=8)
            
            lbl = ctk.CTkTextbox(
                row, font=("Consolas", 14),
                text_color=COLORS["text_primary"], fg_color="transparent",
                wrap="word", height=50
            )
            lbl.insert("1.0", sentence)
            lbl.configure(state="disabled")
            lbl.pack(side="left", padx=16, pady=16, fill="both", expand=True)
            
            btn = ctk.CTkButton(
                row, text="▶", width=40, height=40, font=("Segoe UI Emoji", 14),
                fg_color=COLORS["accent"], hover_color=COLORS["panel_left_end"],
                command=lambda s=sentence: self._play_single(s)
            )
            btn.pack(side="right", padx=16, pady=16)

    def _play_single(self, sentence: str):
        if self.tts._available:
            self._set_status("🟢 Playing", COLORS["success_bg"], COLORS["success"])
            # Fallback mock for demonstration. A real callback hook from pyttsx3 would be strictly better.
            self.after(2500, lambda: self._set_status("⏸ Idle", COLORS["badge_gray_bg"], COLORS["badge_gray_fg"]) if self.tts._available else None)
        self.tts.speak(sentence)

    def _play_all(self):
        sentences = speech_buffer.get_all()
        if not sentences:
            self._handle_tts_error("No text available for speech conversion.")
            return

        full_text = ". ".join(sentences)
        self._play_single(full_text)

    def _handle_tts_error(self, message: str):
        self.after(0, lambda: self._show_error(message))

    def _show_error(self, message: str):
        self._set_status("🔴 Unavailable", COLORS["error_bg"], COLORS["error"])
        messagebox.showerror("Audio Error", message)

    def _on_back(self):
        self._app.show_dashboard(self._username)
