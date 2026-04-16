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
    verify_user, resend_verification_code, create_verified_user
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
# LOGIN PAGE
# ──────────────────────────────────────────────────────────────

class LoginPage(ctk.CTkFrame):
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
        # using a fixed-width container placed at center
        form_wrap = ctk.CTkFrame(right, fg_color="transparent", width=380)
        form_wrap.place(relx=0.5, rely=0.5, anchor="center")

        # ── Heading ────────────────────────────────────────
        ctk.CTkLabel(
            form_wrap, text="Welcome back",
            font=(FONT_PRIMARY, 24, "bold"),
            text_color=C_TEXT_DARK, fg_color="transparent", anchor="w"
        ).pack(fill="x")
        ctk.CTkLabel(
            form_wrap, text="Sign in to continue to SignDesk",
            font=(FONT_PRIMARY, 12),
            text_color=C_TEXT_MID, fg_color="transparent", anchor="w"
        ).pack(fill="x", pady=(4, 28))

        # ── Username field ─────────────────────────────────
        ctk.CTkLabel(
            form_wrap, text="USERNAME",
            font=(FONT_PRIMARY, 10, "bold"),
            text_color=C_TEXT_LIGHT, fg_color="transparent", anchor="w"
        ).pack(fill="x", pady=(0, 6))

        self._user_entry = _make_entry(form_wrap, "Enter your username")

        # ── Password label row (label left + forgot right) ─
        pw_header = ctk.CTkFrame(form_wrap, fg_color="transparent")
        pw_header.pack(fill="x", pady=(4, 6))

        ctk.CTkLabel(
            pw_header, text="PASSWORD",
            font=(FONT_PRIMARY, 10, "bold"),
            text_color=C_TEXT_LIGHT, fg_color="transparent", anchor="w"
        ).pack(side="left")

        ctk.CTkButton(
            pw_header, text="Forgot password?",
            font=(FONT_PRIMARY, 10), fg_color="transparent",
            hover_color=C_INPUT_BG, text_color=C_ACCENT,
            width=0, height=18, corner_radius=4,
            command=lambda: self._app.show_forgot_password()
        ).pack(side="right")

        self._pass_entry = _make_entry(form_wrap, "Enter your password", show="●")

        # ── Show password toggle ───────────────────────────
        show_row = ctk.CTkFrame(form_wrap, fg_color="transparent")
        show_row.pack(fill="x", pady=(0, 24))
        self._show_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            show_row, text="Show Password",
            variable=self._show_var, command=self._toggle_password,
            font=(FONT_PRIMARY, 11), text_color=C_TEXT_MID,
            fg_color=C_ACCENT, hover_color=C_ACCENT_HOVER,
            checkmark_color=C_WHITE, border_color=C_INPUT_BORDER,
            checkbox_width=18, checkbox_height=18, corner_radius=4,
        ).pack(side="left")

        # ── Buttons ────────────────────────────────────────
        _primary_btn(form_wrap, "Sign In", self._on_login).pack(
            fill="x", pady=(0, 6))

        _divider(form_wrap)

        _outline_btn(form_wrap, "Create Account",
                     self._app.show_register).pack(fill="x")

        ctk.CTkLabel(
            form_wrap,
            text="Don't have an account? Click Create Account above.",
            font=(FONT_PRIMARY, 10), text_color=C_TEXT_LIGHT,
            fg_color="transparent"
        ).pack(pady=(16, 0))

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
        self._show_pass = False
        self._show_confirm = False
        self._build()

    # ── Accent-bar label helper ─────────────────────────────
    @staticmethod
    def _accent_label(parent, text):
        """Field label with a small purple accent bar on the left."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, 4))

        # Purple accent bar
        bar = ctk.CTkFrame(row, width=3, height=16,
                           fg_color="#6C63FF", corner_radius=1)
        bar.pack_propagate(False)
        bar.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            row, text=text,
            font=(FONT_PRIMARY, 10, "bold"),
            text_color=C_TEXT_LIGHT, fg_color="transparent", anchor="w"
        ).pack(side="left")

    # ── Password entry with eye toggle ──────────────────────
    def _make_password_field(self, parent, placeholder, toggle_attr):
        """Creates a password CTkEntry with an inline eye toggle button.
        Returns the entry widget.
        """
        wrap = ctk.CTkFrame(parent, fg_color=C_INPUT_BG, corner_radius=8,
                            border_width=1, border_color=C_INPUT_BORDER)
        wrap.pack(fill="x", pady=(0, 8))

        entry = ctk.CTkEntry(
            wrap,
            placeholder_text=placeholder,
            font=FONT_INPUT,
            fg_color="transparent",
            border_width=0,
            text_color=C_TEXT_DARK,
            placeholder_text_color=C_TEXT_LIGHT,
            height=42, corner_radius=8, show="●",
        )
        entry.pack(side="left", fill="x", expand=True, padx=(4, 0))

        eye_btn = ctk.CTkButton(
            wrap, text="👁",
            font=("Segoe UI Emoji", 14),
            fg_color="transparent", hover_color=C_INPUT_BG,
            text_color=C_TEXT_LIGHT,
            width=36, height=36, corner_radius=4,
            command=lambda: self._toggle_eye(entry, eye_btn, toggle_attr)
        )
        eye_btn.pack(side="right", padx=(0, 4))

        # Focus ring on the wrapper
        def _on_focus_in(e):
            wrap.configure(border_color=C_INPUT_FOCUS)
        def _on_focus_out(e):
            wrap.configure(border_color=C_INPUT_BORDER)
        entry.bind("<FocusIn>", _on_focus_in)
        entry.bind("<FocusOut>", _on_focus_out)

        return entry

    def _toggle_eye(self, entry, btn, attr):
        """Toggle password visibility for a specific field."""
        current = getattr(self, attr)
        new_state = not current
        setattr(self, attr, new_state)
        entry.configure(show="" if new_state else "●")
        btn.configure(text="🔒" if new_state else "👁")

    # ──────────────────────────────────────────────────────────
    # BUILD
    # ──────────────────────────────────────────────────────────

    def _build(self):
        make_left_panel(self).pack(side="left", fill="y")

        right = ctk.CTkScrollableFrame(self, fg_color=C_CARD_BG, corner_radius=0)
        right.pack(side="left", fill="both", expand=True)

        form_wrap = ctk.CTkFrame(right, fg_color="transparent")
        form_wrap.pack(padx=60, pady=30, fill="both", expand=True)

        _section_label(form_wrap, "Create your account", "Join SignDesk — it's free")

        # ── Username ───────────────────────────────────────
        self._accent_label(form_wrap, "USERNAME")
        self._uname_entry = _make_entry(form_wrap, "Choose a username")

        # ── Email ──────────────────────────────────────────
        self._accent_label(form_wrap, "EMAIL ADDRESS")
        self._email_entry = _make_entry(form_wrap, "your@email.com")

        # ── Password with eye toggle ───────────────────────
        self._accent_label(form_wrap, "PASSWORD")
        self._pass_entry = self._make_password_field(
            form_wrap, "Min. 8 characters", "_show_pass"
        )
        self._pass_entry.bind("<KeyRelease>", self._on_password_type)

        # ── Password requirements (dark card) ──────────────
        req_box = ctk.CTkFrame(
            form_wrap, fg_color="#1E1E2E", corner_radius=10,
            border_width=1, border_color="#3A3A5C"
        )
        req_box.pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(
            req_box, text="Password must contain:",
            font=(FONT_PRIMARY, 10, "bold"),
            text_color="#FFFFFF", fg_color="transparent"
        ).pack(anchor="w", padx=14, pady=(10, 4))

        self._req_labels = {}
        for key, text, _ in PASSWORD_RULES:
            row = ctk.CTkFrame(req_box, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=2)
            icon_lbl = ctk.CTkLabel(
                row, text="○", font=FONT_REQ,
                text_color="#888888", fg_color="transparent", width=16
            )
            icon_lbl.pack(side="left", padx=(0, 6))
            text_lbl = ctk.CTkLabel(
                row, text=text, font=FONT_REQ,
                text_color="#888888", fg_color="transparent", anchor="w"
            )
            text_lbl.pack(side="left", fill="x")
            self._req_labels[key] = (icon_lbl, text_lbl)

        ctk.CTkFrame(req_box, height=8, fg_color="transparent").pack()

        # ── Confirm password with eye toggle ───────────────
        self._accent_label(form_wrap, "CONFIRM PASSWORD")
        self._confirm_entry = self._make_password_field(
            form_wrap, "Repeat your password", "_show_confirm"
        )
        self._confirm_entry.bind("<KeyRelease>", self._on_confirm_type)

        # ── Confirm password match feedback ────────────────
        self._match_label = ctk.CTkLabel(
            form_wrap, text="", font=(FONT_PRIMARY, 10),
            text_color=C_TEXT_MID, fg_color="transparent", anchor="w"
        )
        self._match_label.pack(fill="x", pady=(0, 12))

        # Status label
        self._status_label = ctk.CTkLabel(
            form_wrap, text="", font=FONT_SMALL,
            text_color=C_TEXT_MID, fg_color="transparent"
        )
        self._status_label.pack(fill="x", pady=(0, 8))

        self._submit_btn = _primary_btn(form_wrap, "Create Account", self._on_submit)
        self._submit_btn.pack(fill="x", pady=(0, 10))
        _outline_btn(form_wrap, "← Back to Login", self._app.show_login).pack(fill="x")

    # ──────────────────────────────────────────────────────────
    # Live validation callbacks
    # ──────────────────────────────────────────────────────────

    def _on_password_type(self, event=None):
        """Update password requirements checklist in real time."""
        password = self._pass_entry.get()
        for key, _, rule_fn in PASSWORD_RULES:
            icon_lbl, text_lbl = self._req_labels[key]
            if rule_fn(password):
                icon_lbl.configure(text="✓", text_color="#4CAF50")
                text_lbl.configure(text_color="#4CAF50")
            else:
                icon_lbl.configure(text="○", text_color="#888888")
                text_lbl.configure(text_color="#888888")
        # Also update confirm match if user already typed there
        self._on_confirm_type()

    def _on_confirm_type(self, event=None):
        """Show inline match feedback for confirm password."""
        confirm = self._confirm_entry.get()
        if not confirm:
            self._match_label.configure(text="")
            return
        password = self._pass_entry.get()
        if confirm == password:
            self._match_label.configure(
                text="✅  Passwords match", text_color="#4CAF50")
        else:
            self._match_label.configure(
                text="❌  Passwords do not match", text_color="#FF4C4C")

    # ──────────────────────────────────────────────────────────
    # Submit + Navigation (unchanged logic)
    # ──────────────────────────────────────────────────────────

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

        # Generate OTP in-memory — NO database insert yet.
        # The user record is only created after successful verification.
        otp_code = generate_otp()
        otp_expiry = get_otp_expiry()

        pending_data = {
            "username": username,
            "email": email,
            "password": password,
            "otp_code": otp_code,
            "otp_expiry": otp_expiry,
        }

        def bg_task():
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
    """
    Email verification screen with:
    • 6-digit OTP entry
    • Resend with per-resend cooldown (60 s) and max-resend limit (5)
    • 10-minute lockout countdown after hitting 5/5, persisted to JSON
    • Warning card + spam-folder tip + self-service help popup
    """

    # 10-minute lockout in seconds
    _LOCKOUT_SECONDS = 10 * 60

    def __init__(self, parent, app, pending_data: dict):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self._app = app
        self._pending = pending_data
        self._resend_tracker = ResendTracker()
        self._resend_tracker.record_resend()  # initial send already happened
        self._attempt_tracker = VerificationAttemptTracker()

        # Timer state
        self._cooldown_job = None          # per-resend 60 s cooldown
        self._lockout_job = None           # 10-minute lockout countdown
        self._lockout_remaining = 0        # seconds left in lockout

        self._build()

        # ── Resume a persisted lockout if the app was restarted ────
        from core.cooldown_persistence import load_cooldown
        persisted = load_cooldown(self._pending["email"])
        if persisted > 0:
            self._lockout_remaining = persisted
            # Force tracker to the limit so UI is consistent
            from core.email_config import OTP_MAX_RESENDS
            while self._resend_tracker.resend_count < OTP_MAX_RESENDS:
                self._resend_tracker.record_resend()
            self._show_lockout_ui()
            self._tick_lockout()
        else:
            # Normal per-resend cooldown
            self._start_cooldown_timer()

    # ──────────────────────────────────────────────────────────
    # BUILD
    # ──────────────────────────────────────────────────────────

    def _build(self):
        make_left_panel(self).pack(side="left", fill="y")

        right = ctk.CTkFrame(self, fg_color=C_WHITE, corner_radius=0)
        right.pack(side="left", fill="both", expand=True)

        self._form_wrap = ctk.CTkFrame(right, fg_color="transparent")
        self._form_wrap.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.72)

        fw = self._form_wrap  # shorthand

        # ── Header ─────────────────────────────────────────
        ctk.CTkLabel(
            fw, text="Verify your email", font=FONT_HEADING,
            text_color=C_TEXT_DARK, fg_color="transparent", anchor="w"
        ).pack(fill="x")

        masked_email = self._mask_email(self._pending["email"])
        ctk.CTkLabel(
            fw, text="We've sent a verification code to:",
            font=FONT_SUBHEAD, text_color=C_TEXT_MID,
            fg_color="transparent", anchor="w"
        ).pack(fill="x", pady=(4, 2))
        ctk.CTkLabel(
            fw, text=masked_email,
            font=(FONT_PRIMARY, 13, "bold"), text_color=C_PANEL_LEFT,
            fg_color="transparent", anchor="w"
        ).pack(fill="x", pady=(0, 24))

        # ── OTP input card ─────────────────────────────────
        otp_card = ctk.CTkFrame(
            fw, fg_color=C_INPUT_BG, corner_radius=10,
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

        # Bind <KeyRelease> to enable/disable Verify based on entry content
        self._otp_entry.bind("<KeyRelease>", self._on_otp_key)

        from core.email_config import OTP_EXPIRY_MINUTES
        ctk.CTkLabel(
            otp_inner, text=f"Code expires in {OTP_EXPIRY_MINUTES} minutes",
            font=(FONT_PRIMARY, 10), text_color=C_TEXT_LIGHT,
            fg_color="transparent"
        ).pack()

        # ── Status label ───────────────────────────────────
        self._status_label = ctk.CTkLabel(
            fw, text="", font=(FONT_PRIMARY, 11),
            text_color=C_TEXT_MID, fg_color="transparent"
        )
        self._status_label.pack(fill="x", pady=(0, 12))

        # ── Warning card (hidden by default) ───────────────
        self._warning_card = ctk.CTkFrame(
            fw, fg_color="#1E1E2E", corner_radius=10,
            border_width=1, border_color="#3A3A4A"
        )
        # NOT packed yet — shown only after 5/5

        warn_inner = ctk.CTkFrame(self._warning_card, fg_color="transparent")
        warn_inner.pack(padx=18, pady=16)

        ctk.CTkLabel(
            warn_inner,
            text="⚠  You've reached the resend limit.\n"
                 "     Please wait before retrying.",
            font=(FONT_PRIMARY, 11, "bold"),
            text_color="#FFA500",  # orange warning
            fg_color="transparent", justify="left", anchor="w"
        ).pack(fill="x", pady=(0, 10))

        self._lockout_timer_label = ctk.CTkLabel(
            warn_inner,
            text="Too many attempts. Try again in 10:00",
            font=(FONT_PRIMARY, 12, "bold"),
            text_color="#FFFFFF",
            fg_color="transparent", anchor="w"
        )
        self._lockout_timer_label.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            warn_inner,
            text="📧  Can't find the email?\n"
                 "      Check your spam or junk folder.",
            font=(FONT_PRIMARY, 10),
            text_color="#AAAAAA",
            fg_color="transparent", justify="left", anchor="w"
        ).pack(fill="x")

        # ── Verify button (starts disabled) ────────────────
        self._verify_btn = _primary_btn(
            fw, "✓  Verify & Create Account", self._on_verify
        )
        self._verify_btn.configure(state="disabled")
        self._verify_btn.pack(fill="x", pady=(0, 10))

        # ── Resend row ─────────────────────────────────────
        resend_row = ctk.CTkFrame(fw, fg_color="transparent")
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

        # ── "Having trouble? View Help" link (hidden by default)
        self._help_link = ctk.CTkButton(
            fw, text="Having trouble? View Help",
            command=self._show_help_popup,
            font=(FONT_PRIMARY, 10),
            fg_color="transparent", hover_color=C_INPUT_BG,
            text_color=C_TEXT_LIGHT,
            width=0, height=24, corner_radius=4,
        )
        # NOT packed yet — shown only after 5/5

        # ── Back to Registration ───────────────────────────
        _outline_btn(
            fw, "← Back to Registration", self._on_back
        ).pack(fill="x")

    # ──────────────────────────────────────────────────────────
    # OTP entry → Verify button state
    # ──────────────────────────────────────────────────────────

    def _on_otp_key(self, event=None):
        """Enable Verify only when entry contains exactly 6 digits."""
        value = self._otp_entry.get().strip()
        if len(value) == 6 and value.isdigit():
            self._verify_btn.configure(state="normal")
        else:
            self._verify_btn.configure(state="disabled")

    # ──────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────

    def _mask_email(self, email: str) -> str:
        try:
            local, domain = email.split("@")
            masked = local[0] + "***" + (local[-1] if len(local) > 2 else "")
            return f"{masked}@{domain}"
        except Exception:
            return email

    # ──────────────────────────────────────────────────────────
    # Verify flow
    # ──────────────────────────────────────────────────────────

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

        # ── In-memory OTP verification ─────────────────────
        stored_code = self._pending.get("otp_code", "")
        stored_expiry = self._pending.get("otp_expiry")

        if stored_expiry and is_otp_expired(stored_expiry):
            self._status_label.configure(
                text="Verification code has expired. Please resend.",
                text_color=C_ERROR_RED)
            self._attempt_tracker.record_attempt()
            self._otp_entry.delete(0, "end")
            self._on_otp_key()
            return

        if entered_code != stored_code:
            self._attempt_tracker.record_attempt()
            remaining = self._attempt_tracker.attempts_remaining
            self._status_label.configure(
                text=f"Incorrect verification code. ({remaining} attempts left)",
                text_color=C_ERROR_RED)
            self._otp_entry.delete(0, "end")
            self._on_otp_key()
            return

        # ── Code matches — now create the user in the DB ───
        self._verify_btn.configure(state="disabled", text="Creating account...")
        self._status_label.configure(text="Creating your account...", text_color=C_ACCENT)

        def run_create():
            ok, msg = create_verified_user(
                self._pending["username"],
                self._pending["email"],
                self._pending["password"]
            )
            self.after(0, lambda: self._on_create_result(ok, msg))

        threading.Thread(target=run_create, daemon=True).start()

    def _on_create_result(self, success, msg):
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
            self._status_label.configure(
                text=msg, text_color=C_ERROR_RED)
            messagebox.showerror("Account Error", msg)

    # ──────────────────────────────────────────────────────────
    # Resend flow (in-memory OTP — no DB)
    # ──────────────────────────────────────────────────────────

    def _on_resend(self):
        can_resend, reason = self._resend_tracker.can_resend()
        if not can_resend:
            self._status_label.configure(text=reason, text_color=C_WARN)
            return
        # Disable immediately to prevent rapid double-clicks
        self._resend_btn.configure(state="disabled")
        self._status_label.configure(text="Sending new code...", text_color=C_ACCENT)

        # Generate a fresh OTP in memory
        new_code = generate_otp()
        new_expiry = get_otp_expiry()
        self._pending["otp_code"] = new_code
        self._pending["otp_expiry"] = new_expiry

        def resend_task():
            email_ok, email_msg = send_verification_email(
                self._pending["email"], new_code)
            self.after(0, lambda: self._on_resend_complete(email_ok, email_msg, new_code))

        threading.Thread(target=resend_task, daemon=True).start()

    def _on_resend_complete(self, success, message, new_code=None):
        from core.email_config import OTP_MAX_RESENDS

        if success:
            self._resend_tracker.record_resend()
            count = self._resend_tracker.resend_count
            self._status_label.configure(
                text=f"New code sent! ({count}/{OTP_MAX_RESENDS} resends used)",
                text_color=C_SUCCESS)
            self._otp_entry.delete(0, "end")
            self._on_otp_key()  # update verify button state

            # Check if limit just reached → start lockout
            if count >= OTP_MAX_RESENDS:
                self._begin_lockout()
            else:
                self._start_cooldown_timer()
        else:
            if new_code:
                self._resend_tracker.record_resend()
                count = self._resend_tracker.resend_count
                self._status_label.configure(
                    text=f"Offline Mode: ({count}/{OTP_MAX_RESENDS} resends used)",
                    text_color=C_WARN)
                self._otp_entry.delete(0, "end")
                self._on_otp_key()

                if count >= OTP_MAX_RESENDS:
                    self._begin_lockout()
                else:
                    self._start_cooldown_timer()

                messagebox.showinfo(
                    "Offline Mode",
                    f"Could not connect to SMTP.\n"
                    f"New offline code: {new_code}")
            else:
                self._status_label.configure(text=message, text_color=C_ERROR_RED)
                self._resend_btn.configure(state="normal")

    # ──────────────────────────────────────────────────────────
    # Per-resend 60 s cooldown (existing behavior)
    # ──────────────────────────────────────────────────────────

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

    # ──────────────────────────────────────────────────────────
    # 10-minute LOCKOUT (after 5/5 resends)
    # ──────────────────────────────────────────────────────────

    def _begin_lockout(self):
        """Start the 10-minute lockout and persist it to JSON."""
        from datetime import datetime, timedelta
        from core.cooldown_persistence import save_cooldown

        self._lockout_remaining = self._LOCKOUT_SECONDS
        expiry = datetime.now() + timedelta(seconds=self._LOCKOUT_SECONDS)
        save_cooldown(self._pending["email"], expiry)

        self._show_lockout_ui()
        self._tick_lockout()

    def _show_lockout_ui(self):
        """Make the warning card and help link visible."""
        self._resend_btn.configure(state="disabled")
        self._cooldown_label.configure(text="")

        # Show the warning card (pack it above the verify button)
        # We need to insert it in the right place in the layout.
        # Pack it before the verify button by using pack with before=
        self._warning_card.pack(
            fill="x", pady=(0, 12),
            before=self._verify_btn
        )

        # Show the help link (pack it before the back button)
        self._help_link.pack(fill="x", pady=(0, 8))
        # Re-pack the back button so help link stays above it
        # (it's already at the bottom, help_link goes just before it)

    def _hide_lockout_ui(self):
        """Hide the warning card and help link."""
        self._warning_card.pack_forget()
        self._help_link.pack_forget()

    def _tick_lockout(self):
        """Countdown tick — called every second via .after()."""
        if self._lockout_remaining <= 0:
            self._on_lockout_expired()
            return

        minutes = self._lockout_remaining // 60
        seconds = self._lockout_remaining % 60
        self._lockout_timer_label.configure(
            text=f"Too many attempts. Try again in {minutes:02d}:{seconds:02d}"
        )

        self._lockout_remaining -= 1
        self._lockout_job = self.after(1000, self._tick_lockout)

    def _on_lockout_expired(self):
        """Called when the 10-minute countdown reaches zero."""
        from core.cooldown_persistence import clear_cooldown

        # Reset tracker so user can resend again
        self._resend_tracker.reset()
        clear_cooldown()

        # Update UI
        self._hide_lockout_ui()
        self._resend_btn.configure(state="normal")
        self._cooldown_label.configure(text="")
        self._status_label.configure(
            text="Cooldown expired. You may resend the code.",
            text_color=C_SUCCESS
        )

    # ──────────────────────────────────────────────────────────
    # Self-service help popup
    # ──────────────────────────────────────────────────────────

    def _show_help_popup(self):
        """Open a CTkToplevel with offline self-service tips."""
        popup = ctk.CTkToplevel(self)
        popup.title("Having trouble verifying?")
        popup.resizable(False, False)
        popup.grab_set()

        # Size and center over the main window
        pw, ph = 420, 340
        popup.geometry(f"{pw}x{ph}")
        popup.after(10, lambda: self._center_popup(popup, pw, ph))

        popup.configure(fg_color="#1E1E2E")

        content = ctk.CTkFrame(popup, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=28, pady=24)

        ctk.CTkLabel(
            content, text="Having trouble verifying?",
            font=(FONT_PRIMARY, 16, "bold"),
            text_color="#FFFFFF", fg_color="transparent", anchor="w"
        ).pack(fill="x", pady=(0, 16))

        tips = [
            "Check your spam or junk folder",
            "Make sure you entered the correct email address",
            "Wait for the 10-minute cooldown to reset, then try again",
            "Click 'Back to Registration' to re-enter your email",
            "Restart the app if the issue persists",
        ]

        for tip in tips:
            row = ctk.CTkFrame(content, fg_color="transparent")
            row.pack(fill="x", pady=4)

            ctk.CTkLabel(
                row, text="•", font=(FONT_PRIMARY, 12, "bold"),
                text_color="#6C63FF", fg_color="transparent", width=16
            ).pack(side="left", padx=(0, 8))

            ctk.CTkLabel(
                row, text=tip,
                font=(FONT_PRIMARY, 11),
                text_color="#CCCCCC", fg_color="transparent",
                anchor="w"
            ).pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            content, text="Close", command=popup.destroy,
            font=FONT_BTN,
            fg_color=C_ACCENT, hover_color=C_ACCENT_HOVER,
            text_color=C_WHITE,
            height=38, corner_radius=19, width=140
        ).pack(pady=(20, 0))

    def _center_popup(self, popup, pw, ph):
        """Center the popup over the main app window."""
        try:
            mx = self.winfo_toplevel().winfo_x()
            my = self.winfo_toplevel().winfo_y()
            mw = self.winfo_toplevel().winfo_width()
            mh = self.winfo_toplevel().winfo_height()
            x = mx + (mw - pw) // 2
            y = my + (mh - ph) // 2
            popup.geometry(f"{pw}x{ph}+{x}+{y}")
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────
    # Back to Registration — full reset
    # ──────────────────────────────────────────────────────────

    def _on_back(self):
        from core.cooldown_persistence import clear_cooldown

        # Cancel active timers
        if self._cooldown_job:
            self.after_cancel(self._cooldown_job)
            self._cooldown_job = None
        if self._lockout_job:
            self.after_cancel(self._lockout_job)
            self._lockout_job = None

        # Reset state
        self._resend_tracker.reset()
        clear_cooldown()

        # Navigate
        self._app.show_register()

    # ──────────────────────────────────────────────────────────
    # Cleanup on destroy
    # ──────────────────────────────────────────────────────────

    def destroy(self):
        if self._cooldown_job:
            self.after_cancel(self._cooldown_job)
        if self._lockout_job:
            self.after_cancel(self._lockout_job)
        super().destroy()
