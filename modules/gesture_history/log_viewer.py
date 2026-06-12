

import csv
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QScrollArea, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QCursor, QPainter, QLinearGradient, QColor

from core.theme import c, ThemeSignal
from core.ui_helpers import _set_font
from modules.gesture_history.backend import (
    get_history,
    clear_history,
    get_record_count,
    get_setting,
)

C_PURPLE_BG  = "#EEEDFE"
C_PURPLE_FG  = "#534AB7"
C_GREEN_BG   = "#d1fae5"
C_GREEN_FG   = "#1D9E75"
C_YELLOW_BG  = "#fef3c7"
C_YELLOW_FG  = "#b45309"




def _fmt_datetime(iso: str) -> tuple[str, str]:
    """Return (date_str, time_str) from ISO timestamp."""
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%b %d, %Y"), dt.strftime("%I:%M:%S %p").lstrip("0")
    except Exception:
        return iso, ""

def _conf_colors(conf, dark=False) -> tuple[str, str, str]:
    """Return (bg, fg, text) for a confidence value."""
    if conf is None:
        return c("input_bg", dark), c("text_muted", dark), "N/A"
    if conf >= 0.80:
        return C_GREEN_BG, C_GREEN_FG, f"{int(conf * 100)}%"
    return C_YELLOW_BG, C_YELLOW_FG, f"{int(conf * 100)}%"

