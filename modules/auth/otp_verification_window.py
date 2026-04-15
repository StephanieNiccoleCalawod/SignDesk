"""
otp_verification_window.py - OTP Verification UI (Password Reset)
Step 2 of the password reset flow: 6-digit OTP entry with auto-advance.
Matches the existing VerificationPage layout and style.
"""

import customtkinter as ctk
import threading

from core.theme import *
from core.ui_helpers import make_left_panel
from core.email_service import ResendTracker, VerificationAttemptTracker
from core.email_config import OTP_RESEND_COOLDOWN
from modules.auth.otp_manager import (
    create_otp, verify_otp, PASSWORD_RESET_OTP_EXPIRY_MINUTES
)
from modules.auth.password_reset_email import send_password_reset_email


# ── Shared helpers (same as auth/ui.py) ─────────────────────

def _primary_btn(parent, text, command):
    return ctk.CTkButton(
        parent, text=text, command=command,
        font=FONT_BTN,
        fg_color=C_ACCENT, hover_color=C_ACCENT_HOVER,
        text_color=C_WHITE,
        height=42, corner_radius=21
    )


def _outline_btn(parent, text, command):
    return ctk.CTkButton(
        parent, text=text, command=command,
        font=FONT_BTN,
        fg_color=C_WHITE, hover_color=C_INPUT_BG,
        text_color=C_TEXT_DARK,
        border_width=1, border_color=C_CARD_BORDER,
        height=42, corner_radius=21
    )


# ──────────────────────────────────────────────────────────────
# FORGOT PASSWORD OTP PAGE
# ──────────────────────────────────────────────────────────────

