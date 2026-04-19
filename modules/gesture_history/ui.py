"""
SignDesk — Gesture History UI
CustomTkinter implementation matching the gesture_history_wireframe.

SD009-AC1: Logging disabled by default (toggle in settings panel).
SD009-AC5: Privacy note — all data stored locally.
"""

import tkinter as tk
from datetime import datetime

import customtkinter as ctk

from modules.gesture_history.backend import (
    get_setting,
    set_setting,
    get_history,
    clear_history,
    get_record_count,
    init_history_db,
)

# ── Color constants ───────────────────────────────────────────────────────────
C_PANEL_BG      = "#1c1c2e"
C_ROW_BG        = "#13131f"
C_BORDER        = "#2a2a3d"
C_PURPLE_BG     = "#EEEDFE"
C_PURPLE_FG     = "#534AB7"
C_GREEN_BG      = "#d1fae5"
C_GREEN_FG      = "#1D9E75"
C_YELLOW_BG     = "#fef3c7"
C_YELLOW_FG     = "#b45309"
C_INFO_BG       = "#1e3a5f"
C_INFO_BORDER   = "#2563eb"
C_INFO_FG       = "#93c5fd"
C_DANGER        = "#e24b4a"
C_TEXT_PRIMARY  = "#ffffff"
C_TEXT_SECONDARY= "#888888"
C_DOT_DISABLED  = "#534AB7"
C_DOT_ENABLED   = "#1D9E75"
C_DOT_NEUTRAL   = "#93c5fd"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_time(iso: str) -> str:
    """Convert ISO timestamp to '2:14:32 PM' format."""
    try:
        # Changed %-I to %#I for Windows compatibility
        return datetime.fromisoformat(iso).strftime("%#I:%M:%S %p")
    except Exception:
        return iso


def _make_dot(parent, color: str, size: int = 8) -> tk.Canvas:
    """Return a small colored circle canvas."""
    c = tk.Canvas(parent, width=size, height=size,
                  bg=C_PANEL_BG, highlightthickness=0)
    c.create_oval(1, 1, size - 1, size - 1, fill=color, outline="")
    return c


def _separator(parent) -> ctk.CTkFrame:
    """1px horizontal separator."""
    return ctk.CTkFrame(parent, height=1, fg_color=C_BORDER, corner_radius=0)


# ── Panel builder helper ──────────────────────────────────────────────────────

def _make_panel(parent) -> tuple[ctk.CTkFrame, ctk.CTkFrame, ctk.CTkFrame]:
    """
    Create a panel with header + body.
    Returns (panel, header_frame, body_frame).
    """
    panel = ctk.CTkFrame(parent, fg_color=C_PANEL_BG, corner_radius=10,
                         border_width=1, border_color=C_BORDER)
    header = ctk.CTkFrame(panel, fg_color=C_PANEL_BG, corner_radius=0, height=40)
    header.pack(fill="x", padx=0, pady=0)
    header.pack_propagate(False)

    _separator(panel).pack(fill="x")

    body = ctk.CTkFrame(panel, fg_color=C_PANEL_BG, corner_radius=0)
    body.pack(fill="both", expand=True, padx=14, pady=10)

    return panel, header, body


# ── Main Section ──────────────────────────────────────────────────────────────

