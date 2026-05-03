"""
modules/vision/ui.py
Full-page Vision + Gesture Translation interface.
PyQt6 refactored version with standardized practices, safety guards, and clean UI components.

Fixes applied:
  1. GestureRecognizer properly receives the configured hold_seconds to fix the delay bug.
  2. Lambdas overriding QWidget events replaced with standard QPushButton and QSS.
  3. Proper module structure, standard error handling, and robust update loop.
"""

from __future__ import annotations

import os
import time

import cv2
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QColor, QCursor, QImage, QLinearGradient, QPainter, QPixmap,
)
from PyQt6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QMessageBox, QProgressBar,
    QPushButton, QScrollArea, QTextEdit, QVBoxLayout, QWidget,
)

from core.config import config
from core.theme import c
from core.ui_helpers import _set_font, create_nav_item

# Logic & Backend
from modules.gestures.engine import GestureRecognizer
from modules.sentence.builder import SentenceBuilder
from modules.speech.buffer import speech_buffer
from modules.speech.tts import TTSEngine
from modules.speech.word_assembler import word_assembler
from modules.text.buffer import TextBuffer
from modules.text.mapper import map_gesture_to_text
from modules.vision.camera import CameraManager
from modules.vision.tracker import HandTracker


# ══════════════════════════════════════════════════════════════════════════════
# GRADIENT SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

