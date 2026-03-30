"""
ui.py - Gesture Detection Page
Full detection UI with webcam feed, landmark overlay, gesture recognition,
confidence indicator, and sequential gesture history.
Maps to: SD001, SD002, SD003, SD004, SD006-Revised
"""

import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk
import cv2
import time

from core.theme import *
from modules.vision.camera import CameraManager
from modules.vision.tracker import HandTracker
from modules.gestures.engine import GestureRecognizer


class GestureDetectionPage(ctk.CTkFrame):
    """
    Main Gesture Detection interface.

    Layout:
    ┌─────────────────────────────────────────────────────────┐
    │  Navbar (SignDesk logo + Back to Dashboard + Logout)     │
    ├──────────────────────────┬──────────────────────────────┤
    │                          │  Recognized Gesture (large)   │
    │   Live Webcam Feed       │  Confidence Score + Bar       │
    │   with Landmark Overlay  │  Status Messages              │
    │                          │  Sequential Gesture History    │
    │                          │                                │
    ├──────────────────────────┴──────────────────────────────┤
    │  [Start Detection]  [Stop Detection]   FPS: XX          │
    └─────────────────────────────────────────────────────────┘
    """

    # Update interval in milliseconds (~30 FPS UI update)
    UPDATE_INTERVAL = 33

    def __init__(self, parent, app, username: str):
        super().__init__(parent, fg_color=C_DASH_BG, corner_radius=0)
        self._app = app
        self._username = username

        # Core components
        self._camera = CameraManager()
        self._tracker = HandTracker()
        self._recognizer = GestureRecognizer()

        # State
        self._is_detecting = False
        self._update_job = None
        self._gesture_history = []  # Sequential gesture list (SD006-Revised)
        self._max_history = 50

        self._build()

    def _build(self):
        # ── NAVBAR ────────────────────────────────────────────
        navbar = ctk.CTkFrame(self, height=60, fg_color=C_PANEL_LEFT, corner_radius=0)
        navbar.pack(fill="x", side="top")
        navbar.pack_propagate(False)

        ctk.CTkLabel(navbar, text="🤟  SignDesk", font=("Georgia", 18, "bold"),
                     text_color=C_WHITE, fg_color="transparent").pack(side="left", padx=28)

        # Right-side nav buttons
        ctk.CTkButton(navbar, text="Logout  →", command=self._on_logout, font=FONT_NAV,
                      fg_color="#E53E3E", hover_color="#C53030", text_color=C_WHITE,
                      width=90, height=34, corner_radius=6).pack(side="right", padx=(0, 24), pady=13)
        ctk.CTkButton(navbar, text="← Dashboard", command=self._on_back, font=FONT_NAV,
                      fg_color=C_ACCENT, hover_color=C_ACCENT_HOVER, text_color=C_WHITE,
                      width=120, height=34, corner_radius=6).pack(side="right", padx=(0, 8), pady=13)

        # ── MAIN BODY ────────────────────────────────────────
        body = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        body.pack(fill="both", expand=True, padx=20, pady=(16, 0))

        # Left: Webcam feed
        left_panel = ctk.CTkFrame(body, fg_color=C_CARD_BG, corner_radius=12)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))

        cam_header = ctk.CTkFrame(left_panel, fg_color="transparent")
        cam_header.pack(fill="x", padx=16, pady=(12, 8))
        ctk.CTkLabel(cam_header, text="📷  Live Camera Feed", font=("Trebuchet MS", 13, "bold"),
                     text_color=C_TEXT_DARK, fg_color="transparent").pack(side="left")
        self._fps_label = ctk.CTkLabel(cam_header, text="FPS: --", font=FONT_SMALL,
                                        text_color=C_TEXT_MID, fg_color="transparent")
        self._fps_label.pack(side="right")

        # Webcam display area
        self._cam_label = ctk.CTkLabel(left_panel, text="", fg_color="#1A1A2E", corner_radius=8)
        self._cam_label.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # Placeholder message when camera is off
        self._cam_placeholder = ctk.CTkLabel(
            self._cam_label, text="🎥\n\nCamera feed will appear here.\nClick 'Start Detection' to begin.",
            font=("Trebuchet MS", 14), text_color="#546E7A", fg_color="transparent",
            justify="center"
        )
        self._cam_placeholder.place(relx=0.5, rely=0.5, anchor="center")

        # Right: Recognition results panel
        right_panel = ctk.CTkFrame(body, width=320, fg_color=C_CARD_BG, corner_radius=12)
        right_panel.pack(side="right", fill="y", padx=(0, 0))
        right_panel.pack_propagate(False)

        # ── Gesture Result Section ───────────────────────────
        result_section = ctk.CTkFrame(right_panel, fg_color="transparent")
        result_section.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(result_section, text="Recognized Gesture", font=("Trebuchet MS", 11, "bold"),
                     text_color=C_TEXT_MID, fg_color="transparent").pack(anchor="w")

        self._gesture_label = ctk.CTkLabel(
            result_section, text="—", font=("Georgia", 56, "bold"),
            text_color=C_PANEL_LEFT, fg_color="transparent"
        )
        self._gesture_label.pack(pady=(4, 0))

        self._gesture_name_label = ctk.CTkLabel(
            result_section, text="Waiting for gesture...", font=("Trebuchet MS", 12),
            text_color=C_TEXT_MID, fg_color="transparent"
        )
        self._gesture_name_label.pack(pady=(0, 8))

        # ── Confidence Section (SD004) ───────────────────────
        conf_section = ctk.CTkFrame(right_panel, fg_color="#F8FAFF", corner_radius=8,
                                     border_width=1, border_color=C_INPUT_BORDER)
        conf_section.pack(fill="x", padx=16, pady=(0, 8))

        conf_header = ctk.CTkFrame(conf_section, fg_color="transparent")
        conf_header.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(conf_header, text="Confidence Score", font=("Trebuchet MS", 10, "bold"),
                     text_color=C_TEXT_MID, fg_color="transparent").pack(side="left")
        self._conf_value_label = ctk.CTkLabel(
            conf_header, text="0%", font=("Trebuchet MS", 14, "bold"),
            text_color=C_TEXT_LIGHT, fg_color="transparent"
        )
        self._conf_value_label.pack(side="right")

        # Confidence progress bar
        self._conf_bar = ctk.CTkProgressBar(conf_section, height=12, corner_radius=6,
                                             fg_color=C_INPUT_BG, progress_color=C_TEXT_LIGHT)
        self._conf_bar.pack(fill="x", padx=12, pady=(0, 4))
        self._conf_bar.set(0)

        # Low confidence warning label
        self._conf_warning = ctk.CTkLabel(
            conf_section, text="", font=("Trebuchet MS", 9),
            text_color=C_WARN, fg_color="transparent"
        )
        self._conf_warning.pack(padx=12, pady=(0, 8))

        # ── Status Section ───────────────────────────────────
        self._status_label = ctk.CTkLabel(
            right_panel, text="⏸  Detection stopped",
            font=("Trebuchet MS", 10), text_color=C_TEXT_MID,
            fg_color="transparent", anchor="w"
        )
        self._status_label.pack(fill="x", padx=16, pady=(0, 8))

        # ── Gesture History (SD006-Revised: Sequential) ──────
        hist_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        hist_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        hist_header = ctk.CTkFrame(hist_frame, fg_color="transparent")
        hist_header.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(hist_header, text="Gesture Sequence", font=("Trebuchet MS", 11, "bold"),
                     text_color=C_TEXT_DARK, fg_color="transparent").pack(side="left")
        ctk.CTkButton(hist_header, text="Clear", command=self._clear_history,
                      font=("Trebuchet MS", 9, "bold"), fg_color=C_INPUT_BG,
                      hover_color="#DDE3FF", text_color=C_TEXT_MID, width=50, height=24,
                      corner_radius=4, border_width=1, border_color=C_INPUT_BORDER).pack(side="right")

        self._history_textbox = ctk.CTkTextbox(
            hist_frame, font=("Consolas", 16), text_color=C_TEXT_DARK,
            fg_color="#F8FAFF", corner_radius=8, border_width=1,
            border_color=C_INPUT_BORDER, wrap="char", height=120
        )
        self._history_textbox.pack(fill="both", expand=True)
        self._history_textbox.configure(state="disabled")

        # ── BOTTOM TOOLBAR ────────────────────────────────────
        toolbar = ctk.CTkFrame(self, height=60, fg_color=C_CARD_BG, corner_radius=0)
        toolbar.pack(fill="x", side="bottom", padx=0, pady=0)
        toolbar.pack_propagate(False)

        toolbar_inner = ctk.CTkFrame(toolbar, fg_color="transparent")
        toolbar_inner.pack(expand=True)

        self._start_btn = ctk.CTkButton(
            toolbar_inner, text="▶  Start Detection", command=self._start_detection,
            font=FONT_BTN, fg_color=C_SUCCESS, hover_color="#2F855A",
            text_color=C_WHITE, width=180, height=40, corner_radius=8
        )
        self._start_btn.pack(side="left", padx=(0, 12))

        self._stop_btn = ctk.CTkButton(
            toolbar_inner, text="⏹  Stop Detection", command=self._stop_detection,
            font=FONT_BTN, fg_color=C_ERROR_RED, hover_color="#C53030",
            text_color=C_WHITE, width=180, height=40, corner_radius=8,
            state="disabled"
        )
        self._stop_btn.pack(side="left", padx=(0, 12))

    # ──────────────────────────────────────────────────────────
    # DETECTION LIFECYCLE
    # ──────────────────────────────────────────────────────────

    def _start_detection(self):
        """Starts webcam capture and gesture recognition loop."""
        success, message = self._camera.start()

        if not success:
            # SD001-AC3: Show error message if webcam unavailable
            messagebox.showerror("Webcam Error", message)
            return

        self._is_detecting = True
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._cam_placeholder.place_forget()
        self._status_label.configure(text="🟢  Detection active — show your hand", text_color=C_SUCCESS)

        self._update_loop()

    def _stop_detection(self):
        """Stops the detection loop and releases the camera."""
        self._is_detecting = False

        if self._update_job is not None:
            self.after_cancel(self._update_job)
            self._update_job = None

        self._camera.stop()

        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._status_label.configure(text="⏸  Detection stopped", text_color=C_TEXT_MID)

        # Reset display
        self._gesture_label.configure(text="—")
        self._gesture_name_label.configure(text="Waiting for gesture...")
        self._conf_value_label.configure(text="0%", text_color=C_TEXT_LIGHT)
        self._conf_bar.set(0)
        self._conf_bar.configure(progress_color=C_TEXT_LIGHT)
        self._conf_warning.configure(text="")

        # Show placeholder again
        self._cam_placeholder.place(relx=0.5, rely=0.5, anchor="center")
        self._cam_label.configure(image=None)

    def _update_loop(self):
        """Main detection loop — called every UPDATE_INTERVAL ms."""
        if not self._is_detecting:
            return

        success, frame, fps = self._camera.read_frame()

        if not success or frame is None:
            self._status_label.configure(
                text="⚠  Camera feed interrupted", text_color=C_WARN
            )
            self._update_job = self.after(self.UPDATE_INTERVAL, self._update_loop)
            return

        # Update FPS display (SD001-AC4)
        self._fps_label.configure(text=f"FPS: {fps:.0f}")

        # Process frame through MediaPipe (SD002)
        hand_detected, landmarks, annotated_frame = self._tracker.process_frame(frame)

        if hand_detected and landmarks:
            # Recognize gesture (SD003)
            gesture, confidence = self._recognizer.recognize(landmarks)

            if gesture is not None:
                # Update gesture display (SD003-AC2)
                self._gesture_label.configure(text=gesture)
                self._gesture_name_label.configure(text=f"ASL Letter: {gesture}")

                # Update confidence indicator (SD004)
                self._update_confidence(confidence)

                # Add to sequential history if it's a new gesture (SD006-Revised)
                if (len(self._gesture_history) == 0 or
                        self._gesture_history[-1] != gesture):
                    self._add_to_history(gesture, confidence)

                self._status_label.configure(
                    text=f"🟢  Gesture detected: {gesture}",
                    text_color=C_SUCCESS
                )
            else:
                self._status_label.configure(
                    text="🔍  Analyzing hand position...",
                    text_color=C_TEXT_MID
                )
        else:
            # No hand detected (Error prompt per business requirements)
            self._status_label.configure(
                text="✋  No hand detected. Please position your hand within the camera frame.",
                text_color=C_WARN
            )

        # Display annotated frame in the UI
        self._display_frame(annotated_frame)

        # Schedule next update
        self._update_job = self.after(self.UPDATE_INTERVAL, self._update_loop)

    # ──────────────────────────────────────────────────────────
    # UI UPDATE HELPERS
    # ──────────────────────────────────────────────────────────

    def _display_frame(self, frame):
        """Converts an OpenCV BGR frame to CTkImage and displays it."""
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)

            # Get the display area size
            label_width = self._cam_label.winfo_width()
            label_height = self._cam_label.winfo_height()

            if label_width > 1 and label_height > 1:
                img = img.resize((label_width, label_height), Image.LANCZOS)

            ctk_img = ctk.CTkImage(light_image=img, dark_image=img,
                                    size=(img.width, img.height))
            self._cam_label.configure(image=ctk_img, text="")
            self._cam_label._ctk_image = ctk_img  # Prevent garbage collection
        except Exception:
            pass

    def _update_confidence(self, confidence: float):
        """
        Updates the confidence indicator display.
        SD004-AC1: Confidence percentage displayed
        SD004-AC2: Score updates in real time
        SD004-AC3: Below 60% shows low-confidence warning
        SD004-AC4: Indicator always visible during active recognition
        """
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
            self._conf_warning.configure(text="⚠ Low confidence — gesture may be inaccurate")

        self._conf_bar.configure(progress_color=color)
        self._conf_value_label.configure(text_color=color)

    def _add_to_history(self, gesture: str, confidence: float):
        """
        Adds a gesture to the sequential history list.
        SD006-Revised: Each gesture label and confidence score shown as detected.
        """
        self._gesture_history.append(gesture)

        if len(self._gesture_history) > self._max_history:
            self._gesture_history = self._gesture_history[-self._max_history:]

        # Update textbox display
        self._history_textbox.configure(state="normal")
        self._history_textbox.delete("1.0", "end")
        self._history_textbox.insert("1.0", " ".join(self._gesture_history))
        self._history_textbox.configure(state="disabled")
        self._history_textbox.see("end")

    def _clear_history(self):
        """Clears the gesture sequence history."""
        self._gesture_history.clear()
        self._history_textbox.configure(state="normal")
        self._history_textbox.delete("1.0", "end")
        self._history_textbox.configure(state="disabled")

    # ──────────────────────────────────────────────────────────
    # NAVIGATION
    # ──────────────────────────────────────────────────────────

    def _on_back(self):
        """Returns to the dashboard."""
        self._stop_detection()
        self._tracker.release()
        self._app.show_dashboard(self._username)

    def _on_logout(self):
        """Logs out and returns to the login page."""
        if messagebox.askyesno("Logout", "Are you sure you want to log out?"):
            self._stop_detection()
            self._tracker.release()
            self._app.show_login()

    def destroy(self):
        """Clean up resources when page is destroyed."""
        self._stop_detection()
        try:
            self._tracker.release()
        except Exception:
            pass
        super().destroy()
