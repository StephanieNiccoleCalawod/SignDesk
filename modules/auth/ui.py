"""
ui.py - Authentication UI Pages
Contains LoginPage, RegisterPage, and VerificationPage.
"""

import customtkinter as ctk
from tkinter import messagebox
import threading

from core.theme import *
from core.ui_helpers import make_left_panel, make_field, make_primary_button, make_ghost_button
from core.email_service import (
    generate_otp, get_otp_expiry, is_otp_expired,
    send_verification_email, ResendTracker
)
from core.email_config import OTP_RESEND_COOLDOWN
from modules.auth.service import (
    login_user, register_user, validate_password,
    validate_registration, check_duplicate_username, check_duplicate_email
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
        make_left_panel(self).pack(side="left", fill="y")

        right = ctk.CTkFrame(self, fg_color=C_WHITE, corner_radius=0)
        right.pack(side="left", fill="both", expand=True)

        form_wrap = ctk.CTkFrame(right, fg_color="transparent")
        form_wrap.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.78)

        ctk.CTkLabel(form_wrap, text="Welcome back", font=FONT_HEADING,
                     text_color=C_TEXT_DARK, fg_color="transparent", anchor="w").pack(fill="x")
        ctk.CTkLabel(form_wrap, text="Sign in to continue to SignDesk", font=FONT_SUBHEAD,
                     text_color=C_TEXT_MID, fg_color="transparent", anchor="w").pack(fill="x", pady=(4, 24))

        self._user_entry = make_field(form_wrap, "Username", "Enter your username")
        self._pass_entry = make_field(form_wrap, "Password", "Enter your password", show="●")

        show_row = ctk.CTkFrame(form_wrap, fg_color="transparent")
        show_row.pack(fill="x", pady=(0, 20))
        self._show_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(show_row, text="Show Password", variable=self._show_var,
                        command=self._toggle_password, font=FONT_SMALL, text_color=C_TEXT_MID,
                        fg_color=C_ACCENT, hover_color=C_ACCENT_HOVER,
                        checkmark_color=C_WHITE, border_color=C_INPUT_BORDER).pack(side="left")

        make_primary_button(form_wrap, "Sign In", self._on_login).pack(fill="x", pady=(0, 10))
        make_ghost_button(form_wrap, "Create Account", self._app.show_register).pack(fill="x")

        ctk.CTkLabel(form_wrap, text="Don't have an account? Click Create Account above.",
                     font=FONT_SMALL, text_color=C_TEXT_LIGHT,
                     fg_color="transparent").pack(pady=(16, 0))

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
    """
    Registration form with email field.
    Does NOT create the account — it validates, sends OTP, and
    navigates to the VerificationPage.
    """

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

        ctk.CTkLabel(form_wrap, text="Create your account", font=FONT_HEADING,
                     text_color=C_TEXT_DARK, fg_color="transparent", anchor="w").pack(fill="x")
        ctk.CTkLabel(form_wrap, text="Join SignDesk — it's free", font=FONT_SUBHEAD,
                     text_color=C_TEXT_MID, fg_color="transparent", anchor="w").pack(fill="x", pady=(4, 20))

        # Input Fields: Username, Email, Password, Confirm Password
        self._uname_entry = make_field(form_wrap, "Username", "Choose a username")
        self._email_entry = make_field(form_wrap, "Email Address", "your@email.com")

        # Password field with live checker
        ctk.CTkLabel(form_wrap, text="Password", font=FONT_LABEL,
                     text_color=C_TEXT_DARK, fg_color="transparent", anchor="w").pack(fill="x", pady=(0, 4))
        self._pass_entry = ctk.CTkEntry(
            form_wrap, placeholder_text="Min. 8 characters", font=FONT_INPUT,
            fg_color=C_INPUT_BG, border_color=C_INPUT_BORDER, border_width=1,
            text_color=C_TEXT_DARK, placeholder_text_color=C_TEXT_LIGHT,
            height=42, corner_radius=8, show="●",
        )
        self._pass_entry.pack(fill="x", pady=(0, 6))
        self._pass_entry.bind("<KeyRelease>", self._on_password_type)

        # Password Requirements Checklist
        req_box = ctk.CTkFrame(form_wrap, fg_color="#F8FAFF", corner_radius=8,
                               border_width=1, border_color=C_INPUT_BORDER)
        req_box.pack(fill="x", pady=(0, 16))

        header_row = ctk.CTkFrame(req_box, fg_color="transparent")
        header_row.pack(fill="x", padx=12, pady=(8, 4))
        ctk.CTkLabel(header_row, text="Password must contain:",
                     font=("Trebuchet MS", 10, "bold"),
                     text_color=C_TEXT_MID, fg_color="transparent").pack(side="left")

        self._req_labels = {}
        for key, text, _ in PASSWORD_RULES:
            row = ctk.CTkFrame(req_box, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=2)
            icon_lbl = ctk.CTkLabel(row, text="○", font=FONT_REQ,
                                    text_color=C_TEXT_LIGHT, fg_color="transparent", width=16)
            icon_lbl.pack(side="left", padx=(0, 6))
            text_lbl = ctk.CTkLabel(row, text=text, font=FONT_REQ,
                                    text_color=C_TEXT_LIGHT, fg_color="transparent", anchor="w")
            text_lbl.pack(side="left", fill="x")
            self._req_labels[key] = (icon_lbl, text_lbl)

        ctk.CTkFrame(req_box, height=6, fg_color="transparent").pack()

        # Confirm password
        self._confirm_entry = make_field(form_wrap, "Confirm Password", "Repeat your password", show="●")

        # Show passwords
        show_row = ctk.CTkFrame(form_wrap, fg_color="transparent")
        show_row.pack(fill="x", pady=(0, 16))
        self._show_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(show_row, text="Show Passwords", variable=self._show_var,
                        command=self._toggle_passwords, font=FONT_SMALL, text_color=C_TEXT_MID,
                        fg_color=C_ACCENT, hover_color=C_ACCENT_HOVER,
                        checkmark_color=C_WHITE, border_color=C_INPUT_BORDER).pack(side="left")

        # Status label for showing progress
        self._status_label = ctk.CTkLabel(form_wrap, text="", font=FONT_SMALL,
                                           text_color=C_TEXT_MID, fg_color="transparent")
        self._status_label.pack(fill="x", pady=(0, 8))

        # Buttons
        self._submit_btn = make_primary_button(form_wrap, "Create Account", self._on_submit)
        self._submit_btn.pack(fill="x", pady=(0, 10))
        make_ghost_button(form_wrap, "← Back to Login", self._app.show_login).pack(fill="x")

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
        """
        Step 1: Validate all fields
        Step 2: Check for duplicates
        Step 3: Generate OTP and send email
        Step 4: Navigate to VerificationPage (account NOT created yet)
        """
        username = self._uname_entry.get().strip()
        email    = self._email_entry.get().strip()
        password = self._pass_entry.get().strip()
        confirm  = self._confirm_entry.get().strip()

        # Step 1: Validate all input
        errors = validate_registration(username, email, password, confirm)
        if errors:
            error_text = "\n".join(f"  • {e}" for e in errors)
            messagebox.showerror("Validation Error", f"Please fix the following:\n\n{error_text}")
            return

        # Step 2: Check for duplicate username
        dup_user, dup_user_msg = check_duplicate_username(username)
        if dup_user:
            messagebox.showerror("Username Taken", dup_user_msg)
            return

        # Step 3: Check for duplicate email
        dup_email, dup_email_msg = check_duplicate_email(email)
        if dup_email:
            messagebox.showerror("Email Exists", dup_email_msg)
            return

        # Step 4: Generate OTP and send email (in a background thread to avoid UI freeze)
        self._submit_btn.configure(state="disabled", text="Sending code...")
        self._status_label.configure(text="📧  Sending verification code to your email...",
                                      text_color=C_ACCENT)

        otp_code = generate_otp()
        otp_expiry = get_otp_expiry()

        # Store pending registration data
        pending_data = {
            "username": username,
            "email": email,
            "password": password,
            "otp_code": otp_code,
            "otp_expiry": otp_expiry,
        }

        # Send email in background thread
        def send_email_task():
            success, msg = send_verification_email(email, otp_code)

            # Update UI from main thread
            self.after(0, lambda: self._on_email_sent(success, msg, pending_data))

        thread = threading.Thread(target=send_email_task, daemon=True)
        thread.start()

    def _on_email_sent(self, success: bool, message: str, pending_data: dict):
        """Callback after email sending attempt completes."""
        self._submit_btn.configure(state="normal", text="Create Account")

        if success:
            self._status_label.configure(text="")

            # FALLBACK MODE: email not configured — show code on screen
            if message == "FALLBACK":
                messagebox.showinfo(
                    "Verification Code",
                    f"Your verification code is:\n\n"
                    f"   {pending_data['otp_code']}\n\n"
                    f"Please enter this code on the next screen."
                )

            # Navigate to verification page — account NOT created yet
            self._app.show_verification(pending_data)
        else:
            self._status_label.configure(text="", text_color=C_ERROR_RED)
            messagebox.showerror("Email Error", message)


