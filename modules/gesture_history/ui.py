"""
modules/gesture_history/ui.py
Practice Log viewer — shows quiz_results rows for the logged-in user.
Columns: #  |  Source  |  Letter  |  Result  |  Confidence  |  Set  |  Date  |  Time
"""

import csv
from datetime import datetime, date
from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QScrollArea, QMessageBox, QFileDialog,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCursor

from core.theme import c
from core.ui_helpers import _set_font
from modules.gesture_history.backend import (
    get_quiz_results,
    clear_history,
    get_record_count,
    today_count,
)

# Badge palette
_PURPLE_BG = "#EEEDFE";  _PURPLE_FG = "#534AB7"
_GREEN_BG  = "#d1fae5";  _GREEN_FG  = "#1D9E75"
_YELLOW_BG = "#fef3c7";  _YELLOW_FG = "#b45309"
_RED_BG    = "#fee2e2";  _RED_FG    = "#DC2626"
_GRAY_BG   = "#F3F4F6";  _GRAY_FG   = "#6B7280"


def _fmt_datetime(iso: str) -> tuple[str, str]:
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%b %d, %Y"), dt.strftime("%I:%M %p").lstrip("0")
    except Exception:
        return iso, ""


def _result_badge(result: str) -> tuple[str, str, str]:
    """Return (bg, fg, label) for a result value."""
    r = (result or "").lower()
    if r == "correct":
        return _GREEN_BG, _GREEN_FG, "✓ Correct"
    if r == "missed":
        return _RED_BG, _RED_FG, "✗ Missed"
    if r == "skipped":
        return _YELLOW_BG, _YELLOW_FG, "→ Skipped"
    return _GRAY_BG, _GRAY_FG, result.capitalize()


def _conf_badge(conf) -> tuple[str, str, str]:
    if conf is None:
        return _GRAY_BG, _GRAY_FG, "—"
    pct = int(conf * 100)
    if pct >= 80:
        return _GREEN_BG, _GREEN_FG, f"{pct}%"
    if pct >= 60:
        return _YELLOW_BG, _YELLOW_FG, f"{pct}%"
    return _RED_BG, _RED_FG, f"{pct}%"


def _source_label(source: str) -> str:
    return "📷 Camera" if source == "camera_practice" else "🃏 Flashcard"


