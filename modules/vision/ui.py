"""
ui_combined.py - Combined Gesture Detection + Speech Output Page

Merges GestureDetectionPage (modules/vision/ui.py) and
SpeechOutputPage (modules/speech/ui.py) into a single page.

Layout:
  ┌─────────────────────────────────────────────────────────┐
  │  Navbar                                                 │
  ├──────────────────┬──────────────────┬───────────────────┤
  │  Camera Feed     │  Gesture Status  │  Speech Output    │
  │  (Live Det.)     │  Comm. Output    │  (Finalized       │
  │  Start/Stop      │  Final Sentence  │   Sentences +     │
  │                  │  Gesture Seq.    │   Play buttons)   │
  └──────────────────┴──────────────────┴───────────────────┘
"""

import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageOps
import cv2
import os
import time
import threading

from core.theme import *
from core.config import config
from modules.vision.camera import CameraManager
from modules.vision.tracker import HandTracker
from modules.gestures.engine import GestureRecognizer
from modules.text.mapper import map_gesture_to_text
from modules.text.buffer import TextBuffer
from modules.sentence.builder import SentenceBuilder
from modules.speech.buffer import speech_buffer
from modules.speech.word_assembler import word_assembler
from modules.speech.tts import TTSEngine


_VOICE_LABELS = {
    "default": ("🔊", "Default"),
    "female":  ("♀",  "Female"),
    "male":    ("♂",  "Male"),
}


