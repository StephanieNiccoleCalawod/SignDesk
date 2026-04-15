"""
forgot_password_window.py - Forgot Password UI
Step 1 of the password reset flow: email input → send OTP.
Matches the existing LoginPage layout and style exactly.
"""

import customtkinter as ctk
import threading

from core.theme import *
from core.ui_helpers import make_left_panel
from modules.auth.otp_manager import check_email_exists, create_otp
from modules.auth.password_reset_email import send_password_reset_email


# ── Shared helpers (same as auth/ui.py) ─────────────────────

def _make_entry(parent, placeholder, show=None):
    """Styled entry field — identical to the one in auth/ui.py."""
    e = ctk.CTkEntry(
        parent,
        placeholder_text=placeholder,
        font=FONT_INPUT,
        fg_color=C_INPUT_BG,
        border_color=C_INPUT_BORDER,
        border_width=1,
        text_color=C_TEXT_DARK,
        placeholder_text_color=C_TEXT_LIGHT,
        height=42,
        corner_radius=8,
    )
    if show:
        e.configure(show=show)
    e.pack(fill="x", pady=(0, 14))

    def _on_focus_in(event):
        e.configure(border_color=C_INPUT_FOCUS, border_width=1)
    def _on_focus_out(event):
        e.configure(border_color=C_INPUT_BORDER, border_width=1)
    e.bind("<FocusIn>",  _on_focus_in)
    e.bind("<FocusOut>", _on_focus_out)
    return e


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
# FORGOT PASSWORD PAGE
# ──────────────────────────────────────────────────────────────

class ForgotPasswordPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self._app = app
        self._build()

    def _build(self):
        # ── Left brand panel ───────────────────────────────
        make_left_panel(self).pack(side="left", fill="y")

        # ── Right content area ─────────────────────────────
        right = ctk.CTkFrame(self, fg_color=C_WHITE, corner_radius=0)
        right.pack(side="left", fill="both", expand=True)

        # Center the form both horizontally and vertically
        form_wrap = ctk.CTkFrame(right, fg_color="transparent", width=380)
        form_wrap.place(relx=0.5, rely=0.5, anchor="center")

        # ── Heading ────────────────────────────────────────
        ctk.CTkLabel(
            form_wrap, text="Forgot your password?",
            font=(FONT_PRIMARY, 24, "bold"),
            text_color=C_TEXT_DARK, fg_color="transparent", anchor="w"
        ).pack(fill="x")
        ctk.CTkLabel(
            form_wrap,
            text="Enter your email and we'll send you a verification code",
            font=(FONT_PRIMARY, 12),
            text_color=C_TEXT_MID, fg_color="transparent", anchor="w"
        ).pack(fill="x", pady=(4, 28))

        # ── Email field ────────────────────────────────────
        ctk.CTkLabel(
            form_wrap, text="EMAIL ADDRESS",
            font=(FONT_PRIMARY, 10, "bold"),
            text_color=C_TEXT_LIGHT, fg_color="transparent", anchor="w"
        ).pack(fill="x", pady=(0, 6))

        self._email_entry = _make_entry(form_wrap, "Enter your registered email")

        # ── Status label ───────────────────────────────────
        self._status_label = ctk.CTkLabel(
            form_wrap, text="", font=(FONT_PRIMARY, 11),
            text_color=C_TEXT_MID, fg_color="transparent"
        )
        self._status_label.pack(fill="x", pady=(0, 12))

        # ── Send Code button ──────────────────────────────
        self._send_btn = _primary_btn(form_wrap, "Send Code", self._on_send)
        self._send_btn.pack(fill="x", pady=(0, 10))

        # ── Back to Login ──────────────────────────────────
        _outline_btn(
            form_wrap, "← Back to Login", self._app.show_login
        ).pack(fill="x")

    def _on_send(self):
        email = self._email_entry.get().strip()
        if not email:
            self._status_label.configure(
                text="Please enter your email address.", text_color=C_WARN
            )
            return

        # Disable button while sending
        self._send_btn.configure(state="disabled", text="Checking...")
        self._status_label.configure(
            text="Verifying email...", text_color=C_ACCENT
        )

        def bg_task():
            # Step 1: Check if email exists
            exists, msg = check_email_exists(email)
            if not exists:
                self.after(0, lambda: self._on_send_fail(msg))
                return

            # Step 2: Generate OTP and insert into DB
            otp_code = create_otp(email)

            # Step 3: Send OTP email
            self.after(0, lambda: self._status_label.configure(
                text="Sending verification code...", text_color=C_ACCENT
            ))
            email_ok, email_msg = send_password_reset_email(email, otp_code)

            self.after(0, lambda: self._on_send_result(email_ok, email_msg, email))

        threading.Thread(target=bg_task, daemon=True).start()

    def _on_send_fail(self, message: str):
        self._send_btn.configure(state="normal", text="Send Code")
        self._status_label.configure(text=message, text_color=C_ERROR_RED)

    def _on_send_result(self, success: bool, message: str, email: str):
        self._send_btn.configure(state="normal", text="Send Code")
        if success:
            self._status_label.configure(text="", text_color=C_TEXT_MID)
            self._app.show_otp_verification(email)
        else:
            self._status_label.configure(
                text=f"Could not send email: {message}", text_color=C_ERROR_RED
            )
