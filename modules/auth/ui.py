"""
modules/auth/ui.py - Authentication UI Pages
Contains LoginPage, RegisterPage, and VerificationPage.
"""

import customtkinter as ctk
from tkinter import messagebox
import threading

from core.theme import *
from core.ui_helpers import make_left_panel, make_field, make_primary_button, make_ghost_button
from core.email_service import (
    generate_otp, get_otp_expiry, is_otp_expired,
    send_verification_email, ResendTracker, VerificationAttemptTracker
)
from core.email_config import OTP_RESEND_COOLDOWN
from modules.auth.service import (
    login_user, register_user, validate_password,
    validate_registration, check_duplicate_username, check_duplicate_email,
    verify_user, resend_verification_code
)


# ── Shared helpers ─────────────────────────────────────────

def _make_entry(parent, placeholder, show=None):
    """Styled entry field used across all auth pages."""
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

    # 1px brand-blue border on focus — closest to CSS focus ring in CTk
    def _on_focus_in(event):
        e.configure(border_color=C_INPUT_FOCUS, border_width=1)
    def _on_focus_out(event):
        e.configure(border_color=C_INPUT_BORDER, border_width=1)
    e.bind("<FocusIn>",  _on_focus_in)
    e.bind("<FocusOut>", _on_focus_out)
    return e


def _field_label(parent, text):
    """Small uppercase field label."""
    ctk.CTkLabel(
        parent, text=text,
        font=(FONT_PRIMARY, 10, "bold"),
        text_color=C_TEXT_LIGHT,
        fg_color="transparent", anchor="w"
    ).pack(fill="x", pady=(0, 4))


def _section_label(parent, heading, subheading):
    ctk.CTkLabel(
        parent, text=heading, font=FONT_HEADING,
        text_color=C_TEXT_DARK, fg_color="transparent", anchor="w"
    ).pack(fill="x")
    ctk.CTkLabel(
        parent, text=subheading, font=FONT_SUBHEAD,
        text_color=C_TEXT_MID, fg_color="transparent", anchor="w"
    ).pack(fill="x", pady=(4, 24))


def _divider(parent):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", pady=(4, 4))
    ctk.CTkFrame(row, height=1, fg_color=C_CARD_BORDER).pack(
        side="left", fill="x", expand=True, pady=6
    )
    ctk.CTkLabel(row, text="  or  ", font=FONT_SMALL,
                 text_color=C_TEXT_LIGHT, fg_color="transparent").pack(side="left")
    ctk.CTkFrame(row, height=1, fg_color=C_CARD_BORDER).pack(
        side="left", fill="x", expand=True, pady=6
    )


def _primary_btn(parent, text, command):
    return ctk.CTkButton(
        parent, text=text, command=command,
        font=FONT_BTN,
        fg_color=C_ACCENT, hover_color=C_ACCENT_HOVER,
        text_color=C_WHITE,
        height=42, corner_radius=8
    )


def _outline_btn(parent, text, command):
    return ctk.CTkButton(
        parent, text=text, command=command,
        font=FONT_BTN,
        fg_color=C_WHITE, hover_color=C_INPUT_BG,
        text_color=C_TEXT_DARK,
        border_width=1, border_color=C_CARD_BORDER,
        height=42, corner_radius=8
    )


# ──────────────────────────────────────────────────────────────
# LOGIN PAGE
# ──────────────────────────────────────────────────────────────

class LoginPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self._app = app
        self._build()

    def _build(self):
        # Left brand panel (unchanged — uses existing make_left_panel)
        make_left_panel(self).pack(side="left", fill="y")

        right = ctk.CTkFrame(self, fg_color=C_WHITE, corner_radius=0)
        right.pack(side="left", fill="both", expand=True)

        form_wrap = ctk.CTkFrame(right, fg_color="transparent")
        form_wrap.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.72)

        _section_label(form_wrap, "Welcome back", "Sign in to continue to SignDesk")

        _field_label(form_wrap, "USERNAME")
        self._user_entry = _make_entry(form_wrap, "Enter your username")

        # Password row with forgot link
        pw_row = ctk.CTkFrame(form_wrap, fg_color="transparent")
        pw_row.pack(fill="x", pady=(0, 4))
        _field_label(pw_row, "PASSWORD")
        # Forgot password floated right
        ctk.CTkButton(
            pw_row, text="Forgot password?",
            font=(FONT_PRIMARY, 10), fg_color="transparent",
            hover_color=C_INPUT_BG, text_color=C_ACCENT,
            width=0, height=18, corner_radius=4
        ).pack(side="right")

        self._pass_entry = _make_entry(form_wrap, "Enter your password", show="●")

        # Show password checkbox
        show_row = ctk.CTkFrame(form_wrap, fg_color="transparent")
        show_row.pack(fill="x", pady=(0, 20))
        self._show_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            show_row, text="Show Password",
            variable=self._show_var, command=self._toggle_password,
            font=FONT_SMALL, text_color=C_TEXT_MID,
            fg_color=C_ACCENT, hover_color=C_ACCENT_HOVER,
            checkmark_color=C_WHITE, border_color=C_INPUT_BORDER
        ).pack(side="left")

        _primary_btn(form_wrap, "Sign In", self._on_login).pack(fill="x", pady=(0, 0))
        _divider(form_wrap)
        _outline_btn(form_wrap, "Create Account", self._app.show_register).pack(fill="x")

        ctk.CTkLabel(
            form_wrap,
            text="Don't have an account? Click Create Account above.",
            font=FONT_SMALL, text_color=C_TEXT_LIGHT, fg_color="transparent"
        ).pack(pady=(14, 0))

    def _toggle_password(self):
        self._pass_entry.configure(show="" if self._show_var.get() else "●")

    def _on_login(self):
        username = self._user_entry.get().strip()
        password = self._pass_entry.get().strip()
        if not username or not password:
            messagebox.showwarning("Missing Fields", "Please fill in all required fields.")
            return
        success, message = login_user(username, password)
        if success:
            self._app.show_dashboard(username)
        else:
            messagebox.showerror("Login Failed", message)


# ──────────────────────────────────────────────────────────────
# REGISTER PAGE
# ──────────────────────────────────────────────────────────────

class RegisterPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self._app = app
        self._build()

    def _build(self):
        make_left_panel(self).pack(side="left", fill="y")

        right = ctk.CTkScrollableFrame(self, fg_color=C_WHITE, corner_radius=0)
        right.pack(side="left", fill="both", expand=True)

        form_wrap = ctk.CTkFrame(right, fg_color="transparent")
        form_wrap.pack(padx=60, pady=30, fill="both", expand=True)

        _section_label(form_wrap, "Create your account", "Join SignDesk — it's free")

        _field_label(form_wrap, "USERNAME")
        self._uname_entry = _make_entry(form_wrap, "Choose a username")

        _field_label(form_wrap, "EMAIL ADDRESS")
        self._email_entry = _make_entry(form_wrap, "your@email.com")

        # ── Password with live checker ──────────────────────
        _field_label(form_wrap, "PASSWORD")
        self._pass_entry = ctk.CTkEntry(
            form_wrap,
            placeholder_text="Min. 8 characters",
            font=FONT_INPUT,
            fg_color=C_INPUT_BG,
            border_color=C_INPUT_BORDER, border_width=1,
            text_color=C_TEXT_DARK,
            placeholder_text_color=C_TEXT_LIGHT,
            height=42, corner_radius=8, show="●",
        )
        self._pass_entry.pack(fill="x", pady=(0, 8))
        self._pass_entry.bind("<KeyRelease>", self._on_password_type)

        # Focus ring
        self._pass_entry.bind("<FocusIn>",  lambda e: self._pass_entry.configure(border_color=C_INPUT_FOCUS))
        self._pass_entry.bind("<FocusOut>", lambda e: self._pass_entry.configure(border_color=C_INPUT_BORDER))

        # ── Inline password requirements (live) ─────────────
        req_box = ctk.CTkFrame(
            form_wrap, fg_color="#F8FAFF", corner_radius=8,
            border_width=1, border_color=C_INPUT_BORDER
        )
        req_box.pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(
            req_box, text="Password must contain:",
            font=(FONT_PRIMARY, 10, "bold"),
            text_color=C_TEXT_MID, fg_color="transparent"
        ).pack(anchor="w", padx=14, pady=(10, 4))

        self._req_labels = {}
        for key, text, _ in PASSWORD_RULES:
            row = ctk.CTkFrame(req_box, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=2)
            icon_lbl = ctk.CTkLabel(
                row, text="○", font=FONT_REQ,
                text_color=C_TEXT_LIGHT, fg_color="transparent", width=16
            )
            icon_lbl.pack(side="left", padx=(0, 6))
            text_lbl = ctk.CTkLabel(
                row, text=text, font=FONT_REQ,
                text_color=C_TEXT_LIGHT, fg_color="transparent", anchor="w"
            )
            text_lbl.pack(side="left", fill="x")
            self._req_labels[key] = (icon_lbl, text_lbl)

        ctk.CTkFrame(req_box, height=8, fg_color="transparent").pack()

        # ── Confirm password ────────────────────────────────
        _field_label(form_wrap, "CONFIRM PASSWORD")
        self._confirm_entry = _make_entry(form_wrap, "Repeat your password", show="●")

        # Show passwords toggle
        show_row = ctk.CTkFrame(form_wrap, fg_color="transparent")
        show_row.pack(fill="x", pady=(0, 16))
        self._show_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            show_row, text="Show Passwords",
            variable=self._show_var, command=self._toggle_passwords,
            font=FONT_SMALL, text_color=C_TEXT_MID,
            fg_color=C_ACCENT, hover_color=C_ACCENT_HOVER,
            checkmark_color=C_WHITE, border_color=C_INPUT_BORDER
        ).pack(side="left")

        # Status label
        self._status_label = ctk.CTkLabel(
            form_wrap, text="", font=FONT_SMALL,
            text_color=C_TEXT_MID, fg_color="transparent"
        )
        self._status_label.pack(fill="x", pady=(0, 8))

        self._submit_btn = _primary_btn(form_wrap, "Create Account", self._on_submit)
        self._submit_btn.pack(fill="x", pady=(0, 10))
        _outline_btn(form_wrap, "← Back to Login", self._app.show_login).pack(fill="x")

    def _on_password_type(self, event=None):
        password = self._pass_entry.get()
        for key, _, rule_fn in PASSWORD_RULES:
            icon_lbl, text_lbl = self._req_labels[key]
            if rule_fn(password):
                icon_lbl.configure(text="✓", text_color=C_SUCCESS)
                text_lbl.configure(text_color=C_SUCCESS)
            else:
                icon_lbl.configure(text="○", text_color=C_TEXT_LIGHT)
                text_lbl.configure(text_color=C_TEXT_LIGHT)

    def _toggle_passwords(self):
        char = "" if self._show_var.get() else "●"
        self._pass_entry.configure(show=char)
        self._confirm_entry.configure(show=char)

    def _on_submit(self):
        username = self._uname_entry.get().strip()
        email    = self._email_entry.get().strip()
        password = self._pass_entry.get().strip()
        confirm  = self._confirm_entry.get().strip()

        errors = validate_registration(username, email, password, confirm)
        if errors:
            messagebox.showerror("Validation Error",
                                 "Please fix the following:\n\n" +
                                 "\n".join(f"  • {e}" for e in errors))
            return

        dup_user, dup_user_msg = check_duplicate_username(username)
        if dup_user:
            messagebox.showerror("Username Taken", dup_user_msg)
            return

        dup_email, dup_email_msg = check_duplicate_email(email)
        if dup_email:
            messagebox.showerror("Email Exists", dup_email_msg)
            return

        self._submit_btn.configure(state="disabled", text="Sending code...")
        self._status_label.configure(
            text="Sending verification code to your email...",
            text_color=C_ACCENT
        )

        pending_data = {"username": username, "email": email, "password": password}

        def bg_task():
            success, msg, otp_code = register_user(username, email, password)
            if not success:
                self.after(0, lambda: self._on_register_fail(msg))
                return
            email_success, email_msg = send_verification_email(email, otp_code)
            self.after(0, lambda: self._on_email_sent(
                email_success, email_msg, pending_data, otp_code))

        threading.Thread(target=bg_task, daemon=True).start()

    def _on_register_fail(self, message: str):
        self._submit_btn.configure(state="normal", text="Create Account")
        self._status_label.configure(text=message, text_color=C_ERROR_RED)
        messagebox.showerror("Registration Error", message)

    def _on_email_sent(self, success, message, pending_data, otp_code=None):
        self._submit_btn.configure(state="normal", text="Create Account")
        if success:
            self._status_label.configure(text="")
            self._app.show_verification(pending_data)
        else:
            self._status_label.configure(
                text="Offline Mode: Verification email bypassed.",
                text_color=C_WARN
            )
            messagebox.showinfo(
                "Offline Mode",
                f"Could not connect to SMTP server.\n"
                f"Your offline verification code is: {otp_code}\n\n"
                f"Use this code to pass verification without internet."
            )
            self._app.show_verification(pending_data)


