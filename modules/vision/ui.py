"""
modules/vision/ui.py - Gesture Detection Page
"""

import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageOps
import cv2
import os

from core.theme import *
from modules.vision.camera import CameraManager
from modules.vision.tracker import HandTracker
from modules.gestures.engine import GestureRecognizer


class GestureDetectionPage(ctk.CTkFrame):
    UPDATE_INTERVAL = 33

    def __init__(self, parent, app, username: str):
        super().__init__(parent, fg_color=C_DASH_BG, corner_radius=0)
        self._app        = app
        self._username   = username
        self._camera     = CameraManager()
        self._tracker    = HandTracker()
        self._recognizer = GestureRecognizer()
        self._is_detecting  = False
        self._update_job    = None
        self._gesture_history = []
        self._max_history = 50
        self._build()

    # ── Build ──────────────────────────────────────────────

    def _build(self):
        self._build_navbar()
        self._build_body()
        self._build_toolbar()

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
        ).pack(side="left", padx=24)

        ctk.CTkButton(
            navbar, text="Logout  →",
            command=self._on_logout, font=FONT_NAV,
            fg_color=C_ERROR_RED, hover_color="#C73D3C",
            text_color=C_WHITE, width=90, height=32, corner_radius=6
        ).pack(side="right", padx=(0, 20), pady=14)

        ctk.CTkButton(
            navbar, text="← Dashboard",
            command=self._on_back, font=FONT_NAV,
            fg_color="transparent", hover_color=C_PANEL_LEFT2,
            text_color=C_WHITE, border_width=1, border_color=C_WHITE,
            width=120, height=32, corner_radius=6
        ).pack(side="right", padx=(0, 8), pady=14)

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        body.pack(fill="both", expand=True, padx=20, pady=(16, 0))
        body.grid_columnconfigure(0, weight=7, uniform="panels")
        body.grid_columnconfigure(1, weight=3, uniform="panels")
        body.grid_rowconfigure(0, weight=1)

        # ── Left: camera panel ──────────────────────────────
        left = ctk.CTkFrame(body, fg_color=C_CARD_BG, corner_radius=12,
                            border_width=1, border_color=C_CARD_BORDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.pack_propagate(False)

        cam_hdr = ctk.CTkFrame(left, fg_color="transparent")
        cam_hdr.pack(fill="x", padx=16, pady=(12, 8))
        ctk.CTkLabel(
            cam_hdr, text="📷  Live Camera Feed",
            font=(FONT_PRIMARY, 13, "bold"),
            text_color=C_TEXT_DARK, fg_color="transparent"
        ).pack(side="left")
        self._fps_label = ctk.CTkLabel(
            cam_hdr, text="FPS: --",
            font=FONT_SMALL, text_color=C_TEXT_LIGHT, fg_color="transparent"
        )
        self._fps_label.pack(side="right")

        self._cam_label = ctk.CTkLabel(
            left, text="", fg_color="#0D1117", corner_radius=8)
        self._cam_label.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # Camera offline placeholder
        self._cam_placeholder = ctk.CTkFrame(
            self._cam_label, fg_color="#1A1F2E",
            corner_radius=14, border_width=1, border_color="#2A3050"
        )
        self._cam_placeholder.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            self._cam_placeholder, text="📸",
            font=("Arial", 32), text_color=C_CYAN
        ).pack(pady=(22, 6))
        ctk.CTkLabel(
            self._cam_placeholder, text="Camera Offline",
            font=(FONT_PRIMARY, 16, "bold"), text_color="#E2E8F0"
        ).pack(padx=40)
        ctk.CTkLabel(
            self._cam_placeholder,
            text="Click 'Start Detection' below\nto activate your webcam and begin.",
            font=(FONT_PRIMARY, 12), text_color="#94A3B8", justify="center"
        ).pack(padx=40, pady=(4, 22))

        # ── Right: recognition panel ────────────────────────
        right = ctk.CTkFrame(body, fg_color=C_CARD_BG, corner_radius=12,
                             border_width=1, border_color=C_CARD_BORDER)
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right.pack_propagate(False)

        ctk.CTkLabel(
            right, text="Recognized Gesture",
            font=(FONT_PRIMARY, 14, "bold"),
            text_color=C_TEXT_DARK, fg_color="transparent"
        ).pack(pady=(20, 8), padx=20, anchor="w")

        # Gesture result card
        result_card = ctk.CTkFrame(
            right, fg_color=C_INPUT_BG, corner_radius=10,
            border_width=1, border_color=C_CARD_BORDER
        )
        result_card.pack(fill="x", padx=20, pady=(0, 14))

        self._gesture_label = ctk.CTkLabel(
            result_card, text="—",
            font=("Georgia", 52, "bold"), text_color=C_ACCENT
        )
        self._gesture_label.pack(pady=(16, 2))
        self._gesture_name_label = ctk.CTkLabel(
            result_card, text="Waiting for gesture...",
            font=(FONT_PRIMARY, 12), text_color=C_TEXT_MID
        )
        self._gesture_name_label.pack(pady=(0, 16))

        # Confidence meter
        conf_frame = ctk.CTkFrame(right, fg_color="transparent")
        conf_frame.pack(fill="x", padx=20, pady=(0, 10))

        conf_row = ctk.CTkFrame(conf_frame, fg_color="transparent")
        conf_row.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(
            conf_row, text="Confidence",
            font=(FONT_PRIMARY, 12), text_color=C_TEXT_MID, fg_color="transparent"
        ).pack(side="left")
        self._conf_value_label = ctk.CTkLabel(
            conf_row, text="0%",
            font=(FONT_PRIMARY, 13, "bold"),
            text_color=C_TEXT_LIGHT, fg_color="transparent"
        )
        self._conf_value_label.pack(side="right")

        self._conf_bar = ctk.CTkProgressBar(
            conf_frame, height=6, corner_radius=3,
            progress_color=C_SUCCESS, fg_color=C_CARD_BORDER
        )
        self._conf_bar.pack(fill="x")
        self._conf_bar.set(0)  # starts empty — fixes the original 0%-but-full-bar bug

        # Status pill
        self._status_pill = ctk.CTkFrame(
            right, fg_color=C_BADGE_GRAY_BG, corner_radius=8
        )
        self._status_pill.pack(anchor="w", padx=20, pady=(12, 4))
        self._status_label = ctk.CTkLabel(
            self._status_pill, text="⏸  Detection stopped",
            font=(FONT_PRIMARY, 11), text_color=C_BADGE_GRAY_FG,
            fg_color="transparent"
        )
        self._status_label.pack(padx=10, pady=5)

        self._conf_warning = ctk.CTkLabel(
            right, text="", font=(FONT_PRIMARY, 11),
            text_color=C_WARN, fg_color="transparent"
        )
        self._conf_warning.pack(padx=20, anchor="w")

        # Sequence history
        seq_hdr = ctk.CTkFrame(right, fg_color="transparent")
        seq_hdr.pack(fill="x", padx=20, pady=(14, 6))
        ctk.CTkLabel(
            seq_hdr, text="Gesture Sequence",
            font=(FONT_PRIMARY, 13, "bold"),
            text_color=C_TEXT_DARK, fg_color="transparent"
        ).pack(side="left")
        ctk.CTkButton(
            seq_hdr, text="Clear", command=self._clear_history,
            font=(FONT_PRIMARY, 11), fg_color="transparent",
            hover_color=C_INPUT_BG, text_color=C_ACCENT,
            width=50, height=24, corner_radius=4
        ).pack(side="right")

        self._history_textbox = ctk.CTkTextbox(
            right,
            font=("Consolas", 22),
            fg_color=C_INPUT_BG,
            text_color=C_TEXT_DARK,
            wrap="word",
            border_width=1, border_color=C_CARD_BORDER,
            corner_radius=8
        )
        self._history_textbox.pack(
            fill="both", expand=True, padx=20, pady=(0, 20))
        self._history_textbox.configure(state="disabled")

    def _build_toolbar(self):
        toolbar = ctk.CTkFrame(
            self, height=64, fg_color=C_CARD_BG,
            corner_radius=0, border_width=1, border_color=C_CARD_BORDER
        )
        toolbar.pack(fill="x", side="bottom")
        toolbar.pack_propagate(False)

        inner = ctk.CTkFrame(toolbar, fg_color="transparent")
        inner.pack(expand=True)

        self._start_btn = ctk.CTkButton(
            inner, text="▶  Start Detection",
            command=self._start_detection,
            font=FONT_BTN,
            fg_color=C_SUCCESS, hover_color="#178A64",
            text_color=C_WHITE, width=180, height=40, corner_radius=8
        )
        self._start_btn.pack(side="left", padx=(0, 12))

        self._stop_btn = ctk.CTkButton(
            inner, text="■  Stop Detection",
            command=self._stop_detection,
            font=FONT_BTN,
            fg_color=C_ERROR_RED, hover_color="#C73D3C",
            text_color=C_WHITE, width=180, height=40, corner_radius=8,
            state="disabled"
        )
        self._stop_btn.pack(side="left")

    # ── Detection lifecycle (unchanged logic) ──────────────

    def _start_detection(self):
        if getattr(self, "_permission_granted", False) == False:
            response = messagebox.askyesno(
                "Camera Permission Required",
                "SignDesk requires access to your webcam to detect hand gestures.\n\n"
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

        # Switch status pill to active (green)
        self._status_pill.configure(fg_color=C_SUCCESS_BG)
        self._status_label.configure(
            text="🟢  Detection active — show your hand",
            text_color=C_SUCCESS
        )
        self._update_loop()

    def _stop_detection(self):
        self._is_detecting = False
        if self._update_job is not None:
            self.after_cancel(self._update_job)
            self._update_job = None

        self._camera.stop()
        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")

        # Reset status pill
        self._status_pill.configure(fg_color=C_BADGE_GRAY_BG)
        self._status_label.configure(
            text="⏸  Detection stopped", text_color=C_BADGE_GRAY_FG)

        self._gesture_label.configure(text="—")
        self._gesture_name_label.configure(text="Waiting for gesture...")
        self._conf_value_label.configure(text="0%", text_color=C_TEXT_LIGHT)
        self._conf_bar.set(0)
        self._conf_bar.configure(progress_color=C_SUCCESS)
        self._conf_warning.configure(text="")
        self._cam_placeholder.place(relx=0.5, rely=0.5, anchor="center")
        self._cam_label.configure(image=None)

    def _update_loop(self):
        if not self._is_detecting:
            return

        success, frame, fps = self._camera.read_frame()

        if not success or frame is None:
            self._status_pill.configure(fg_color=C_WARN_BG)
            self._status_label.configure(
                text="⚠  Camera feed interrupted", text_color=C_WARN)
            self._update_job = self.after(self.UPDATE_INTERVAL, self._update_loop)
            return

        self._fps_label.configure(text=f"FPS: {fps:.0f}")
        hand_detected, landmarks, annotated_frame = self._tracker.process_frame(frame)

        if hand_detected and landmarks:
            gesture, confidence = self._recognizer.recognize(landmarks)
            if gesture is not None:
                self._update_confidence(confidence)
                if confidence >= self._recognizer.CONFIDENCE_THRESHOLD:
                    self._gesture_label.configure(text=gesture)
                    self._gesture_name_label.configure(text=f"ASL Letter: {gesture}")
                    if (not self._gesture_history or
                            self._gesture_history[-1] != gesture):
                        self._add_to_history(gesture, confidence)
                    self._status_pill.configure(fg_color=C_SUCCESS_BG)
                    self._status_label.configure(
                        text=f"🟢  Gesture detected: {gesture}",
                        text_color=C_SUCCESS)
                else:
                    self._gesture_label.configure(text="—")
                    self._gesture_name_label.configure(
                        text="Gesture unclear. Reposition your hand.")
                    self._status_pill.configure(fg_color=C_WARN_BG)
                    self._status_label.configure(
                        text="⚠  Low confidence. Repeat gesture clearly.",
                        text_color=C_WARN)
            else:
                self._status_pill.configure(fg_color=C_WARN_BG)
                self._status_label.configure(
                    text="🔍  Gesture not recognized.",
                    text_color=C_WARN)
        else:
            self._status_pill.configure(fg_color=C_WARN_BG)
            self._status_label.configure(
                text="✋  No hand detected. Position hand in frame.",
                text_color=C_WARN)

        self._display_frame(annotated_frame)
        self._update_job = self.after(self.UPDATE_INTERVAL, self._update_loop)

    # ── UI helpers (unchanged logic) ───────────────────────

    def _display_frame(self, frame):
        try:
            from PIL import ImageOps
            import cv2
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            w = self._cam_label.winfo_width()
            h = self._cam_label.winfo_height()
            if w > 1 and h > 1:
                img = ImageOps.contain(img, (w, h), Image.LANCZOS)
            ctk_img = ctk.CTkImage(
                light_image=img, dark_image=img, size=(img.width, img.height))
            self._cam_label.configure(image=ctk_img, text="")
            self._cam_label._ctk_image = ctk_img
        except Exception:
            pass

    def _update_confidence(self, confidence: float):
        pct = int(confidence * 100)
        self._conf_value_label.configure(text=f"{pct}%")
        self._conf_bar.set(confidence)

        if confidence >= 0.80:
            color = C_SUCCESS
            self._conf_warning.configure(text="")
        elif confidence >= 0.60:
            color = C_ACCENT
            self._conf_warning.configure(text="")
        else:
            color = C_WARN
            self._conf_warning.configure(
                text="⚠ Low confidence. Repeat the gesture more clearly.")

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
        try:
            self._tracker.release()
        except Exception:
            pass
        super().destroy()
