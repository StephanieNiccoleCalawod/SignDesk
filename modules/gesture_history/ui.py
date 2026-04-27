"""
modules/gesture_history/ui.py
==============================
GestureHistorySection — the full-page history log viewer widget.
Used by GestureHistoryPage (page.py) as its body content.

Features:
  * Stats bar: total records, today's count, logging status badge
  * Search / filter by gesture letter or translated text
  * Sortable table: #, Gesture, Translated, Confidence, Date, Time
  * Auto-refresh every 10 s while the page is visible
  * Export CSV  |  Clear all  buttons
  * Empty-state hint when logging is disabled
"""

import csv
import tkinter as tk
from datetime import datetime, date
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.theme import COLORS, FONT_PRIMARY
from modules.gesture_history.backend import (
    get_history,
    clear_history,
    get_record_count,
    get_setting,
)

# ── Colour aliases (matches the rest of the app) ─────────────────────────────
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

# Extra badge palette
_PURPLE_BG = "#EEEDFE"
_PURPLE_FG = "#534AB7"
_GREEN_BG  = "#d1fae5"
_GREEN_FG  = "#1D9E75"
_YELLOW_BG = "#fef3c7"
_YELLOW_FG = "#b45309"
_BLUE_BG   = COLORS.get("info_bg", "#EFF6FF")
_BLUE_FG   = COLORS.get("info",    "#2563EB")
_ROW_ALT   = COLORS.get("bg_secondary", "#13131f")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fmt_datetime(iso: str) -> tuple[str, str]:
    """Return (date_str, time_str) from an ISO-8601 timestamp string."""
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%b %d, %Y"), dt.strftime("%I:%M:%S %p").lstrip("0")
    except Exception:
        return iso, ""


def _conf_badge(conf) -> tuple[str, str, str]:
    """Return (bg, fg, label) for a confidence value."""
    if conf is None:
        return _INPUT_BG, _TEXT_MUT, "N/A"
    pct = int(conf * 100)
    if pct >= 80:
        return _GREEN_BG, _GREEN_FG, f"{pct}%"
    if pct >= 60:
        return _YELLOW_BG, _YELLOW_FG, f"{pct}%"
    return _ERROR_BG, _ERROR, f"{pct}%"


def _today_count(records: list[dict]) -> int:
    today = date.today().isoformat()
    return sum(1 for r in records if r.get("logged_at", "").startswith(today))


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN WIDGET
# ═══════════════════════════════════════════════════════════════════════════════