class GestureLogViewerPage(QWidget):
    """
    Standalone full page — push onto app via app.show_gesture_log_viewer(username).
    Constructor matches all other SignDesk pages: (parent, app, username).
    """

    def __init__(self, parent, app, username: str):
        super().__init__(parent)
        self._app      = app
        self._username = username
        self._user_id  = getattr(app, 'current_user_id', None)
        self._records: list[dict] = []
        self._filtered: list[dict] = []
        self.setStyleSheet(f"background-color: {c('bg_secondary')};")
        
        self._build()
        self._load_records()

        try:
            ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(10)

        # ── Title row ─────────────────────────────────────
        title_row = QHBoxLayout()

        self._btn_back = QPushButton("←  Back to Settings")
        self._btn_back.setFixedHeight(32)
        self._btn_back.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_back.setStyleSheet(f"""
            QPushButton {{
                background-color: #495086;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-family: 'Segoe UI';
                font-size: 11px;
                font-weight: bold;
                padding: 0px 12px;
            }}
            QPushButton:hover {{
                background-color: #3F4678;
            }}
        """)
        self._btn_back.clicked.connect(self._on_back)
        title_row.addWidget(self._btn_back)
        title_row.addSpacing(14)

        self._title_lbl = QLabel("Saved Gesture Log")
        self._title_lbl.setStyleSheet(f"color: {c('text_primary')}; background: transparent;")
        _set_font(self._title_lbl, size=20, bold=True)
        title_row.addWidget(self._title_lbl)
        
        title_row.addSpacing(10)
        
        self._count_badge = QLabel("0 records")
        self._count_badge.setStyleSheet(f"background-color: {C_PURPLE_BG}; color: {C_PURPLE_FG}; border-radius: 10px; padding: 3px 10px; font-weight: bold; font-family: 'Segoe UI'; font-size: 11px;")
        title_row.addWidget(self._count_badge)
        
        title_row.addStretch()
        layout.addLayout(title_row)

        self._desc_lbl = QLabel("All gesture logs stored locally on this device.")
        self._desc_lbl.setStyleSheet(f"color: {c('text_muted')}; background: transparent;")
        _set_font(self._desc_lbl, size=11)
        layout.addWidget(self._desc_lbl)
        layout.addSpacing(4)

        # ── Toolbar ───────────────────────────────────────
        self._toolbar = QFrame()
        self._toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 10px;
            }}
        """)
        tb_layout = QHBoxLayout(self._toolbar)
        tb_layout.setContentsMargins(14, 12, 14, 12)

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
        self._filter_var.setPlaceholderText("Filter by gesture or text…")
        self._filter_var.setFixedWidth(220)
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
        self._filter_var.textChanged.connect(self._apply_filter)
        
        s_layout.addWidget(self._search_icon)
        s_layout.addWidget(self._filter_var)
        tb_layout.addWidget(self._search_wrap)
        
        tb_layout.addStretch()

        self._download_btn = QPushButton("⬇ Export CSV")
        self._download_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._download_btn.setStyleSheet(f"""
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
        self._download_btn.clicked.connect(self._export_csv)
        tb_layout.addWidget(self._download_btn)
        
        tb_layout.addSpacing(8)

        self._btn_clear = QPushButton("🗑 Clear all")
        self._btn_clear.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_clear.setStyleSheet(f"""
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
        self._btn_clear.clicked.connect(self._handle_clear)
        tb_layout.addWidget(self._btn_clear)

        layout.addWidget(self._toolbar)

        # ── Table header ──────────────────────────────────
        self._header_frame = QFrame()
        self._header_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 10px;
            }}
        """)
        h_layout = QHBoxLayout(self._header_frame)
        h_layout.setContentsMargins(14, 8, 14, 8)
        h_layout.setSpacing(8)

        cols = [
            ("#", 40, Qt.AlignmentFlag.AlignCenter),
            ("Gesture", 70, Qt.AlignmentFlag.AlignCenter),
            ("Translated", 160, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            ("Confidence", 110, Qt.AlignmentFlag.AlignCenter),
            ("Date", 130, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            ("Time", 130, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
        ]

        for label, width, anchor in cols:
            lbl = QLabel(label)
            lbl.setFixedWidth(width)
            lbl.setAlignment(anchor)
            lbl.setStyleSheet(f"color: {c('text_muted')}; border: none; background: transparent;")
            _set_font(lbl, size=11, bold=True)
            h_layout.addWidget(lbl)
        h_layout.addStretch()

        layout.addWidget(self._header_frame)

        # ── Scrollable rows ───────────────────────────────
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 10px;
            }}
        """)

        self._list_frame = QWidget()
        self._list_frame.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_frame)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._scroll_area.setWidget(self._list_frame)
        layout.addWidget(self._scroll_area, stretch=1)

        # ── Feedback bar ──────────────────────────────────
        self._feedback_lbl = QLabel("")
        self._feedback_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._feedback_lbl.setStyleSheet(f"color: {c('success')}; border: none; background: transparent;")
        _set_font(self._feedback_lbl, size=11)
        layout.addWidget(self._feedback_lbl)
        
        self._feedback_timer = QTimer(self)
        self._feedback_timer.setSingleShot(True)
        self._feedback_timer.timeout.connect(lambda: self._feedback_lbl.setText(""))

    # ── Logic ─────────────────────────────────────────────────────────────────

    def _load_records(self):
        self._records = get_history(self._user_id)
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
            
        self._count_badge.setText(f"{len(self._filtered)} records")
        self._populate_rows()

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
            wrap = QWidget()
            w_layout = QVBoxLayout(wrap)
            w_layout.setContentsMargins(0, 40, 0, 40)
            w_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl = QLabel("📭 No records found.")
            lbl.setStyleSheet(f"color: {c('text_secondary')}; font-family: 'Segoe UI'; font-size: 14px; font-weight: bold; background: transparent; border: none;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            w_layout.addWidget(lbl)
            self._list_layout.addWidget(wrap)
            return

        for i, rec in enumerate(self._filtered):
            iso = rec.get("logged_at", "")
            date_str, time_str = _fmt_datetime(iso)
            conf_bg, conf_fg, conf_text = _conf_colors(rec.get("confidence"))
            translated = rec.get("translated_text") or "—"
            gesture    = rec.get("gesture", "?")

            row_bg = c("bg_primary") if i % 2 == 0 else c("bg_secondary")

            row = QFrame()
            row.setFixedHeight(48)
            row.setStyleSheet(f"background-color: {row_bg}; border: none;")
            
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(14, 0, 14, 0)
            r_layout.setSpacing(8)

            # index
            lbl_idx = QLabel(str(i + 1))
            lbl_idx.setFixedWidth(40)
            lbl_idx.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_idx.setStyleSheet(f"color: {c('text_muted')}; background: transparent;")
            _set_font(lbl_idx, size=11)
            r_layout.addWidget(lbl_idx)

            # Gesture letter badge
            g_char = gesture[0].upper() if gesture else "?"
            g_badge = QLabel(g_char)
            g_badge.setFixedSize(32, 32)
            g_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            g_badge.setStyleSheet(f"background-color: {C_PURPLE_BG}; color: {C_PURPLE_FG}; border-radius: 8px; font-weight: bold; font-family: 'Segoe UI'; font-size: 13px;")
            r_layout.addWidget(g_badge)

            # Translated text
            lbl_trans = QLabel(translated)
            lbl_trans.setFixedWidth(160)
            lbl_trans.setStyleSheet(f"color: {c('text_primary')}; background: transparent;")
            _set_font(lbl_trans, size=12)
            r_layout.addWidget(lbl_trans)

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
            r_layout.addWidget(conf_wrap)

            # Date
            lbl_date = QLabel(date_str)
            lbl_date.setFixedWidth(130)
            lbl_date.setStyleSheet(f"color: {c('text_secondary')}; background: transparent;")
            _set_font(lbl_date, size=11)
            r_layout.addWidget(lbl_date)

            # Time
            lbl_time = QLabel(time_str)
            lbl_time.setFixedWidth(130)
            lbl_time.setStyleSheet(f"color: {c('text_muted')}; background: transparent;")
            _set_font(lbl_time, size=11)
            r_layout.addWidget(lbl_time)

            r_layout.addStretch()
            self._list_layout.addWidget(row)
            
            # Divider
            div = QFrame()
            div.setFixedHeight(1)
            div.setStyleSheet(f"background-color: {c('border')}; border: none;")
            self._list_layout.addWidget(div)

    def _show_feedback(self, msg: str, success: bool = True):
        color = c("success") if success else c("error")
        self._feedback_lbl.setStyleSheet(f"color: {color}; border: none; background: transparent;")
        self._feedback_lbl.setText(msg)
        self._feedback_timer.start(4000)

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
                self._count_badge.setText("0 records")
                self._populate_rows()
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
            print(f"[history] CSV export error: {e}")
            QMessageBox.critical(self, "Export failed", "Could not export the file. Please check the file path and try again.")

    def _on_back(self):
        if hasattr(self._app, 'show_settings'):
            self._app.show_settings(self._username)

    def _on_logout(self):
        reply = QMessageBox.question(
            self, "Logout", "Are you sure you want to log out?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._app.show_login()

    def _on_theme_changed(self, is_dark: bool):
        self._update_styles()
      
    def _update_styles(self):
        self.setStyleSheet(f"background-color: {c('bg_secondary')};")
        if hasattr(self, '_btn_back') and self._btn_back:
            self._btn_back.setStyleSheet(f"""
                QPushButton {{
                    background-color: #495086;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 6px;
                    font-family: 'Segoe UI';
                    font-size: 11px;
                    font-weight: bold;
                    padding: 0px 12px;
                }}
                QPushButton:hover {{
                    background-color: #3F4678;
                }}
            """)
        if hasattr(self, '_title_lbl') and self._title_lbl:
            self._title_lbl.setStyleSheet(f"color: {c('text_primary')}; background: transparent;")
        if hasattr(self, '_count_badge') and self._count_badge:
            self._count_badge.setStyleSheet(f"background-color: {C_PURPLE_BG}; color: {C_PURPLE_FG}; border-radius: 10px; padding: 3px 10px; font-weight: bold; font-family: 'Segoe UI'; font-size: 11px;")
        if hasattr(self, '_desc_lbl') and self._desc_lbl:
            self._desc_lbl.setStyleSheet(f"color: {c('text_muted')}; background: transparent;")
        if hasattr(self, '_toolbar') and self._toolbar:
            self._toolbar.setStyleSheet(f"""
                QFrame {{
                    background-color: {c('bg_primary')};
                    border: 1px solid {c('border')};
                    border-radius: 10px;
                }}
            """)
        if hasattr(self, '_search_wrap') and self._search_wrap:
            self._search_wrap.setStyleSheet(f"""
                QFrame {{
                    background-color: {c('input_bg')};
                    border: 1px solid {c('border')};
                    border-radius: 8px;
                }}
            """)
        if hasattr(self, '_search_icon') and self._search_icon:
            self._search_icon.setStyleSheet(f"color: {c('text_muted')}; border: none; background: transparent;")
        if hasattr(self, '_filter_var') and self._filter_var:
            self._filter_var.setStyleSheet(f"""
                QLineEdit {{
                    border: none;
                    background: transparent;
                    color: {c('text_primary')};
                    font-family: 'Segoe UI';
                    font-size: 12px;
                }}
            """)
        if hasattr(self, '_download_btn') and self._download_btn:
            self._download_btn.setStyleSheet(f"""
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
        if hasattr(self, '_btn_clear') and self._btn_clear:
            self._btn_clear.setStyleSheet(f"""
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
            """)
            
        self._load_records()