class GestureHistorySection(ctk.CTkFrame):
    """
    2×2 grid layout:
      A (top-left)  — disabled state
      B (top-right) — enabled + records state
      C (bottom-left)  — settings toggles
      D (bottom-right) — static error/empty state reference
    """

    def __init__(self, parent, focus_callback=None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        init_history_db()

        self._focus_callback = focus_callback  # optional: called when "Settings" link clicked
        self._feedback_var   = tk.StringVar()

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._build_panel_a()
        self._build_panel_b()
        self._build_panel_c()
        self._build_panel_d()

        self._refresh_panels()

    # ── Panel A — Disabled state ──────────────────────────────────────────────

    def _build_panel_a(self):
        panel, header, body = _make_panel(self)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 6))

        # Header
        header.columnconfigure(1, weight=1)
        self._dot_a = _make_dot(header, C_DOT_DISABLED)
        self._dot_a.grid(row=0, column=0, padx=(14, 6), pady=10)

        ctk.CTkLabel(header, text="Gesture history",
                     font=("Segoe UI", 13, "bold"),
                     text_color=C_TEXT_PRIMARY).grid(row=0, column=1, sticky="w")

        self._badge_a = ctk.CTkLabel(header, text="Disabled",
                                     font=("Segoe UI", 11, "bold"),
                                     text_color=C_TEXT_SECONDARY,
                                     fg_color=C_BORDER, corner_radius=99,
                                     padx=8, pady=2)
        self._badge_a.grid(row=0, column=2, padx=14)

        # Body — centered disabled message
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        center = ctk.CTkFrame(body, fg_color="transparent")
        center.grid(row=0, column=0)

        # Circle icon
        icon_canvas = tk.Canvas(center, width=36, height=36,
                                bg=C_PANEL_BG, highlightthickness=0)
        icon_canvas.create_oval(2, 2, 34, 34, fill=C_BORDER, outline="")
        icon_canvas.create_text(18, 18, text="i", fill=C_TEXT_SECONDARY,
                                font=("Segoe UI", 14, "bold"))
        icon_canvas.pack(pady=(0, 10))

        msg_frame = ctk.CTkFrame(center, fg_color="transparent")
        msg_frame.pack()

        ctk.CTkLabel(msg_frame,
                     text="Gesture history logging is currently disabled.",
                     font=("Segoe UI", 11), text_color=C_TEXT_SECONDARY,
                     wraplength=200).pack()

        link_row = ctk.CTkFrame(msg_frame, fg_color="transparent")
        link_row.pack()
        ctk.CTkLabel(link_row, text="Enable it in ",
                     font=("Segoe UI", 11), text_color=C_TEXT_SECONDARY).pack(side="left")

        settings_link = ctk.CTkLabel(link_row, text="Settings",
                                     font=("Segoe UI", 11, "bold"),
                                     text_color=C_INFO_FG, cursor="hand2")
        settings_link.pack(side="left")
        settings_link.bind("<Button-1>", lambda e: self._focus_settings_panel())

        ctk.CTkLabel(link_row, text=" to start tracking.",
                     font=("Segoe UI", 11), text_color=C_TEXT_SECONDARY).pack(side="left")

    # ── Panel B — Enabled + records ───────────────────────────────────────────

    def _build_panel_b(self):
        panel, header, body = _make_panel(self)
        panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 6))

        # Header
        header.columnconfigure(1, weight=1)
        self._dot_b = _make_dot(header, C_DOT_ENABLED)
        self._dot_b.grid(row=0, column=0, padx=(14, 6), pady=10)

        ctk.CTkLabel(header, text="Gesture history",
                     font=("Segoe UI", 13, "bold"),
                     text_color=C_TEXT_PRIMARY).grid(row=0, column=1, sticky="w")

        self._badge_b = ctk.CTkLabel(header, text="0 records",
                                     font=("Segoe UI", 11, "bold"),
                                     text_color=C_PURPLE_FG,
                                     fg_color=C_PURPLE_BG, corner_radius=99,
                                     padx=8, pady=2)
        self._badge_b.grid(row=0, column=2, padx=14)

        # Body
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)

        today_str = datetime.now().strftime("%b %d, %Y").upper()
        ctk.CTkLabel(body,
                     text=f"TODAY — {today_str}",
                     font=("Segoe UI", 9, "bold"),
                     text_color=C_TEXT_SECONDARY).grid(row=0, column=0, sticky="w", pady=(0, 6))

        # Scrollable list
        self._scroll_frame = ctk.CTkScrollableFrame(
            body, fg_color="transparent", height=240,
            scrollbar_button_color=C_BORDER,
            scrollbar_button_hover_color=C_PURPLE_FG,
        )
        self._scroll_frame.grid(row=1, column=0, sticky="nsew")
        self._scroll_frame.columnconfigure(0, weight=1)

        # Footer
        footer = ctk.CTkFrame(body, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        footer.columnconfigure(0, weight=1)

        _separator(body).grid(row=3, column=0, sticky="ew", pady=(0, 8))

        self._count_label = ctk.CTkLabel(footer, text="0 gestures logged locally",
                                         font=("Segoe UI", 10),
                                         text_color=C_TEXT_SECONDARY)
        self._count_label.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(footer, text="Clear history",
                      font=("Segoe UI", 11), text_color=C_DANGER,
                      fg_color="transparent", border_color=C_DANGER,
                      border_width=1, hover_color="#2a1a1a",
                      width=90, height=26,
                      command=self._handle_clear,
                      ).grid(row=0, column=1)

        # Feedback label
        self._feedback_label = ctk.CTkLabel(body, textvariable=self._feedback_var,
                                            font=("Segoe UI", 10),
                                            text_color="#a78bfa")
        self._feedback_label.grid(row=4, column=0, sticky="e")

    def _populate_history(self, records: list[dict]):
        """Clear and re-populate the scrollable history list."""
        for w in self._scroll_frame.winfo_children():
            w.destroy()

        if not records:
            ctk.CTkLabel(self._scroll_frame,
                         text="No gestures have been logged yet.",
                         font=("Segoe UI", 11), text_color=C_TEXT_SECONDARY,
                         ).pack(pady=20)
            return

        for rec in records:
            row = ctk.CTkFrame(self._scroll_frame, fg_color=C_ROW_BG,
                               corner_radius=8, border_width=1,
                               border_color=C_BORDER)
            row.pack(fill="x", pady=3)
            row.columnconfigure(1, weight=1)

            # Gesture badge
            ctk.CTkLabel(row, text=rec["gesture"][0].upper(),
                         font=("Segoe UI", 13, "bold"),
                         text_color=C_PURPLE_FG, fg_color=C_PURPLE_BG,
                         width=32, height=32, corner_radius=8,
                         ).grid(row=0, column=0, rowspan=2, padx=(10, 8), pady=8)

            # Info
            gesture_text = rec["gesture"]
            if rec.get("translated_text"):
                gesture_text += f" → \"{rec['translated_text']}\""
            ctk.CTkLabel(row, text=gesture_text,
                         font=("Segoe UI", 12, "bold"),
                         text_color=C_TEXT_PRIMARY, anchor="w",
                         ).grid(row=0, column=1, sticky="w", pady=(8, 0))

            ctk.CTkLabel(row, text=_format_time(rec["logged_at"]),
                         font=("Segoe UI", 10),
                         text_color=C_TEXT_SECONDARY, anchor="w",
                         ).grid(row=1, column=1, sticky="w", pady=(0, 8))

            # Confidence pill
            conf = rec.get("confidence")
            if conf is None:
                pill_bg, pill_fg, pill_text = C_BORDER, C_TEXT_SECONDARY, "N/A"
            elif conf >= 0.80:
                pill_bg, pill_fg, pill_text = C_GREEN_BG, C_GREEN_FG, f"{int(conf*100)}%"
            else:
                pill_bg, pill_fg, pill_text = C_YELLOW_BG, C_YELLOW_FG, f"{int(conf*100)}%"

            ctk.CTkLabel(row, text=pill_text,
                         font=("Segoe UI", 10, "bold"),
                         text_color=pill_fg, fg_color=pill_bg,
                         corner_radius=99, padx=8, pady=2,
                         ).grid(row=0, column=2, rowspan=2, padx=(0, 10))

    def _handle_clear(self):
        success, msg = clear_history()
        if success:
            self._refresh_panels()
            self._show_feedback(f"✓  {msg}")

    # ── Panel C — Settings ────────────────────────────────────────────────────

    def _build_panel_c(self):
        panel, header, body = _make_panel(self)
        panel.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=(6, 0))

        # Header
        header.columnconfigure(1, weight=1)
        _make_dot(header, C_DOT_NEUTRAL).grid(row=0, column=0, padx=(14, 6), pady=10)
        ctk.CTkLabel(header, text="Settings — history",
                     font=("Segoe UI", 13, "bold"),
                     text_color=C_TEXT_PRIMARY).grid(row=0, column=1, sticky="w")

        # Toggle rows
        self._settings_body = body
        self._render_settings_rows()

    def _render_settings_rows(self):
        for w in self._settings_body.winfo_children():
            w.destroy()

        self._settings_body.columnconfigure(0, weight=1)

        toggles = [
            ("Enable gesture history logging",
             "Disabled by default (SD009-AC1)",   # SD009-AC1
             "logging_enabled"),
            ("Include confidence score",
             "Save score alongside each gesture",
             "include_confidence"),
            ("Include translated text",
             "Save phonetic output per gesture",
             "include_translation"),
        ]

        for i, (title, desc, key) in enumerate(toggles):
            row = ctk.CTkFrame(self._settings_body, fg_color="transparent")
            row.grid(row=i * 2, column=0, sticky="ew", pady=4)
            row.columnconfigure(0, weight=1)

            # Labels
            label_col = ctk.CTkFrame(row, fg_color="transparent")
            label_col.grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(label_col, text=title,
                         font=("Segoe UI", 12), text_color=C_TEXT_PRIMARY,
                         anchor="w").pack(anchor="w")
            ctk.CTkLabel(label_col, text=desc,
                         font=("Segoe UI", 10), text_color=C_TEXT_SECONDARY,
                         anchor="w").pack(anchor="w")

            # Toggle
            current_val = get_setting(key) == "1"
            switch_var  = tk.BooleanVar(value=current_val)

            def _on_toggle(var=switch_var, k=key):
                set_setting(k, "1" if var.get() else "0")
                if k == "logging_enabled":
                    self._refresh_panels()

            ctk.CTkSwitch(row, text="", variable=switch_var,
                          command=_on_toggle,
                          progress_color=C_GREEN_FG,
                          button_color="#ffffff",
                          button_hover_color="#dddddd",
                          width=36, height=20,
                          ).grid(row=0, column=1, padx=(12, 0))

            # Separator (skip after last row)
            if i < len(toggles) - 1:
                _separator(self._settings_body).grid(
                    row=i * 2 + 1, column=0, sticky="ew", pady=2
                )

        # Privacy note — SD009-AC5
        note = ctk.CTkFrame(self._settings_body, fg_color=C_INFO_BG,
                            corner_radius=8, border_width=1,
                            border_color=C_INFO_BORDER)
        note.grid(row=len(toggles) * 2, column=0, sticky="ew", pady=(10, 0))
        note.columnconfigure(1, weight=1)

        _make_dot(note, C_INFO_FG).grid(row=0, column=0, padx=(10, 6), pady=10, sticky="n")
        ctk.CTkLabel(note,
                     text="All history data is stored locally on your device. "
                          "No data is transmitted externally. (SD009-AC5)",  # SD009-AC5
                     font=("Segoe UI", 10), text_color=C_INFO_FG,
                     wraplength=220, justify="left",
                     ).grid(row=0, column=1, sticky="w", padx=(0, 10), pady=10)

    # ── Panel D — Static error/empty states reference ─────────────────────────

    def _build_panel_d(self):
        panel, header, body = _make_panel(self)
        panel.grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=(6, 0))

        header.columnconfigure(1, weight=1)
        _make_dot(header, C_TEXT_SECONDARY).grid(row=0, column=0, padx=(14, 6), pady=10)
        ctk.CTkLabel(header, text="Error + empty states",
                     font=("Segoe UI", 13, "bold"),
                     text_color=C_TEXT_PRIMARY).grid(row=0, column=1, sticky="w")

        body.columnconfigure(0, weight=1)

        states = [
            ("#2d1a1a", C_DANGER,        C_INFO_BORDER, "Logging disabled",
             "Gesture history logging is currently disabled. Enable it in Settings to start tracking."),
            (C_ROW_BG, C_TEXT_SECONDARY, C_BORDER,      "No records yet",
             "No gestures have been logged yet. Start detection to begin recording history."),
            ("#0f2a1e", C_GREEN_FG,      C_GREEN_FG,    "History cleared",
             "All gesture history records have been cleared successfully."),
        ]

        for i, (bg, fg, border, title, desc) in enumerate(states):
            box = ctk.CTkFrame(body, fg_color=bg, corner_radius=8,
                               border_width=1, border_color=border)
            box.grid(row=i, column=0, sticky="ew", pady=4)
            box.columnconfigure(0, weight=1)

            ctk.CTkLabel(box, text=title,
                         font=("Segoe UI", 11, "bold"), text_color=fg,
                         anchor="w").grid(row=0, column=0, sticky="w", padx=12, pady=(10, 2))
            ctk.CTkLabel(box, text=desc,
                         font=("Segoe UI", 10), text_color=fg,
                         wraplength=200, justify="left", anchor="w",
                         ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))

    # ── Refresh ───────────────────────────────────────────────────────────────

    def _refresh_panels(self):
        """
        Re-reads settings + history and updates Panel A and B.
        Call externally after log_gesture() to update the UI live.
        """
        enabled = get_setting("logging_enabled") == "1"
        records = get_history() if enabled else []
        count   = len(records)

        # Panel A badge
        if enabled:
            self._badge_a.configure(text="Enabled",
                                    text_color=C_GREEN_FG, fg_color=C_GREEN_BG)
            self._dot_a.delete("all")
            self._dot_a.create_oval(1, 1, 7, 7, fill=C_DOT_ENABLED, outline="")
        else:
            self._badge_a.configure(text="Disabled",
                                    text_color=C_TEXT_SECONDARY, fg_color=C_BORDER)
            self._dot_a.delete("all")
            self._dot_a.create_oval(1, 1, 7, 7, fill=C_DOT_DISABLED, outline="")

        # Panel B badge + list
        self._badge_b.configure(text=f"{count} record{'s' if count != 1 else ''}")
        self._count_label.configure(text=f"{count} gesture{'s' if count != 1 else ''} logged locally")
        self._populate_history(records)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _focus_settings_panel(self):
        """Called when the 'Settings' link in Panel A is clicked."""
        if self._focus_callback:
            self._focus_callback()

    def _show_feedback(self, msg: str, error: bool = False):
        color = "#f87171" if error else "#a78bfa"
        self._feedback_label.configure(text_color=color)
        self._feedback_var.set(msg)
        self.after(3500, lambda: self._feedback_var.set(""))
