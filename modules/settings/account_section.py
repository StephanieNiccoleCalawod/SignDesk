"""
SignDesk — Account Settings UI (original ttkbootstrap version)
Kept as reference — the project uses CustomTkinter, so this UI is
integrated via the existing _build_account() in settings/ui.py
which calls the backend functions from account_backend.py.

For standalone testing:
    pip install ttkbootstrap bcrypt
    python -m modules.settings.account_section
"""

import tkinter as tk

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
except ImportError:
    import tkinter.ttk as ttk

from modules.settings.account_backend import (
    update_display_name,
    update_email,
    update_password,
)


def get_initials(name: str) -> str:
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper() if name else "?"


# ── Account Section ─────────────────────────────────────────────────────────────

class AccountSection(ttk.Frame):
    """
    Drop-in Account settings panel (ttkbootstrap version).

    Parameters
    ----------
    parent  : widget  — your content frame
    session : Session — the Session instance from account_backend
    """

    def __init__(self, parent, session, **kwargs):
        super().__init__(parent, **kwargs)
        self.session = session
        self._email_edit_open = False
        self._name_edit_open  = False
        self._feedback_var    = tk.StringVar()

        self.columnconfigure(0, weight=1)
        self._build()

    # ── Build ────────────────────────────────────────────────────────────────────

    def _build(self):
        # Section label
        ttk.Label(
            self, text="ACCOUNT",
            font=("Segoe UI", 9, "bold"), foreground="#888888",
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(20, 8))

        # Profile card
        profile_card = ttk.Frame(self, padding=20)
        profile_card.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 16))
        profile_card.columnconfigure(1, weight=1)

        self._avatar_canvas = tk.Canvas(
            profile_card, width=56, height=56,
            bg="#1c1c2e", highlightthickness=0,
        )
        self._avatar_canvas.grid(row=0, column=0, rowspan=2, padx=(0, 16))

        self._name_var  = tk.StringVar(value=self.session.user["name"])
        self._email_var = tk.StringVar(value=self.session.user["email"])

        ttk.Label(profile_card, textvariable=self._name_var,
                  font=("Segoe UI", 13, "bold"), foreground="#ffffff",
                  ).grid(row=0, column=1, sticky="sw")
        ttk.Label(profile_card, textvariable=self._email_var,
                  font=("Segoe UI", 10), foreground="#aaaaaa",
                  ).grid(row=1, column=1, sticky="nw")

        self._draw_avatar()

        # Settings card
        self._card = ttk.Frame(self, padding=(20, 12))
        self._card.grid(row=2, column=0, sticky="ew", padx=24)
        self._card.columnconfigure(0, weight=1)

        self._email_frame = ttk.Frame(self._card)
        self._email_frame.grid(row=0, column=0, sticky="ew", pady=6)
        self._email_frame.columnconfigure(0, weight=1)

        ttk.Separator(self._card).grid(row=1, column=0, sticky="ew", pady=4)

        self._name_frame = ttk.Frame(self._card)
        self._name_frame.grid(row=2, column=0, sticky="ew", pady=6)
        self._name_frame.columnconfigure(0, weight=1)

        ttk.Separator(self._card).grid(row=3, column=0, sticky="ew", pady=4)

        self._password_frame = ttk.Frame(self._card)
        self._password_frame.grid(row=4, column=0, sticky="ew", pady=6)
        self._password_frame.columnconfigure(0, weight=1)

        self._render_email_row()
        self._render_name_row()
        self._render_password_row()

        # Feedback + Save
        self._feedback_label = ttk.Label(
            self, textvariable=self._feedback_var,
            font=("Segoe UI", 10), foreground="#a78bfa",
        )
        self._feedback_label.grid(row=3, column=0, sticky="e", padx=24, pady=(10, 0))

        ttk.Button(
            self, text="Save changes",
            command=self._handle_save_all,
        ).grid(row=4, column=0, sticky="e", padx=24, pady=(10, 24))

    # ── Avatar ───────────────────────────────────────────────────────────────────

    def _draw_avatar(self):
        self._avatar_canvas.delete("all")
        self._avatar_canvas.create_oval(2, 2, 54, 54, fill="#6C63FF", outline="")
        self._avatar_canvas.create_text(
            28, 28,
            text=get_initials(self.session.user["name"]),
            fill="white",
            font=("Segoe UI", 16, "bold"),
        )

    # ── Email row ────────────────────────────────────────────────────────────────

    def _render_email_row(self):
        for w in self._email_frame.winfo_children():
            w.destroy()

        left = ttk.Frame(self._email_frame)
        left.grid(row=0, column=0, sticky="w")
        ttk.Label(left, text="Change email address",
                  font=("Segoe UI", 11), foreground="#ffffff",
                  ).pack(anchor="w")
        ttk.Label(left, text="Update your registered email",
                  font=("Segoe UI", 9), foreground="#888888",
                  ).pack(anchor="w")

        label = "Cancel" if self._email_edit_open else "Edit"
        cmd   = self._close_email_edit if self._email_edit_open else self._open_email_edit
        ttk.Button(self._email_frame, text=label, width=8,
                   command=cmd).grid(row=0, column=1, padx=(12, 0))

        if self._email_edit_open:
            wrap = ttk.Frame(self._email_frame)
            wrap.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
            wrap.columnconfigure(0, weight=1)

            ttk.Label(wrap, text="Current password (required to change email)",
                      font=("Segoe UI", 9), foreground="#888888",
                      ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
            self._email_pw_entry = ttk.Entry(wrap, show="●", font=("Segoe UI", 11))
            self._email_pw_entry.grid(row=1, column=0, sticky="ew", ipady=5, pady=(0, 6))

            ttk.Label(wrap, text="New email address",
                      font=("Segoe UI", 9), foreground="#888888",
                      ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 4))
            self._email_entry = ttk.Entry(wrap, font=("Segoe UI", 11))
            self._email_entry.insert(0, self.session.user["email"])
            self._email_entry.grid(row=3, column=0, sticky="ew", ipady=5)
            self._email_entry.bind("<Return>", lambda e: self._save_email())
            self._email_entry.focus_set()

            ttk.Button(wrap, text="Save", width=8,
                       command=self._save_email).grid(row=3, column=1, padx=(8, 0))

    def _open_email_edit(self):
        self._email_edit_open = True
        self._render_email_row()

    def _close_email_edit(self):
        self._email_edit_open = False
        self._render_email_row()

    def _save_email(self):
        new_email  = self._email_entry.get().strip()
        current_pw = self._email_pw_entry.get()

        if not current_pw:
            self._show_feedback("⚠  Enter your current password to verify.", error=True)
            return

        success, msg = update_email(self.session.user_id, new_email, current_pw)
        if not success:
            self._show_feedback(f"⚠  {msg}", error=True)
            return

        self.session.refresh()
        self._email_var.set(self.session.user["email"])
        self._close_email_edit()
        self._show_feedback(f"✓  {msg}")

    # ── Name row ─────────────────────────────────────────────────────────────────

    def _render_name_row(self):
        for w in self._name_frame.winfo_children():
            w.destroy()

        left = ttk.Frame(self._name_frame)
        left.grid(row=0, column=0, sticky="w")
        ttk.Label(left, text="Display name",
                  font=("Segoe UI", 11), foreground="#ffffff",
                  ).pack(anchor="w")
        ttk.Label(left, text="How your name appears in the app",
                  font=("Segoe UI", 9), foreground="#888888",
                  ).pack(anchor="w")

        label = "Cancel" if self._name_edit_open else "Edit"
        cmd   = self._close_name_edit if self._name_edit_open else self._open_name_edit
        ttk.Button(self._name_frame, text=label, width=8,
                   command=cmd).grid(row=0, column=1, padx=(12, 0))

        if self._name_edit_open:
            wrap = ttk.Frame(self._name_frame)
            wrap.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
            wrap.columnconfigure(0, weight=1)

            self._name_entry = ttk.Entry(wrap, font=("Segoe UI", 11))
            self._name_entry.insert(0, self.session.user["name"])
            self._name_entry.select_range(0, "end")
            self._name_entry.grid(row=0, column=0, sticky="ew", ipady=5)
            self._name_entry.bind("<Return>", lambda e: self._save_name())
            self._name_entry.focus_set()

            ttk.Button(wrap, text="Save", width=8,
                       command=self._save_name).grid(row=0, column=1, padx=(8, 0))

    def _open_name_edit(self):
        self._name_edit_open = True
        self._render_name_row()

    def _close_name_edit(self):
        self._name_edit_open = False
        self._render_name_row()

    def _save_name(self):
        new_name = self._name_entry.get().strip()
        success, msg = update_display_name(self.session.user_id, new_name)
        if not success:
            self._show_feedback(f"⚠  {msg}", error=True)
            return

        self.session.refresh()
        self._name_var.set(self.session.user["name"])
        self._draw_avatar()
        self._close_name_edit()
        self._show_feedback(f"✓  {msg}")

    # ── Password row ──────────────────────────────────────────────────────────────

    def _render_password_row(self):
        for w in self._password_frame.winfo_children():
            w.destroy()

        left = ttk.Frame(self._password_frame)
        left.grid(row=0, column=0, sticky="w")
        ttk.Label(left, text="Change password",
                  font=("Segoe UI", 11), foreground="#ffffff",
                  ).pack(anchor="w")
        ttk.Label(left, text="Keep your account secure",
                  font=("Segoe UI", 9), foreground="#888888",
                  ).pack(anchor="w")

        ttk.Button(self._password_frame, text="Change", width=8,
                   command=self._open_password_dialog,
                   ).grid(row=0, column=1, padx=(12, 0))

    def _open_password_dialog(self):
        PasswordDialog(self, self.session, self._show_feedback)

    # ── Save all ─────────────────────────────────────────────────────────────────

    def _handle_save_all(self):
        if self._email_edit_open:
            self._save_email()
        if self._name_edit_open:
            self._save_name()
        if not self._email_edit_open and not self._name_edit_open:
            self._show_feedback("✓  All changes saved.")

    # ── Feedback ──────────────────────────────────────────────────────────────────

    def _show_feedback(self, msg: str, error: bool = False):
        color = "#f87171" if error else "#a78bfa"
        self._feedback_label.configure(foreground=color)
        self._feedback_var.set(msg)
        self.after(3500, lambda: self._feedback_var.set(""))