class GestureDetectionPage(ctk.CTkFrame):
    UPDATE_INTERVAL = 33

    def __init__(self, parent, app, username: str):
        super().__init__(parent, fg_color=COLORS["bg_secondary"], corner_radius=0)
        self._app             = app
        self._username        = username
        self._camera          = CameraManager()
        self._tracker         = HandTracker()
        self._recognizer      = GestureRecognizer()
        self._text_buffer     = TextBuffer()
        self._sentence_builder = SentenceBuilder(timeout=4.0)

        self._is_detecting        = False
        self._update_job          = None
        self._gesture_history     = []
        self._max_history         = 50
        self._live_speech_enabled = False
        self._tts_speaking        = False
        self._last_spoken_char    = None

        # TTS engine (from SpeechOutputPage)
        self.tts = TTSEngine(on_error=self._handle_tts_error)

        # Inject TTS into assembler ONCE at page creation
        word_assembler.set_tts(self.tts)

        self._build()

    # ── Build ──────────────────────────────────────────────

    def _build(self):
        self._build_navbar()
        self._build_body()

    def _build_navbar(self):
        navbar = ctk.CTkFrame(self, height=60, fg_color=COLORS["panel_left"], corner_radius=0)
        navbar.pack(fill="x", side="top")
        navbar.pack_propagate(False)

        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "assets", "logo.png"
        )
        if os.path.exists(logo_path):
            try:
                logo_img = ctk.CTkImage(Image.open(logo_path), size=(36, 36))
                ctk.CTkLabel(navbar, image=logo_img, text="").pack(side="left", padx=(20, 10))
            except Exception:
                pass

        ctk.CTkLabel(
            navbar, text="SignDesk",
            font=("Georgia", 18, "bold"),
            text_color=COLORS["text_primary"], fg_color="transparent"
        ).pack(side="left", padx=24)

        ctk.CTkButton(
            navbar, text="Logout  →",
            command=self._on_logout, font=FONT_NAV,
            fg_color=COLORS["error"], hover_color=COLORS["error"],
            text_color=("#FFFFFF", "#FFFFFF"), width=90, height=32, corner_radius=6
        ).pack(side="right", padx=(0, 20), pady=14)

        ctk.CTkButton(
            navbar, text="← Dashboard",
            command=self._on_back, font=FONT_NAV,
            fg_color="transparent", hover_color=COLORS["panel_left_end"],
            text_color=("#FFFFFF", "#FFFFFF"), border_width=1, border_color=("#FFFFFF", "#FFFFFF"),
            width=120, height=32, corner_radius=6
        ).pack(side="right", padx=(0, 8), pady=14)

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        body.pack(fill="both", expand=True, padx=20, pady=20)

        # ── 2-column 50/50 root grid ──────────────────────────
        # LEFT half: gesture system (camera + status panels)
        # RIGHT half: speech output
        body.grid_columnconfigure(0, weight=1, minsize=500)
        body.grid_columnconfigure(1, weight=1, minsize=320)
        body.grid_rowconfigure(0, weight=1)

        # ── LEFT HALF: contains camera + gesture panels ────────
        left_half = ctk.CTkFrame(body, fg_color="transparent")
        left_half.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left_half.grid_rowconfigure(0, weight=1)
        left_half.grid_columnconfigure(0, weight=5)   # camera
        left_half.grid_columnconfigure(1, weight=4)   # gesture panels

        # Camera sub-column
        left_col = ctk.CTkFrame(left_half, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left_col.grid_rowconfigure(0, weight=1)
        left_col.grid_columnconfigure(0, weight=1)

        # Gesture status/output/sequence sub-column
        mid_outer = ctk.CTkFrame(left_half, fg_color=COLORS["bg_secondary"], corner_radius=12,
                                 border_width=1, border_color=COLORS["border"])
        mid_outer.grid(row=0, column=1, sticky="nsew")
        mid_outer.grid_rowconfigure(0, weight=1)
        mid_outer.grid_columnconfigure(0, weight=1)

        mid_col = ctk.CTkScrollableFrame(
            mid_outer,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["accent"],
        )
        mid_col.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        # ── RIGHT HALF: speech output ──────────────────────────
        right_col = ctk.CTkFrame(body, fg_color=COLORS["bg_secondary"], corner_radius=12,
                                 border_width=1, border_color=COLORS["border"])
        right_col.grid(row=0, column=1, sticky="nsew")
        right_col.grid_rowconfigure(0, weight=1)
        right_col.grid_columnconfigure(0, weight=1)

        self._build_camera_panel(left_col)
        self._build_status_panel(mid_col)
        self._build_output_panel(mid_col)
        self._build_sequence_panel(mid_col)
        self._build_speech_panel(right_col)

    # ── Camera panel (left) ────────────────────────────────

    def _build_camera_panel(self, parent):
        panel = ctk.CTkFrame(parent, fg_color=COLORS["bg_primary"], corner_radius=12,
                             border_width=1, border_color=COLORS["border"])
        panel.grid(row=0, column=0, sticky="nsew")
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        cam_hdr = ctk.CTkFrame(panel, fg_color="transparent")
        cam_hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 8))
        ctk.CTkLabel(
            cam_hdr, text="📷  Live Detection",
            font=(FONT_PRIMARY, 14, "bold"),
            text_color=COLORS["text_primary"]
        ).pack(side="left")
        self._fps_label = ctk.CTkLabel(
            cam_hdr, text="FPS: --",
            font=FONT_SMALL, text_color=COLORS["text_muted"]
        )
        self._fps_label.pack(side="right")

        self._cam_label = ctk.CTkLabel(
            panel, text="", fg_color=("#0D1117", "#0D1117"), corner_radius=8)
        self._cam_label.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 12))
        self._cam_label.grid_propagate(False)

        self._cam_placeholder = ctk.CTkFrame(
            self._cam_label, fg_color=("#1A1F2E", "#1A1F2E"),
            corner_radius=14, border_width=1, border_color=("#2A3050", "#2A3050")
        )
        self._cam_placeholder.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            self._cam_placeholder, text="📸",
            font=("Arial", 32), text_color=COLORS["cyan"]
        ).pack(pady=(22, 6))
        ctk.CTkLabel(
            self._cam_placeholder, text="Camera Offline",
            font=(FONT_PRIMARY, 16, "bold"), text_color=("#E2E8F0", "#E2E8F0")
        ).pack(padx=40)
        ctk.CTkLabel(
            self._cam_placeholder,
            text="Click 'Start Detection' below\\nto activate your webcam and begin.",
            font=(FONT_PRIMARY, 12), text_color=("#94A3B8", "#94A3B8"), justify="center"
        ).pack(padx=40, pady=(4, 22))

        toolbar = ctk.CTkFrame(panel, fg_color="transparent")
        toolbar.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))

        self._start_btn = ctk.CTkButton(
            toolbar, text="▶  Start Detection",
            command=self._start_detection,
            font=FONT_BTN, fg_color=COLORS["success"], hover_color=COLORS["success"],
            text_color=("#FFFFFF", "#FFFFFF"), height=40, corner_radius=8
        )
        self._start_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self._stop_btn = ctk.CTkButton(
            toolbar, text="■  Stop Detection",
            command=self._stop_detection,
            font=FONT_BTN, fg_color=COLORS["error"], hover_color=COLORS["error"],
            text_color=("#FFFFFF", "#FFFFFF"), height=40, corner_radius=8,
            state="disabled"
        )
        self._stop_btn.pack(side="left", fill="x", expand=True, padx=(8, 0))

        self._live_speech_btn = ctk.CTkButton(
            toolbar, text="🔇  Live Speech: OFF",
            command=self._toggle_live_speech,
            font=FONT_BTN,
            fg_color=COLORS["badge_gray_bg"],
            hover_color=COLORS["input_bg"],
            text_color=("#FFFFFF", "#FFFFFF"),
            height=40, corner_radius=8
        )
        self._live_speech_btn.pack(side="left", fill="x", expand=True, padx=(8, 0))

    # ── Gesture status panel (middle) ──────────────────────

    def _build_status_panel(self, parent):
        panel = ctk.CTkFrame(parent, fg_color=COLORS["bg_primary"], corner_radius=12,
                             border_width=1, border_color=COLORS["border"])
        panel.pack(fill="x", padx=4, pady=(4, 8))

        hdr = ctk.CTkFrame(panel, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkLabel(
            hdr, text="⬡  Gesture Status",
            font=(FONT_PRIMARY, 14, "bold"),
            text_color=COLORS["text_primary"]
        ).pack(side="left")

        # Thin divider line
        ctk.CTkFrame(panel, height=1, fg_color=COLORS["border"]).pack(fill="x", padx=16, pady=(0, 10))

        result_card = ctk.CTkFrame(
            panel, fg_color=COLORS["input_bg"], corner_radius=10,
            border_width=1, border_color=COLORS["border"]
        )
        result_card.pack(fill="x", padx=16, pady=(0, 12))

        self._gesture_label = ctk.CTkLabel(
            result_card, text="—",
            font=("Georgia", 52, "bold"), text_color=COLORS["accent"]
        )
        self._gesture_label.pack(pady=(12, 2))
        self._gesture_name_label = ctk.CTkLabel(
            result_card, text="Waiting for gesture...",
            font=(FONT_PRIMARY, 12), text_color=COLORS["text_secondary"]
        )
        self._gesture_name_label.pack(pady=(0, 12))

        conf_frame = ctk.CTkFrame(panel, fg_color="transparent")
        conf_frame.pack(fill="x", padx=16, pady=(0, 8))
        conf_row = ctk.CTkFrame(conf_frame, fg_color="transparent")
        conf_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(
            conf_row, text="Confidence",
            font=(FONT_PRIMARY, 12), text_color=COLORS["text_secondary"]
        ).pack(side="left")
        self._conf_value_label = ctk.CTkLabel(
            conf_row, text="0%",
            font=(FONT_PRIMARY, 13, "bold"), text_color=COLORS["text_muted"]
        )
        self._conf_value_label.pack(side="right")

        self._conf_bar = ctk.CTkProgressBar(
            conf_frame, height=6, corner_radius=3,
            progress_color=COLORS["badge_gray_bg"], fg_color=COLORS["border"]
        )
        self._conf_bar.pack(fill="x")
        self._conf_bar.set(0)

        # Hold Progress Bar
        self._hold_progress_bar = ctk.CTkProgressBar(
            conf_frame, height=4, corner_radius=2,
            progress_color=COLORS["badge_gray_bg"], fg_color=COLORS["border"]
        )
        self._hold_progress_bar.pack(fill="x", pady=(8, 0))
        self._hold_progress_bar.set(0)

        self._conf_warning = ctk.CTkLabel(
            panel, text="", font=(FONT_PRIMARY, 11),
            text_color=COLORS["warn"], fg_color="transparent"
        )
        self._conf_warning.pack(padx=16, anchor="w", pady=(0, 4))

        self._status_pill = ctk.CTkFrame(
            panel, fg_color=COLORS["badge_gray_bg"], corner_radius=8
        )
        self._status_pill.pack(anchor="w", padx=16, pady=(4, 16))
        self._status_label = ctk.CTkLabel(
            self._status_pill, text="⏸  Detection stopped",
            font=(FONT_PRIMARY, 11), text_color=COLORS["badge_gray_fg"]
        )
        self._status_label.pack(padx=10, pady=5)

    def _build_output_panel(self, parent):
        panel = ctk.CTkFrame(parent, fg_color=COLORS["bg_primary"], corner_radius=12,
                             border_width=1, border_color=COLORS["border"])
        panel.pack(fill="x", padx=4, pady=(0, 8))

        out_hdr = ctk.CTkFrame(panel, fg_color="transparent")
        out_hdr.pack(fill="x", padx=16, pady=(12, 6))
        ctk.CTkLabel(
            out_hdr, text="💬  Communication Output",
            font=(FONT_PRIMARY, 13, "bold"), text_color=COLORS["text_primary"]
        ).pack(side="left")
        ctk.CTkButton(
            out_hdr, text="Clear", command=self._clear_output,
            font=(FONT_PRIMARY, 11), fg_color="transparent",
            hover_color=COLORS["input_bg"], text_color=COLORS["accent"],
            width=50, height=24, corner_radius=4
        ).pack(side="right")

        self._output_textbox = ctk.CTkTextbox(
            panel, font=("Consolas", 20),
            fg_color=COLORS["input_bg"], text_color=COLORS["text_primary"],
            wrap="word", height=60,
            border_width=1, border_color=COLORS["border"], corner_radius=8
        )
        self._output_textbox.pack(fill="x", padx=16, pady=(0, 12))
        self._output_textbox.configure(state="disabled")

        ctk.CTkLabel(
            panel, text="🧾  Final Sentence",
            font=(FONT_PRIMARY, 13, "bold"), text_color=COLORS["text_primary"]
        ).pack(fill="x", padx=16, pady=(0, 6), anchor="w")

        self._final_sentence_label = ctk.CTkTextbox(
            panel, font=("Consolas", 20, "bold"),
            fg_color=COLORS["success_bg"], text_color=COLORS["text_primary"],
            wrap="word", height=45,
            border_width=1, border_color=COLORS["success"], corner_radius=8
        )
        self._final_sentence_label.pack(fill="x", padx=16, pady=(0, 16))
        self._final_sentence_label.configure(state="disabled")

    def _build_sequence_panel(self, parent):
        panel = ctk.CTkFrame(parent, fg_color=COLORS["bg_primary"], corner_radius=12,
                             border_width=1, border_color=COLORS["border"])
        panel.pack(fill="x", padx=4, pady=(0, 8))

        seq_hdr = ctk.CTkFrame(panel, fg_color="transparent")
        seq_hdr.pack(fill="x", padx=16, pady=(12, 6))
        ctk.CTkLabel(
            seq_hdr, text="📋  Gesture Sequence",
            font=(FONT_PRIMARY, 12, "bold"), text_color=COLORS["text_primary"]
        ).pack(side="left")
        ctk.CTkButton(
            seq_hdr, text="Clear", command=self._clear_history,
            font=(FONT_PRIMARY, 11), fg_color="transparent",
            hover_color=COLORS["input_bg"], text_color=COLORS["text_muted"],
            width=40, height=20, corner_radius=4
        ).pack(side="right")

        self._history_textbox = ctk.CTkTextbox(
            panel, font=("Consolas", 14),
            fg_color=COLORS["input_bg"], text_color=COLORS["text_secondary"],
            wrap="word", border_width=0, corner_radius=8,
            height=120,
        )
        self._history_textbox.pack(fill="x", padx=16, pady=(0, 16))
        self._history_textbox.configure(state="disabled")

    # ── Speech output panel (right) ────────────────────────

    def _build_speech_panel(self, parent):
        panel = ctk.CTkFrame(parent, fg_color=COLORS["bg_primary"], corner_radius=12,
                             border_width=1, border_color=COLORS["border"])
        panel.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        # Header
        hdr = ctk.CTkFrame(panel, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(12, 8))

        ctk.CTkLabel(
            hdr, text="🔊  Speech Output",
            font=(FONT_PRIMARY, 14, "bold"),
            text_color=COLORS["text_primary"]
        ).pack(side="left")

        # TTS status pill
        self._tts_status_pill = ctk.CTkFrame(
            hdr, fg_color=COLORS["badge_gray_bg"], corner_radius=12
        )
        self._tts_status_pill.pack(side="left", padx=8)
        self._tts_status_label = ctk.CTkLabel(
            self._tts_status_pill, text="⏸ Idle",
            font=(FONT_PRIMARY, 11, "bold"),
            text_color=COLORS["badge_gray_fg"]
        )
        self._tts_status_label.pack(padx=10, pady=4)

        if not self.tts._available:
            self._set_tts_status("🔴 Unavailable", COLORS["error_bg"], COLORS["error"])

        # Voice badge
        self._voice_badge = self._build_voice_badge(hdr)

        # Play All button
        ctk.CTkButton(
            hdr, text="▶ Play All", command=self._play_all,
            font=FONT_BTN, fg_color=COLORS["success"],
            hover_color=COLORS["success"],
            text_color=("#FFFFFF", "#FFFFFF"),
            width=90, height=30, corner_radius=6
        ).pack(side="right")

        # Subheader: Finalized Sentences + Clear All
        sent_hdr = ctk.CTkFrame(panel, fg_color="transparent")
        sent_hdr.pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkLabel(
            sent_hdr, text="Finalized Sentences",
            font=(FONT_PRIMARY, 12, "bold"),
            text_color=COLORS["text_secondary"]
        ).pack(side="left")

        ctk.CTkButton(
            sent_hdr, text="Clear All",
            command=self._clear_all_sentences,
            font=(FONT_PRIMARY, 11),
            fg_color="transparent",
            hover_color=COLORS["error_bg"],
            text_color=COLORS["error"],
            width=70, height=24, corner_radius=4
        ).pack(side="right")

        # Scrollable sentence list
        self._scroll_frame = ctk.CTkScrollableFrame(
            panel, fg_color=COLORS["bg_secondary"], corner_radius=8,
            border_width=1, border_color=COLORS["border"]
        )
        self._scroll_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # Populate existing sentences (if any)
        self._populate_sentences()

    def _build_voice_badge(self, parent) -> ctk.CTkLabel:
        preference = config.get("speech.voice", "default")
        icon, label = _VOICE_LABELS.get(preference, ("🔊", "Default"))
        badge = ctk.CTkLabel(
            parent,
            text=f"{icon} {label} voice",
            font=(FONT_PRIMARY, 11),
            text_color=COLORS["info"],
            fg_color=COLORS["info_bg"],
            corner_radius=8, height=26,
        )
        badge.pack(side="left", padx=(0, 4))
        return badge

    def _refresh_voice_badge(self):
        preference = config.get("speech.voice", "default")
        icon, label = _VOICE_LABELS.get(preference, ("🔊", "Default"))
        self._voice_badge.configure(text=f"{icon} {label} voice")

    # ── TTS status helpers ─────────────────────────────────

    def _set_tts_status(self, text, bg, fg):
        self._tts_status_pill.configure(fg_color=bg)
        self._tts_status_label.configure(text=text, text_color=fg)

    # ── Sentence list ──────────────────────────────────────

    def _populate_sentences(self):
        for widget in self._scroll_frame.winfo_children():
            widget.destroy()

        sentences = speech_buffer.get_all()

        if not sentences:
            ctk.CTkLabel(
                self._scroll_frame,
                text="No finalized sentences yet.",
                font=FONT_SUBHEAD, text_color=COLORS["text_muted"]
            ).pack(pady=30)
            return

        for i, sentence in enumerate(sentences):
            row = ctk.CTkFrame(
                self._scroll_frame,
                fg_color=COLORS["input_bg"], corner_radius=8
            )
            row.pack(fill="x", padx=8, pady=6)

            # × remove button
            ctk.CTkButton(
                row, text="×", width=28, height=28,
                font=("Segoe UI", 14),
                fg_color="transparent",
                hover_color=COLORS["error_bg"],
                text_color=COLORS["text_muted"],
                command=lambda idx=i: self._remove_sentence(idx)
            ).pack(side="left", padx=(8, 0), pady=10)

            lbl = ctk.CTkTextbox(
                row, font=("Consolas", 13),
                text_color=COLORS["text_primary"],
                fg_color="transparent",
                wrap="word", height=46
            )
            lbl.insert("1.0", sentence)
            lbl.configure(state="disabled")
            lbl.pack(side="left", padx=8, pady=10, fill="both", expand=True)

            ctk.CTkButton(
                row, text="▶", width=36, height=36,
                font=("Segoe UI Emoji", 13),
                fg_color=COLORS["accent"],
                hover_color=COLORS["panel_left_end"],
                command=lambda s=sentence: self._play_single(s)
            ).pack(side="right", padx=10, pady=10)

    def _refresh_sentences(self):
        """Re-populates the sentence list — called after a new sentence is finalized."""
        self._populate_sentences()

    def _remove_sentence(self, index: int):
        """Remove one sentence by index and refresh the list."""
        speech_buffer.remove_at(index)
        self._refresh_sentences()

    def _clear_all_sentences(self):
        """Clear all finalized sentences and refresh the list."""
        speech_buffer.clear()
        self._refresh_sentences()

    # ── TTS playback ───────────────────────────────────────

    def _play_single(self, sentence: str):
        if self.tts._available:
            self._set_tts_status("🟢 Playing", COLORS["success_bg"], COLORS["success"])
            self.after(
                2500,
                lambda: self._set_tts_status(
                    "⏸ Idle", COLORS["badge_gray_bg"], COLORS["badge_gray_fg"]
                ) if self.tts._available else None
            )
        self.tts.speak(sentence)

    def _play_all(self):
        sentences = speech_buffer.get_all()
        if not sentences:
            self._handle_tts_error("No text available for speech conversion.")
            return
        self._play_single(". ".join(sentences))

    def _handle_tts_error(self, message: str):
        if self._live_speech_enabled:
            return   # Silently ignore TTS errors during live speech — no popup
        self.after(0, lambda: self._show_tts_error(message))

    def _speak_async(self, text: str):
        """Speaks text in a background thread. Silently ignores errors in live mode."""
        try:
            self.tts.speak(text)
        except Exception:
            pass
        finally:
            self._tts_speaking = False

    def _show_tts_error(self, message: str):
        self._set_tts_status("🔴 Unavailable", COLORS["error_bg"], COLORS["error"])
        messagebox.showerror("Audio Error", message)

    # ── Detection lifecycle ────────────────────────────────

    def _start_detection(self):
        if getattr(self, "_permission_granted", False) == False:
            response = messagebox.askyesno(
                "Camera Permission Required",
                "SignDesk requires access to your webcam to detect hand gestures.\\n\\n"
                "Allow SignDesk to use your camera?"
            )
            if not response:
                messagebox.showerror(
                    "Permission Denied",
                    "Webcam permission denied. Please enable camera access.")
                return
            self._permission_granted = True

        success, message = self._camera.start()
        if not success:
            messagebox.showerror("Webcam Error", message)
            return

        self._is_detecting = True
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._cam_placeholder.place_forget()

        self._status_pill.configure(fg_color=COLORS["info_bg"])
        self._status_label.configure(text="🔵  Detecting...", text_color=COLORS["info"])
        self._gesture_name_label.configure(text="Looking for gesture...")
        self._update_loop()

    def _stop_detection(self):
        self._is_detecting = False
        if self._update_job is not None:
            self.after_cancel(self._update_job)
            self._update_job = None

        self._camera.stop()
        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")

        self._set_status_pill("⏸  Detection stopped", COLORS["badge_gray_bg"], COLORS["badge_gray_fg"])
        self._gesture_label.configure(text="—")
        self._gesture_name_label.configure(text="Waiting for gesture...")
        self._conf_value_label.configure(text="0%", text_color=COLORS["text_muted"])
        self._conf_bar.set(0)
        self._conf_bar.configure(progress_color=COLORS["badge_gray_bg"])
        self._conf_warning.configure(text="")

        self._text_buffer.clear()
        self._sentence_builder.reset()
        word_assembler.cancel()
        self._refresh_output()
        if hasattr(self, "_final_sentence_label"):
            self._final_sentence_label.configure(state="normal")
            self._final_sentence_label.delete("1.0", "end")
            self._final_sentence_label.configure(state="disabled")

        self._cam_placeholder.place(relx=0.5, rely=0.5, anchor="center")
        self._cam_label.configure(image=None)

    def _set_status_pill(self, text, bg, fg):
        self._status_pill.configure(fg_color=bg)
        self._status_label.configure(text=text, text_color=fg)

    def _toggle_live_speech(self):
        self._live_speech_enabled = not self._live_speech_enabled
        word_assembler.set_live_speech(self._live_speech_enabled)
        
        if self._live_speech_enabled:
            self._live_speech_btn.configure(
                text="🔊  Live Speech: ON",
                fg_color=COLORS["success"],
                hover_color=COLORS["success"],
            )
        else:
            self._live_speech_btn.configure(
                text="🔇  Live Speech: OFF",
                fg_color=COLORS["badge_gray_bg"],
                hover_color=COLORS["input_bg"],
            )

    def _update_hold_bar(self, progress: float):
        """
        Updates the hold progress bar color based on hold progress.

        Progress states:
          0.0       = no gesture / idle       → gray
          0.0–1.0   = holding in progress     → warn (amber)
          1.0       = hold confirmed          → success (green)

        Wrapped in try/except so a bad color key never
        crashes the Tkinter callback and freezes the camera.
        """
        try:
            self._hold_progress_bar.set(progress)

            if progress >= 1.0:
                # Hold confirmed — green
                self._hold_progress_bar.configure(
                    progress_color=COLORS["success"]
                )
            elif progress > 0.0:
                # Holding in progress — amber
                # ✅ FIXED: was COLORS["warning"] → KeyError every frame
                self._hold_progress_bar.configure(
                    progress_color=COLORS["warn"]
                )
            else:
                # No gesture — gray
                self._hold_progress_bar.configure(
                    progress_color=COLORS["badge_gray_bg"]
                )

        except KeyError as e:
            # Safety net: bad color key should never freeze the camera
            print(f"[UI] WARNING: Missing color key in _update_hold_bar: {e}")
        except Exception as e:
            # Any other UI error — log and continue, never crash the loop
            print(f"[UI] WARNING: _update_hold_bar failed: {e}")

    def _update_loop(self):
        if not self._is_detecting:
            return

        success, frame, fps = self._camera.read_frame()

        if not success or frame is None:
            self._set_status_pill(
                "⚠  Camera feed interrupted",
                COLORS["error_bg"], COLORS["error"]
            )
            self._update_job = self.after(self.UPDATE_INTERVAL, self._update_loop)
            return

        self._fps_label.configure(text=f"FPS: {fps:.0f}")
        hand_detected, landmarks, annotated_frame = self._tracker.process_frame(frame)

        if hand_detected and landmarks:
            gesture, confidence = self._recognizer.recognize(landmarks)

            # Update hold progress bar every frame regardless of state
            progress = self._recognizer.hold_progress
            self._update_hold_bar(progress)

            # Get hold state BEFORE branching
            current = self._recognizer.current_hold_gesture

            # ── STATE A: Hold complete — gesture committed ─────────────────
            if gesture is not None:
                self._update_confidence(confidence)

                if not self._gesture_history or \
                   self._gesture_history[-1] != gesture:
                    self._add_to_history(gesture, confidence)

                text_char = map_gesture_to_text(gesture)
                if self._text_buffer.append_if_new(text_char):
                    self._sentence_builder.add_gesture(
                        text_char, time.monotonic()
                    )
                    self._refresh_output()
                    if self._live_speech_enabled:
                        word_assembler.add_letter(text_char)

                self._recognizer.reset_hold()
                self._gesture_label.configure(text=gesture)
                self._gesture_name_label.configure(
                    text=f"ASL Letter: {gesture}"
                )
                self._set_status_pill(
                    f"🟢  Gesture committed: {gesture}",
                    COLORS["success_bg"], COLORS["success"]
                )
                print(f"[UI] State A — committed: '{gesture}'")

            # ── STATE B: Hold in progress — user actively signing ──────────
            elif current is not None:
                # DO NOT call add_space() — hold is in progress
                # DO NOT reset confidence bar
                # DO NOT show "Gesture unclear"
                self._gesture_label.configure(text=current)
                self._gesture_name_label.configure(
                    text=f"ASL Letter: {current}"
                )
                self._set_status_pill(
                    f"⏳  Holding: {current}...",
                    COLORS["info_bg"], COLORS["info"]
                )
                print(
                    f"[UI] State B — holding '{current}' "
                    f"({self._recognizer.hold_progress * 100:.0f}%)"
                )

            # ── STATE C: Truly no gesture — safe to insert space ───────────
            else:
                self._gesture_label.configure(text="—")
                self._gesture_name_label.configure(text="Gesture unclear")
                self._update_confidence(0.0)   # safe to reset here only

                if self._text_buffer.maybe_insert_space():
                    self._refresh_output()
                    if self._live_speech_enabled:
                        word_assembler.add_space()  # safe — no hold active

                self._set_status_pill(
                    "🔍  Analyzing...",
                    COLORS["info_bg"], COLORS["info"]
                )
                print("[UI] State C — no gesture, inserting space if needed")

        else:
            # ── NO HAND in frame ───────────────────────────────────────────
            self._gesture_label.configure(text="—")
            self._gesture_name_label.configure(text="Gesture unclear")
            self._update_confidence(0.0)
            self._update_hold_bar(0.0)   # reset progress bar

            if self._text_buffer.maybe_insert_space():
                self._refresh_output()
                if self._live_speech_enabled:
                    word_assembler.add_space()

            self._set_status_pill(
                "🔵  No hand detected",
                COLORS["info_bg"], COLORS["info"]
            )
            print("[UI] No hand — space inserted if needed")

        # ── Sentence finalization ──────────────────────────────────────────
        current_time = time.monotonic()
        if self._sentence_builder.should_finalize(current_time):
            final_sentence = self._sentence_builder.finalize()
            if final_sentence:
                self._final_sentence_label.configure(state="normal")
                self._final_sentence_label.delete("1.0", "end")
                self._final_sentence_label.insert("1.0", final_sentence)
                self._final_sentence_label.configure(state="disabled")
                speech_buffer.push(final_sentence)
                self._refresh_sentences()

            self._sentence_builder.reset()
            self._text_buffer.clear()
            self._refresh_output()

        self._display_frame(annotated_frame)
        self._update_job = self.after(self.UPDATE_INTERVAL, self._update_loop)

    def _display_frame(self, frame):
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            w = self._cam_label.winfo_width()
            h = self._cam_label.winfo_height()
            if w > 1 and h > 1:
                max_w = min(w, 900)
                max_h = min(h, 700)
                img = ImageOps.contain(img, (max_w, max_h), Image.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
            self._cam_label.configure(image=ctk_img, text="")
            self._cam_label._ctk_image = ctk_img
        except Exception:
            pass

    def _update_confidence(self, confidence: float):
        pct = int(confidence * 100)
        self._conf_value_label.configure(text=f"{pct}%")
        self._conf_bar.set(confidence)

        if confidence >= 0.80:
            color = COLORS["success"]
            self._conf_warning.configure(text="")
        elif confidence >= 0.60:
            color = COLORS["warn"]
            self._conf_warning.configure(text="⚠ Improve positioning")
        else:
            color = COLORS["error"]
            self._conf_warning.configure(text="⚠ Low confidence")

        self._conf_bar.configure(progress_color=color)
        self._conf_value_label.configure(text_color=color)

    def _add_to_history(self, gesture: str, confidence: float):
        self._gesture_history.append(gesture)
        if len(self._gesture_history) > self._max_history:
            self._gesture_history = self._gesture_history[-self._max_history:]
        self._history_textbox.configure(state="normal")
        self._history_textbox.delete("1.0", "end")
        self._history_textbox.insert("1.0", " ".join(self._gesture_history))
        self._history_textbox.configure(state="disabled")
        self._history_textbox.see("end")

    def _clear_history(self):
        self._gesture_history.clear()
        self._history_textbox.configure(state="normal")
        self._history_textbox.delete("1.0", "end")
        self._history_textbox.configure(state="disabled")

    def _refresh_output(self):
        text = self._text_buffer.get()
        self._output_textbox.configure(state="normal")
        self._output_textbox.delete("1.0", "end")
        if text:
            self._output_textbox.insert("1.0", text)
        self._output_textbox.configure(state="disabled")
        self._output_textbox.see("end")

    def _clear_output(self):
        self._text_buffer.clear()
        self._refresh_output()

    def _on_back(self):
        self._stop_detection()
        self._tracker.release()
        self._app.show_dashboard(self._username)

    def _on_logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to log out?"):
            self._stop_detection()
            self._tracker.release()
            self._app.show_login()

    def destroy(self):
        self._stop_detection()
        word_assembler.cancel()
        try:
            self._tracker.release()
        except Exception:
            pass
        super().destroy()
