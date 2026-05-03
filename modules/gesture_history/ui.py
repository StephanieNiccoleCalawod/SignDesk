"""
modules/gesture_history/ui.py
==============================
GestureHistorySection — the full-page history log viewer widget.
PyQt6 migration.
"""

import csv
from datetime import datetime, date
from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QScrollArea, QDialog, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCursor

from core.theme import c
from core.ui_helpers import _set_font
from modules.gesture_history.backend import (
    get_history,
    clear_history,
    get_record_count,
    get_setting,
)

# Extra badge palette
_PURPLE_BG = "#EEEDFE"
_PURPLE_FG = "#534AB7"
_GREEN_BG  = "#d1fae5"
_GREEN_FG  = "#1D9E75"
_YELLOW_BG = "#fef3c7"
_YELLOW_FG = "#b45309"

def _fmt_datetime(iso: str) -> tuple[str, str]:
    """Return (date_str, time_str) from an ISO-8601 timestamp string."""
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%b %d, %Y"), dt.strftime("%I:%M:%S %p").lstrip("0")
    except Exception:
        return iso, ""

def _conf_badge(conf, dark=False) -> tuple[str, str, str]:
    """Return (bg, fg, label) for a confidence value."""
    if conf is None:
        return c("input_bg", dark), c("text_muted", dark), "N/A"
    pct = int(conf * 100)
    if pct >= 80:
        return _GREEN_BG, _GREEN_FG, f"{pct}%"
    if pct >= 60:
        return _YELLOW_BG, _YELLOW_FG, f"{pct}%"
    return c("error_bg", dark), c("error", dark), f"{pct}%"

def _today_count(records: list[dict]) -> int:
    today = date.today().isoformat()
    return sum(1 for r in records if r.get("logged_at", "").startswith(today))