# ──────────────────────────────────────────────────────────────
# VERIFICATION PAGE
# ──────────────────────────────────────────────────────────────

class VerificationPage(ctk.CTkFrame):
    """
    OTP verification step. The account is only created after
    the user enters the correct verification code.
    """

    def __init__(self, parent, app, pending_data: dict):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self._app = app
        self._pending = pending_data
        self._resend_tracker = ResendTracker()
        self._resend_tracker.record_resend()  # Count the initial send
        self._cooldown_job = None
        self._build()
        self._start_cooldown_timer()

    def _build(self):
        make_left_panel(self).pack(side="left", fill="y")

        right = ctk.CTkFrame(self, fg_color=C_WHITE, corner_radius=0)
        right.pack(side="left", fill="both", expand=True)

        form_wrap = ctk.CTkFrame(right, fg_color="transparent")
        form_wrap.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.78)

        # Header
        ctk.CTkLabel(form_wrap, text="Verify your email", font=FONT_HEADING,
                     text_color=C_TEXT_DARK, fg_color="transparent", anchor="w").pack(fill="x")

        masked_email = self._mask_email(self._pending["email"])
        ctk.CTkLabel(form_wrap, text=f"We've sent a verification code to:",
                     font=FONT_SUBHEAD, text_color=C_TEXT_MID,
                     fg_color="transparent", anchor="w").pack(fill="x", pady=(4, 2))
        ctk.CTkLabel(form_wrap, text=masked_email,
                     font=("Trebuchet MS", 13, "bold"), text_color=C_PANEL_LEFT,
                     fg_color="transparent", anchor="w").pack(fill="x", pady=(0, 24))

        # OTP input area
        otp_frame = ctk.CTkFrame(form_wrap, fg_color="#F8FAFF", corner_radius=12,
                                  border_width=1, border_color=C_INPUT_BORDER)
        otp_frame.pack(fill="x", pady=(0, 16))

        otp_inner = ctk.CTkFrame(otp_frame, fg_color="transparent")
        otp_inner.pack(padx=24, pady=24)

        ctk.CTkLabel(otp_inner, text="Enter the 6-digit verification code",
                     font=("Trebuchet MS", 11, "bold"), text_color=C_TEXT_MID,
                     fg_color="transparent").pack(pady=(0, 12))

        self._otp_entry = ctk.CTkEntry(
            otp_inner, placeholder_text="000000",
            font=("Courier New", 32, "bold"), justify="center",
            fg_color=C_WHITE, border_color=C_INPUT_BORDER, border_width=2,
            text_color=C_PANEL_LEFT, placeholder_text_color="#C5CAE9",
            height=60, width=280, corner_radius=10
        )
        self._otp_entry.pack(pady=(0, 8))

        # Expiry info
        from core.email_config import OTP_EXPIRY_MINUTES
        ctk.CTkLabel(otp_inner, text=f"Code expires in {OTP_EXPIRY_MINUTES} minutes",
                     font=("Trebuchet MS", 10), text_color=C_TEXT_LIGHT,
                     fg_color="transparent").pack()

        # Status message
        self._status_label = ctk.CTkLabel(
            form_wrap, text="", font=("Trebuchet MS", 11),
            text_color=C_TEXT_MID, fg_color="transparent"
        )
        self._status_label.pack(fill="x", pady=(0, 12))

        # Verify button
        self._verify_btn = make_primary_button(form_wrap, "✓  Verify & Create Account", self._on_verify)
        self._verify_btn.pack(fill="x", pady=(0, 10))

        # Resend row
        resend_row = ctk.CTkFrame(form_wrap, fg_color="transparent")
        resend_row.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(resend_row, text="Didn't receive the code?", font=FONT_SMALL,
                     text_color=C_TEXT_LIGHT, fg_color="transparent").pack(side="left")

        self._resend_btn = ctk.CTkButton(
            resend_row, text="Resend Code", command=self._on_resend,
            font=("Trebuchet MS", 11, "bold"), fg_color="transparent",
            hover_color=C_INPUT_BG, text_color=C_ACCENT,
            width=100, height=28, corner_radius=4, state="disabled"
        )
        self._resend_btn.pack(side="left", padx=(8, 0))

        self._cooldown_label = ctk.CTkLabel(
            resend_row, text="", font=("Trebuchet MS", 10),
            text_color=C_TEXT_LIGHT, fg_color="transparent"
        )
        self._cooldown_label.pack(side="left", padx=(6, 0))

        # Back button
        make_ghost_button(form_wrap, "← Back to Registration", self._on_back).pack(fill="x")

    def _mask_email(self, email: str) -> str:
        """Masks the email for display (e.g., j***n@gmail.com)."""
        try:
            local, domain = email.split("@")
            if len(local) <= 2:
                masked = local[0] + "***"
            else:
                masked = local[0] + "***" + local[-1]
            return f"{masked}@{domain}"
        except Exception:
            return email

    # ── VERIFICATION ─────────────────────────────────────────

    def _on_verify(self):
        """Validates the entered OTP code and creates the account if correct."""
        entered_code = self._otp_entry.get().strip()

        if not entered_code:
            self._status_label.configure(text="⚠  Please enter the verification code.",
                                          text_color=C_WARN)
            return

        if len(entered_code) != 6 or not entered_code.isdigit():
            self._status_label.configure(text="⚠  Code must be exactly 6 digits.",
                                          text_color=C_WARN)
            return

        # Check expiry
        if is_otp_expired(self._pending["otp_expiry"]):
            self._status_label.configure(
                text="❌  Verification code has expired. Please request a new one.",
                text_color=C_ERROR_RED
            )
            return

        # Check code
        if entered_code != self._pending["otp_code"]:
            self._status_label.configure(
                text="❌  Incorrect verification code. Please try again.",
                text_color=C_ERROR_RED
            )
            self._otp_entry.delete(0, "end")
            return

        # ── CODE IS CORRECT — Create the account now ──
        self._verify_btn.configure(state="disabled", text="Creating account...")
        self._status_label.configure(text="✅  Code verified! Creating your account...",
                                      text_color=C_SUCCESS)

        result = register_user(
            self._pending["username"],
            self._pending["email"],
            self._pending["password"]
        )

        if result.startswith("ERROR:"):
            self._verify_btn.configure(state="normal", text="✓  Verify & Create Account")
            messagebox.showerror("Registration Failed", result.replace("ERROR: ", ""))
        else:
            messagebox.showinfo("Account Created", result)
            self._app.show_login()

    # ── RESEND ───────────────────────────────────────────────

    def _on_resend(self):
        """Resends the verification code to the same email."""
        can_resend, reason = self._resend_tracker.can_resend()
        if not can_resend:
            self._status_label.configure(text=f"⚠  {reason}", text_color=C_WARN)
            return

        # Generate new OTP
        new_otp = generate_otp()
        new_expiry = get_otp_expiry()
        self._pending["otp_code"] = new_otp
        self._pending["otp_expiry"] = new_expiry

        self._resend_btn.configure(state="disabled")
        self._status_label.configure(text="📧  Sending new code...", text_color=C_ACCENT)

        # Send in background thread
        def resend_task():
            success, msg = send_verification_email(self._pending["email"], new_otp)
            self.after(0, lambda: self._on_resend_complete(success, msg))

        thread = threading.Thread(target=resend_task, daemon=True)
        thread.start()

    def _on_resend_complete(self, success: bool, message: str):
        """Callback after resend attempt."""
        if success:
            self._resend_tracker.record_resend()
            count = self._resend_tracker.resend_count
            from core.email_config import OTP_MAX_RESENDS
            self._status_label.configure(
                text=f"✅  New code sent! ({count}/{OTP_MAX_RESENDS} resends used)",
                text_color=C_SUCCESS
            )
            self._otp_entry.delete(0, "end")
            self._start_cooldown_timer()
        else:
            self._status_label.configure(text=f"❌  {message}", text_color=C_ERROR_RED)
            self._resend_btn.configure(state="normal")

    # ── COOLDOWN TIMER ───────────────────────────────────────

    def _start_cooldown_timer(self):
        """Starts the visual countdown timer for the resend button."""
        self._resend_btn.configure(state="disabled")
        self._update_cooldown()

    def _update_cooldown(self):
        """Updates the cooldown label every second."""
        remaining = self._resend_tracker.cooldown_remaining

        if remaining > 0:
            self._cooldown_label.configure(text=f"({remaining}s)")
            self._resend_btn.configure(state="disabled")
            self._cooldown_job = self.after(1000, self._update_cooldown)
        else:
            self._cooldown_label.configure(text="")
            # Check if max resends reached
            can_resend, _ = self._resend_tracker.can_resend()
            if can_resend:
                self._resend_btn.configure(state="normal")
            else:
                self._resend_btn.configure(state="disabled")
                self._cooldown_label.configure(text="(limit reached)")

    # ── NAVIGATION ───────────────────────────────────────────

    def _on_back(self):
        """Go back to the registration form."""
        if self._cooldown_job:
            self.after_cancel(self._cooldown_job)
        self._app.show_register()

    def destroy(self):
        if self._cooldown_job:
            self.after_cancel(self._cooldown_job)
        super().destroy()