class GestureHistorySection(ctk.CTkFrame):
    """
    Self-contained gesture-log viewer.
    Designed to be embedded into GestureHistoryPage or any CTk container.
    """

    _REFRESH_MS = 10_000   # auto-refresh interval

    def __init__(self, parent, user_id: int | None = None, **kwargs):
        super().__init__(parent, fg_color="transparent", corner_radius=0, **kwargs)
        self._user_id   = user_id
        self._records:  list[dict] = []
        self._filtered: list[dict] = []
        self._sort_col  = "logged_at"
        self._sort_asc  = False
        self._filter_var = tk.StringVar()
        self._filter_var.trace_add("write", lambda *_: self._apply_filter())
        self._refresh_job = None

        self._build()
        self._load()
        self._schedule_refresh()

    # ── Build ────────────────────────────────────────────────────────────────

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._build_stats_bar()
        self._build_toolbar()
        self._build_table_header()
        self._build_table_body()
        self._build_feedback_bar()

    # ── Stats bar ────────────────────────────────────────────────────────────

    def _build_stats_bar(self):
        bar = ctk.CTkFrame(self, fg_color=_CARD_BG, corner_radius=12,
                           border_width=1, border_color=_CARD_BORDER)
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        bar.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self._stat_total  = self._stat_card(bar, 0, "Total Records", "0",
                                            _PURPLE_FG, _PURPLE_BG)
        self._stat_today  = self._stat_card(bar, 1, "Today",         "0",
                                            _GREEN_FG,  _GREEN_BG)
        self._stat_status = self._stat_card(bar, 2, "Logging",       "—",
                                            _YELLOW_FG, _YELLOW_BG)
        self._stat_last   = self._stat_card(bar, 3, "Last Gesture",  "—",
                                            _BLUE_FG,   _BLUE_BG)

    @staticmethod
    def _stat_card(parent, col, label, value, fg, bg):
        cell = ctk.CTkFrame(parent, fg_color="transparent")
        cell.grid(row=0, column=col, padx=16, pady=14, sticky="ew")
        val_lbl = ctk.CTkLabel(
            cell, text=value,
            font=(FONT_PRIMARY, 22, "bold"),
            text_color=fg, fg_color=bg,
            corner_radius=8, width=64, height=36,
        )
        val_lbl.pack()
        ctk.CTkLabel(
            cell, text=label,
            font=(FONT_PRIMARY, 11),
            text_color=_TEXT_MUT, fg_color="transparent",
        ).pack(pady=(4, 0))
        return val_lbl

    # ── Toolbar ──────────────────────────────────────────────────────────────

    def _build_toolbar(self):
        bar = ctk.CTkFrame(self, fg_color=_CARD_BG, corner_radius=10,
                           border_width=1, border_color=_CARD_BORDER)
        bar.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        bar.grid_columnconfigure(1, weight=1)

        # Search box
        search_wrap = ctk.CTkFrame(bar, fg_color=_INPUT_BG, corner_radius=8,
                                   border_width=1, border_color=_CARD_BORDER)
        search_wrap.grid(row=0, column=0, padx=14, pady=10, sticky="w")

        ctk.CTkLabel(search_wrap, text="🔍",
                     font=("Segoe UI Emoji", 12),
                     fg_color="transparent", text_color=_TEXT_MUT
                     ).pack(side="left", padx=(10, 4))

        ctk.CTkEntry(
            search_wrap, textvariable=self._filter_var,
            placeholder_text="Search gesture or translation…",
            font=(FONT_PRIMARY, 12),
            fg_color="transparent", border_width=0,
            text_color=_TEXT_PRI,
            placeholder_text_color=_TEXT_MUT,
            height=32, width=230,
        ).pack(side="left", padx=(0, 10))

        # Right-side action buttons
        btn_row = ctk.CTkFrame(bar, fg_color="transparent")
        btn_row.grid(row=0, column=2, padx=14, pady=10, sticky="e")

        ctk.CTkButton(
            btn_row, text="↻  Refresh",
            font=(FONT_PRIMARY, 12),
            fg_color="transparent",
            hover_color=_INPUT_BG,
            text_color=_ACCENT,
            border_width=1, border_color=_ACCENT,
            width=90, height=34, corner_radius=8,
            command=self._load,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="⬇  Export CSV",
            font=(FONT_PRIMARY, 12, "bold"),
            fg_color=_ACCENT, hover_color=_ACCENT_HOV,
            text_color=("#FFFFFF", "#FFFFFF"),
            width=120, height=34, corner_radius=8,
            command=self._export_csv,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="🗑  Clear all",
            font=(FONT_PRIMARY, 12),
            fg_color="transparent",
            hover_color=("#4A2222", "#4A2222"),
            text_color=_ERROR,
            border_width=1, border_color=_ERROR,
            width=100, height=34, corner_radius=8,
            command=self._handle_clear,
        ).pack(side="left")

    # ── Table header ─────────────────────────────────────────────────────────

    _COLUMNS = [
        ("",               "#",          40,  "center"),
        ("gesture",        "Gesture",    70,  "center"),
        ("translated_text","Translated", 160, "w"),
        ("confidence",     "Confidence", 110, "center"),
        ("logged_at",      "Date",       130, "w"),
        ("logged_at",      "Time",       130, "w"),
    ]

    def _build_table_header(self):
        hdr = ctk.CTkFrame(self, fg_color=_CARD_BG, corner_radius=10,
                           border_width=1, border_color=_CARD_BORDER)
        hdr.grid(row=2, column=0, sticky="ew", pady=(0, 2))

        row = ctk.CTkFrame(hdr, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=8)

        for col_key, label, width, anchor in self._COLUMNS:
            lbl = ctk.CTkLabel(
                row, text=label,
                font=(FONT_PRIMARY, 11, "bold"),
                text_color=_TEXT_MUT if col_key != self._sort_col else _ACCENT,
                fg_color="transparent",
                width=width, anchor=anchor,
                cursor="hand2" if col_key else "arrow",
            )
            lbl.pack(side="left", padx=4)
            if col_key:
                lbl.bind("<Button-1>", lambda e, k=col_key: self._toggle_sort(k))

    # ── Table body ───────────────────────────────────────────────────────────

    def _build_table_body(self):
        self._list_frame = ctk.CTkScrollableFrame(
            self, fg_color=_CARD_BG, corner_radius=10,
            border_width=1, border_color=_CARD_BORDER,
            scrollbar_button_color=_CARD_BORDER,
            scrollbar_button_hover_color=_ACCENT,
        )
        self._list_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 8))
        self._list_frame.grid_columnconfigure(0, weight=1)

    # ── Feedback bar ─────────────────────────────────────────────────────────

    def _build_feedback_bar(self):
        self._feedback_var = tk.StringVar()
        self._feedback_lbl = ctk.CTkLabel(
            self, textvariable=self._feedback_var,
            font=(FONT_PRIMARY, 11),
            text_color=_SUCCESS, fg_color="transparent", anchor="e",
        )
        self._feedback_lbl.grid(row=4, column=0, sticky="e", pady=(0, 4))

    # ── Data loading & filtering ─────────────────────────────────────────────

    def _load(self):
        self._records = get_history(self._user_id)
        self._apply_filter()
        self._update_stats()

    def _apply_filter(self):
        q = self._filter_var.get().strip().lower()
        if q:
            self._filtered = [
                r for r in self._records
                if q in (r.get("gesture") or "").lower()
                or q in (r.get("translated_text") or "").lower()
            ]
        else:
            self._filtered = list(self._records)
        self._apply_sort()

    def _apply_sort(self):
        key = self._sort_col

        def _sort_key(r):
            v = r.get(key)
            return (v is None, v or "")

        self._filtered.sort(key=_sort_key, reverse=not self._sort_asc)
        self._populate_rows()

    def _toggle_sort(self, col_key: str):
        if self._sort_col == col_key:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col_key
            self._sort_asc = False
        self._apply_sort()

    # ── Row rendering ────────────────────────────────────────────────────────

    def _populate_rows(self):
        for w in self._list_frame.winfo_children():
            w.destroy()

        if not self._filtered:
            self._build_empty_state()
            return

        for i, rec in enumerate(self._filtered):
            self._build_row(i, rec)

    def _build_empty_state(self):
        wrap = ctk.CTkFrame(self._list_frame, fg_color="transparent")
        wrap.pack(expand=True, pady=50)

        ctk.CTkLabel(wrap, text="📭",
                     font=("Segoe UI Emoji", 36),
                     fg_color="transparent").pack()

        if self._records:
            msg  = "No records match your search."
            hint = ""
        else:
            msg = "No gesture history yet."
            enabled = get_setting("logging_enabled") == "1"
            hint = (
                "Start the Gesture Translator to begin logging."
                if enabled
                else "Enable gesture logging in Settings → Privacy & Data."
            )

        ctk.CTkLabel(wrap, text=msg,
                     font=(FONT_PRIMARY, 14, "bold"),
                     text_color=_TEXT_SEC,
                     fg_color="transparent").pack(pady=(10, 0))

        if hint:
            ctk.CTkLabel(wrap, text=hint,
                         font=(FONT_PRIMARY, 11),
                         text_color=_TEXT_MUT,
                         fg_color="transparent",
                         wraplength=340).pack(pady=(6, 0))

    def _build_row(self, index: int, rec: dict):
        iso = rec.get("logged_at", "")
        date_str, time_str = _fmt_datetime(iso)
        conf_bg, conf_fg, conf_text = _conf_badge(rec.get("confidence"))
        translated = rec.get("translated_text") or "—"
        gesture    = rec.get("gesture", "?")

        row_bg = _CARD_BG if index % 2 == 0 else _ROW_ALT

        row = ctk.CTkFrame(self._list_frame, fg_color=row_bg,
                           corner_radius=0, height=48)
        row.pack(fill="x")
        row.pack_propagate(False)

        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=14, pady=6)

        # # index
        ctk.CTkLabel(inner, text=str(index + 1),
                     font=(FONT_PRIMARY, 11), text_color=_TEXT_MUT,
                     fg_color="transparent", width=40, anchor="center",
                     ).pack(side="left", padx=4)

        # Gesture letter badge
        g_char = gesture[0].upper() if gesture else "?"
        ctk.CTkLabel(inner, text=g_char,
                     font=(FONT_PRIMARY, 13, "bold"),
                     text_color=_PURPLE_FG, fg_color=_PURPLE_BG,
                     width=32, height=32, corner_radius=8,
                     ).pack(side="left", padx=(4, 12))

        # Translated text
        ctk.CTkLabel(inner, text=translated,
                     font=(FONT_PRIMARY, 12), text_color=_TEXT_PRI,
                     fg_color="transparent", width=160, anchor="w",
                     ).pack(side="left", padx=4)

        # Confidence pill
        ctk.CTkLabel(inner, text=conf_text,
                     font=(FONT_PRIMARY, 11, "bold"),
                     text_color=conf_fg, fg_color=conf_bg,
                     corner_radius=99, padx=8, pady=2,
                     width=80, anchor="center",
                     ).pack(side="left", padx=4)

        # Date
        ctk.CTkLabel(inner, text=date_str,
                     font=(FONT_PRIMARY, 11), text_color=_TEXT_SEC,
                     fg_color="transparent", width=130, anchor="w",
                     ).pack(side="left", padx=4)

        # Time
        ctk.CTkLabel(inner, text=time_str,
                     font=(FONT_PRIMARY, 11), text_color=_TEXT_MUT,
                     fg_color="transparent", width=130, anchor="w",
                     ).pack(side="left", padx=4)

        # Row divider
        ctk.CTkFrame(self._list_frame, height=1,
                     fg_color=_CARD_BORDER, corner_radius=0).pack(fill="x")

    # ── Stats update ─────────────────────────────────────────────────────────

    def _update_stats(self):
        total   = len(self._records)
        today   = _today_count(self._records)
        enabled = get_setting("logging_enabled") == "1"

        self._stat_total.configure(text=str(total))
        self._stat_today.configure(text=str(today))
        self._stat_status.configure(
            text="ON" if enabled else "OFF",
            text_color=_GREEN_FG if enabled else _ERROR,
            fg_color=_GREEN_BG if enabled else _ERROR_BG,
        )

        if self._records:
            last_gesture = self._records[0].get("gesture", "—")
            self._stat_last.configure(text=last_gesture.upper())
        else:
            self._stat_last.configure(text="—")

    # ── Actions ──────────────────────────────────────────────────────────────

    def _handle_clear(self):
        if not self._records:
            self._show_feedback("No records to clear.", success=False)
            return

        dlg = ctk.CTkToplevel(self)
        dlg.title("Clear Gesture History")
        dlg.geometry("420x190")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.configure(fg_color=_CARD_BG)

        # Center over main window
        try:
            top = self.winfo_toplevel()
            mx, my = top.winfo_x(), top.winfo_y()
            mw, mh = top.winfo_width(), top.winfo_height()
            dlg.geometry(f"420x190+{mx + (mw - 420) // 2}+{my + (mh - 190) // 2}")
        except Exception:
            pass

        ctk.CTkLabel(
            dlg, text="Clear Gesture History",
            font=(FONT_PRIMARY, 16, "bold"),
            text_color=_TEXT_PRI, fg_color="transparent"
        ).pack(padx=24, pady=(20, 8), anchor="w")

        ctk.CTkLabel(
            dlg,
            text="This will permanently delete all saved gesture\n"
                 "history. This cannot be undone. Continue?",
            font=(FONT_PRIMARY, 12),
            text_color=_TEXT_SEC, fg_color="transparent",
            anchor="w", justify="left"
        ).pack(padx=24, fill="x")

        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=(20, 20))

        ctk.CTkButton(
            btn_row, text="Cancel",
            font=(FONT_PRIMARY, 12),
            fg_color="transparent", hover_color=_INPUT_BG,
            text_color=_TEXT_SEC,
            width=80, height=34, corner_radius=8,
            command=dlg.destroy
        ).pack(side="right", padx=(8, 0))

        def _on_confirm():
            dlg.destroy()
            success, msg = clear_history(self._user_id)
            if success:
                self._records  = []
                self._filtered = []
                self._populate_rows()
                self._update_stats()
                self._show_feedback("✓  All records cleared.")

        ctk.CTkButton(
            btn_row, text="Clear",
            font=(FONT_PRIMARY, 12, "bold"),
            fg_color=_ERROR,
            hover_color=("#C0392B", "#A93226"),
            text_color=("#FFFFFF", "#FFFFFF"),
            width=80, height=34, corner_radius=8,
            command=_on_confirm
        ).pack(side="right")

    def _export_csv(self):
        rows = self._filtered if self._filtered or self._filter_var.get().strip() else self._records
        if not rows:
            messagebox.showinfo("Export", "No records to export.")
            return

        default_name = f"gesture_log_{datetime.now().strftime('%Y-%m-%d')}.csv"
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=default_name,
            title="Save gesture log as CSV",
        )
        if not path:
            return

        try:
            fieldnames = ["#", "Gesture", "Translated", "Confidence", "Date", "Time"]
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(fieldnames)
                for i, rec in enumerate(rows):
                    date_str, time_str = _fmt_datetime(rec.get("logged_at", ""))
                    conf = rec.get("confidence")
                    conf_str = f"{int(conf * 100)}%" if conf is not None else "N/A"
                    writer.writerow([
                        i + 1,
                        rec.get("gesture", ""),
                        rec.get("translated_text", ""),
                        conf_str,
                        date_str,
                        time_str,
                    ])
            self._show_feedback(
                f"✓  Exported {len(rows)} records to CSV."
            )
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    # ── Feedback ─────────────────────────────────────────────────────────────

    def _show_feedback(self, msg: str, success: bool = True):
        color = _SUCCESS if success else _ERROR
        self._feedback_lbl.configure(text_color=color)
        self._feedback_var.set(msg)
        self.after(4000, lambda: self._feedback_var.set(""))

    # ── Auto-refresh ─────────────────────────────────────────────────────────

    def _schedule_refresh(self):
        self._refresh_job = self.after(self._REFRESH_MS, self._auto_refresh)

    def _auto_refresh(self):
        self._load()
        self._schedule_refresh()

    def destroy(self):
        if self._refresh_job is not None:
            self.after_cancel(self._refresh_job)
        super().destroy()