class GestureHistorySection(QWidget):
    """
    Self-contained gesture-log viewer.
    Designed to be embedded into GestureHistoryPage or any QWidget container.
    """

    _REFRESH_MS = 10_000   # auto-refresh interval

    def __init__(self, parent=None, user_id: int | None = None, **kwargs):
        super().__init__(parent)
        self._user_id   = user_id
        self._records:  list[dict] = []
        self._filtered: list[dict] = []
        self._sort_col  = "logged_at"
        self._sort_asc  = False
        
        self.setStyleSheet("background: transparent;")
        
        self._build()
        self._load()
        
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._auto_refresh)
        self._refresh_timer.start(self._REFRESH_MS)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._build_stats_bar(layout)
        self._build_toolbar(layout)
        self._build_table_header(layout)
        self._build_table_body(layout)
        self._build_feedback_bar(layout)

    # ── Stats bar ────────────────────────────────────────────────────────────

    def _build_stats_bar(self, parent_layout):
        bar = QFrame()
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 12px;
            }}
        """)
        
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stat_total  = self._stat_card(layout, "Total Records", "0", _PURPLE_FG, _PURPLE_BG)
        self._stat_today  = self._stat_card(layout, "Today", "0", _GREEN_FG, _GREEN_BG)
        self._stat_status = self._stat_card(layout, "Logging", "—", _YELLOW_FG, _YELLOW_BG)
        self._stat_last   = self._stat_card(layout, "Last Gesture", "—", c("info"), c("info_bg"))

        parent_layout.addWidget(bar)
        parent_layout.addSpacing(4)

    def _stat_card(self, parent_layout, label, value, fg, bg):
        cell = QWidget()
        c_layout = QVBoxLayout(cell)
        c_layout.setContentsMargins(16, 14, 16, 14)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        val_lbl = QLabel(value)
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val_lbl.setFixedSize(64, 36)
        val_lbl.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border-radius: 8px;
                font-family: 'Segoe UI';
                font-size: 22px;
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

    # ── Toolbar ──────────────────────────────────────────────────────────────

    def _build_toolbar(self, parent_layout):
        bar = QFrame()
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 10px;
            }}
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 10, 14, 10)
        
        # Search box
        search_wrap = QFrame()
        search_wrap.setStyleSheet(f"""
            QFrame {{
                background-color: {c('input_bg')};
                border: 1px solid {c('border')};
                border-radius: 8px;
            }}
        """)
        s_layout = QHBoxLayout(search_wrap)
        s_layout.setContentsMargins(10, 0, 10, 0)
        
        s_icon = QLabel("🔍")
        s_icon.setStyleSheet(f"color: {c('text_muted')}; font-family: 'Segoe UI Emoji'; border: none; background: transparent;")
        
        self._filter_var = QLineEdit()
        self._filter_var.setPlaceholderText("Search gesture or translation…")
        self._filter_var.setFixedWidth(230)
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
        
        s_layout.addWidget(s_icon)
        s_layout.addWidget(self._filter_var)
        layout.addWidget(search_wrap)
        
        layout.addStretch()

        # Action buttons
        btn_refresh = QPushButton("↻ Refresh")
        btn_refresh.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {c('accent')};
                border: 1px solid {c('accent')};
                border-radius: 8px;
                font-family: 'Segoe UI';
                font-size: 12px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {c('input_bg')};
            }}
        """)
        btn_refresh.clicked.connect(self._load)
        layout.addWidget(btn_refresh)
        
        layout.addSpacing(8)

        btn_export = QPushButton("⬇ Export CSV")
        btn_export.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_export.setStyleSheet(f"""
            QPushButton {{
                background-color: {c('accent')};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-family: 'Segoe UI';
                font-size: 12px;
                font-weight: bold;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {c('accent_hover')};
            }}
        """)
        btn_export.clicked.connect(self._export_csv)
        layout.addWidget(btn_export)
        
        layout.addSpacing(8)

        btn_clear = QPushButton("🗑 Clear all")
        btn_clear.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_clear.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {c('error')};
                border: 1px solid {c('error')};
                border-radius: 8px;
                font-family: 'Segoe UI';
                font-size: 12px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: #4A2222;
                color: #FFFFFF;
            }}
        """)
        btn_clear.clicked.connect(self._handle_clear)
        layout.addWidget(btn_clear)

        parent_layout.addWidget(bar)

    # ── Table header ─────────────────────────────────────────────────────────

    _COLUMNS = [
        ("",               "#",          40,  Qt.AlignmentFlag.AlignCenter),
        ("gesture",        "Gesture",    70,  Qt.AlignmentFlag.AlignCenter),
        ("translated_text","Translated", 160, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
        ("confidence",     "Confidence", 110, Qt.AlignmentFlag.AlignCenter),
        ("logged_at",      "Date",       130, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
        ("logged_at",      "Time",       130, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
    ]

    def _build_table_header(self, parent_layout):
        hdr = QFrame()
        hdr.setStyleSheet(f"""
            QFrame {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 10px;
            }}
        """)
        layout = QHBoxLayout(hdr)
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
                def make_click_handler(k):
                    def handler(e):
                        if e.button() == Qt.MouseButton.LeftButton:
                            self._toggle_sort(k)
                    return handler
                lbl.mousePressEvent = make_click_handler(col_key)
            
            layout.addWidget(lbl)
            self._header_labels.append((col_key, lbl))

        layout.addStretch()
        parent_layout.addWidget(hdr)

    # ── Table body ───────────────────────────────────────────────────────────

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
                background: {c('bg_primary')};
                width: 10px;
            }}
            QScrollBar::handle:vertical {{
                background: {c('border')};
                border-radius: 5px;
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

    # ── Feedback bar ─────────────────────────────────────────────────────────

    def _build_feedback_bar(self, parent_layout):
        self._feedback_lbl = QLabel("")
        self._feedback_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._feedback_lbl.setStyleSheet(f"color: {c('success')}; border: none; background: transparent;")
        _set_font(self._feedback_lbl, size=11)
        parent_layout.addWidget(self._feedback_lbl)
        
        self._feedback_timer = QTimer(self)
        self._feedback_timer.setSingleShot(True)
        self._feedback_timer.timeout.connect(lambda: self._feedback_lbl.setText(""))

    # ── Data loading & filtering ─────────────────────────────────────────────

    def _load(self):
        self._records = get_history(self._user_id)
        self._apply_filter()
        self._update_stats()

    def _on_filter_changed(self, text):
        self._apply_filter()

    def _apply_filter(self):
        q = self._filter_var.text().strip().lower()
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
        
        # Update header styling
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

    # ── Row rendering ────────────────────────────────────────────────────────

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

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

        icon = QLabel("📭")
        icon.setStyleSheet("font-family: 'Segoe UI Emoji'; font-size: 36px; background: transparent; border: none;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

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
        iso = rec.get("logged_at", "")
        date_str, time_str = _fmt_datetime(iso)
        conf_bg, conf_fg, conf_text = _conf_badge(rec.get("confidence"))
        translated = rec.get("translated_text") or "—"
        gesture    = rec.get("gesture", "?")

        # Alternate background colors
        # Since we don't have a reliable dark mode boolean here, we will just use theme values directly
        row_bg = c("bg_primary") if index % 2 == 0 else c("bg_secondary")

        row = QFrame()
        row.setFixedHeight(48)
        row.setStyleSheet(f"background-color: {row_bg}; border: none;")
        
        layout = QHBoxLayout(row)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(8)

        # index
        lbl_idx = QLabel(str(index + 1))
        lbl_idx.setFixedWidth(40)
        lbl_idx.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_idx.setStyleSheet(f"color: {c('text_muted')}; background: transparent;")
        _set_font(lbl_idx, size=11)
        layout.addWidget(lbl_idx)

        # Gesture letter badge
        g_char = gesture[0].upper() if gesture else "?"
        g_badge = QLabel(g_char)
        g_badge.setFixedSize(32, 32)
        g_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        g_badge.setStyleSheet(f"background-color: {_PURPLE_BG}; color: {_PURPLE_FG}; border-radius: 8px; font-weight: bold; font-family: 'Segoe UI'; font-size: 13px;")
        layout.addWidget(g_badge)

        # Translated text
        lbl_trans = QLabel(translated)
        lbl_trans.setFixedWidth(160)
        lbl_trans.setStyleSheet(f"color: {c('text_primary')}; background: transparent;")
        _set_font(lbl_trans, size=12)
        layout.addWidget(lbl_trans)

        # Confidence pill
        conf_wrap = QWidget()
        conf_wrap.setFixedWidth(110)
        cw_layout = QVBoxLayout(conf_wrap)
        cw_layout.setContentsMargins(0, 0, 0, 0)
        cw_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_conf = QLabel(conf_text)
        lbl_conf.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_conf.setStyleSheet(f"background-color: {conf_bg}; color: {conf_fg}; border-radius: 12px; padding: 2px 8px; font-weight: bold; font-family: 'Segoe UI'; font-size: 11px;")
        cw_layout.addWidget(lbl_conf)
        layout.addWidget(conf_wrap)

        # Date
        lbl_date = QLabel(date_str)
        lbl_date.setFixedWidth(130)
        lbl_date.setStyleSheet(f"color: {c('text_secondary')}; background: transparent;")
        _set_font(lbl_date, size=11)
        layout.addWidget(lbl_date)

        # Time
        lbl_time = QLabel(time_str)
        lbl_time.setFixedWidth(130)
        lbl_time.setStyleSheet(f"color: {c('text_muted')}; background: transparent;")
        _set_font(lbl_time, size=11)
        layout.addWidget(lbl_time)

        layout.addStretch()

        self._list_layout.addWidget(row)
        
        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background-color: {c('border')}; border: none;")
        self._list_layout.addWidget(div)

    # ── Stats update ─────────────────────────────────────────────────────────

    def _update_stats(self):
        total   = len(self._records)
        today   = _today_count(self._records)
        enabled = get_setting("logging_enabled") == "1"

        self._stat_total.setText(str(total))
        self._stat_today.setText(str(today))
        
        status_txt = "ON" if enabled else "OFF"
        status_fg = _GREEN_FG if enabled else c("error")
        status_bg = _GREEN_BG if enabled else c("error_bg")
        self._stat_status.setText(status_txt)
        self._stat_status.setStyleSheet(f"background-color: {status_bg}; color: {status_fg}; border-radius: 8px; font-family: 'Segoe UI'; font-size: 22px; font-weight: bold; border: none;")

        if self._records:
            last_gesture = self._records[0].get("gesture", "—")
            self._stat_last.setText(last_gesture.upper())
        else:
            self._stat_last.setText("—")

    # ── Actions ──────────────────────────────────────────────────────────────

    def _handle_clear(self):
        if not self._records:
            self._show_feedback("No records to clear.", success=False)
            return

        reply = QMessageBox.question(
            self, "Clear Gesture History", 
            "This will permanently delete all saved gesture history. This cannot be undone. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = clear_history(self._user_id)
            if success:
                self._records  = []
                self._filtered = []
                self._populate_rows()
                self._update_stats()
                self._show_feedback("✓ All records cleared.")

    def _export_csv(self):
        rows = self._filtered if self._filtered or self._filter_var.text().strip() else self._records
        if not rows:
            QMessageBox.information(self, "Export", "No records to export.")
            return

        default_name = f"gesture_log_{datetime.now().strftime('%Y-%m-%d')}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save gesture log as CSV",
            default_name,
            "CSV files (*.csv);;All files (*.*)"
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
            self._show_feedback(f"✓ Exported {len(rows)} records to CSV.")
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))

    # ── Feedback ─────────────────────────────────────────────────────────────

    def _show_feedback(self, msg: str, success: bool = True):
        color = c("success") if success else c("error")
        self._feedback_lbl.setStyleSheet(f"color: {color}; border: none; background: transparent;")
        self._feedback_lbl.setText(msg)
        self._feedback_timer.start(4000)

    # ── Auto-refresh ─────────────────────────────────────────────────────────

    def _auto_refresh(self):
        self._load()
