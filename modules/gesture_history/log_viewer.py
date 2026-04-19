"""
modules/gesture_history/log_viewer.py
Full-page viewer for saved gesture history logs.
Accessible from Settings → Privacy & Data → "View saved gesture log".
Supports CSV download.
"""

import csv
import os
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.theme import COLORS, FONT_PRIMARY
from modules.gesture_history.backend import (
    get_history,
    clear_history,
    get_record_count,
    get_setting,
)

# ── Color aliases ─────────────────────────────────────────────────────────────
_CARD_BG     = COLORS["bg_primary"]
_CARD_BORDER = COLORS["border"]
_BG          = COLORS["bg_secondary"]
_TEXT_PRI    = COLORS["text_primary"]
_TEXT_SEC    = COLORS["text_secondary"]
_TEXT_MUT    = COLORS["text_muted"]
_ACCENT      = COLORS["accent"]
_ACCENT_HOV  = COLORS["accent_hover"]
_ERROR       = COLORS["error"]
_ERROR_BG    = COLORS["error_bg"]
_SUCCESS     = COLORS["success"]
_SUCCESS_BG  = COLORS["success_bg"]
_INPUT_BG    = COLORS["input_bg"]

C_PURPLE_BG  = "#EEEDFE"
C_PURPLE_FG  = "#534AB7"
C_GREEN_BG   = "#d1fae5"
C_GREEN_FG   = "#1D9E75"
C_YELLOW_BG  = "#fef3c7"
C_YELLOW_FG  = "#b45309"
C_ROW_BG     = COLORS.get("bg_tertiary", "#13131f")


def _fmt_datetime(iso: str) -> tuple[str, str]:
    """Return (date_str, time_str) from ISO timestamp."""
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%b %d, %Y"), dt.strftime("%I:%M:%S %p").lstrip("0")
    except Exception:
        return iso, ""


def _conf_colors(conf) -> tuple[str, str, str]:
    """Return (bg, fg, text) for a confidence value."""
    if conf is None:
        return _INPUT_BG, _TEXT_MUT, "N/A"
    if conf >= 0.80:
        return C_GREEN_BG, C_GREEN_FG, f"{int(conf * 100)}%"
    return C_YELLOW_BG, C_YELLOW_FG, f"{int(conf * 100)}%"


# ══════════════════════════════════════════════════════════════════════════════
# LOG VIEWER PAGE
# ══════════════════════════════════════════════════════════════════════════════