# ── Password Change Dialog ────────────────────────────────────────────────────────

class PasswordDialog(tk.Toplevel):
    def __init__(self, parent, session, feedback_fn):
        super().__init__(parent)
        self.session     = session
        self.feedback_fn = feedback_fn

        self.title("Change Password")
        self.resizable(False, False)
        self.configure(bg="#1c1c2e")
        self.grab_set()
        self._build()
        self._center()

    def _center(self):
        self.update_idletasks()
        x = self.master.winfo_rootx() + (self.master.winfo_width()  - self.winfo_width())  // 2
        y = self.master.winfo_rooty() + (self.master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build(self):
        ttk.Label(self, text="Change Password",
                  font=("Segoe UI", 13, "bold"),
                  foreground="#ffffff", background="#1c1c2e",
                  ).grid(row=0, column=0, columnspan=2, sticky="w", padx=24, pady=(20, 4))

        fields = [
            ("Current password",     "current"),
            ("New password",          "new"),
            ("Confirm new password", "confirm"),
        ]
        self._entries = {}
        for i, (label, key) in enumerate(fields, start=1):
            ttk.Label(self, text=label, foreground="#aaaaaa",
                      background="#1c1c2e",
                      ).grid(row=i*2-1, column=0, columnspan=2, sticky="w", padx=24, pady=(10, 2))
            e = ttk.Entry(self, show="●", font=("Segoe UI", 11), width=34)
            e.grid(row=i*2, column=0, columnspan=2, sticky="ew", padx=24, ipady=5)
            self._entries[key] = e

        ttk.Label(self,
                  text="Min 8 characters · 1 uppercase · 1 number",
                  font=("Segoe UI", 8), foreground="#666666",
                  background="#1c1c2e",
                  ).grid(row=7, column=0, columnspan=2, sticky="w", padx=24, pady=(4, 0))

        self._err_var = tk.StringVar()
        ttk.Label(self, textvariable=self._err_var,
                  foreground="#f87171", background="#1c1c2e",
                  font=("Segoe UI", 9),
                  ).grid(row=8, column=0, columnspan=2, padx=24, pady=(6, 0))

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=9, column=0, columnspan=2, sticky="e", padx=24, pady=(14, 20))
        ttk.Button(btn_frame, text="Cancel",
                   command=self.destroy).pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="Save password",
                   command=self._save).pack(side="left")

    def _save(self):
        current = self._entries["current"].get()
        new_pw  = self._entries["new"].get()
        confirm = self._entries["confirm"].get()

        success, msg = update_password(
            self.session.user_id, current, new_pw, confirm
        )
        if not success:
            self._err_var.set(f"⚠  {msg}")
            return

        self.destroy()
        self.feedback_fn(f"✓  {msg}")
