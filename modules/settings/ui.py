"""
modules/settings/ui.py — Full Settings Page
Two-column layout: sidebar navigation + scrollable content panels.
Translated from React reference into CustomTkinter.
"""

import customtkinter as ctk
from tkinter import messagebox
import os

from core.theme import *
from core.config import config


# ══════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════

SIDEBAR_W   = 220
SECTION_IDS = [
    ("account",       "Account",              "👤"),
    ("appearance",    "Appearance",            "🎨"),
    ("gesture",       "Gesture Recognition",   "🤟"),
    ("speech",        "Speech Output",         "🔊"),
    ("privacy",       "Privacy & Data",        "🔒"),
    ("accessibility", "Accessibility",         "♿"),
    ("webcam",        "Webcam",                "📷"),
    ("about",         "About & Support",       "ℹ️"),
]

# Consistent dark-card colours
_CARD_BG     = COLORS["bg_primary"]
_CARD_BORDER = COLORS["border"]
_ROW_BORDER  = ("#F1F5F9", "#1E1E28")
_ACCENT      = COLORS["accent"]
_ACCENT_HOVER = COLORS["accent_hover"]
_TEXT_PRI    = COLORS["text_primary"]
_TEXT_SEC    = COLORS["text_secondary"]
_TEXT_MUT    = COLORS["text_muted"]
_INPUT_BG    = COLORS["input_bg"]
_SUCCESS     = COLORS["success"]
_ERROR       = COLORS["error"]
_BG          = COLORS["bg_secondary"]


# ══════════════════════════════════════════════════════════════
# MAIN PAGE
# ══════════════════════════════════════════════════════════════

