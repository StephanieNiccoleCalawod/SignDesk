"""
reset_password_window.py - Reset Password UI
Step 3 of the password reset flow: new password entry with strength indicator.
Matches the existing RegisterPage password section style.
"""

import customtkinter as ctk
import threading
from tkinter import messagebox

from core.theme import *
from core.ui_helpers import make_left_panel
from modules.auth.service import validate_password
from modules.auth.otp_manager import update_password


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
# RESET PASSWORD PAGE
# ──────────────────────────────────────────────────────────────

class ResetPasswordPage(ctk.CTkFrame):
    def __init__(self, parent, app, email: str):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self._app = app
        self._email = email
        self._build()

    def _build(self):
        # ── Left brand panel ───────────────────────────────
        make_left_panel(self).pack(side="left", fill="y")

        # ── Right content area ─────────────────────────────
        right = ctk.CTkScrollableFrame(self, fg_color=C_WHITE, corner_radius=0)
        right.pack(side="left", fill="both", expand=True)

        form_wrap = ctk.CTkFrame(right, fg_color="transparent")
        form_wrap.pack(padx=60, pady=40, fill="both", expand=True)

        # ── Heading ────────────────────────────────────────
        ctk.CTkLabel(
            form_wrap, text="Create new password",
            font=(FONT_PRIMARY, 24, "bold"),
            text_color=C_TEXT_DARK, fg_color="transparent", anchor="w"
        ).pack(fill="x")
        ctk.CTkLabel(
            form_wrap,
            text="Your new password must meet the requirements below",
            font=(FONT_PRIMARY, 12),
            text_color=C_TEXT_MID, fg_color="transparent", anchor="w"
        ).pack(fill="x", pady=(4, 28))

        # ── New password field with show/hide ──────────────
        ctk.CTkLabel(
            form_wrap, text="NEW PASSWORD",
            font=(FONT_PRIMARY, 10, "bold"),
            text_color=C_TEXT_LIGHT, fg_color="transparent", anchor="w"
        ).pack(fill="x", pady=(0, 6))

        pw_frame = ctk.CTkFrame(form_wrap, fg_color="transparent")
        pw_frame.pack(fill="x", pady=(0, 8))

        self._pass_entry = ctk.CTkEntry(
            pw_frame,
            placeholder_text="Min. 8 characters",
            font=FONT_INPUT,
            fg_color=C_INPUT_BG,
            border_color=C_INPUT_BORDER, border_width=1,
            text_color=C_TEXT_DARK,
            placeholder_text_color=C_TEXT_LIGHT,
            height=42, corner_radius=8, show="●",
        )
        self._pass_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._pass_entry.bind("<KeyRelease>", self._on_password_type)
        self._pass_entry.bind("<FocusIn>",
            lambda e: self._pass_entry.configure(border_color=C_INPUT_FOCUS))
        self._pass_entry.bind("<FocusOut>",
            lambda e: self._pass_entry.configure(border_color=C_INPUT_BORDER))

        self._show_pass = False
        self._pass_toggle_btn = ctk.CTkButton(
            pw_frame, text="👁",
            font=("Segoe UI Emoji", 14),
            fg_color=C_INPUT_BG, hover_color=C_INPUT_BORDER,
            text_color=C_TEXT_MID,
            width=42, height=42, corner_radius=8,
            command=self._toggle_new_password
        )
        self._pass_toggle_btn.pack(side="right")

        # ── Password strength indicator ────────────────────
        # Progress bar showing overall strength
        self._strength_frame = ctk.CTkFrame(form_wrap, fg_color="transparent")
        self._strength_frame.pack(fill="x", pady=(0, 4))

        self._strength_bar = ctk.CTkProgressBar(
            self._strength_frame,
            height=6, corner_radius=3,
            fg_color=C_INPUT_BORDER,
            progress_color=C_TEXT_LIGHT,
        )
        self._strength_bar.pack(fill="x")
        self._strength_bar.set(0)

        self._strength_label = ctk.CTkLabel(
            self._strength_frame, text="",
            font=(FONT_PRIMARY, 10), text_color=C_TEXT_LIGHT,
            fg_color="transparent", anchor="e"
        )
        self._strength_label.pack(fill="x")

        # ── Password requirements checklist ────────────────
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

        # ── Confirm password field with show/hide ──────────
        ctk.CTkLabel(
            form_wrap, text="CONFIRM PASSWORD",
            font=(FONT_PRIMARY, 10, "bold"),
            text_color=C_TEXT_LIGHT, fg_color="transparent", anchor="w"
        ).pack(fill="x", pady=(0, 6))

        cf_frame = ctk.CTkFrame(form_wrap, fg_color="transparent")
        cf_frame.pack(fill="x", pady=(0, 14))

        self._confirm_entry = ctk.CTkEntry(
            cf_frame,
            placeholder_text="Repeat your new password",
            font=FONT_INPUT,
            fg_color=C_INPUT_BG,
            border_color=C_INPUT_BORDER, border_width=1,
            text_color=C_TEXT_DARK,
            placeholder_text_color=C_TEXT_LIGHT,
            height=42, corner_radius=8, show="●",
        )
        self._confirm_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._confirm_entry.bind("<FocusIn>",
            lambda e: self._confirm_entry.configure(border_color=C_INPUT_FOCUS))
        self._confirm_entry.bind("<FocusOut>",
            lambda e: self._confirm_entry.configure(border_color=C_INPUT_BORDER))

        self._show_confirm = False
        self._confirm_toggle_btn = ctk.CTkButton(
            cf_frame, text="👁",
            font=("Segoe UI Emoji", 14),
            fg_color=C_INPUT_BG, hover_color=C_INPUT_BORDER,
            text_color=C_TEXT_MID,
            width=42, height=42, corner_radius=8,
            command=self._toggle_confirm_password
        )
        self._confirm_toggle_btn.pack(side="right")

        # ── Status label ───────────────────────────────────
        self._status_label = ctk.CTkLabel(
            form_wrap, text="", font=(FONT_PRIMARY, 11),
            text_color=C_TEXT_MID, fg_color="transparent"
        )
        self._status_label.pack(fill="x", pady=(0, 12))

        # ── Update Password button ─────────────────────────
        self._update_btn = _primary_btn(
            form_wrap, "Update Password", self._on_update
        )
        self._update_btn.pack(fill="x", pady=(0, 10))

    # ── Show/hide toggles ──────────────────────────────────

    def _toggle_new_password(self):
        self._show_pass = not self._show_pass
        self._pass_entry.configure(show="" if self._show_pass else "●")
        self._pass_toggle_btn.configure(
            text="🙈" if self._show_pass else "👁"
        )

    def _toggle_confirm_password(self):
        self._show_confirm = not self._show_confirm
        self._confirm_entry.configure(show="" if self._show_confirm else "●")
        self._confirm_toggle_btn.configure(
            text="🙈" if self._show_confirm else "👁"
        )

    # ── Live password strength checker ─────────────────────

    def _on_password_type(self, event=None):
        password = self._pass_entry.get()
        passed = 0
        total = len(PASSWORD_RULES)

        for key, _, rule_fn in PASSWORD_RULES:
            icon_lbl, text_lbl = self._req_labels[key]
            if rule_fn(password):
                icon_lbl.configure(text="✓", text_color=C_SUCCESS)
                text_lbl.configure(text_color=C_SUCCESS)
                passed += 1
            else:
                icon_lbl.configure(text="○", text_color=C_TEXT_LIGHT)
                text_lbl.configure(text_color=C_TEXT_LIGHT)

        # Update strength bar and label
        ratio = passed / total if total > 0 else 0
        self._strength_bar.set(ratio)

        if password == "":
            self._strength_bar.configure(progress_color=C_TEXT_LIGHT)
            self._strength_label.configure(text="", text_color=C_TEXT_LIGHT)
        elif passed <= 2:
            self._strength_bar.configure(progress_color=C_ERROR_RED)
            self._strength_label.configure(text="Weak", text_color=C_ERROR_RED)
        elif passed <= 3:
            self._strength_bar.configure(progress_color=C_WARN)
            self._strength_label.configure(text="Fair", text_color=C_WARN)
        elif passed <= 4:
            self._strength_bar.configure(progress_color=C_ACCENT)
            self._strength_label.configure(text="Good", text_color=C_ACCENT)
        else:
            self._strength_bar.configure(progress_color=C_SUCCESS)
            self._strength_label.configure(text="Strong", text_color=C_SUCCESS)

    # ── Update password flow ───────────────────────────────

    def _on_update(self):
        password = self._pass_entry.get().strip()
        confirm = self._confirm_entry.get().strip()

        if not password or not confirm:
            self._status_label.configure(
                text="Please fill in both password fields.", text_color=C_WARN
            )
            return

        # Validate password strength
        errors = validate_password(password)
        if errors:
            self._status_label.configure(
                text="Password does not meet requirements.",
                text_color=C_ERROR_RED
            )
            return

        # Check passwords match
        if password != confirm:
            self._status_label.configure(
                text="Passwords do not match.", text_color=C_ERROR_RED
            )
            return

        # Disable button while updating
        self._update_btn.configure(state="disabled", text="Updating...")
        self._status_label.configure(
            text="Updating your password...", text_color=C_ACCENT
        )

        def bg_task():
            ok, msg = update_password(self._email, password)
            self.after(0, lambda: self._on_update_result(ok, msg))

        threading.Thread(target=bg_task, daemon=True).start()

    def _on_update_result(self, success: bool, msg: str):
        if success:
            self._status_label.configure(text="", text_color=C_TEXT_MID)

            # Look up the username so the user knows what to type at login
            try:
                from core.database import get_connection
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT username FROM users WHERE email = ?",
                    (self._email,)
                )
                row = cursor.fetchone()
                conn.close()
                username_hint = row[0] if row else None
            except Exception:
                username_hint = None

            if username_hint:
                messagebox.showinfo(
                    "Password Updated",
                    f"Your password has been updated successfully.\n\n"
                    f"Sign in with your username: {username_hint}"
                )
            else:
                messagebox.showinfo(
                    "Password Updated",
                    "Your password has been updated successfully.\n"
                    "You can now log in with your new password."
                )
            self._app.show_login()
        else:
            self._update_btn.configure(state="normal", text="Update Password")
            self._status_label.configure(text=msg, text_color=C_ERROR_RED)