class GestureHistorySection(QWidget):
    """
    Self-contained practice-log viewer.
    Embed into GestureHistoryPage or any QWidget container.
    Pass username= (str) to scope records.
    """

    _REFRESH_MS = 10_000

    def __init__(self, parent=None, username: str = "", user_id=None, **kwargs):
        super().__init__(parent)
        # Accept both username= and legacy user_id= kwargs
        self._username = username
        self._records:  list[dict] = []
        self._filtered: list[dict] = []
        self._sort_col = "logged_at"
        self._sort_asc = False

        self.setStyleSheet("background: transparent;")
        self._build()
        self._load()

        try:
            from core.theme import ThemeSignal
            ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._load)
        self._refresh_timer.start(self._REFRESH_MS)

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._build_stats_bar(layout)
        self._build_toolbar(layout)
        self._build_table_header(layout)
        self._build_table_body(layout)
        self._build_feedback_bar(layout)

    # ── Stats bar ─────────────────────────────────────────────────────────────

    def _build_stats_bar(self, parent_layout):
        self._stats_bar = QFrame()
        self._stats_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 12px;
            }}
        """)
        layout = QHBoxLayout(self._stats_bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stat_total   = self._stat_card(layout, "Total Attempts", "0",  _PURPLE_FG, _PURPLE_BG)
        self._stat_today   = self._stat_card(layout, "Today",          "0",  _GREEN_FG,  _GREEN_BG)
        self._stat_correct = self._stat_card(layout, "Correct",        "0",  _GREEN_FG,  _GREEN_BG)
        self._stat_last    = self._stat_card(layout, "Last Letter",    "—",  c("info"),  c("info_bg"))

        parent_layout.addWidget(self._stats_bar)
        parent_layout.addSpacing(4)

    def _stat_card(self, parent_layout, label, value, fg, bg):
        cell = QWidget()
        c_layout = QVBoxLayout(cell)
        c_layout.setContentsMargins(16, 14, 16, 14)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        val_lbl = QLabel(value)
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val_lbl.setFixedSize(72, 36)
        val_lbl.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border-radius: 8px;
                font-family: 'Segoe UI';
                font-size: 20px;
                font-weight: bold;
                border: none;
            }}
        """)
        c_layout.addWidget(val_lbl, 0, Qt.AlignmentFlag.AlignCenter)
        c_layout.addSpacing(4)

        txt_lbl = QLabel(label)
        txt_lbl.setStyleSheet(f"color: {c('text_muted')}; border: none; background: transparent;")
        _set_font(txt_lbl, size=11)
        c_layout.addWidget(txt_lbl, 0, Qt.AlignmentFlag.AlignCenter)

        parent_layout.addWidget(cell, stretch=1)
        return val_lbl

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def _build_toolbar(self, parent_layout):
        self._toolbar = QFrame()
        self._toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 10px;
            }}
        """)
        layout = QHBoxLayout(self._toolbar)
        layout.setContentsMargins(14, 10, 14, 10)

        self._search_wrap = QFrame()
        self._search_wrap.setStyleSheet(f"""
            QFrame {{
                background-color: {c('input_bg')};
                border: 1px solid {c('border')};
                border-radius: 8px;
            }}
        """)
        s_layout = QHBoxLayout(self._search_wrap)
        s_layout.setContentsMargins(10, 0, 10, 0)

        self._search_icon = QLabel("⌕")
        self._search_icon.setStyleSheet(f"color: {c('text_muted')}; border: none; background: transparent;")

        self._filter_var = QLineEdit()
        self._filter_var.setPlaceholderText("Search letter, set, or result…")
        self._filter_var.setFixedWidth(240)
        self._filter_var.setFixedHeight(32)
        self._filter_var.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                background: transparent;
                color: {c('text_primary')};
                font-family: 'Segoe UI';
                font-size: 12px;
            }}
        """)
        self._filter_var.textChanged.connect(self._on_filter_changed)

        s_layout.addWidget(self._search_icon)
        s_layout.addWidget(self._filter_var)
        layout.addWidget(self._search_wrap)
        layout.addStretch()

        for label, slot, style in [
            ("Refresh",    self._load,         "outline"),
            ("Export CSV", self._export_csv,   "filled"),
            ("Clear all",  self._handle_clear, "danger"),
        ]:
            btn = QPushButton(label)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet(self._btn_style(style))
            btn.clicked.connect(slot)
            layout.addSpacing(8)
            layout.addWidget(btn)
            if label == "Refresh":
                self._btn_refresh = btn
            elif label == "Export CSV":
                self._btn_export = btn
            else:
                self._btn_clear = btn

        parent_layout.addWidget(self._toolbar)

    def _btn_style(self, kind: str) -> str:
        if kind == "filled":
            return f"""
                QPushButton {{
                    background-color: {c('accent')}; color: #FFFFFF;
                    border: none; border-radius: 8px;
                    font-family: 'Segoe UI'; font-size: 12px; font-weight: bold;
                    padding: 6px 14px;
                }}
                QPushButton:hover {{ background-color: {c('accent_hover')}; }}
            """
        if kind == "danger":
            return f"""
                QPushButton {{
                    background: transparent; color: {c('error')};
                    border: 1px solid {c('error')}; border-radius: 8px;
                    font-family: 'Segoe UI'; font-size: 12px; padding: 6px 14px;
                }}
                QPushButton:hover {{ background-color: {c('error_bg')}; }}
            """
        return f"""
            QPushButton {{
                background: transparent; color: {c('accent')};
                border: 1px solid {c('accent')}; border-radius: 8px;
                font-family: 'Segoe UI'; font-size: 12px; padding: 6px 14px;
            }}
            QPushButton:hover {{ background-color: {c('input_bg')}; }}
        """

    # ── Table header ──────────────────────────────────────────────────────────

    _COLUMNS = [
        ("",          "#",          40,  Qt.AlignmentFlag.AlignCenter),
        ("source",    "Source",     100, Qt.AlignmentFlag.AlignCenter),
        ("letter",    "Letter",     70,  Qt.AlignmentFlag.AlignCenter),
        ("result",    "Result",     110, Qt.AlignmentFlag.AlignCenter),
        ("confidence","Confidence", 100, Qt.AlignmentFlag.AlignCenter),
        ("set_name",  "Set",        150, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
        ("logged_at", "Date",       120, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
        ("logged_at", "Time",       100, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
    ]

    def _build_table_header(self, parent_layout):
        self._header_frame = QFrame()
        self._header_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 10px;
            }}
        """)
        layout = QHBoxLayout(self._header_frame)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(8)

        self._header_labels = []
        for col_key, label, width, anchor in self._COLUMNS:
            lbl = QLabel(label)
            lbl.setFixedWidth(width)
            lbl.setAlignment(anchor)
            color = c('accent') if col_key == self._sort_col else c('text_muted')
            lbl.setStyleSheet(f"color: {color}; border: none; background: transparent;")
            _set_font(lbl, size=11, bold=True)

            if col_key:
                lbl.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                def _make_handler(k):
                    def handler(e):
                        if e.button() == Qt.MouseButton.LeftButton:
                            self._toggle_sort(k)
                    return handler
                lbl.mousePressEvent = _make_handler(col_key)

            layout.addWidget(lbl)
            self._header_labels.append((col_key, lbl))

        layout.addStretch()
        parent_layout.addWidget(self._header_frame)

    # ── Table body ────────────────────────────────────────────────────────────

    def _build_table_body(self, parent_layout):
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 10px;
            }}
            QScrollBar:vertical {{
                background: {c('bg_primary')}; width: 10px;
            }}
            QScrollBar::handle:vertical {{
                background: {c('border')}; border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {c('accent')};
            }}
        """)

        self._list_frame = QWidget()
        self._list_frame.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_frame)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._scroll_area.setWidget(self._list_frame)
        parent_layout.addWidget(self._scroll_area, stretch=1)

    # ── Feedback bar ──────────────────────────────────────────────────────────

    def _build_feedback_bar(self, parent_layout):
        self._feedback_lbl = QLabel("")
        self._feedback_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._feedback_lbl.setStyleSheet(f"color: {c('success')}; border: none; background: transparent;")
        _set_font(self._feedback_lbl, size=11)
        parent_layout.addWidget(self._feedback_lbl)

        self._feedback_timer = QTimer(self)
        self._feedback_timer.setSingleShot(True)
        self._feedback_timer.timeout.connect(lambda: self._feedback_lbl.setText(""))

    # ── Data ──────────────────────────────────────────────────────────────────

    def _load(self):
        self._records = get_quiz_results(self._username)
        self._apply_filter()
        self._update_stats()

    def _on_filter_changed(self, text):
        self._apply_filter()

    def _apply_filter(self):
        q = self._filter_var.text().strip().lower()
        if q:
            self._filtered = [
                r for r in self._records
                if q in (r.get("letter") or "").lower()
                or q in (r.get("result") or "").lower()
                or q in (r.get("set_name") or "").lower()
                or q in (r.get("source") or "").lower()
            ]
        else:
            self._filtered = list(self._records)
        self._apply_sort()

    def _apply_sort(self):
        key = self._sort_col

        def _sk(r):
            v = r.get(key)
            return (v is None, v or "")

        self._filtered.sort(key=_sk, reverse=not self._sort_asc)

        for col_key, lbl in self._header_labels:
            if col_key:
                color = c('accent') if col_key == self._sort_col else c('text_muted')
                lbl.setStyleSheet(f"color: {color}; border: none; background: transparent;")

        self._populate_rows()

    def _toggle_sort(self, col_key: str):
        if self._sort_col == col_key:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col_key
            self._sort_asc = False
        self._apply_sort()

    # ── Rows ──────────────────────────────────────────────────────────────────

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _populate_rows(self):
        self._clear_layout(self._list_layout)
        if not self._filtered:
            self._build_empty_state()
            return
        for i, rec in enumerate(self._filtered):
            self._build_row(i, rec)

    def _build_empty_state(self):
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 50, 0, 50)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("—")
        icon.setStyleSheet("font-size: 36px; background: transparent; border: none; color: #9CA3AF;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        if self._records:
            msg  = "No records match your search."
            hint = ""
        else:
            msg  = "No practice records yet."
            hint = "Complete a Camera Practice or Flashcard Quiz session to see your history here."

        msg_lbl = QLabel(msg)
        msg_lbl.setStyleSheet(f"color: {c('text_secondary')}; background: transparent; border: none;")
        _set_font(msg_lbl, size=14, bold=True)
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg_lbl)

        if hint:
            hint_lbl = QLabel(hint)
            hint_lbl.setStyleSheet(f"color: {c('text_muted')}; background: transparent; border: none;")
            _set_font(hint_lbl, size=11)
            hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hint_lbl.setWordWrap(True)
            layout.addWidget(hint_lbl)

        self._list_layout.addWidget(wrap)

    def _build_row(self, index: int, rec: dict):
        iso       = rec.get("logged_at", "")
        date_str, time_str = _fmt_datetime(iso)
        res_bg, res_fg, res_text = _result_badge(rec.get("result", ""))
        conf_bg, conf_fg, conf_text = _conf_badge(rec.get("confidence"))
        source    = _source_label(rec.get("source", ""))
        letter    = (rec.get("letter") or "?").upper()
        set_name  = rec.get("set_name") or "—"

        row_bg = c("bg_primary") if index % 2 == 0 else c("bg_secondary")

        row = QFrame()
        row.setFixedHeight(48)
        row.setStyleSheet(f"background-color: {row_bg}; border: none;")

        layout = QHBoxLayout(row)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(8)

        def _lbl(text, width, align=Qt.AlignmentFlag.AlignVCenter, bold=False, color=None):
            l = QLabel(text)
            l.setFixedWidth(width)
            l.setAlignment(align)
            l.setStyleSheet(f"color: {color or c('text_primary')}; background: transparent;")
            _set_font(l, size=11, bold=bold)
            return l

        def _badge(text, width, bg, fg):
            wrap = QWidget()
            wrap.setFixedWidth(width)
            wl = QHBoxLayout(wrap)
            wl.setContentsMargins(0, 0, 0, 0)
            wl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            b = QLabel(text)
            b.setAlignment(Qt.AlignmentFlag.AlignCenter)
            b.setStyleSheet(
                f"background-color: {bg}; color: {fg}; border-radius: 10px; "
                f"padding: 2px 8px; font-weight: bold; font-family: 'Segoe UI'; font-size: 11px;"
            )
            wl.addWidget(b)
            return wrap

        layout.addWidget(_lbl(str(index + 1), 40, Qt.AlignmentFlag.AlignCenter, color=c("text_muted")))
        layout.addWidget(_lbl(source, 100, Qt.AlignmentFlag.AlignCenter))
        layout.addWidget(_badge(letter, 70, _PURPLE_BG, _PURPLE_FG))
        layout.addWidget(_badge(res_text, 110, res_bg, res_fg))
        layout.addWidget(_badge(conf_text, 100, conf_bg, conf_fg))
        layout.addWidget(_lbl(set_name, 150, color=c("text_secondary")))
        layout.addWidget(_lbl(date_str, 120, color=c("text_secondary")))
        layout.addWidget(_lbl(time_str, 100, color=c("text_muted")))
        layout.addStretch()

        self._list_layout.addWidget(row)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background-color: {c('border')}; border: none;")
        self._list_layout.addWidget(div)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def _update_stats(self):
        total   = len(self._records)
        t_today = today_count(self._username)
        correct = sum(1 for r in self._records if r.get("result") == "correct")

        self._stat_total.setText(str(total))
        self._stat_today.setText(str(t_today))
        self._stat_correct.setText(str(correct))

        if self._records:
            self._stat_last.setText((self._records[0].get("letter") or "—").upper())
        else:
            self._stat_last.setText("—")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _handle_clear(self):
        if not self._records:
            self._show_feedback("No records to clear.", success=False)
            return
        reply = QMessageBox.question(
            self, "Clear Practice History",
            "Permanently delete all saved practice records? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = clear_history(self._username)
            if success:
                self._records  = []
                self._filtered = []
                self._populate_rows()
                self._update_stats()
                self._show_feedback("✓ All records cleared.")

    def _export_csv(self):
        rows = self._filtered if (self._filtered or self._filter_var.text().strip()) else self._records
        if not rows:
            QMessageBox.information(self, "Export", "No records to export.")
            return

        default_name = f"practice_log_{datetime.now().strftime('%Y-%m-%d')}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save practice log as CSV", default_name,
            "CSV files (*.csv);;All files (*.*)",
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["#", "Source", "Letter", "Result", "Confidence", "Set", "Date", "Time"])
                for i, rec in enumerate(rows):
                    date_str, time_str = _fmt_datetime(rec.get("logged_at", ""))
                    conf = rec.get("confidence")
                    conf_str = f"{int(conf * 100)}%" if conf is not None else "—"
                    writer.writerow([
                        i + 1,
                        rec.get("source", ""),
                        rec.get("letter", ""),
                        rec.get("result", ""),
                        conf_str,
                        rec.get("set_name") or "—",
                        date_str,
                        time_str,
                    ])
            self._show_feedback(f"✓ Exported {len(rows)} records to CSV.")
        except Exception as e:
            print(f"[history] CSV export error: {e}")
            QMessageBox.critical(self, "Export failed", "Could not save the file.")

    # ── Feedback / theme ──────────────────────────────────────────────────────

    def _show_feedback(self, msg: str, success: bool = True):
        color = c("success") if success else c("error")
        self._feedback_lbl.setStyleSheet(f"color: {color}; border: none; background: transparent;")
        self._feedback_lbl.setText(msg)
        self._feedback_timer.start(4000)

    def _on_theme_changed(self, _):
        self._update_styles()

    def _update_styles(self):
        if hasattr(self, '_stats_bar') and self._stats_bar:
            self._stats_bar.setStyleSheet(f"""
                QFrame {{
                    background-color: {c('bg_primary')};
                    border: 1px solid {c('border')};
                    border-radius: 12px;
                }}
            """)
        if hasattr(self, '_toolbar') and self._toolbar:
            self._toolbar.setStyleSheet(f"""
                QFrame {{
                    background-color: {c('bg_primary')};
                    border: 1px solid {c('border')};
                    border-radius: 10px;
                }}
            """)
        if hasattr(self, '_header_frame') and self._header_frame:
            self._header_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {c('bg_primary')};
                    border: 1px solid {c('border')};
                    border-radius: 10px;
                }}
            """)
        if hasattr(self, '_scroll_area') and self._scroll_area:
            self._scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    background-color: {c('bg_primary')};
                    border: 1px solid {c('border')};
                    border-radius: 10px;
                }}
                QScrollBar:vertical {{
                    background: {c('bg_primary')}; width: 10px;
                }}
                QScrollBar::handle:vertical {{
                    background: {c('border')}; border-radius: 5px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background: {c('accent')};
                }}
            """)
        if hasattr(self, '_btn_refresh'):
            self._btn_refresh.setStyleSheet(self._btn_style("outline"))
        if hasattr(self, '_btn_export'):
            self._btn_export.setStyleSheet(self._btn_style("filled"))
        if hasattr(self, '_btn_clear'):
            self._btn_clear.setStyleSheet(self._btn_style("danger"))
        self._load()