class ForgotPasswordOTPPage(ctk.CTkFrame):
    def __init__(self, parent, app, email: str):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self._app = app
        self._email = email
        self._resend_tracker = ResendTracker()
        self._resend_tracker.record_resend()  # Initial send already happened
        self._attempt_tracker = VerificationAttemptTracker()
        self._cooldown_job = None
        self._otp_boxes = []
        self._build()
        self._start_cooldown_timer()

    def _build(self):
        # ── Left brand panel ───────────────────────────────
        make_left_panel(self).pack(side="left", fill="y")

        # ── Right content area ─────────────────────────────
        right = ctk.CTkFrame(self, fg_color=C_WHITE, corner_radius=0)
        right.pack(side="left", fill="both", expand=True)

        form_wrap = ctk.CTkFrame(right, fg_color="transparent")
        form_wrap.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.72)

        # ── Header ─────────────────────────────────────────
        ctk.CTkLabel(
            form_wrap, text="Verify your identity",
            font=FONT_HEADING,
            text_color=C_TEXT_DARK, fg_color="transparent", anchor="w"
        ).pack(fill="x")

        masked = self._mask_email(self._email)
        ctk.CTkLabel(
            form_wrap,
            text="We've sent a verification code to:",
            font=FONT_SUBHEAD, text_color=C_TEXT_MID,
            fg_color="transparent", anchor="w"
        ).pack(fill="x", pady=(4, 2))
        ctk.CTkLabel(
            form_wrap, text=masked,
            font=(FONT_PRIMARY, 13, "bold"), text_color=C_PANEL_LEFT,
            fg_color="transparent", anchor="w"
        ).pack(fill="x", pady=(0, 24))

        # ── OTP input card ─────────────────────────────────
        otp_card = ctk.CTkFrame(
            form_wrap, fg_color=C_INPUT_BG, corner_radius=10,
            border_width=1, border_color=C_CARD_BORDER
        )
        otp_card.pack(fill="x", pady=(0, 16))

        otp_inner = ctk.CTkFrame(otp_card, fg_color="transparent")
        otp_inner.pack(padx=24, pady=22)

        ctk.CTkLabel(
            otp_inner, text="Enter the 6-digit verification code",
            font=(FONT_PRIMARY, 11, "bold"), text_color=C_TEXT_MID,
            fg_color="transparent"
        ).pack(pady=(0, 12))

        # ── 6 individual digit boxes ───────────────────────
        boxes_frame = ctk.CTkFrame(otp_inner, fg_color="transparent")
        boxes_frame.pack(pady=(0, 8))

        self._otp_boxes = []
        for i in range(6):
            box = ctk.CTkEntry(
                boxes_frame,
                font=("Courier New", 24, "bold"),
                justify="center",
                fg_color=C_WHITE,
                border_color=C_INPUT_BORDER,
                border_width=1,
                text_color=C_PANEL_LEFT,
                placeholder_text_color="#C5CAE9",
                height=56, width=48,
                corner_radius=8,
            )
            box.pack(side="left", padx=4)

            # Focus ring
            box.bind("<FocusIn>",
                     lambda e, b=box: b.configure(border_color=C_INPUT_FOCUS))
            box.bind("<FocusOut>",
                     lambda e, b=box: b.configure(border_color=C_INPUT_BORDER))

            # Auto-advance / auto-backspace bindings
            box.bind("<KeyRelease>", lambda e, idx=i: self._on_key(e, idx))

            self._otp_boxes.append(box)

        ctk.CTkLabel(
            otp_inner,
            text=f"Code expires in {PASSWORD_RESET_OTP_EXPIRY_MINUTES} minutes",
            font=(FONT_PRIMARY, 10), text_color=C_TEXT_LIGHT,
            fg_color="transparent"
        ).pack()

        # ── Status label ───────────────────────────────────
        self._status_label = ctk.CTkLabel(
            form_wrap, text="", font=(FONT_PRIMARY, 11),
            text_color=C_TEXT_MID, fg_color="transparent"
        )
        self._status_label.pack(fill="x", pady=(0, 12))

        # ── Verify button ──────────────────────────────────
        self._verify_btn = _primary_btn(
            form_wrap, "Verify Code", self._on_verify
        )
        self._verify_btn.pack(fill="x", pady=(0, 10))

        # ── Resend row ─────────────────────────────────────
        resend_row = ctk.CTkFrame(form_wrap, fg_color="transparent")
        resend_row.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            resend_row, text="Didn't receive the code?",
            font=FONT_SMALL, text_color=C_TEXT_LIGHT, fg_color="transparent"
        ).pack(side="left")

        self._resend_btn = ctk.CTkButton(
            resend_row, text="Resend Code",
            command=self._on_resend,
            font=(FONT_PRIMARY, 11, "bold"),
            fg_color="transparent", hover_color=C_INPUT_BG,
            text_color=C_ACCENT,
            width=100, height=28, corner_radius=4, state="disabled"
        )
        self._resend_btn.pack(side="left", padx=(8, 0))

        self._cooldown_label = ctk.CTkLabel(
            resend_row, text="", font=(FONT_PRIMARY, 10),
            text_color=C_TEXT_LIGHT, fg_color="transparent"
        )
        self._cooldown_label.pack(side="left", padx=(6, 0))

        # ── Back button ───────────────────────────────────
        _outline_btn(
            form_wrap, "← Back", self._on_back
        ).pack(fill="x")

    # ── OTP box logic ──────────────────────────────────────

    def _on_key(self, event, index):
        """Handle auto-advance and auto-backspace for OTP digit boxes."""
        value = self._otp_boxes[index].get()

        # If a digit was typed, keep only the last digit and advance
        if value and value[-1].isdigit():
            self._otp_boxes[index].delete(0, "end")
            self._otp_boxes[index].insert(0, value[-1])
            if index < 5:
                self._otp_boxes[index + 1].focus_set()
        elif event.keysym == "BackSpace":
            # Move focus to previous box on backspace
            if index > 0:
                self._otp_boxes[index - 1].focus_set()
        else:
            # Remove any non-digit characters
            self._otp_boxes[index].delete(0, "end")

    def _get_otp_code(self) -> str:
        """Collect all 6 digits into one string."""
        return "".join(box.get().strip() for box in self._otp_boxes)

    def _clear_otp_boxes(self):
        """Clear all 6 OTP digit boxes."""
        for box in self._otp_boxes:
            box.delete(0, "end")
        self._otp_boxes[0].focus_set()

    # ── Email masking ──────────────────────────────────────

    def _mask_email(self, email: str) -> str:
        try:
            local, domain = email.split("@")
            masked = local[0] + "***" + (local[-1] if len(local) > 2 else "")
            return f"{masked}@{domain}"
        except Exception:
            return email

    # ── Verify flow ────────────────────────────────────────

    def _on_verify(self):
        code = self._get_otp_code()

        if len(code) != 6 or not code.isdigit():
            self._status_label.configure(
                text="Please enter all 6 digits.", text_color=C_WARN
            )
            return

        # Check brute-force protection
        can_try, reason = self._attempt_tracker.can_attempt()
        if not can_try:
            self._status_label.configure(text=reason, text_color=C_ERROR_RED)
            self._verify_btn.configure(state="disabled")
            return

        self._verify_btn.configure(state="disabled", text="Verifying...")
        self._status_label.configure(text="Verifying code...", text_color=C_ACCENT)

        def run_verify():
            ok, msg = verify_otp(self._email, code)
            self.after(0, lambda: self._on_verify_result(ok, msg))

        threading.Thread(target=run_verify, daemon=True).start()

    def _on_verify_result(self, success: bool, msg: str):
        if success:
            self._status_label.configure(
                text="Code verified!", text_color=C_SUCCESS
            )
            self._app.show_reset_password(self._email)
        else:
            self._verify_btn.configure(state="normal", text="Verify Code")
            self._attempt_tracker.record_attempt()
            remaining = self._attempt_tracker.attempts_remaining
            self._status_label.configure(
                text=f"{msg} ({remaining} attempts left)",
                text_color=C_ERROR_RED
            )
            self._clear_otp_boxes()

    # ── Resend flow ────────────────────────────────────────

    def _on_resend(self):
        can_resend, reason = self._resend_tracker.can_resend()
        if not can_resend:
            self._status_label.configure(text=reason, text_color=C_WARN)
            return

        self._resend_btn.configure(state="disabled")
        self._status_label.configure(
            text="Sending new code...", text_color=C_ACCENT
        )

        def resend_task():
            otp_code = create_otp(self._email)
            email_ok, email_msg = send_password_reset_email(
                self._email, otp_code
            )
            self.after(0, lambda: self._on_resend_complete(email_ok, email_msg))

        threading.Thread(target=resend_task, daemon=True).start()

    def _on_resend_complete(self, success: bool, message: str):
        if success:
            self._resend_tracker.record_resend()
            from core.email_config import OTP_MAX_RESENDS
            count = self._resend_tracker.resend_count
            self._status_label.configure(
                text=f"New code sent! ({count}/{OTP_MAX_RESENDS} resends used)",
                text_color=C_SUCCESS
            )
            self._clear_otp_boxes()
            self._start_cooldown_timer()
        else:
            self._status_label.configure(text=message, text_color=C_ERROR_RED)
            self._resend_btn.configure(state="normal")

    # ── Cooldown timer ─────────────────────────────────────

    def _start_cooldown_timer(self):
        self._resend_btn.configure(state="disabled")
        self._update_cooldown()

    def _update_cooldown(self):
        remaining = self._resend_tracker.cooldown_remaining
        if remaining > 0:
            self._cooldown_label.configure(text=f"({remaining}s)")
            self._resend_btn.configure(state="disabled")
            self._cooldown_job = self.after(1000, self._update_cooldown)
        else:
            self._cooldown_label.configure(text="")
            can_resend, _ = self._resend_tracker.can_resend()
            if can_resend:
                self._resend_btn.configure(state="normal")
            else:
                from core.email_config import OTP_MAX_RESENDS
                if self._resend_tracker.resend_count >= OTP_MAX_RESENDS:
                    self._resend_btn.configure(state="disabled")
                    self._cooldown_label.configure(text="(limit reached)")
                else:
                    self._cooldown_job = self.after(500, self._update_cooldown)

    # ── Navigation ─────────────────────────────────────────

    def _on_back(self):
        if self._cooldown_job:
            self.after_cancel(self._cooldown_job)
        self._app.show_forgot_password()

    def destroy(self):
        if self._cooldown_job:
            self.after_cancel(self._cooldown_job)
        super().destroy()