class GestureLogViewerPage(ctk.CTkFrame):
    """
    Standalone full page — push onto app via app.show_gesture_log_viewer(username).
    Constructor matches all other SignDesk pages: (parent, app, username).
    """

    def __init__(self, parent, app, username: str):
        super().__init__(parent, fg_color=_BG, corner_radius=0)
        self._app      = app
        self._username = username
        self._records: list[dict] = []
        self._filter_var = tk.StringVar()
        self._filter_var.trace_add("write", lambda *_: self._apply_filter())
        self._build()
        self._load_records()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        self._build_navbar()
        self._build_body()

    def _build_navbar(self):
        navbar = ctk.CTkFrame(self, height=60,
                              fg_color=COLORS["panel_left"], corner_radius=0)
        navbar.pack(fill="x", side="top")
        navbar.pack_propagate(False)

        # Logo
        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "assets", "logo.png"
        )
        if os.path.exists(logo_path):
            try:
                from PIL import Image
                logo_img = ctk.CTkImage(Image.open(logo_path), size=(36, 36))
                ctk.CTkLabel(navbar, image=logo_img, text="").pack(
                    side="left", padx=(20, 10))
                self._logo_img = logo_img
            except Exception:
                pass

        ctk.CTkLabel(
            navbar, text="SignDesk",
            font=("Georgia", 18, "bold"),
            text_color=_TEXT_PRI, fg_color="transparent"
        ).pack(side="left", padx=24)

        ctk.CTkButton(
            navbar, text="Logout  →",
            command=self._on_logout,
            font=(FONT_PRIMARY, 11),
            fg_color=_ERROR, hover_color=_ERROR,
            text_color=("#FFFFFF", "#FFFFFF"),
            width=90, height=32, corner_radius=6
        ).pack(side="right", padx=(0, 20), pady=14)

        ctk.CTkButton(
            navbar, text="← Back to Settings",
            command=self._on_back,
            font=(FONT_PRIMARY, 11),
            fg_color="transparent", hover_color=COLORS["panel_left_end"],
            text_color=("#FFFFFF", "#FFFFFF"),
            border_width=1, border_color=("#FFFFFF", "#FFFFFF"),
            width=140, height=32, corner_radius=6
        ).pack(side="right", padx=(0, 8), pady=14)

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color=_BG, corner_radius=0)
        body.pack(fill="both", expand=True, padx=28, pady=20)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(2, weight=1)

        # ── Title row ─────────────────────────────────────
        title_row = ctk.CTkFrame(body, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        title_row.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            title_row, text="Saved Gesture Log",
            font=(FONT_PRIMARY, 20, "bold"),
            text_color=_TEXT_PRI, fg_color="transparent", anchor="w"
        ).grid(row=0, column=0, sticky="w")

        self._count_badge = ctk.CTkLabel(
            title_row, text="0 records",
            font=(FONT_PRIMARY, 11, "bold"),
            text_color=C_PURPLE_FG, fg_color=C_PURPLE_BG,
            corner_radius=99, padx=10, pady=3
        )
        self._count_badge.grid(row=0, column=1, padx=(10, 0))

        ctk.CTkLabel(
            body, text="All gesture logs stored locally on this device.",
            font=(FONT_PRIMARY, 11), text_color=_TEXT_MUT,
            fg_color="transparent", anchor="w"
        ).grid(row=1, column=0, sticky="w", pady=(0, 14))

        # ── Toolbar ───────────────────────────────────────
        toolbar = ctk.CTkFrame(body, fg_color=_CARD_BG,
                               corner_radius=10, border_width=1,
                               border_color=_CARD_BORDER)
        toolbar.grid(row=2, column=0, sticky="new", pady=(0, 10))
        toolbar.columnconfigure(1, weight=1)

        # Search
        search_wrap = ctk.CTkFrame(toolbar, fg_color=_INPUT_BG,
                                   corner_radius=8, border_width=1,
                                   border_color=_CARD_BORDER)
        search_wrap.grid(row=0, column=0, padx=14, pady=12, sticky="w")

        ctk.CTkLabel(search_wrap, text="🔍",
                     font=("Segoe UI Emoji", 12),
                     fg_color="transparent", text_color=_TEXT_MUT
                     ).pack(side="left", padx=(10, 4))

        ctk.CTkEntry(
            search_wrap, textvariable=self._filter_var,
            placeholder_text="Filter by gesture or text…",
            font=(FONT_PRIMARY, 12),
            fg_color="transparent", border_width=0,
            text_color=_TEXT_PRI,
            placeholder_text_color=_TEXT_MUT,
            height=32, width=220,
        ).pack(side="left", padx=(0, 10))

        # Right buttons
        btn_row = ctk.CTkFrame(toolbar, fg_color="transparent")
        btn_row.grid(row=0, column=2, padx=14, pady=12, sticky="e")

        self._download_btn = ctk.CTkButton(
            btn_row, text="⬇  Export CSV",
            font=(FONT_PRIMARY, 12, "bold"),
            fg_color=_ACCENT, hover_color=_ACCENT_HOV,
            text_color=("#FFFFFF", "#FFFFFF"),
            width=120, height=34, corner_radius=8,
            command=self._export_csv
        )
        self._download_btn.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="🗑  Clear all",
            font=(FONT_PRIMARY, 12),
            fg_color="transparent",
            hover_color=("#4A2222", "#4A2222"),
            text_color=_ERROR,
            border_width=1, border_color=_ERROR,
            width=100, height=34, corner_radius=8,
            command=self._handle_clear
        ).pack(side="left")

        # ── Table header ──────────────────────────────────
        header = ctk.CTkFrame(body, fg_color=_CARD_BG,
                              corner_radius=10, border_width=1,
                              border_color=_CARD_BORDER)
        header.grid(row=3, column=0, sticky="ew", pady=(0, 2))
        self._build_table_header(header)

        # ── Scrollable rows ───────────────────────────────
        self._list_frame = ctk.CTkScrollableFrame(
            body, fg_color=_CARD_BG, corner_radius=10,
            border_width=1, border_color=_CARD_BORDER,
            scrollbar_button_color=_CARD_BORDER,
            scrollbar_button_hover_color=_ACCENT,
        )
        self._list_frame.grid(row=4, column=0, sticky="nsew", pady=(0, 10))
        body.grid_rowconfigure(4, weight=1)
        self._list_frame.columnconfigure(0, weight=1)

        # ── Feedback bar ──────────────────────────────────
        self._feedback_var = tk.StringVar()
        self._feedback_lbl = ctk.CTkLabel(
            body, textvariable=self._feedback_var,
            font=(FONT_PRIMARY, 11),
            text_color=_SUCCESS, fg_color="transparent", anchor="e"
        )
        self._feedback_lbl.grid(row=5, column=0, sticky="e", pady=(4, 0))

    def _build_table_header(self, parent):
        cols = [
            ("#",          40,  "center"),
            ("Gesture",    80,  "center"),
            ("Translated", 160, "w"),
            ("Confidence", 110, "center"),
            ("Date",       120, "w"),
            ("Time",       120, "w"),
        ]
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=8)

        for label, width, anchor in cols:
            ctk.CTkLabel(
                row, text=label,
                font=(FONT_PRIMARY, 11, "bold"),
                text_color=_TEXT_MUT, fg_color="transparent",
                width=width, anchor=anchor
            ).pack(side="left", padx=4)

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load_records(self):
        self._records = get_history()
        self._apply_filter()
        self._update_count(len(self._records))

    def _apply_filter(self):
        query = self._filter_var.get().strip().lower()
        if query:
            filtered = [
                r for r in self._records
                if query in (r.get("gesture") or "").lower()
                or query in (r.get("translated_text") or "").lower()
            ]
        else:
            filtered = self._records

        self._populate_rows(filtered)

    def _populate_rows(self, records: list[dict]):
        for w in self._list_frame.winfo_children():
            w.destroy()

        if not records:
            self._build_empty_state()
            return

        for i, rec in enumerate(records):
            self._build_row(i, rec)

    def _build_empty_state(self):
        wrap = ctk.CTkFrame(self._list_frame, fg_color="transparent")
        wrap.pack(expand=True, pady=40)

        ctk.CTkLabel(
            wrap, text="📭",
            font=("Segoe UI Emoji", 32), fg_color="transparent"
        ).pack()
        ctk.CTkLabel(
            wrap,
            text="No gesture records found." if not self._records
                 else "No records match your filter.",
            font=(FONT_PRIMARY, 13), text_color=_TEXT_MUT,
            fg_color="transparent"
        ).pack(pady=(8, 0))

        if not self._records:
            enabled = get_setting("logging_enabled") == "1"
            hint = (
                "Start the Gesture Translator to log gestures."
                if enabled
                else "Enable gesture history logging in Settings → Privacy & Data."
            )
            ctk.CTkLabel(
                wrap, text=hint,
                font=(FONT_PRIMARY, 11), text_color=_TEXT_MUT,
                fg_color="transparent", wraplength=300
            ).pack(pady=(4, 0))

    def _build_row(self, index: int, rec: dict):
        date_str, time_str = _fmt_datetime(rec.get("logged_at", ""))
        conf_bg, conf_fg, conf_text = _conf_colors(rec.get("confidence"))
        translated = rec.get("translated_text") or "—"
        gesture    = rec.get("gesture", "?")

        row_bg = _CARD_BG if index % 2 == 0 else C_ROW_BG

        row = ctk.CTkFrame(self._list_frame, fg_color=row_bg,
                           corner_radius=0, height=44)
        row.pack(fill="x")
        row.pack_propagate(False)

        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=14, pady=4)

        # Index
        ctk.CTkLabel(inner, text=str(index + 1),
                     font=(FONT_PRIMARY, 11), text_color=_TEXT_MUT,
                     fg_color="transparent", width=40, anchor="center"
                     ).pack(side="left", padx=4)

        # Gesture badge
        badge = ctk.CTkLabel(inner, text=gesture[0].upper(),
                             font=(FONT_PRIMARY, 12, "bold"),
                             text_color=C_PURPLE_FG, fg_color=C_PURPLE_BG,
                             width=28, height=28, corner_radius=6)
        badge.pack(side="left", padx=(4, 12))

        # Translated text
        ctk.CTkLabel(inner, text=translated,
                     font=(FONT_PRIMARY, 12), text_color=_TEXT_PRI,
                     fg_color="transparent", width=160, anchor="w"
                     ).pack(side="left", padx=4)

        # Confidence pill
        ctk.CTkLabel(inner, text=conf_text,
                     font=(FONT_PRIMARY, 11, "bold"),
                     text_color=conf_fg, fg_color=conf_bg,
                     corner_radius=99, padx=8, pady=2,
                     width=80, anchor="center"
                     ).pack(side="left", padx=4)

        # Date
        ctk.CTkLabel(inner, text=date_str,
                     font=(FONT_PRIMARY, 11), text_color=_TEXT_SEC,
                     fg_color="transparent", width=120, anchor="w"
                     ).pack(side="left", padx=4)

        # Time
        ctk.CTkLabel(inner, text=time_str,
                     font=(FONT_PRIMARY, 11), text_color=_TEXT_MUT,
                     fg_color="transparent", width=120, anchor="w"
                     ).pack(side="left", padx=4)

        # Row divider
        ctk.CTkFrame(self._list_frame, height=1,
                     fg_color=_CARD_BORDER, corner_radius=0).pack(fill="x")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _update_count(self, n: int):
        self._count_badge.configure(
            text=f"{n} record{'s' if n != 1 else ''}"
        )

    def _handle_clear(self):
        if not self._records:
            return
        if messagebox.askyesno(
            "Clear History",
            "Permanently delete all gesture history records?\nThis cannot be undone."
        ):
            success, msg = clear_history()
            if success:
                self._records = []
                self._populate_rows([])
                self._update_count(0)
                self._show_feedback("✓  All records cleared.", success=True)

    def _export_csv(self):
        if not self._records:
            messagebox.showinfo("Export", "No records to export.")
            return

        default_name = f"gesture_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=default_name,
            title="Save gesture log as CSV"
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["id", "gesture", "translated_text",
                                   "confidence", "logged_at"]
                )
                writer.writeheader()
                writer.writerows(self._records)

            self._show_feedback(
                f"✓  Exported {len(self._records)} records to CSV.", success=True
            )
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    def _show_feedback(self, msg: str, success: bool = True):
        color = _SUCCESS if success else _ERROR
        self._feedback_lbl.configure(text_color=color)
        self._feedback_var.set(msg)
        self.after(4000, lambda: self._feedback_var.set(""))

    # ── Navigation ────────────────────────────────────────────────────────────

    def _on_back(self):
        self._app.show_settings(self._username)

    def _on_logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to log out?"):
            self._app.show_login()