# ──────────────────────────────────────────────────────────────
# VERIFICATION PAGE
# ──────────────────────────────────────────────────────────────

class VerificationPage(ctk.CTkFrame):
    def __init__(self, parent, app, pending_data: dict):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self._app = app
        self._pending = pending_data
        self._resend_tracker = ResendTracker()
        self._resend_tracker.record_resend()
        self._attempt_tracker = VerificationAttemptTracker()
        self._cooldown_job = None
        self._build()
        self._start_cooldown_timer()

    def _build(self):
        make_left_panel(self).pack(side="left", fill="y")

        right = ctk.CTkFrame(self, fg_color=C_WHITE, corner_radius=0)
        right.pack(side="left", fill="both", expand=True)

        form_wrap = ctk.CTkFrame(right, fg_color="transparent")
        form_wrap.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.72)

        # Header
        ctk.CTkLabel(
            form_wrap, text="Verify your email", font=FONT_HEADING,
            text_color=C_TEXT_DARK, fg_color="transparent", anchor="w"
        ).pack(fill="x")
        masked_email = self._mask_email(self._pending["email"])
        ctk.CTkLabel(
            form_wrap,
            text="We've sent a verification code to:",
            font=FONT_SUBHEAD, text_color=C_TEXT_MID,
            fg_color="transparent", anchor="w"
        ).pack(fill="x", pady=(4, 2))
        ctk.CTkLabel(
            form_wrap, text=masked_email,
            font=(FONT_PRIMARY, 13, "bold"), text_color=C_PANEL_LEFT,
            fg_color="transparent", anchor="w"
        ).pack(fill="x", pady=(0, 24))

        # OTP input card
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

        self._otp_entry = ctk.CTkEntry(
            otp_inner,
            placeholder_text="000000",
            font=("Courier New", 32, "bold"), justify="center",
            fg_color=C_WHITE, border_color=C_INPUT_BORDER, border_width=1,
            text_color=C_PANEL_LEFT, placeholder_text_color="#C5CAE9",
            height=60, width=280, corner_radius=8
        )
        self._otp_entry.pack(pady=(0, 8))
        self._otp_entry.bind("<FocusIn>",
            lambda e: self._otp_entry.configure(border_color=C_INPUT_FOCUS))
        self._otp_entry.bind("<FocusOut>",
            lambda e: self._otp_entry.configure(border_color=C_INPUT_BORDER))

        from core.email_config import OTP_EXPIRY_MINUTES
        ctk.CTkLabel(
            otp_inner, text=f"Code expires in {OTP_EXPIRY_MINUTES} minutes",
            font=(FONT_PRIMARY, 10), text_color=C_TEXT_LIGHT, fg_color="transparent"
        ).pack()

        # Status
        self._status_label = ctk.CTkLabel(
            form_wrap, text="", font=(FONT_PRIMARY, 11),
            text_color=C_TEXT_MID, fg_color="transparent"
        )
        self._status_label.pack(fill="x", pady=(0, 12))

        # Verify button
        self._verify_btn = _primary_btn(
            form_wrap, "✓  Verify & Create Account", self._on_verify
        )
        self._verify_btn.pack(fill="x", pady=(0, 10))

        # Resend row
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

        _outline_btn(
            form_wrap, "← Back to Registration", self._on_back
        ).pack(fill="x")

    def _mask_email(self, email: str) -> str:
        try:
            local, domain = email.split("@")
            masked = local[0] + "***" + (local[-1] if len(local) > 2 else "")
            return f"{masked}@{domain}"
        except Exception:
            return email

    def _on_verify(self):
        entered_code = self._otp_entry.get().strip()
        if not entered_code:
            self._status_label.configure(
                text="Please enter the verification code.", text_color=C_WARN)
            return
        if len(entered_code) != 6 or not entered_code.isdigit():
            self._status_label.configure(
                text="Code must be exactly 6 digits.", text_color=C_WARN)
            return

        can_try, reason = self._attempt_tracker.can_attempt()
        if not can_try:
            self._status_label.configure(text=reason, text_color=C_ERROR_RED)
            self._verify_btn.configure(state="disabled")
            messagebox.showerror("Verification Locked", reason)
            self._on_back()
            return

        self._verify_btn.configure(state="disabled", text="Verifying code...")
        self._status_label.configure(text="Verifying code...", text_color=C_ACCENT)

        def run_verify():
            result_ok, msg = verify_user(self._pending["email"], entered_code)
            self.after(0, lambda: self._on_verify_result(result_ok, msg))

        threading.Thread(target=run_verify, daemon=True).start()

    def _on_verify_result(self, success, msg):
        if success:
            self._status_label.configure(
                text="Code verified! Account created successfully.",
                text_color=C_SUCCESS)
            messagebox.showinfo("Success",
                                "Account verified! You can now log in.")
            self._app.show_login()
        else:
            self._verify_btn.configure(
                state="normal", text="✓  Verify & Create Account")
            self._attempt_tracker.record_attempt()
            remaining = self._attempt_tracker.attempts_remaining
            self._status_label.configure(
                text=f"{msg} ({remaining} attempts left)",
                text_color=C_ERROR_RED)
            self._otp_entry.delete(0, "end")

    def _on_resend(self):
        can_resend, reason = self._resend_tracker.can_resend()
        if not can_resend:
            self._status_label.configure(text=reason, text_color=C_WARN)
            return
        self._resend_btn.configure(state="disabled")
        self._status_label.configure(text="Sending new code...", text_color=C_ACCENT)

        def resend_task():
            success, msg, new_code = resend_verification_code(self._pending["email"])
            if not success:
                self.after(0, lambda: self._on_resend_complete(False, msg, None))
                return
            email_ok, email_msg = send_verification_email(
                self._pending["email"], new_code)
            self.after(0, lambda: self._on_resend_complete(email_ok, email_msg, new_code))

        threading.Thread(target=resend_task, daemon=True).start()

    def _on_resend_complete(self, success, message, new_code=None):
        if success:
            self._resend_tracker.record_resend()
            from core.email_config import OTP_MAX_RESENDS
            count = self._resend_tracker.resend_count
            self._status_label.configure(
                text=f"New code sent! ({count}/{OTP_MAX_RESENDS} resends used)",
                text_color=C_SUCCESS)
            self._otp_entry.delete(0, "end")
            self._start_cooldown_timer()
        else:
            if new_code:
                self._resend_tracker.record_resend()
                from core.email_config import OTP_MAX_RESENDS
                count = self._resend_tracker.resend_count
                self._status_label.configure(
                    text=f"Offline Mode: ({count}/{OTP_MAX_RESENDS} resends used)",
                    text_color=C_WARN)
                self._otp_entry.delete(0, "end")
                self._start_cooldown_timer()
                messagebox.showinfo(
                    "Offline Mode",
                    f"Could not connect to SMTP.\n"
                    f"New offline code: {new_code}")
            else:
                self._status_label.configure(text=message, text_color=C_ERROR_RED)
                self._resend_btn.configure(state="normal")

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

    def _on_back(self):
        if self._cooldown_job:
            self.after_cancel(self._cooldown_job)
        self._app.show_register()

    def destroy(self):
        if self._cooldown_job:
            self.after_cancel(self._cooldown_job)
        super().destroy()