class GradientSidebar(QFrame):
    """Sidebar with vertical gradient background."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(210)

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, QColor(c("panel_left", dark=True)))
        grad.setColorAt(1, QColor(c("panel_left_end", dark=True)))
        painter.fillRect(self.rect(), grad)


# ══════════════════════════════════════════════════════════════════════════════
# GESTURE DETECTION PAGE
# ══════════════════════════════════════════════════════════════════════════════

class GestureDetectionPage(QWidget):
    UPDATE_INTERVAL = 33   # ~30 fps

    def __init__(self, parent: QWidget, app, username: str) -> None:
        super().__init__(parent)
        self._app = app
        self._username = username
        self.setStyleSheet(f"background-color: {c('bg_secondary')};")

        # ── Config ───────────────────────────────────────
        self._conf_threshold = config.get("gesture.confidence_threshold", 60.0) / 100.0
        self._hold_duration  = config.get("gesture.timeout", 2.0)

        # ── Backend objects ──────────────────────────────
        self._camera           = CameraManager()
        self._tracker          = HandTracker()
        self._recognizer       = GestureRecognizer(hold_seconds=self._hold_duration)
        self._text_buffer      = TextBuffer()
        self._sentence_builder = SentenceBuilder(timeout=4.0)

        # ── TTS Integration ──────────────────────────────
        self._tts = TTSEngine(on_error=self._handle_tts_error)
        word_assembler.set_tts(self._tts)

        # ── State ────────────────────────────────────────
        self._is_detecting         = False
        self._update_timer         = QTimer(self)
        self._update_timer.setInterval(self.UPDATE_INTERVAL)
        self._update_timer.timeout.connect(self._update_loop)

        self._gesture_history      = []
        self._max_history          = 50
        self._live_speech_enabled  = False
        self._permission_granted   = False

        self._build()

    # ══════════════════════════════════════════════════════
    # UI CONSTRUCTION
    # ══════════════════════════════════════════════════════

    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._build_sidebar(layout)
        self._build_main_area(layout)

    def _build_sidebar(self, parent_layout: QHBoxLayout) -> None:
        sidebar = GradientSidebar(self)
        parent_layout.addWidget(sidebar)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 24, 16, 20)
        layout.setSpacing(0)

        # Logo + brand
        brand = QHBoxLayout()
        brand.setSpacing(10)
        brand.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "assets", "logo.png",
        )
        if os.path.exists(logo_path):
            lbl = QLabel()
            px = QPixmap(logo_path).scaled(
                36, 36,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            lbl.setPixmap(px)
            brand.addWidget(lbl)

        title = QLabel("SignDesk")
        title.setStyleSheet("color: #FFFFFF; background: transparent;")
        _set_font(title, 16, bold=True)
        brand.addWidget(title)
        layout.addLayout(brand)

        # Divider
        layout.addSpacing(16)
        div1 = QFrame()
        div1.setFixedHeight(1)
        div1.setStyleSheet("background-color: #4A4590; border: none;")
        layout.addWidget(div1)
        layout.addSpacing(16)

        # Back nav item
        nav = QVBoxLayout()
        nav.setSpacing(2)
        nav.addWidget(create_nav_item(
            sidebar, "←", "Back to Dashboard",
            command=self._on_back, dark=True,
        ))
        layout.addLayout(nav)
        layout.addSpacing(24)

        # System settings labels
        sys_lbl = QLabel("SYSTEM SETTINGS")
        sys_lbl.setStyleSheet("color: #84849E; background: transparent;")
        _set_font(sys_lbl, 11, bold=True)
        layout.addWidget(sys_lbl)
        layout.addSpacing(10)

        settings = [
            ("Camera",     "Built-in HD",                            "📷"),
            ("Model",      "ASL Standard",                           "🧠"),
            ("Confidence", f"Min {int(self._conf_threshold * 100)}%","🎯"),
            ("Hold Time",  f"{self._hold_duration}s",                "⏱️"),
        ]
        for title_txt, val, icon in settings:
            row = QWidget()
            r = QHBoxLayout(row)
            r.setContentsMargins(0, 0, 0, 0)
            i_lbl = QLabel(icon)
            i_lbl.setStyleSheet(
                "color: #B8B5D0; font-family: 'Segoe UI Emoji'; background: transparent;")
            t_lbl = QLabel(title_txt)
            t_lbl.setStyleSheet("color: #B8B5D0; background: transparent;")
            _set_font(t_lbl, 11)
            v_lbl = QLabel(val)
            v_lbl.setStyleSheet("color: #FFFFFF; background: transparent;")
            _set_font(v_lbl, 11, bold=True)
            r.addWidget(i_lbl)
            r.addWidget(t_lbl)
            r.addStretch()
            r.addWidget(v_lbl)
            layout.addWidget(row)
            layout.addSpacing(8)

        layout.addStretch()

        # Logout Button
        div2 = QFrame()
        div2.setFixedHeight(1)
        div2.setStyleSheet("background-color: #4A4590; border: none;")
        layout.addWidget(div2)
        layout.addSpacing(8)

        self._logout_btn = QPushButton("🚪  Logout")
        self._logout_btn.setFixedHeight(38)
        self._logout_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._logout_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: #FF8A80; text-align: left;
                padding-left: 12px; border-radius: 10px; font-family: 'Segoe UI'; font-size: 13px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #3D4470; }}
        """)
        self._logout_btn.clicked.connect(self._on_logout)
        layout.addWidget(self._logout_btn)

    def _build_main_area(self, parent_layout: QHBoxLayout) -> None:
        main = QWidget()
        main.setStyleSheet(f"background-color: {c('bg_secondary')};")
        parent_layout.addWidget(main, stretch=1)

        ml = QVBoxLayout(main)
        ml.setContentsMargins(24, 20, 24, 20)
        ml.setSpacing(16)

        # Top bar
        topbar = QHBoxLayout()
        title = QLabel("Real-time Gesture Translation")
        title.setStyleSheet(f"color: {c('text_primary')}; background: transparent;")
        _set_font(title, 22, bold=True)
        topbar.addWidget(title)
        topbar.addStretch()

        self._speech_toggle_btn = QPushButton("🔇 Live Speech: OFF")
        self._speech_toggle_btn.setFixedHeight(34)
        self._speech_toggle_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._speech_toggle_btn.clicked.connect(self._toggle_speech)
        self._update_speech_toggle_ui()
        topbar.addWidget(self._speech_toggle_btn)
        ml.addLayout(topbar)

        # Three-column layout: camera | gesture status | speech output
        split = QHBoxLayout()
        split.setSpacing(14)
        self._build_camera_panel(split)   # col 1
        self._build_right_panel(split)    # col 2
        self._build_speech_panel(split)   # col 3
        ml.addLayout(split, stretch=1)

        # Start / Stop buttons
        btn_row = QHBoxLayout()
        self._start_btn = QPushButton("▶  Start Detection")
        self._start_btn.setFixedHeight(40)
        self._start_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c('success')};
                color: #FFFFFF; border: none; border-radius: 8px;
                font-family: 'Segoe UI'; font-size: 13px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #17876A; }}
            QPushButton:disabled {{ background-color: {c('border')}; color: {c('text_muted')}; }}
        """)
        self._start_btn.clicked.connect(self._start_detection)

        self._stop_btn = QPushButton("■  Stop Detection")
        self._stop_btn.setFixedHeight(40)
        self._stop_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._stop_btn.setEnabled(False)
        self._stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c('error')};
                color: #FFFFFF; border: none; border-radius: 8px;
                font-family: 'Segoe UI'; font-size: 13px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #C0392B; }}
            QPushButton:disabled {{ background-color: {c('border')}; color: {c('text_muted')}; }}
        """)
        self._stop_btn.clicked.connect(self._stop_detection)

        btn_row.addWidget(self._start_btn)
        btn_row.addWidget(self._stop_btn)
        ml.addLayout(btn_row)

    def _build_camera_panel(self, parent_layout: QHBoxLayout) -> None:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 14px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)

        # FPS label
        fps_row = QHBoxLayout()
        cam_title = QLabel("📷  Live Detection")
        cam_title.setStyleSheet(f"color: {c('text_primary')}; background: transparent; border: none;")
        _set_font(cam_title, 14, bold=True)
        fps_row.addWidget(cam_title)
        fps_row.addStretch()
        self._fps_label = QLabel("FPS: --")
        self._fps_label.setStyleSheet(f"color: {c('text_muted')}; background: transparent; border: none;")
        _set_font(self._fps_label, 11)
        fps_row.addWidget(self._fps_label)
        layout.addLayout(fps_row)

        # Camera feed label
        self._cam_label = QLabel()
        self._cam_label.setStyleSheet("background-color: #0D1117; border-radius: 8px; border: none;")
        self._cam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cam_label.setMinimumSize(320, 240)
        layout.addWidget(self._cam_label, stretch=1)

        # Placeholder
        self._cam_placeholder = QLabel("📸\n\nCamera Offline\n\nClick 'Start Detection' to activate your webcam.")
        self._cam_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cam_placeholder.setStyleSheet(f"color: {c('text_muted')}; background: transparent; font-size: 14px; border: none;")
        self._cam_placeholder.setWordWrap(True)
        layout.addWidget(self._cam_placeholder)

        parent_layout.addWidget(card, stretch=5)

    def _build_right_panel(self, parent_layout: QHBoxLayout) -> None:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # ── Status card ───────────────────────────────────
        status_card = QFrame()
        status_card.setStyleSheet(f"""
            QFrame {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 14px;
            }}
        """)
        s_layout = QVBoxLayout(status_card)
        s_layout.setContentsMargins(20, 16, 20, 16)

        hdr = QHBoxLayout()
        s_lbl = QLabel("System Status")
        s_lbl.setStyleSheet(f"color: {c('text_muted')}; border: none; background: transparent;")
        _set_font(s_lbl, 11, bold=True)
        hdr.addWidget(s_lbl)
        hdr.addStretch()
        self._status_pill = QLabel("⏸  Detection stopped")
        self._status_pill.setStyleSheet(
            f"background-color: {c('badge_gray_bg')}; color: {c('badge_gray_fg')};"
            " border-radius: 10px; padding: 4px 10px; font-weight: bold; border: none;")
        hdr.addWidget(self._status_pill)
        s_layout.addLayout(hdr)
        s_layout.addSpacing(10)

        self._gesture_label = QLabel("—")
        self._gesture_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._gesture_label.setStyleSheet(f"color: {c('accent')}; border: none; background: transparent;")
        _set_font(self._gesture_label, 48, bold=True)
        s_layout.addWidget(self._gesture_label)

        self._gesture_name_label = QLabel("Waiting for gesture...")
        self._gesture_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._gesture_name_label.setStyleSheet(f"color: {c('text_secondary')}; border: none; background: transparent;")
        _set_font(self._gesture_name_label, 12)
        s_layout.addWidget(self._gesture_name_label)
        layout.addWidget(status_card)

        # ── Confidence card ───────────────────────────────
        conf_card = QFrame()
        conf_card.setStyleSheet(f"""
            QFrame {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 14px;
            }}
        """)
        c_layout = QVBoxLayout(conf_card)
        c_layout.setContentsMargins(20, 14, 20, 14)

        ch = QHBoxLayout()
        c_lbl = QLabel("Match Confidence")
        c_lbl.setStyleSheet(f"color: {c('text_muted')}; border: none; background: transparent;")
        _set_font(c_lbl, 11, bold=True)
        ch.addWidget(c_lbl)
        ch.addStretch()
        self._conf_value_label = QLabel("0%")
        self._conf_value_label.setStyleSheet(f"color: {c('text_muted')}; border: none; background: transparent;")
        _set_font(self._conf_value_label, 12, bold=True)
        ch.addWidget(self._conf_value_label)
        c_layout.addLayout(ch)

        self._conf_bar = QProgressBar()
        self._conf_bar.setTextVisible(False)
        self._conf_bar.setRange(0, 100)
        self._conf_bar.setValue(0)
        self._conf_bar.setFixedHeight(6)
        self._conf_bar.setStyleSheet(f"""
            QProgressBar {{ background-color: {c('border')}; border: none; border-radius: 3px; }}
            QProgressBar::chunk {{ background-color: {c('badge_gray_bg')}; border-radius: 3px; }}
        """)
        c_layout.addWidget(self._conf_bar)

        # Hold progress bar
        hold_row = QHBoxLayout()
        h_lbl = QLabel("Hold to confirm:")
        h_lbl.setStyleSheet(f"color: {c('text_muted')}; border: none; background: transparent;")
        _set_font(h_lbl, 10)
        hold_row.addWidget(h_lbl)

        self._hold_bar = QProgressBar()
        self._hold_bar.setTextVisible(False)
        self._hold_bar.setRange(0, 100)
        self._hold_bar.setValue(0)
        self._hold_bar.setFixedHeight(6)
        self._hold_bar.setStyleSheet(f"""
            QProgressBar {{ background-color: {c('border')}; border: none; border-radius: 3px; }}
            QProgressBar::chunk {{ background-color: {c('cyan')}; border-radius: 3px; }}
        """)
        hold_row.addWidget(self._hold_bar)
        c_layout.addLayout(hold_row)

        self._conf_warning = QLabel("")
        self._conf_warning.setStyleSheet(f"color: {c('warn')}; border: none; background: transparent;")
        _set_font(self._conf_warning, 10)
        c_layout.addWidget(self._conf_warning)
        layout.addWidget(conf_card)

        # ── Output card ───────────────────────────────────
        out_card = QFrame()
        out_card.setStyleSheet(f"""
            QFrame {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 14px;
            }}
        """)
        o_layout = QVBoxLayout(out_card)
        o_layout.setContentsMargins(20, 14, 20, 14)

        oh = QHBoxLayout()
        o_lbl = QLabel("Current Output")
        o_lbl.setStyleSheet(f"color: {c('text_muted')}; border: none; background: transparent;")
        _set_font(o_lbl, 11, bold=True)
        oh.addWidget(o_lbl)
        oh.addStretch()
        clr_btn = QPushButton("Clear")
        clr_btn.setStyleSheet(f"background: transparent; color: {c('error')}; border: none; font-size: 11px;")
        clr_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        clr_btn.clicked.connect(self._clear_output)
        oh.addWidget(clr_btn)
        o_layout.addLayout(oh)

        self._output_textbox = QTextEdit()
        self._output_textbox.setReadOnly(True)
        self._output_textbox.setFixedHeight(56)
        self._output_textbox.setStyleSheet(f"""
            QTextEdit {{
                background-color: {c('input_bg')}; border: 1px solid {c('border')};
                border-radius: 8px; color: {c('text_primary')};
                font-family: 'Consolas'; font-size: 16px; padding: 8px;
            }}
        """)
        o_layout.addWidget(self._output_textbox)

        f_lbl = QLabel("Finalized Sentences")
        f_lbl.setStyleSheet(f"color: {c('text_muted')}; border: none; background: transparent;")
        _set_font(f_lbl, 11, bold=True)
        o_layout.addWidget(f_lbl)

        self._final_sentence_label = QTextEdit()
        self._final_sentence_label.setReadOnly(True)
        self._final_sentence_label.setFixedHeight(56)
        self._final_sentence_label.setStyleSheet(f"""
            QTextEdit {{
                background-color: {c('success_bg')}; border: 1px solid {c('success')};
                border-radius: 8px; color: {c('text_primary')};
                font-family: 'Consolas'; font-size: 14px; padding: 8px;
            }}
        """)
        o_layout.addWidget(self._final_sentence_label)
        layout.addWidget(out_card)

        # ── Gesture sequence ──────────────────────────────
        seq_card = QFrame()
        seq_card.setStyleSheet(f"""
            QFrame {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 14px;
            }}
        """)
        sq = QVBoxLayout(seq_card)
        sq.setContentsMargins(20, 14, 20, 14)

        sh = QHBoxLayout()
        seq_lbl = QLabel("📋  Gesture Sequence")
        seq_lbl.setStyleSheet(f"color: {c('text_primary')}; border: none; background: transparent;")
        _set_font(seq_lbl, 12, bold=True)
        sh.addWidget(seq_lbl)
        sh.addStretch()
        seq_clr = QPushButton("Clear")
        seq_clr.setStyleSheet(f"background: transparent; color: {c('text_muted')}; border: none; font-size: 11px;")
        seq_clr.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        seq_clr.clicked.connect(self._clear_history)
        sh.addWidget(seq_clr)
        sq.addLayout(sh)

        self._history_textbox = QTextEdit()
        self._history_textbox.setReadOnly(True)
        self._history_textbox.setFixedHeight(80)
        self._history_textbox.setStyleSheet(f"""
            QTextEdit {{
                background-color: {c('input_bg')}; border: 1px solid {c('border')};
                border-radius: 8px; color: {c('text_secondary')};
                font-family: 'Consolas'; font-size: 13px; padding: 8px;
            }}
        """)
        sq.addWidget(self._history_textbox)
        layout.addWidget(seq_card)

        layout.addStretch()
        parent_layout.addWidget(panel, stretch=3)

    def _build_speech_panel(self, parent_layout: QHBoxLayout) -> None:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 14px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("🔊  Speech Output")
        title.setStyleSheet(f"color: {c('text_primary')}; background: transparent; border: none;")
        _set_font(title, 14, bold=True)
        hdr.addWidget(title)
        hdr.addStretch()

        self._tts_status_pill = QLabel("⏸ Idle")
        self._tts_status_pill.setStyleSheet(
            f"background-color: {c('badge_gray_bg')}; color: {c('badge_gray_fg')};"
            " border-radius: 10px; padding: 3px 10px; font-weight: bold; border: none; font-size: 11px;")
        hdr.addWidget(self._tts_status_pill)
        layout.addLayout(hdr)

        # Voice Selector
        voice_row = QHBoxLayout()
        voice_lbl = QLabel("Voice:")
        voice_lbl.setStyleSheet(f"color: {c('text_muted')}; background: transparent; border: none;")
        _set_font(voice_lbl, 11)
        voice_row.addWidget(voice_lbl)

        self._voice_combo = QComboBox()
        self._voice_combo.addItems(["🔊 Default", "♀ Female", "♂ Male"])
        self._voice_combo.setFixedHeight(30)
        self._voice_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {c('input_bg')}; border: 1px solid {c('input_border')};
                border-radius: 8px; padding: 2px 10px; font-family: 'Segoe UI'; font-size: 12px; color: {c('text_primary')};
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{
                background-color: {c('bg_primary')}; border: 1px solid {c('border')};
                selection-background-color: {c('accent')}; color: {c('text_primary')};
            }}
        """)
        saved_voice = config.get("speech.voice", "default")
        voice_map = {"default": 0, "female": 1, "male": 2}
        self._voice_combo.setCurrentIndex(voice_map.get(saved_voice, 0))
        self._voice_combo.currentIndexChanged.connect(self._on_voice_changed)
        voice_row.addWidget(self._voice_combo, 1)
        layout.addLayout(voice_row)

        # Sentences Header
        sent_hdr = QHBoxLayout()
        sent_lbl = QLabel("Finalized Sentences")
        sent_lbl.setStyleSheet(f"color: {c('text_secondary')}; background: transparent; border: none;")
        _set_font(sent_lbl, 12, bold=True)
        sent_hdr.addWidget(sent_lbl)
        sent_hdr.addStretch()

        play_all_btn = QPushButton("▶ Play All")
        play_all_btn.setFixedHeight(28)
        play_all_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        play_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c('success')}; color: #FFFFFF; border: none; border-radius: 6px;
                font-family: 'Segoe UI'; font-size: 11px; font-weight: bold; padding: 0 10px;
            }}
            QPushButton:hover {{ background-color: #17876A; }}
        """)
        play_all_btn.clicked.connect(self._play_all)
        sent_hdr.addWidget(play_all_btn)

        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.setFixedHeight(28)
        clear_all_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        clear_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {c('error')}; border: 1px solid {c('error')};
                border-radius: 6px; font-family: 'Segoe UI'; font-size: 11px; padding: 0 10px;
            }}
            QPushButton:hover {{ background-color: {c('error_bg')}; }}
        """)
        clear_all_btn.clicked.connect(self._clear_all_sentences)
        sent_hdr.addWidget(clear_all_btn)
        layout.addLayout(sent_hdr)

        # Sentence List Container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background-color: {c('bg_secondary')}; border: 1px solid {c('border')}; border-radius: 8px; }}
        """)

        self._sentences_container = QWidget()
        self._sentences_container.setStyleSheet(f"background-color: {c('bg_secondary')};")
        self._sentences_layout = QVBoxLayout(self._sentences_container)
        self._sentences_layout.setContentsMargins(8, 8, 8, 8)
        self._sentences_layout.setSpacing(6)
        self._sentences_layout.addStretch()

        scroll.setWidget(self._sentences_container)
        layout.addWidget(scroll, stretch=1)

        parent_layout.addWidget(card, stretch=4)
        self._populate_sentences()

    # ══════════════════════════════════════════════════════
    # STATE MANAGEMENT & LIFECYCLE
    # ══════════════════════════════════════════════════════

    def _start_detection(self) -> None:
        if not self._permission_granted:
            reply = QMessageBox.question(
                self, "Camera Permission Required",
                "SignDesk requires access to your webcam to detect hand gestures.\n\nAllow SignDesk to use your camera?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                QMessageBox.critical(self, "Permission Denied", "Webcam permission denied.")
                return
            self._permission_granted = True

        success, message = self._camera.start()
        if not success:
            QMessageBox.critical(self, "Webcam Error", message)
            return

        self._is_detecting = True
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._cam_placeholder.setVisible(False)

        self._set_status_pill("🔵  Detecting…", c("info_bg"), c("info"))
        self._gesture_name_label.setText("Looking for gesture…")
        self._update_timer.start()

    def _stop_detection(self) -> None:
        self._is_detecting = False
        self._update_timer.stop()
        self._camera.stop()

        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._cam_placeholder.setVisible(True)
        self._cam_label.clear()

        self._set_status_pill("⏸  Detection stopped", c("badge_gray_bg"), c("badge_gray_fg"))
        self._gesture_label.setText("—")
        self._gesture_name_label.setText("Waiting for gesture…")
        self._conf_value_label.setText("0%")
        self._conf_bar.setValue(0)
        self._hold_bar.setValue(0)
        self._conf_warning.setText("")
        self._fps_label.setText("FPS: --")

        self._text_buffer.clear()
        self._sentence_builder.reset()
        word_assembler.cancel()
        self._refresh_output()

    def _toggle_speech(self) -> None:
        self._live_speech_enabled = not self._live_speech_enabled
        word_assembler.set_live_speech(self._live_speech_enabled)
        self._update_speech_toggle_ui()

    def _update_speech_toggle_ui(self) -> None:
        if self._live_speech_enabled:
            self._speech_toggle_btn.setText("🔊 Live Speech: ON")
            self._speech_toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c('success_bg')}; color: {c('success')};
                    border: 1px solid {c('success')}; border-radius: 17px;
                    font-weight: bold; padding: 4px 16px;
                }}
            """)
        else:
            self._speech_toggle_btn.setText("🔇 Live Speech: OFF")
            self._speech_toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; color: {c('text_muted')};
                    border: 1px solid {c('text_muted')}; border-radius: 17px;
                    font-weight: bold; padding: 4px 16px;
                }}
            """)

    def _on_voice_changed(self, index: int) -> None:
        voice_keys = ["default", "female", "male"]
        selected = voice_keys[index]
        config.set("speech.voice", selected)
        try:
            self._tts.set_voice(selected)
        except Exception:
            pass

    def _handle_tts_error(self, message: str) -> None:
        if not self._live_speech_enabled:
            QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Audio Error", message))

    # ══════════════════════════════════════════════════════
    # DETECTION LOGIC
    # ══════════════════════════════════════════════════════

    def _update_loop(self) -> None:
        if not self._is_detecting:
            return

        success, frame, fps = self._camera.read_frame()
        if not success or frame is None:
            self._set_status_pill("⚠  Camera feed interrupted", c("error_bg"), c("error"))
            return

        self._fps_label.setText(f"FPS: {fps:.0f}")

        hand_detected, landmarks, annotated_frame = self._tracker.process_frame(frame)

        if hand_detected and landmarks:
            gesture, confidence = self._recognizer.recognize(landmarks)
            self._update_hold_bar(self._recognizer.hold_progress)
            self._process_gesture_state(gesture, confidence, self._recognizer.current_hold_gesture)
        else:
            self._process_no_gesture()

        # Sentence finalization
        if self._sentence_builder.should_finalize(time.monotonic()):
            final = self._sentence_builder.finalize()
            if final:
                self._final_sentence_label.setPlainText(final)
                speech_buffer.push(final)
                self._refresh_sentences()
            self._sentence_builder.reset()
            self._text_buffer.clear()
            self._refresh_output()

        self._display_frame(annotated_frame)

    def _process_gesture_state(self, gesture: str | None, confidence: float, current_hold: str | None) -> None:
        if gesture is not None:
            self._update_confidence(confidence)
            if not self._gesture_history or self._gesture_history[-1] != gesture:
                self._add_to_history(gesture, confidence)

            text_char = map_gesture_to_text(gesture)
            if self._text_buffer.append_if_new(text_char):
                self._sentence_builder.add_gesture(text_char, time.monotonic())
                self._refresh_output()
                if self._live_speech_enabled:
                    word_assembler.add_letter(text_char)

            self._recognizer.reset_hold()
            self._gesture_label.setText(gesture)
            self._gesture_name_label.setText(f"ASL Letter: {gesture}")
            self._set_status_pill(f"🟢  Committed: {gesture}", c("success_bg"), c("success"))

        elif current_hold is not None:
            self._gesture_label.setText(current_hold)
            self._gesture_name_label.setText(f"ASL Letter: {current_hold}")
            self._set_status_pill(f"⏳  Holding: {current_hold}…", c("info_bg"), c("info"))

        else:
            self._gesture_label.setText("—")
            self._gesture_name_label.setText("Gesture unclear")
            self._update_confidence(0.0)
            if self._text_buffer.maybe_insert_space():
                self._refresh_output()
                if self._live_speech_enabled:
                    word_assembler.add_space()
            self._set_status_pill("🔍  Analyzing…", c("info_bg"), c("info"))

    def _process_no_gesture(self) -> None:
        self._gesture_label.setText("—")
        self._gesture_name_label.setText("No hand detected")
        self._update_confidence(0.0)
        self._update_hold_bar(0.0)
        if self._text_buffer.maybe_insert_space():
            self._refresh_output()
            if self._live_speech_enabled:
                word_assembler.add_space()
        self._set_status_pill("🔵  No hand detected", c("info_bg"), c("info"))

    # ══════════════════════════════════════════════════════
    # SPEECH LOGIC
    # ══════════════════════════════════════════════════════

    def _populate_sentences(self) -> None:
        while self._sentences_layout.count() > 1:
            item = self._sentences_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        sentences = speech_buffer.get_all()
        if not sentences:
            empty = QLabel("No finalized sentences yet.")
            empty.setStyleSheet(f"color: {c('text_muted')}; background: transparent; border: none;")
            _set_font(empty, 11)
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._sentences_layout.insertWidget(0, empty)
            return

        for i, sentence in enumerate(sentences):
            row = QFrame()
            row.setStyleSheet(f"QFrame {{ background-color: {c('bg_primary')}; border: 1px solid {c('border')}; border-radius: 8px; }}")
            r = QHBoxLayout(row)
            r.setContentsMargins(8, 8, 8, 8)
            r.setSpacing(6)

            remove_btn = QPushButton("×")
            remove_btn.setFixedSize(26, 26)
            remove_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            remove_btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {c('text_muted')}; border: none; font-size: 14px; border-radius: 4px; }} QPushButton:hover {{ background-color: {c('error_bg')}; color: {c('error')}; }}")
            remove_btn.clicked.connect(lambda _, idx=i: self._remove_sentence(idx))
            r.addWidget(remove_btn)

            txt = QLabel(sentence)
            txt.setWordWrap(True)
            txt.setStyleSheet(f"color: {c('text_primary')}; background: transparent; border: none; font-family: 'Consolas'; font-size: 13px;")
            r.addWidget(txt, 1)

            play_btn = QPushButton("▶")
            play_btn.setFixedSize(32, 32)
            play_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            play_btn.setStyleSheet(f"QPushButton {{ background-color: {c('accent')}; color: #FFFFFF; border: none; border-radius: 6px; font-size: 12px; }} QPushButton:hover {{ background-color: {c('accent_hover')}; }}")
            play_btn.clicked.connect(lambda _, s=sentence: self._play_single(s))
            r.addWidget(play_btn)

            self._sentences_layout.insertWidget(self._sentences_layout.count() - 1, row)

    def _refresh_sentences(self) -> None:
        self._populate_sentences()

    def _remove_sentence(self, index: int) -> None:
        speech_buffer.remove_at(index)
        self._populate_sentences()

    def _clear_all_sentences(self) -> None:
        speech_buffer.clear()
        self._populate_sentences()

    def _play_single(self, sentence: str) -> None:
        self._set_tts_status("🟢 Playing", c("success_bg"), c("success"))
        QTimer.singleShot(2500, lambda: self._set_tts_status("⏸ Idle", c("badge_gray_bg"), c("badge_gray_fg")))
        self._tts.speak(sentence)

    def _play_all(self) -> None:
        sentences = speech_buffer.get_all()
        if not sentences:
            QMessageBox.information(self, "Speech Output", "No sentences to play.")
            return
        self._play_single(". ".join(sentences))

    # ══════════════════════════════════════════════════════
    # UTILITY / UI HELPERS
    # ══════════════════════════════════════════════════════

    def _display_frame(self, frame) -> None:
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
            lw, lh = self._cam_label.width(), self._cam_label.height()
            if lw > 1 and lh > 1:
                px = QPixmap.fromImage(qimg).scaled(lw, lh, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self._cam_label.setPixmap(px)
        except Exception:
            pass

    def _set_status_pill(self, text: str, bg: str, fg: str) -> None:
        self._status_pill.setText(text)
        self._status_pill.setStyleSheet(f"background-color: {bg}; color: {fg}; border-radius: 10px; padding: 4px 10px; font-weight: bold; border: none;")

    def _set_tts_status(self, text: str, bg: str, fg: str) -> None:
        self._tts_status_pill.setText(text)
        self._tts_status_pill.setStyleSheet(f"background-color: {bg}; color: {fg}; border-radius: 10px; padding: 3px 10px; font-weight: bold; border: none; font-size: 11px;")

    def _update_hold_bar(self, progress: float) -> None:
        pct = int(min(1.0, max(0.0, progress)) * 100)
        self._hold_bar.setValue(pct)
        color = c("success") if pct >= 100 else c("warn") if pct > 0 else c("badge_gray_bg")
        self._hold_bar.setStyleSheet(f"QProgressBar {{ background-color: {c('border')}; border: none; border-radius: 3px; }} QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}")

    def _update_confidence(self, confidence: float) -> None:
        pct = int(confidence * 100)
        self._conf_value_label.setText(f"{pct}%")
        self._conf_bar.setValue(pct)
        
        if confidence >= 0.80:
            color = c("success")
            self._conf_warning.setText("")
        elif confidence >= 0.60:
            color = c("warn")
            self._conf_warning.setText("⚠ Improve positioning")
        else:
            color = c("error")
            self._conf_warning.setText("⚠ Low confidence")
            
        self._conf_bar.setStyleSheet(f"QProgressBar {{ background-color: {c('border')}; border: none; border-radius: 3px; }} QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}")
        self._conf_value_label.setStyleSheet(f"color: {color}; border: none; background: transparent;")

    def _add_to_history(self, gesture: str, confidence: float) -> None:
        self._gesture_history.append(gesture)
        if len(self._gesture_history) > self._max_history:
            self._gesture_history = self._gesture_history[-self._max_history:]
        self._history_textbox.setPlainText(" ".join(self._gesture_history))
        sb = self._history_textbox.verticalScrollBar()
        sb.setValue(sb.maximum())
        try:
            from modules.gesture_history.backend import log_gesture
            translated = map_gesture_to_text(gesture) or gesture
            log_gesture(self._app.current_user_id, gesture, translated, confidence)
        except Exception as e:
            print(f"[GestureHistory] log_gesture failed: {e}")

    def _refresh_output(self) -> None:
        self._output_textbox.setPlainText(self._text_buffer.get())
        sb = self._output_textbox.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _clear_output(self) -> None:
        self._text_buffer.clear()
        self._refresh_output()

    def _clear_history(self) -> None:
        self._gesture_history.clear()
        self._history_textbox.clear()

    # ── App Navigation ────────────────────────────────────

    def _on_back(self) -> None:
        self._stop_detection()
        try:
            self._tracker.release()
        except Exception:
            pass
        self._app.show_dashboard(self._username)

    def _on_logout(self) -> None:
        reply = QMessageBox.question(
            self, "Logout", "Are you sure you want to log out?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._stop_detection()
            try:
                self._tracker.release()
            except Exception:
                pass
            self._app.show_login()

    def destroy(self) -> None:
        self._stop_detection()
        word_assembler.cancel()
        try:
            self._tracker.release()
        except Exception:
            pass
        super().destroy()