class SettingsPage(ctk.CTkFrame):
    def __init__(self, parent, app, username: str):
        super().__init__(parent, fg_color=_BG, corner_radius=0)
        self._app = app
        self._username = username
        self._active_section = "account"
        self._section_frames = {}
        self._save_labels = {}
        self._save_feedback_job = None
        self._build()

    # ──────────────────────────────────────────────────────
    # TOP-LEVEL LAYOUT
    # ──────────────────────────────────────────────────────

    def _build(self):
        self.grid_columnconfigure(0, weight=0, minsize=SIDEBAR_W)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content_area()
        self._show_section("account")

    # ──────────────────────────────────────────────────────
    # SIDEBAR
    # ──────────────────────────────────────────────────────

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(
            self, width=SIDEBAR_W, fg_color=_CARD_BG,
            corner_radius=0, border_width=0,
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        # Right-side border line
        border_line = ctk.CTkFrame(sidebar, width=1, fg_color=_CARD_BORDER)
        border_line.place(relx=1.0, y=0, relheight=1, anchor="ne")

        # Brand
        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=16, pady=(24, 4))

        brand_row = ctk.CTkFrame(brand, fg_color="transparent")
        brand_row.pack(anchor="w")

        ctk.CTkLabel(
            brand_row, text="🤟",
            font=("Segoe UI Emoji", 20), fg_color="transparent"
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            brand_row, text="SignDesk",
            font=(FONT_PRIMARY, 16, "bold"),
            text_color=_ACCENT, fg_color="transparent"
        ).pack(side="left")

        ctk.CTkLabel(
            brand, text="Settings",
            font=(FONT_PRIMARY, 12), text_color=_TEXT_MUT,
            fg_color="transparent"
        ).pack(anchor="w", pady=(2, 0))

        # Back to Dashboard
        ctk.CTkButton(
            sidebar, text="← Dashboard",
            command=self._on_back,
            font=(FONT_PRIMARY, 11),
            fg_color="transparent", hover_color=_INPUT_BG,
            text_color=_ACCENT, anchor="w",
            height=28, corner_radius=6,
        ).pack(fill="x", padx=16, pady=(12, 0))

        # Nav items
        self._nav_buttons = {}
        nav = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav.pack(fill="x", padx=12, pady=(20, 0))

        for sid, label, icon in SECTION_IDS:
            btn_frame = ctk.CTkFrame(nav, fg_color="transparent",
                                     height=38, corner_radius=8)
            btn_frame.pack(fill="x", pady=1)
            btn_frame.pack_propagate(False)

            inner = ctk.CTkFrame(btn_frame, fg_color="transparent")
            inner.pack(fill="both", expand=True, padx=4)

            # Left accent bar (hidden by default)
            bar = ctk.CTkFrame(inner, width=3, height=20,
                               fg_color="transparent", corner_radius=1)
            bar.pack(side="left", padx=(0, 8), pady=9)

            icon_lbl = ctk.CTkLabel(
                inner, text=icon, font=("Segoe UI Emoji", 14),
                fg_color="transparent", width=24
            )
            icon_lbl.pack(side="left", padx=(0, 8))

            text_lbl = ctk.CTkLabel(
                inner, text=label,
                font=(FONT_PRIMARY, 13),
                text_color=_TEXT_SEC, fg_color="transparent", anchor="w"
            )
            text_lbl.pack(side="left", fill="x")

            self._nav_buttons[sid] = (btn_frame, inner, bar, icon_lbl, text_lbl)

            # Click binding
            for w in (btn_frame, inner, icon_lbl, text_lbl):
                w.configure(cursor="hand2")
                w.bind("<Button-1>", lambda e, s=sid: self._show_section(s))

    # ──────────────────────────────────────────────────────
    # CONTENT AREA
    # ──────────────────────────────────────────────────────

    def _build_content_area(self):
        self._content_outer = ctk.CTkFrame(self, fg_color=_BG, corner_radius=0)
        self._content_outer.grid(row=0, column=1, sticky="nsew")

        # Pre-build every section once — never destroyed, only shown/hidden
        builders = {
            "account":       self._build_account,
            "appearance":    self._build_appearance,
            "gesture":       self._build_gesture,
            "speech":        self._build_speech,
            "privacy":       self._build_privacy,
            "accessibility": self._build_accessibility,
            "webcam":        self._build_webcam,
            "about":         self._build_about,
        }

        for section_id, builder in builders.items():
            scroll = ctk.CTkScrollableFrame(
                self._content_outer, fg_color=_BG, corner_radius=0
            )

            wrap = ctk.CTkFrame(scroll, fg_color=_BG, width=620)
            wrap.pack(padx=24, pady=(24, 8), fill="x", anchor="n")

            builder(wrap)

            if section_id != "about":
                self._build_save_bar(wrap, section_id)

            self._section_frames[section_id] = scroll

    def _show_section(self, section_id: str):
        self._active_section = section_id

        # Update nav highlight
        for sid, (frame, inner, bar, icon_lbl, text_lbl) in self._nav_buttons.items():
            is_active = (sid == section_id)
            frame.configure(fg_color=("#F5F3FF", "#1C1C28") if is_active else "transparent")
            bar.configure(fg_color=_ACCENT if is_active else "transparent")
            text_lbl.configure(
                text_color=_ACCENT if is_active else _TEXT_SEC,
                font=(FONT_PRIMARY, 13, "bold") if is_active else (FONT_PRIMARY, 13)
            )

        # Show selected section, hide all others
        for sid, scroll_frame in self._section_frames.items():
            if sid == section_id:
                scroll_frame.place(x=0, y=0, relwidth=1, relheight=1)
                scroll_frame.lift()
            else:
                scroll_frame.place_forget()

        self._content_outer.update_idletasks()

    # ══════════════════════════════════════════════════════
    # WIDGET HELPERS
    # ══════════════════════════════════════════════════════

    @staticmethod
    def _section_title(parent, text):
        ctk.CTkLabel(
            parent, text=text.upper(),
            font=(FONT_PRIMARY, 11, "bold"),
            text_color=_TEXT_MUT, fg_color="transparent",
            anchor="w"
        ).pack(fill="x", pady=(24, 8), padx=4)

    @staticmethod
    def _card(parent) -> ctk.CTkFrame:
        c = ctk.CTkFrame(
            parent, fg_color=_CARD_BG, corner_radius=14,
            border_width=1, border_color=_CARD_BORDER
        )
        c.pack(fill="x", pady=(0, 20))
        return c

    @staticmethod
    def _row_divider(parent):
        ctk.CTkFrame(parent, height=1, fg_color=_ROW_BORDER).pack(fill="x")

    def _row(self, parent, label, desc=None, danger=False):
        """Standard settings row. Returns a right-side container to pack controls into."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=14)

        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            left, text=label,
            font=(FONT_PRIMARY, 13),
            text_color=_ERROR if danger else _TEXT_PRI,
            fg_color="transparent", anchor="w"
        ).pack(fill="x")

        if desc:
            ctk.CTkLabel(
                left, text=desc,
                font=(FONT_PRIMARY, 11),
                text_color=_TEXT_MUT, fg_color="transparent", anchor="w"
            ).pack(fill="x", pady=(2, 0))

        right = ctk.CTkFrame(row, fg_color="transparent")
        right.pack(side="right")
        return right

    def _toggle_row(self, parent, label, desc, key, disabled=False):
        """Row with a CTkSwitch on the right, bound to a config key."""
        right = self._row(parent, label, desc)

        var = ctk.BooleanVar(value=config.get(key, False))

        def _on_toggle():
            config.set(key, var.get())

        switch = ctk.CTkSwitch(
            right, text="", variable=var,
            onvalue=True, offvalue=False,
            command=_on_toggle,
            switch_width=44, switch_height=22,
            progress_color=_ACCENT,
            button_color=("#FFFFFF", "#FFFFFF"),
            fg_color=("#CBD5E1", "#444458"),
        )
        if disabled:
            switch.configure(state="disabled")
        switch.pack()

        self._row_divider(parent)

    def _select_row(self, parent, label, desc, key, options):
        """Row with a dropdown on the right."""
        right = self._row(parent, label, desc)

        current = config.get(key, options[0][0])
        labels = [o[1] for o in options]
        values = [o[0] for o in options]

        # Find the display label for the current value
        try:
            display = labels[values.index(current)]
        except ValueError:
            display = labels[0]

        menu = ctk.CTkOptionMenu(
            right, values=labels,
            command=lambda chosen: config.set(key, values[labels.index(chosen)]),
            font=(FONT_PRIMARY, 12),
            fg_color=_INPUT_BG, button_color=_ACCENT,
            button_hover_color=_ACCENT_HOVER,
            text_color=_TEXT_PRI,
            dropdown_fg_color=_CARD_BG,
            dropdown_text_color=_TEXT_PRI,
            dropdown_hover_color=_INPUT_BG,
            width=180, height=32, corner_radius=8,
        )
        menu.set(display)
        menu.pack()

        self._row_divider(parent)

    def _slider_row(self, parent, label, desc, key, min_val, max_val, step, fmt_fn):
        """Row with a slider + value display."""
        outer = ctk.CTkFrame(parent, fg_color="transparent")
        outer.pack(fill="x", padx=20, pady=14)

        top = ctk.CTkFrame(outer, fg_color="transparent")
        top.pack(fill="x")

        left = ctk.CTkFrame(top, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            left, text=label,
            font=(FONT_PRIMARY, 13), text_color=_TEXT_PRI,
            fg_color="transparent", anchor="w"
        ).pack(fill="x")

        if desc:
            ctk.CTkLabel(
                left, text=desc,
                font=(FONT_PRIMARY, 11), text_color=_TEXT_MUT,
                fg_color="transparent", anchor="w"
            ).pack(fill="x", pady=(2, 0))

        current_val = config.get(key, min_val)
        val_label = ctk.CTkLabel(
            top, text=fmt_fn(current_val),
            font=(FONT_PRIMARY, 13, "bold"), text_color=_ACCENT,
            fg_color="transparent", width=56, anchor="e"
        )
        val_label.pack(side="right")

        def _on_slide(v):
            # Snap to step
            snapped = round(round(v / step) * step, 4)
            config.set(key, snapped)
            val_label.configure(text=fmt_fn(snapped))

        slider = ctk.CTkSlider(
            outer,
            from_=min_val, to=max_val,
            number_of_steps=int((max_val - min_val) / step),
            command=_on_slide,
            progress_color=_ACCENT,
            button_color=_ACCENT,
            button_hover_color=_ACCENT_HOVER,
            fg_color=("#CBD5E1", "#333344"),
            height=16,
        )
        slider.set(current_val)
        slider.pack(fill="x", pady=(8, 0))

        self._row_divider(parent)

    def _badge(self, parent, text, color="blue"):
        colors = {
            "blue":   (("#EFF6FF", "#1E2A4A"), ("#2563EB", "#60A5FA")),
            "amber":  (("#FFFBEB", "#3A2A0D"), ("#B45309", "#FBBF24")),
            "green":  (("#F0FDF4", "#163325"), ("#15803D", "#22C55E")),
            "purple": (("#F5F3FF", "#2C2245"), ("#7C3AED", "#A78BFA")),
        }
        bg, fg = colors.get(color, colors["blue"])
        lbl = ctk.CTkLabel(
            parent, text=text,
            font=(FONT_PRIMARY, 10, "bold"),
            text_color=fg, fg_color=bg,
            corner_radius=6, height=22,
        )
        lbl.pack(side="left", padx=(0, 8))
        return lbl

    # ══════════════════════════════════════════════════════
    # SECTION: ACCOUNT
    # ══════════════════════════════════════════════════════

    def _build_account(self, parent):
        self._section_title(parent, "Account")
        card = self._card(parent)

        # Load user via account backend
        from modules.settings.account_backend import Session
        self._session = Session()
        self._session.load_by_username(self._username)

        if self._session.is_logged_in:
            self._display_name = self._session.user["name"]
            self._user_email = self._session.user["email"]
        else:
            self._display_name = self._username
            self._user_email = ""

        # ── Avatar + info header ──────────────────────────
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=18)

        initials = self._display_name[0].upper() if self._display_name else "?"

        avatar = ctk.CTkFrame(
            header, width=52, height=52, corner_radius=26,
            fg_color=_ACCENT
        )
        avatar.pack(side="left", padx=(0, 14))
        avatar.pack_propagate(False)
        ctk.CTkLabel(
            avatar, text=initials,
            font=(FONT_PRIMARY, 18, "bold"),
            text_color=("#FFFFFF", "#FFFFFF"), fg_color="transparent"
        ).place(relx=0.5, rely=0.5, anchor="center")

        info = ctk.CTkFrame(header, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        self._acct_name_label = ctk.CTkLabel(
            info, text=self._display_name,
            font=(FONT_PRIMARY, 16, "bold"), text_color=_TEXT_PRI,
            fg_color="transparent", anchor="w"
        )
        self._acct_name_label.pack(fill="x")
        self._acct_email_label = ctk.CTkLabel(
            info, text=self._user_email,
            font=(FONT_PRIMARY, 12), text_color=_TEXT_SEC,
            fg_color="transparent", anchor="w"
        )
        self._acct_email_label.pack(fill="x", pady=(2, 0))

        self._row_divider(card)

        # ── Change email (inline edit) ────────────────────
        self._build_editable_row(
            card,
            label="Change email address",
            desc="Update your registered email",
            current_value=self._user_email,
            on_save=self._save_email
        )

        # ── Display name (inline edit) ────────────────────
        self._build_editable_row(
            card,
            label="Display name",
            desc="How your name appears in the app",
            current_value=self._display_name,
            on_save=self._save_display_name
        )

        # ── Change password ───────────────────────────────
        pw_row = ctk.CTkFrame(card, fg_color="transparent")
        pw_row.pack(fill="x", padx=20, pady=14)

        pw_left = ctk.CTkFrame(pw_row, fg_color="transparent")
        pw_left.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            pw_left, text="Change password",
            font=(FONT_PRIMARY, 13), text_color=_TEXT_PRI,
            fg_color="transparent", anchor="w"
        ).pack(fill="x")
        ctk.CTkLabel(
            pw_left, text="Keep your account secure",
            font=(FONT_PRIMARY, 11), text_color=_TEXT_MUT,
            fg_color="transparent", anchor="w"
        ).pack(fill="x", pady=(2, 0))

        ctk.CTkButton(
            pw_row, text="Change",
            font=(FONT_PRIMARY, 12, "bold"),
            fg_color=("#F5F3FF", "#2C2245"),
            hover_color=("#EDE7F6", "#3A3055"),
            text_color=_ACCENT,
            width=80, height=30, corner_radius=8,
            command=self._on_change_password
        ).pack(side="right")

    def _build_editable_row(self, parent, label, desc, current_value, on_save):
        """Builds an inline-editable row with Edit/Cancel toggle + input + Save."""
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="x")

        # Top part: label + Edit/Cancel button
        top = ctk.CTkFrame(container, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(14, 0))

        left = ctk.CTkFrame(top, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            left, text=label,
            font=(FONT_PRIMARY, 13), text_color=_TEXT_PRI,
            fg_color="transparent", anchor="w"
        ).pack(fill="x")
        ctk.CTkLabel(
            left, text=desc,
            font=(FONT_PRIMARY, 11), text_color=_TEXT_MUT,
            fg_color="transparent", anchor="w"
        ).pack(fill="x", pady=(2, 0))

        # Edit form (hidden by default)
        edit_frame = ctk.CTkFrame(container, fg_color="transparent")
        is_editing = [False]

        entry = ctk.CTkEntry(
            edit_frame,
            font=(FONT_PRIMARY, 13),
            fg_color=_INPUT_BG,
            border_color=("#C4B5FD", "#6C63FF"),
            border_width=1,
            text_color=_TEXT_PRI,
            height=36, corner_radius=8,
        )
        entry.insert(0, current_value)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        def _do_save():
            new_val = entry.get().strip()
            if new_val:
                on_save(new_val)
            _toggle_edit()

        ctk.CTkButton(
            edit_frame, text="Save",
            font=(FONT_PRIMARY, 12, "bold"),
            fg_color=_ACCENT, hover_color=_ACCENT_HOVER,
            text_color=("#FFFFFF", "#FFFFFF"),
            width=70, height=36, corner_radius=8,
            command=_do_save
        ).pack(side="right")

        def _toggle_edit():
            is_editing[0] = not is_editing[0]
            if is_editing[0]:
                edit_btn.configure(text="Cancel")
                edit_frame.pack(fill="x", padx=20, pady=(8, 0))
                entry.focus()
            else:
                edit_btn.configure(text="Edit")
                edit_frame.pack_forget()
                entry.delete(0, "end")
                entry.insert(0, current_value)

        edit_btn = ctk.CTkButton(
            top, text="Edit",
            font=(FONT_PRIMARY, 12, "bold"),
            fg_color=("#F5F3FF", "#2C2245"),
            hover_color=("#EDE7F6", "#3A3055"),
            text_color=_ACCENT,
            width=70, height=30, corner_radius=8,
            command=_toggle_edit
        )
        edit_btn.pack(side="right")

        # Bottom padding + divider
        ctk.CTkFrame(container, height=14, fg_color="transparent").pack(fill="x")
        self._row_divider(parent)

    def _save_email(self, new_email):
        """Update email via backend (requires password verification)."""
        from modules.settings.account_backend import update_email

        if not hasattr(self, '_session') or not self._session.is_logged_in:
            messagebox.showerror("Error", "Session not available.")
            return

        # Prompt for password verification
        dialog = ctk.CTkInputDialog(
            text="Enter your current password to verify:",
            title="Verify Identity"
        )
        password = dialog.get_input()
        if not password:
            return

        success, msg = update_email(self._session.user_id, new_email, password)
        if success:
            self._session.refresh()
            self._user_email = self._session.user["email"]
            self._acct_email_label.configure(text=self._user_email)
        else:
            messagebox.showerror("Email Update", msg)

    def _save_display_name(self, new_name):
        """Update display name via backend."""
        from modules.settings.account_backend import update_display_name

        if not hasattr(self, '_session') or not self._session.is_logged_in:
            messagebox.showerror("Error", "Session not available.")
            return

        success, msg = update_display_name(self._session.user_id, new_name)
        if success:
            self._session.refresh()
            self._display_name = self._session.user["name"]
            self._acct_name_label.configure(text=self._display_name)
        else:
            messagebox.showerror("Display Name", msg)

    def _on_change_password(self):
        """Open an in-app password change dialog."""
        from modules.settings.account_backend import update_password

        if not hasattr(self, '_session') or not self._session.is_logged_in:
            messagebox.showerror("Error", "Session not available.")
            return

        dlg = ctk.CTkToplevel(self)
        dlg.title("Change Password")
        dlg.geometry("400x400")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.configure(fg_color=_CARD_BG)

        # Center over main window
        dlg.after(10, lambda: self._center_dialog(dlg, 400, 400))

        ctk.CTkLabel(
            dlg, text="Change Password",
            font=(FONT_PRIMARY, 16, "bold"),
            text_color=_TEXT_PRI, fg_color="transparent"
        ).pack(padx=24, pady=(20, 16), anchor="w")

        fields = {}
        for lbl, key in [
            ("Current password", "current"),
            ("New password", "new"),
            ("Confirm new password", "confirm"),
        ]:
            ctk.CTkLabel(
                dlg, text=lbl,
                font=(FONT_PRIMARY, 11), text_color=_TEXT_MUT,
                fg_color="transparent"
            ).pack(padx=24, anchor="w", pady=(0, 4))
            entry = ctk.CTkEntry(
                dlg, show="\u25cf", font=FONT_INPUT,
                fg_color=_INPUT_BG, border_color=_INPUT_BORDER,
                border_width=1, text_color=_TEXT_PRI,
                height=38, corner_radius=8,
            )
            entry.pack(fill="x", padx=24, pady=(0, 10))
            fields[key] = entry

        ctk.CTkLabel(
            dlg, text="Min 8 chars \u00b7 1 uppercase \u00b7 1 number",
            font=(FONT_PRIMARY, 10), text_color=_TEXT_MUT,
            fg_color="transparent"
        ).pack(padx=24, anchor="w")

        err_label = ctk.CTkLabel(
            dlg, text="",
            font=(FONT_PRIMARY, 11), text_color=COLORS["error"],
            fg_color="transparent"
        )
        err_label.pack(padx=24, pady=(8, 0), anchor="w")

        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=(12, 20))

        def _do_save():
            ok, msg = update_password(
                self._session.user_id,
                fields["current"].get(),
                fields["new"].get(),
                fields["confirm"].get(),
            )
            if not ok:
                err_label.configure(text=f"\u26a0  {msg}")
                return
            dlg.destroy()
            messagebox.showinfo("Password Changed", msg)

        ctk.CTkButton(
            btn_row, text="Save password",
            font=(FONT_PRIMARY, 12, "bold"),
            fg_color=_ACCENT, hover_color=_ACCENT_HOVER,
            text_color=("#FFFFFF", "#FFFFFF"),
            width=130, height=36, corner_radius=8,
            command=_do_save
        ).pack(side="right")

        ctk.CTkButton(
            btn_row, text="Cancel",
            font=(FONT_PRIMARY, 12),
            fg_color="transparent", hover_color=_INPUT_BG,
            text_color=_TEXT_SEC, width=80, height=36,
            corner_radius=8, command=dlg.destroy
        ).pack(side="right", padx=(0, 8))

    def _center_dialog(self, dlg, w, h):
        try:
            mx = self.winfo_toplevel().winfo_x()
            my = self.winfo_toplevel().winfo_y()
            mw = self.winfo_toplevel().winfo_width()
            mh = self.winfo_toplevel().winfo_height()
            dlg.geometry(f"{w}x{h}+{mx + (mw - w) // 2}+{my + (mh - h) // 2}")
        except Exception:
            pass

    # ══════════════════════════════════════════════════════
    # SECTION: APPEARANCE
    # ══════════════════════════════════════════════════════

    def _build_appearance(self, parent):
        self._section_title(parent, "Appearance")
        card = self._card(parent)

        self._select_row(card, "Theme", "App color scheme",
                         "appearance.theme", [
                             ("system", "System default"),
                             ("light",  "Light"),
                             ("dark",   "Dark"),
                             ("high-contrast", "High contrast"),
                         ])

        self._select_row(card, "Font size", "Affects gesture text output",
                         "appearance.font_size", [
                             ("small",  "Small"),
                             ("medium", "Medium"),
                             ("large",  "Large"),
                             ("xl",     "Extra large"),
                         ])

        self._toggle_row(card, "Show landmark overlay",
                         "Draw hand keypoints on webcam view",
                         "appearance.show_landmark_overlay")

    # ══════════════════════════════════════════════════════
    # SECTION: GESTURE RECOGNITION
    # ══════════════════════════════════════════════════════

    def _build_gesture(self, parent):
        self._section_title(parent, "Gesture Recognition")
        card = self._card(parent)

        self._slider_row(card, "Confidence threshold",
                         "Minimum score to accept a gesture",
                         "gesture.confidence_threshold",
                         40, 95, 5, lambda v: f"{int(v)}%")

        self._slider_row(card, "Gesture timeout window",
                         "Pause before assembling a sentence",
                         "gesture.timeout",
                         0.5, 5.0, 0.5, lambda v: f"{v:.1f}s")

        self._select_row(card, "Gesture library",
                         "Active recognition dataset",
                         "gesture.library", [
                             ("asl-standard",     "ASL — Standard"),
                             ("asl-fingerspell",  "ASL — Fingerspelling"),
                             ("custom",           "Custom library"),
                         ])

        self._toggle_row(card, "Show confidence indicator",
                         "Display score badge on each gesture",
                         "gesture.show_confidence_indicator")

    # ══════════════════════════════════════════════════════
    # SECTION: SPEECH OUTPUT
    # ══════════════════════════════════════════════════════

    def _build_speech(self, parent):
        self._section_title(parent, "Speech Output")
        card = self._card(parent)

        self._toggle_row(card, "Text-to-speech",
                         "Read out recognized sentences aloud",
                         "speech.tts_enabled")

        self._select_row(card, "Voice", None,
                         "speech.voice", [
                             ("default", "Default system voice"),
                             ("female",  "Voice 1 (Female)"),
                             ("male",    "Voice 2 (Male)"),
                         ])

        self._slider_row(card, "Speech rate", None,
                         "speech.rate",
                         0.5, 2.0, 0.1, lambda v: f"{v:.1f}×")

        self._slider_row(card, "Volume", None,
                         "speech.volume",
                         0, 100, 5, lambda v: f"{int(v)}%")

    # ══════════════════════════════════════════════════════
    # SECTION: PRIVACY & DATA
    # ══════════════════════════════════════════════════════

    def _build_privacy(self, parent):
        self._section_title(parent, "Privacy & Data")
        card = self._card(parent)

        # Gesture history log — with badge
        right = self._row(card, "Gesture history log",
                          "Save recognized text + timestamps locally")
        self._badge(right, "Off by default", "amber")

        var = ctk.BooleanVar(value=config.get("privacy.gesture_history_log", False))

        from modules.gesture_history.backend import set_setting as _gh_set

        def _toggle_hist():
            config.set("privacy.gesture_history_log", var.get())
            _gh_set("logging_enabled", "1" if var.get() else "0")

        ctk.CTkSwitch(
            right, text="", variable=var,
            onvalue=True, offvalue=False, command=_toggle_hist,
            switch_width=44, switch_height=22,
            progress_color=_ACCENT, button_color=("#FFFFFF", "#FFFFFF"),
            fg_color=("#CBD5E1", "#444458"),
        ).pack(side="right")

        self._row_divider(card)

        # Local-only processing — always on
        right2 = self._row(card, "Local-only processing",
                           "No data is ever sent to external servers")
        self._badge(right2, "Always on", "green")

        ctk.CTkSwitch(
            right2, text="",
            switch_width=44, switch_height=22,
            progress_color=_ACCENT, button_color=("#FFFFFF", "#FFFFFF"),
            fg_color=("#CBD5E1", "#444458"),
            state="disabled",
        ).pack(side="right")
        # Force it on
        right2.winfo_children()[-1].select()

        self._row_divider(card)

        # View saved gesture log
        right3 = self._row(card, "View saved gesture log",
                           "Browse or export your local history")

        def _open_log_viewer():
            self._app.show_gesture_log_viewer(self._username)

        arrow = ctk.CTkLabel(
            right3, text="›", font=(FONT_PRIMARY, 20),
            text_color=_TEXT_MUT, cursor="hand2"
        )
        arrow.pack()
        arrow.bind("<Button-1>", lambda e: _open_log_viewer())
        right3.master.configure(cursor="hand2")
        right3.master.bind("<Button-1>", lambda e: _open_log_viewer())
        self._row_divider(card)

        # Clear history
        self._cleared = False

        def _clear_history():
            from modules.gesture_history.backend import clear_history as _gh_clear
            _gh_clear()
            self._cleared = True
            clear_btn.pack_forget()
            cleared_lbl = ctk.CTkLabel(
                clear_right, text="✓ Cleared",
                font=(FONT_PRIMARY, 10, "bold"),
                text_color=_SUCCESS, fg_color=COLORS["success_bg"],
                corner_radius=6, height=22,
            )
            cleared_lbl.pack()

        clear_right = self._row(card, "Clear gesture history",
                                "Permanently delete all local logs",
                                danger=True)
        clear_btn = ctk.CTkButton(
            clear_right, text="Clear",
            font=(FONT_PRIMARY, 12, "bold"),
            fg_color=COLORS["error_bg"],
            hover_color=("#F8D7DA", "#4A2222"),
            text_color=_ERROR,
            width=70, height=30, corner_radius=8,
            command=_clear_history
        )
        clear_btn.pack()

    # ══════════════════════════════════════════════════════
    # SECTION: ACCESSIBILITY
    # ══════════════════════════════════════════════════════

    def _build_accessibility(self, parent):
        self._section_title(parent, "Accessibility")
        card = self._card(parent)

        self._toggle_row(card, "Screen reader support",
                         "Optimize UI labels for assistive tools",
                         "accessibility.screen_reader_support")

        self._toggle_row(card, "Reduce motion",
                         "Minimize animations in the interface",
                         "accessibility.reduce_motion")

        self._toggle_row(card, "Keyboard navigation",
                         "Control app features without a mouse",
                         "accessibility.keyboard_navigation")

        self._toggle_row(card, "Gesture feedback vibration",
                         "Haptic pulse on successful recognition",
                         "accessibility.haptic_feedback")

    # ══════════════════════════════════════════════════════
    # SECTION: WEBCAM
    # ══════════════════════════════════════════════════════

    def _build_webcam(self, parent):
        self._section_title(parent, "Webcam")
        card = self._card(parent)

        self._toggle_row(card, "Enable webcam on launch",
                         "Auto-start camera when app opens",
                         "webcam.auto_start_on_launch")

        self._select_row(card, "Camera source", None,
                         "webcam.camera_source", [
                             ("builtin",  "Built-in webcam"),
                             ("external", "External USB camera"),
                         ])

        self._select_row(card, "Resolution",
                         "Higher resolution may affect performance",
                         "webcam.resolution", [
                             ("480p",  "480p"),
                             ("720p",  "720p (recommended)"),
                             ("1080p", "1080p"),
                         ])

    # ══════════════════════════════════════════════════════
    # SECTION: ABOUT & SUPPORT
    # ══════════════════════════════════════════════════════

    def _build_about(self, parent):
        self._section_title(parent, "About & Support")
        card = self._card(parent)

        # Version row with badge
        right = self._row(card, "App version", "SignDesk v1.0.0")
        self._badge(right, "Latest", "purple")
        self._row_divider(card)

        # User guide
        right2 = self._row(card, "User guide & documentation")
        ctk.CTkLabel(
            right2, text="›", font=(FONT_PRIMARY, 18),
            text_color=_TEXT_MUT, fg_color="transparent"
        ).pack()
        self._row_divider(card)

        # Send feedback
        right3 = self._row(card, "Send feedback")
        ctk.CTkLabel(
            right3, text="›", font=(FONT_PRIMARY, 18),
            text_color=_TEXT_MUT, fg_color="transparent"
        ).pack()
        self._row_divider(card)

        # Sign out
        right4 = self._row(card, "Sign out", danger=True)
        ctk.CTkLabel(
            right4, text="›", font=(FONT_PRIMARY, 18),
            text_color=("#FDA4AF", "#FDA4AF"), fg_color="transparent"
        ).pack()

        # Make the sign-out row clickable
        sign_out_frame = right4.master  # the row frame
        for w in (sign_out_frame, right4):
            w.configure(cursor="hand2")
            w.bind("<Button-1>", lambda e: self._on_sign_out())

    def _on_sign_out(self):
        if messagebox.askyesno("Sign Out", "Are you sure you want to sign out?"):
            self._app.show_login()

    # ══════════════════════════════════════════════════════
    # SAVE BAR
    # ══════════════════════════════════════════════════════

    def _build_save_bar(self, parent, section_id=None):
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.pack(fill="x", pady=(8, 24))

        # Right-aligned save button
        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right")

        saved_label = ctk.CTkLabel(
            right, text="",
            font=(FONT_PRIMARY, 12),
            text_color=_SUCCESS, fg_color=COLORS["success_bg"],
            corner_radius=8, height=0,
        )
        # hidden by default (height=0)

        if section_id:
            self._save_labels[section_id] = saved_label

        ctk.CTkButton(
            right, text="Save changes",
            font=(FONT_PRIMARY, 13, "bold"),
            fg_color=_ACCENT, hover_color=_ACCENT_HOVER,
            text_color=("#FFFFFF", "#FFFFFF"),
            width=130, height=40, corner_radius=10,
            command=self._on_save
        ).pack(side="right")

    def _on_save(self):
        config.save()

        # Show feedback on the active section's save bar
        saved_label = self._save_labels.get(self._active_section)
        if not saved_label:
            return

        saved_label.configure(text="  ✓ Changes saved  ", height=36)
        saved_label.pack(side="right", padx=(0, 10))

        if self._save_feedback_job:
            self.after_cancel(self._save_feedback_job)

        def _hide():
            saved_label.configure(text="", height=0)
            saved_label.pack_forget()
            self._save_feedback_job = None

        self._save_feedback_job = self.after(2500, _hide)

    # ══════════════════════════════════════════════════════
    # NAVIGATION
    # ══════════════════════════════════════════════════════

    def _on_back(self):
        self._app.show_dashboard(self._username)
