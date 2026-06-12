

import os
import random
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QProgressBar, QGridLayout, QSizePolicy, QSpacerItem, QRadioButton, QButtonGroup,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QCursor, QFont, QColor, QPainter, QPen, QPixmap, QLinearGradient, QBrush

from components.layout.sidebar import Sidebar
from core.theme import c, is_dark, ThemeSignal
from core.ui_helpers import _set_font, _add_shadow
from modules.reference.constants import LETTER_METADATA
from modules.gesture_history.backend import log_quiz_result


class ResultsRing(QWidget):
    """
    Custom painted circular progress ring to display accuracy.
    Uses current theme colors for maximum visual appeal.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 140)
        self.percentage = 0.0

    def set_percentage(self, val: float):
        self.percentage = val
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw clean base circular track
        rect = self.rect().adjusted(10, 10, -10, -10)
        bg_pen = QPen(QColor(c("border")), 8)
        painter.setPen(bg_pen)
        painter.drawEllipse(rect)

        # Draw active accuracy arc
        if self.percentage > 0:
            fg_pen = QPen(QColor(c("success")), 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(fg_pen)
            # 90 degrees starts at the top (12 o'clock)
            # The span is negative for clockwise direction
            span = int(-self.percentage * 3.6 * 16)
            painter.drawArc(rect, 90 * 16, span)

        # Draw percentage label
        painter.setPen(QColor(c("text_primary")))
        font = QFont("Segoe UI", 20, QFont.Weight.Bold)
        painter.setFont(font)
        text = f"{int(self.percentage)}%"
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()


class QuizProgressBar(QWidget):
    """
    Custom-painted segmented progress bar for the quiz.
    Each segment represents one question and is color-coded:
      • completed correct  → green
      • completed missed   → red/orange
      • current            → accent with animated pulse
      • pending            → muted track
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._total = 1
        self._current = 0
        self._answers: list[bool | None] = []
        self._glow_opacity = 1.0
        self.setFixedHeight(28)
        self.setMinimumWidth(100)

        # Pulse animation for the active segment
        self._pulse_anim = QPropertyAnimation(self, b"glowOpacity")
        self._pulse_anim.setDuration(900)
        self._pulse_anim.setStartValue(0.45)
        self._pulse_anim.setEndValue(1.0)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse_anim.setLoopCount(-1)  # infinite
        self._pulse_anim.start()

    # ── Qt property for animation ────────────────────────────────────────────
    def _get_glow(self) -> float:
        return self._glow_opacity

    def _set_glow(self, v: float):
        self._glow_opacity = v
        self.update()

    glowOpacity = pyqtProperty(float, _get_glow, _set_glow)

    # ── Public API ───────────────────────────────────────────────────────────
    def configure(self, total: int, answers: list[bool | None]):
        self._total = max(total, 1)
        self._answers = answers
        self.update()

    def set_current(self, idx: int):
        self._current = idx
        self.update()

    # ── Paint ────────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        n = self._total
        gap = 3 if n <= 26 else 2
        seg_w = (w - gap * (n - 1)) / n
        bar_h = 10
        y = (h - bar_h) / 2
        radius = bar_h / 2

        accent   = QColor(c("accent"))
        success  = QColor(c("success"))
        error    = QColor("#EF4444")
        track    = QColor(c("border"))

        for i in range(n):
            x = i * (seg_w + gap)
            rect = QRectF(x, y, seg_w, bar_h)

            ans = self._answers[i] if i < len(self._answers) else None

            if ans is True:
                # Correct — green gradient
                grad = QLinearGradient(x, y, x + seg_w, y)
                grad.setColorAt(0, success)
                grad.setColorAt(1, success.lighter(115))
                painter.setBrush(QBrush(grad))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(rect, radius, radius)
            elif ans is False:
                # Missed — red/orange gradient
                grad = QLinearGradient(x, y, x + seg_w, y)
                grad.setColorAt(0, error)
                grad.setColorAt(1, error.lighter(120))
                painter.setBrush(QBrush(grad))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(rect, radius, radius)
            elif i == self._current:
                # Current — accent with pulsing glow
                glow_color = QColor(accent)
                glow_color.setAlphaF(self._glow_opacity * 0.25)
                glow_rect = QRectF(x - 2, y - 2, seg_w + 4, bar_h + 4)
                painter.setBrush(QBrush(glow_color))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(glow_rect, radius + 2, radius + 2)

                grad = QLinearGradient(x, y, x + seg_w, y)
                grad.setColorAt(0, accent)
                grad.setColorAt(1, accent.lighter(125))
                painter.setBrush(QBrush(grad))
                painter.drawRoundedRect(rect, radius, radius)
            else:
                # Pending — muted track
                painter.setBrush(QBrush(track))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(rect, radius, radius)

        painter.end()


class FlashcardQuizPage(QWidget):
    """
    Main page for the Flashcard Recognition Quiz.
    Embeds the navigation Sidebar and splits into the main quiz card and side stats panel.
    """
    def __init__(self, parent, app, username: str):
        super().__init__(parent)
        self._app = app
        self._username = username
        self.setObjectName("flashcardQuizPage")

        # Session State Variables
        self.deck = []
        self.current_idx = 0
        self.deck_size = 10
        self.answers = []  # List of bools or None for each question
        self.streak = 0
        self.is_answered = False

        self._build()
        self._update_styles()

        # Connect to theme signal for dynamic switches
        try:
            ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

    def _build(self):
        # 1. Root Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top Bar
        topbar = QWidget()
        topbar.setFixedHeight(60)
        tb_layout = QHBoxLayout(topbar)
        tb_layout.setContentsMargins(28, 16, 28, 4)

        self.title_lbl = QLabel("Flashcard Recognition Quiz")
        _set_font(self.title_lbl, size=16, bold=True)
        tb_layout.addWidget(self.title_lbl)
        tb_layout.addStretch()

        # Avatar
        self.avatar = QLabel(self._username[0].upper() if self._username else "?")
        self.avatar.setFixedSize(36, 36)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tb_layout.addWidget(self.avatar)

        layout.addWidget(topbar)

        # Split Section: Main Card on left, Status panel on right
        content_split = QWidget()
        content_layout = QHBoxLayout(content_split)
        content_layout.setContentsMargins(28, 8, 28, 24)
        content_layout.setSpacing(20)

        # Left Column: The Main Active Screen Card
        self.main_card = QFrame()
        self.main_card.setObjectName("quizMainCard")
        self.card_layout = QVBoxLayout(self.main_card)
        self.card_layout.setContentsMargins(24, 24, 24, 24)
        self.card_layout.setSpacing(20)
        content_layout.addWidget(self.main_card, stretch=3)

        # Right Column: Side Stats Panel
        self.side_panel = QFrame()
        self.side_panel.setObjectName("quizSidePanel")
        self.side_panel.setFixedWidth(240)
        self.side_layout = QVBoxLayout(self.side_panel)
        self.side_layout.setContentsMargins(16, 16, 16, 16)
        self.side_layout.setSpacing(20)
        content_layout.addWidget(self.side_panel, stretch=1)

        # Populate Screens inside self.main_card
        self._build_setup_screen()
        self._build_quiz_screen()
        self._build_results_screen()

        # Populate Side Panel
        self._build_side_panel()

        layout.addWidget(content_split, stretch=1)

        # Default to Setup Screen
        self.go_to_setup()

    # ── Screen Builders ────────────────────────────────────────────────────────

    def _build_setup_screen(self):
        self.setup_widget = QWidget()
        layout = QVBoxLayout(self.setup_widget)
        layout.setContentsMargins(40, 20, 40, 20)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        setup_title = QLabel("Quiz Settings")
        setup_title.setObjectName("setupTitle")
        setup_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_font(setup_title, size=20, bold=True)
        layout.addWidget(setup_title)

        setup_sub = QLabel("Configure your practice session mode and question set.")
        setup_sub.setObjectName("setupSub")
        setup_sub.setWordWrap(True)
        setup_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_font(setup_sub, size=12)
        layout.addWidget(setup_sub)

        layout.addSpacing(10)

        # ── Quiz Mode Section ──
        mode_section = QWidget()
        mode_layout = QVBoxLayout(mode_section)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(8)

        mode_lbl = QLabel("QUIZ MODE")
        mode_lbl.setObjectName("modeLabel")
        _set_font(mode_lbl, size=10, bold=True)
        mode_layout.addWidget(mode_lbl)

        # Options Container Frame for Mode
        mode_container = QFrame()
        mode_container.setObjectName("settingsContainer")
        mc_layout = QVBoxLayout(mode_container)
        mc_layout.setContentsMargins(14, 12, 14, 12)
        mc_layout.setSpacing(10)

        self.mode_flashcard = QRadioButton("Flashcard Quiz")
        self.mode_flashcard.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.mode_camera = QRadioButton("Camera Practice Quiz")
        self.mode_camera.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.mode_flashcard)
        self.mode_group.addButton(self.mode_camera)
        self.mode_flashcard.setChecked(True)

        mc_layout.addWidget(self.mode_flashcard)
        mc_layout.addWidget(self.mode_camera)
        mode_layout.addWidget(mode_container)
        layout.addWidget(mode_section)

        # ── Question Set Section ──
        set_section = QWidget()
        set_layout = QVBoxLayout(set_section)
        set_layout.setContentsMargins(0, 0, 0, 0)
        set_layout.setSpacing(8)

        set_lbl = QLabel("QUESTION SET")
        set_lbl.setObjectName("setLabel")
        _set_font(set_lbl, size=10, bold=True)
        set_layout.addWidget(set_lbl)

        # Options Container Frame for Question Set
        set_container = QFrame()
        set_container.setObjectName("settingsContainer")
        sc_layout = QVBoxLayout(set_container)
        sc_layout.setContentsMargins(14, 12, 14, 12)
        sc_layout.setSpacing(10)

        self.set_random = QRadioButton("New Random Set (10 Questions)")
        self.set_random.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.set_all = QRadioButton("All Letters (26 Questions)")
        self.set_all.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.set_shuffle = QRadioButton("Shuffle All Letters (26 Questions)")
        self.set_shuffle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.set_group = QButtonGroup(self)
        self.set_group.addButton(self.set_random)
        self.set_group.addButton(self.set_all)
        self.set_group.addButton(self.set_shuffle)
        self.set_shuffle.setChecked(True)  # Default option

        sc_layout.addWidget(self.set_shuffle)  # Put default first
        sc_layout.addWidget(self.set_random)
        sc_layout.addWidget(self.set_all)
        set_layout.addWidget(set_container)
        layout.addWidget(set_section)

        layout.addSpacing(15)

        self.btn_start = QPushButton("Start Quiz")
        self.btn_start.setFixedSize(180, 44)
        self.btn_start.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_start.clicked.connect(self.start_quiz)
        layout.addWidget(self.btn_start, 0, Qt.AlignmentFlag.AlignHCenter)

        self.card_layout.addWidget(self.setup_widget)

    def _build_quiz_screen(self):
        self.quiz_widget = QWidget()
        layout = QVBoxLayout(self.quiz_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # ── Header Row: icon + label + pill counter ──────────────────────────
        hdr_row = QWidget()
        hdr_layout = QHBoxLayout(hdr_row)
        hdr_layout.setContentsMargins(0, 0, 0, 4)
        hdr_layout.setSpacing(8)

        quiz_icon_lbl = QLabel("🃏")
        _set_font(quiz_icon_lbl, size=16)
        hdr_layout.addWidget(quiz_icon_lbl)

        self.quiz_mode_lbl = QLabel("Identify the Sign")
        self.quiz_mode_lbl.setObjectName("quizModeLbl")
        _set_font(self.quiz_mode_lbl, size=13, bold=True)
        hdr_layout.addWidget(self.quiz_mode_lbl)
        hdr_layout.addStretch()

        # Pill-shaped question counter
        self.progress_pill = QFrame()
        self.progress_pill.setObjectName("progressPill")
        pill_layout = QHBoxLayout(self.progress_pill)
        pill_layout.setContentsMargins(12, 4, 12, 4)
        pill_layout.setSpacing(4)

        self.progress_lbl = QLabel("Question 0 of 0")
        self.progress_lbl.setObjectName("progressLbl")
        _set_font(self.progress_lbl, size=11, bold=True)
        pill_layout.addWidget(self.progress_lbl)

        hdr_layout.addWidget(self.progress_pill)
        layout.addWidget(hdr_row)

        # ── Segmented Progress Bar ────────────────────────────────────────────
        self.progress_bar = QuizProgressBar()
        layout.addWidget(self.progress_bar)

        layout.addSpacing(10)

        # Center Area: ASL Image Card
        self.img_card = QFrame()
        self.img_card.setObjectName("imgCard")
        self.img_card.setFixedSize(260, 240)
        self.img_card_layout = QVBoxLayout(self.img_card)
        self.img_card_layout.setContentsMargins(4, 4, 4, 4)
        self.img_card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.asl_img_label = QLabel()
        self.asl_img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.asl_img_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.img_card_layout.addWidget(self.asl_img_label)

        # Wrap image container to center it
        img_wrap = QWidget()
        img_wrap_layout = QHBoxLayout(img_wrap)
        img_wrap_layout.setContentsMargins(0, 0, 0, 0)
        img_wrap_layout.addWidget(self.img_card, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(img_wrap)

        layout.addSpacing(10)

        # Choices Grid Row
        choices_wrap = QWidget()
        choices_layout = QHBoxLayout(choices_wrap)
        choices_layout.setContentsMargins(0, 0, 0, 0)
        choices_layout.setSpacing(10)

        self.choice_buttons = []
        for i in range(4):
            btn = QPushButton("")
            btn.setObjectName(f"choiceBtn_{i}")
            btn.setFixedSize(70, 48)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            # Lambda capture correct button callback
            btn.clicked.connect(lambda checked, b=btn: self.on_choice_selected(b))
            choices_layout.addWidget(btn)
            self.choice_buttons.append(btn)

        choices_container = QWidget()
        choices_container_layout = QHBoxLayout(choices_container)
        choices_container_layout.setContentsMargins(0, 0, 0, 0)
        choices_container_layout.addWidget(choices_wrap, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(choices_container)

        # Stop Quizzing Button
        self.btn_stop_quizzing = QPushButton("Stop Quizzing")
        self.btn_stop_quizzing.setFixedSize(140, 36)
        self.btn_stop_quizzing.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_stop_quizzing.clicked.connect(self.stop_quizzing)
        layout.addWidget(self.btn_stop_quizzing, 0, Qt.AlignmentFlag.AlignHCenter)

        self.card_layout.addWidget(self.quiz_widget)

    def _build_results_screen(self):
        self.results_widget = QWidget()
        layout = QVBoxLayout(self.results_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.results_title = QLabel("Quiz Complete!")
        self.results_title.setObjectName("resultsTitle")
        self.results_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_font(self.results_title, size=18, bold=True)
        layout.addWidget(self.results_title)

        # Rings View
        self.results_ring = ResultsRing(self)
        layout.addWidget(self.results_ring, 0, Qt.AlignmentFlag.AlignHCenter)

        self.results_summary = QLabel("You scored 0 of 0 cards.")
        self.results_summary.setObjectName("resultsSummary")
        self.results_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_font(self.results_summary, size=12)
        layout.addWidget(self.results_summary)

        # Stat cards row
        stats_row = QWidget()
        stats_layout = QHBoxLayout(stats_row)
        stats_layout.setSpacing(12)
        stats_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Correct Card
        self.stat_box_correct = QFrame()
        self.stat_box_correct.setObjectName("statBoxCorrect")
        self.stat_box_correct.setFixedSize(80, 56)
        sbc_layout = QVBoxLayout(self.stat_box_correct)
        sbc_layout.setContentsMargins(6, 6, 6, 6)
        sbc_layout.setSpacing(2)
        self.stat_correct_val = QLabel("0")
        self.stat_correct_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_font(self.stat_correct_val, size=16, bold=True)
        lbl_correct = QLabel("CORRECT")
        lbl_correct.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_font(lbl_correct, size=8)
        lbl_correct.setStyleSheet(f"color: {c('text_secondary')};")
        sbc_layout.addWidget(self.stat_correct_val)
        sbc_layout.addWidget(lbl_correct)

        # Missed Card
        self.stat_box_missed = QFrame()
        self.stat_box_missed.setObjectName("statBoxMissed")
        self.stat_box_missed.setFixedSize(80, 56)
        sbm_layout = QVBoxLayout(self.stat_box_missed)
        sbm_layout.setContentsMargins(6, 6, 6, 6)
        sbm_layout.setSpacing(2)
        self.stat_missed_val = QLabel("0")
        self.stat_missed_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_font(self.stat_missed_val, size=16, bold=True)
        lbl_missed = QLabel("MISSED")
        lbl_missed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_font(lbl_missed, size=8)
        lbl_missed.setStyleSheet(f"color: {c('text_secondary')};")
        sbm_layout.addWidget(self.stat_missed_val)
        sbm_layout.addWidget(lbl_missed)

        stats_layout.addWidget(self.stat_box_correct)
        stats_layout.addWidget(self.stat_box_missed)
        layout.addWidget(stats_row)

        # Per-letter results breakdown (populated by show_results)
        breakdown_header = QLabel("Results by Letter")
        breakdown_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_font(breakdown_header, size=10, bold=True)
        breakdown_header.setStyleSheet(f"color: {c('text_secondary')};")
        layout.addWidget(breakdown_header)

        self.letter_breakdown_container = QWidget()
        self.letter_breakdown_container.setStyleSheet(f"""
            background-color: {c('input_bg')};
            border: 1px solid {c('border')};
            border-radius: 8px;
        """)
        self._letter_breakdown_grid = QGridLayout(self.letter_breakdown_container)
        self._letter_breakdown_grid.setContentsMargins(12, 8, 12, 8)
        self._letter_breakdown_grid.setSpacing(6)
        layout.addWidget(self.letter_breakdown_container)

        # Actions Buttons Row
        actions_row = QWidget()
        act_layout = QHBoxLayout(actions_row)
        act_layout.setSpacing(16)
        act_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_retry = QPushButton("Retry Session")
        self.btn_retry.setFixedSize(130, 38)
        self.btn_retry.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_retry.clicked.connect(self.retry_quiz)

        self.btn_dashboard = QPushButton("Dashboard")
        self.btn_dashboard.setFixedSize(130, 38)
        self.btn_dashboard.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_dashboard.clicked.connect(self.return_to_dashboard)

        act_layout.addWidget(self.btn_retry)
        act_layout.addWidget(self.btn_dashboard)
        layout.addWidget(actions_row)

        self.card_layout.addWidget(self.results_widget)

    def _build_side_panel(self):
        # Header/Label
        score_hdr = QLabel("SESSION SCORE")
        score_hdr.setStyleSheet(f"color: {c('text_muted')};")
        _set_font(score_hdr, size=10, bold=True)
        self.side_layout.addWidget(score_hdr)

        # Score box layout grid
        score_grid_w = QWidget()
        score_grid = QGridLayout(score_grid_w)
        score_grid.setContentsMargins(0, 0, 0, 0)
        score_grid.setSpacing(8)

        # Correct Card
        self.side_correct_card = QFrame()
        self.side_correct_card.setObjectName("sideCorrectCard")
        scc_layout = QVBoxLayout(self.side_correct_card)
        scc_layout.setContentsMargins(8, 10, 8, 10)
        self.lbl_side_correct = QLabel("0")
        self.lbl_side_correct.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_font(self.lbl_side_correct, size=18, bold=True)
        lbl_c_lbl = QLabel("Correct")
        lbl_c_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_font(lbl_c_lbl, size=9)
        lbl_c_lbl.setStyleSheet(f"color: {c('text_secondary')};")
        scc_layout.addWidget(self.lbl_side_correct)
        scc_layout.addWidget(lbl_c_lbl)

        # Missed Card
        self.side_missed_card = QFrame()
        self.side_missed_card.setObjectName("sideMissedCard")
        smc_layout = QVBoxLayout(self.side_missed_card)
        smc_layout.setContentsMargins(8, 10, 8, 10)
        self.lbl_side_missed = QLabel("0")
        self.lbl_side_missed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_font(self.lbl_side_missed, size=18, bold=True)
        lbl_m_lbl = QLabel("Missed")
        lbl_m_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_font(lbl_m_lbl, size=9)
        lbl_m_lbl.setStyleSheet(f"color: {c('text_secondary')};")
        smc_layout.addWidget(self.lbl_side_missed)
        smc_layout.addWidget(lbl_m_lbl)

        # Accuracy Card
        self.side_accuracy_card = QFrame()
        self.side_accuracy_card.setObjectName("sideAccuracyCard")
        sac_layout = QVBoxLayout(self.side_accuracy_card)
        sac_layout.setContentsMargins(8, 10, 8, 10)
        self.lbl_side_acc = QLabel("—")
        self.lbl_side_acc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_font(self.lbl_side_acc, size=18, bold=True)
        lbl_a_lbl = QLabel("Accuracy")
        lbl_a_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_font(lbl_a_lbl, size=9)
        lbl_a_lbl.setStyleSheet(f"color: {c('text_secondary')};")
        sac_layout.addWidget(self.lbl_side_acc)
        sac_layout.addWidget(lbl_a_lbl)

        score_grid.addWidget(self.side_correct_card, 0, 0)
        score_grid.addWidget(self.side_missed_card, 0, 1)
        score_grid.addWidget(self.side_accuracy_card, 1, 0, 1, 2)

        self.side_layout.addWidget(score_grid_w)

        # Streak Row
        streak_lbl = QLabel("CURRENT STREAK")
        streak_lbl.setStyleSheet(f"color: {c('text_muted')};")
        _set_font(streak_lbl, size=10, bold=True)
        self.side_layout.addWidget(streak_lbl)

        streak_row = QWidget()
        streak_layout = QHBoxLayout(streak_row)
        streak_layout.setContentsMargins(0, 0, 0, 0)
        streak_layout.setSpacing(10)

        flame_lbl = QLabel("")
        _set_font(flame_lbl, size=24)
        streak_layout.addWidget(flame_lbl)

        self.lbl_streak_val = QLabel("0")
        self.lbl_streak_val.setStyleSheet(f"color: #F97316;")
        _set_font(self.lbl_streak_val, size=26, bold=True)
        streak_layout.addWidget(self.lbl_streak_val)

        lbl_streak_text = QLabel("correct\nin a row")
        lbl_streak_text.setStyleSheet(f"color: {c('text_secondary')};")
        _set_font(lbl_streak_text, size=10)
        streak_layout.addWidget(lbl_streak_text)
        streak_layout.addStretch()

        self.side_layout.addWidget(streak_row)

        # Feedback Section
        fb_lbl = QLabel("FEEDBACK")
        fb_lbl.setStyleSheet(f"color: {c('text_muted')};")
        _set_font(fb_lbl, size=10, bold=True)
        self.side_layout.addWidget(fb_lbl)

        self.fb_box = QFrame()
        self.fb_box.setObjectName("feedbackBox")
        self.fb_box_layout = QVBoxLayout(self.fb_box)
        self.fb_box_layout.setContentsMargins(10, 10, 10, 10)
        self.fb_box_layout.setSpacing(4)

        self.fb_title = QLabel("Ready to Go!")
        self.fb_title.setWordWrap(True)
        _set_font(self.fb_title, size=12, bold=True)
        self.fb_sub = QLabel("Pick a mode and start")
        self.fb_sub.setWordWrap(True)
        _set_font(self.fb_sub, size=10)
        self.fb_box_layout.addWidget(self.fb_title)
        self.fb_box_layout.addWidget(self.fb_sub)

        self.side_layout.addWidget(self.fb_box)

        # Progress Tracker Dots
        tracker_lbl = QLabel("PROGRESS TRACKER")
        tracker_lbl.setStyleSheet(f"color: {c('text_muted')};")
        _set_font(tracker_lbl, size=10, bold=True)
        self.side_layout.addWidget(tracker_lbl)

        self.tracker_container = QWidget()
        self.tracker_grid = QGridLayout(self.tracker_container)
        self.tracker_grid.setContentsMargins(0, 0, 0, 0)
        self.tracker_grid.setSpacing(6)
        self.side_layout.addWidget(self.tracker_container)

        self.side_layout.addStretch()

    # ── Interactive States ─────────────────────────────────────────────────────

    def go_to_setup(self):
        self.setup_widget.show()
        self.quiz_widget.hide()
        self.results_widget.hide()

        # Reset radio buttons to default
        self.mode_flashcard.setChecked(True)
        self.set_shuffle.setChecked(True)

        self.set_feedback("neutral", "Ready to Go!", "Select quiz settings to start.")
        self.lbl_side_correct.setText("0")
        self.lbl_side_missed.setText("0")
        self.lbl_side_acc.setText("—")
        self.lbl_streak_val.setText("0")
        self.streak = 0
        self.answers = []

        # Clear tracker dots
        while self.tracker_grid.count():
            item = self.tracker_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def start_quiz(self):
        if self.mode_camera.isChecked():
            self._app.show_gesture_detection(self._username)
            return

        letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        if self.set_random.isChecked():
            random.shuffle(letters)
            self.deck = letters[:10]
            self.deck_size = 10
        elif self.set_all.isChecked():
            self.deck = letters
            self.deck_size = 26
        else:  # self.set_shuffle.isChecked()
            random.shuffle(letters)
            self.deck = letters
            self.deck_size = 26

        self.current_idx = 0
        self.answers = [None] * self.deck_size
        self.streak = 0

        # Create Tracker dots in Side Panel
        while self.tracker_grid.count():
            item = self.tracker_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cols = 5
        self.tracker_dots = []
        for i, letter in enumerate(self.deck):
            dot = QLabel(str(i + 1))
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dot.setFixedSize(22, 22)
            _set_font(dot, size=9, bold=True)
            dot.setStyleSheet(f"""
                background-color: {c('border')};
                color: {c('text_secondary')};
                border-radius: 11px;
            """)
            row = i // cols
            col = i % cols
            self.tracker_grid.addWidget(dot, row, col)
            self.tracker_dots.append(dot)

        # Switch Screen to Quiz Screen
        self.setup_widget.hide()
        self.quiz_widget.show()
        self.results_widget.hide()

        self.render_question()

    def render_question(self):
        self.is_answered = False
        correct_letter = self.deck[self.current_idx]

        # Update Progress Counter and Segmented Bar
        self.progress_lbl.setText(f"Question {self.current_idx + 1} of {self.deck_size}")
        self.progress_bar.configure(self.deck_size, self.answers)
        self.progress_bar.set_current(self.current_idx)

        # Highlight current dot tracker
        for i, dot in enumerate(self.tracker_dots):
            if i == self.current_idx:
                dot.setStyleSheet(f"""
                    background-color: {c('accent')};
                    color: #FFFFFF;
                    border-radius: 11px;
                """)
            elif self.answers[i] is None:
                dot.setStyleSheet(f"""
                    background-color: {c('border')};
                    color: {c('text_secondary')};
                    border-radius: 11px;
                """)

        # Get local image path
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        img_path = os.path.normpath(
            os.path.join(project_root, "assets", "reference", f"Sign_Language_{correct_letter}.jpg")
        )

        self.asl_img_label.setPixmap(QPixmap())
        self.asl_img_label.setText("")

        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    240, 220, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
                self.asl_img_label.setPixmap(scaled_pixmap)
            else:
                self.render_gradient_placeholder(correct_letter)
        else:
            self.render_gradient_placeholder(correct_letter)

        # Build Multiple-Choice Options
        # Choose 3 random incorrect letters from alphabet (excluding correct)
        other_letters = [ch for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if ch != correct_letter]
        incorrect_options = random.sample(other_letters, 3)
        options = [correct_letter] + incorrect_options
        random.shuffle(options)  # Shuffle position of options

        # Populate choice buttons
        for i, btn in enumerate(self.choice_buttons):
            btn.setText(options[i])
            # Reset stylesheet to normal choices format
            btn.setEnabled(True)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c('bg_primary')};
                    color: {c('text_primary')};
                    border: 2px solid {c('border')};
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    border: 2px solid {c('accent')};
                    background-color: {c('input_bg')};
                }}
            """)

        self.set_feedback("neutral", "Your Turn!", f"What letter does this hand sign represent?")

    def render_gradient_placeholder(self, letter: str):
        # A sleek colored box if the offline asset is missing
        self.asl_img_label.setText(f"Sign: {letter}")
        _set_font(self.asl_img_label, size=32, bold=True)
        self.asl_img_label.setStyleSheet(f"""
            color: #FFFFFF;
            background-color: {c('accent')};
            border-radius: 8px;
        """)

    def on_choice_selected(self, selected_btn: QPushButton):
        if self.is_answered:
            return
        self.is_answered = True

        correct_letter = self.deck[self.current_idx]
        picked_letter = selected_btn.text()
        is_correct = (picked_letter == correct_letter)

        self.answers[self.current_idx] = is_correct

        # Immediately update segmented progress bar
        self.progress_bar.configure(self.deck_size, self.answers)

        # Log to practice history
        if self.set_random.isChecked():
            set_label = "Random 10"
        elif self.set_all.isChecked():
            set_label = "Full Alphabet"
        else:
            set_label = "Shuffle All"
        mode_label = "Camera Practice Quiz" if self.mode_camera.isChecked() else "Flashcard Quiz"
        log_quiz_result(
            username=self._username,
            source="flashcard_quiz",
            letter=correct_letter,
            result="correct" if is_correct else "missed",
            confidence=None,
            set_name=f"{mode_label} — {set_label}",
        )

        # Disable all buttons and highlight correct/incorrect
        for btn in self.choice_buttons:
            btn.setEnabled(False)
            if btn.text() == correct_letter:
                # Highlight correct letter green
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {c('success_bg')};
                        color: {c('success')};
                        border: 2px solid {c('success')};
                        border-radius: 8px;
                        font-size: 16px;
                        font-weight: bold;
                    }}
                """)
            elif btn == selected_btn and not is_correct:
                # Highlight picked incorrect letter red
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {c('error_bg')};
                        color: {c('error')};
                        border: 2px solid {c('error')};
                        border-radius: 8px;
                        font-size: 16px;
                        font-weight: bold;
                    }}
                """)
            else:
                # Normal style but disabled
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {c('bg_primary')};
                        color: {c('text_muted')};
                        border: 1px solid {c('border')};
                        border-radius: 8px;
                        font-size: 16px;
                        font-weight: bold;
                    }}
                """)

        # Update scoring and tracker dot color
        tracker_dot = self.tracker_dots[self.current_idx]
        if is_correct:
            self.streak += 1
            tracker_dot.setStyleSheet(f"""
                background-color: {c('success')};
                color: #FFFFFF;
                border-radius: 11px;
            """)
            tip = LETTER_METADATA.get(correct_letter, {}).get("tip", "Well done!")
            self.set_feedback("correct", "Correct!", tip)
        else:
            self.streak = 0
            tracker_dot.setStyleSheet(f"""
                background-color: {c('error')};
                color: #FFFFFF;
                border-radius: 11px;
            """)
            desc = LETTER_METADATA.get(correct_letter, {}).get("tip", "Keep practicing!")
            self.set_feedback("wrong", f"It was {correct_letter}!", desc)

        self.update_scores()

        # Automatic progression after 1.5s delay
        QTimer.singleShot(1500, self.advance_quiz)

    def advance_quiz(self):
        self.current_idx += 1
        if self.current_idx >= self.deck_size:
            self.show_results()
        else:
            self.render_question()

    def update_scores(self):
        correct = sum(1 for a in self.answers if a is True)
        incorrect = sum(1 for a in self.answers if a is False)
        answered_cnt = correct + incorrect

        self.lbl_side_correct.setText(str(correct))
        self.lbl_side_missed.setText(str(incorrect))
        self.lbl_streak_val.setText(str(self.streak))

        if answered_cnt > 0:
            accuracy = int((correct / answered_cnt) * 100)
            self.lbl_side_acc.setText(f"{accuracy}%")
        else:
            self.lbl_side_acc.setText("—")

    def set_feedback(self, kind: str, title: str, sub: str):
        self.fb_title.setText(title)
        self.fb_sub.setText(sub)

        # Style box according to answer outcome
        if kind == "correct":
            self.fb_box.setStyleSheet(f"""
                background-color: {c('success_bg')};
                border: 1px solid {c('success')};
                border-radius: 8px;
            """)
            self.fb_title.setStyleSheet(f"color: {c('success')};")
            self.fb_sub.setStyleSheet(f"color: {c('success')};")
        elif kind == "wrong":
            self.fb_box.setStyleSheet(f"""
                background-color: {c('error_bg')};
                border: 1px solid {c('error')};
                border-radius: 8px;
            """)
            self.fb_title.setStyleSheet(f"color: {c('error')};")
            self.fb_sub.setStyleSheet(f"color: {c('error')};")
        else:
            # Neutral / Ready states
            self.fb_box.setStyleSheet(f"""
                background-color: {c('input_bg')};
                border: 1px solid {c('border')};
                border-radius: 8px;
            """)
            self.fb_title.setStyleSheet(f"color: {c('text_primary')};")
            self.fb_sub.setStyleSheet(f"color: {c('text_secondary')};")

    def show_results(self):
        correct = sum(1 for a in self.answers if a is True)
        incorrect = sum(1 for a in self.answers if a is False)
        accuracy = int((correct / self.deck_size) * 100) if self.deck_size > 0 else 0

        # Update stats text
        self.stat_correct_val.setText(str(correct))
        self.stat_missed_val.setText(str(incorrect))
        self.results_summary.setText(f"You scored {correct} of {self.deck_size} cards correctly.")

        # Update Circular ring
        self.results_ring.set_percentage(float(accuracy))

        # Update Title Header based on accuracy
        if accuracy >= 90:
            title = "Excellent!"
        elif accuracy >= 70:
            title = "Nice Work!"
        else:
            title = "Keep Practicing!"
        self.results_title.setText(title)

        # Populate per-letter breakdown grid
        # Clear any previous run's cells
        while self._letter_breakdown_grid.count():
            item = self._letter_breakdown_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cols = 5
        letter_results = list(zip(self.deck, [a for a in self.answers if a is not None]))
        for i, (letter, was_correct) in enumerate(letter_results):
            cell = QLabel(f"{letter}")
            cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell.setStyleSheet(
                f"color: {c('success') if was_correct else c('error')};"
                f"font-size: 12px; font-weight: bold; background: transparent; border: none;"
            )
            self._letter_breakdown_grid.addWidget(cell, i // cols, i % cols)

        # Switch Screen
        self.setup_widget.hide()
        self.quiz_widget.hide()
        self.results_widget.show()

        # Update tracker final state
        self.progress_lbl.setText("Session Complete")
        self.progress_bar.configure(self.deck_size, self.answers)
        self.progress_bar.set_current(self.deck_size)  # past last index — no active pulse

    def retry_quiz(self):
        self.start_quiz()

    def stop_quizzing(self):
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Stop Quiz", "Are you sure you want to stop the quiz session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            answered_cnt = sum(1 for a in self.answers if a is not None)
            if answered_cnt > 0:
                self.show_results()
            else:
                self.go_to_setup()

    def return_to_dashboard(self):
        self._app.show_dashboard(self._username)

    # ── Navigation / Core Wiring ──────────────────────────────────────────────

    def _on_navigation_requested(self, key: str):
        if key == "dashboard":
            self._app.show_dashboard(self._username)
        elif key == "camera":
            self._app.show_gesture_detection(self._username)
        elif key == "reference":
            self._app.show_reference_chart(self._username)
        elif key == "flashcards":
            self.go_to_setup()  # Fresh session setup
        elif key == "settings":
            self._app.show_settings(self._username)
        elif key == "history":
            self._app.show_gesture_history(self._username)

    def _on_logout(self):
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Logout", "Are you sure you want to log out?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._app.show_login()

    def _on_theme_changed(self, is_dark: bool):
        self._update_styles()

    def _update_styles(self):
        # Apply stylesheet to main widgets
        self.setStyleSheet(f"QWidget#flashcardQuizPage {{ background-color: {c('bg_secondary')}; }}")
        self.title_lbl.setStyleSheet(f"color: {c('text_primary')}; border: none; background: transparent;")

        self.avatar.setStyleSheet(f"""
            QLabel {{
                background-color: {c('accent')};
                color: #FFFFFF;
                border-radius: 18px;
                font-family: 'Segoe UI';
                font-size: 14px;
                font-weight: bold;
            }}
        """)

        # Main active Card Frame
        self.main_card.setStyleSheet(f"""
            QFrame#quizMainCard {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 12px;
            }}
            QFrame#quizMainCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        _add_shadow(self.main_card)

        # Side Status Panel Frame
        self.side_panel.setStyleSheet(f"""
            QFrame#quizSidePanel {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 12px;
            }}
            QFrame#quizSidePanel QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        _add_shadow(self.side_panel)

        # Setup Screen Widgets
        setup_title = self.setup_widget.findChild(QLabel, "setupTitle")
        if setup_title:
            setup_title.setStyleSheet(f"color: {c('text_primary')};")
        setup_sub = self.setup_widget.findChild(QLabel, "setupSub")
        if setup_sub:
            setup_sub.setStyleSheet(f"color: {c('text_secondary')};")

        # Radio buttons and containers styling
        radio_style = f"""
            QRadioButton {{
                color: {c('text_primary')};
                spacing: 10px;
                font-size: 13px;
                background: transparent;
            }}
            QRadioButton::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid {c('border')};
                background-color: {c('bg_primary')};
            }}
            QRadioButton::indicator:hover {{
                border-color: {c('accent')};
            }}
            QRadioButton::indicator:checked {{
                border: 5px solid {c('input_bg')};
                background-color: {c('accent')};
            }}
        """
        for r_btn in [self.mode_flashcard, self.mode_camera, self.set_random, self.set_all, self.set_shuffle]:
            r_btn.setStyleSheet(radio_style)

        # Container styling update
        for container in self.setup_widget.findChildren(QFrame, "settingsContainer"):
            container.setStyleSheet(f"""
                QFrame#settingsContainer {{
                    background-color: {c('input_bg')};
                    border: 1px solid {c('border')};
                    border-radius: 8px;
                }}
            """)

        # Label styling update
        for label_name in ["modeLabel", "setLabel"]:
            lbl = self.setup_widget.findChild(QLabel, label_name)
            if lbl:
                lbl.setStyleSheet(f"color: {c('text_muted')};")

        # Start Quiz Button
        self.btn_start.setStyleSheet(f"""
            QPushButton {{
                background-color: {c('accent')};
                color: #FFFFFF;
                border: none;
                border-radius: 22px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {c('accent_hover')};
            }}
        """)

        # Quiz Screen components
        self.quiz_mode_lbl.setStyleSheet(f"color: {c('text_primary')};")

        # Progress pill
        self.progress_pill.setStyleSheet(f"""
            QFrame#progressPill {{
                background-color: {c('accent')}20;
                border: 1px solid {c('accent')}50;
                border-radius: 12px;
            }}
        """)
        self.progress_lbl.setStyleSheet(f"color: {c('accent')}; background: transparent; border: none;")

        # The custom QuizProgressBar paints itself using c() — just trigger repaint
        self.progress_bar.update()

        # ASL Image Container Box
        self.img_card.setStyleSheet(f"""
            QFrame#imgCard {{
                background-color: {c('input_bg')};
                border: 2px solid {c('border')};
                border-radius: 10px;
            }}
        """)

        # Results Screen components
        self.results_title.setStyleSheet(f"color: {c('text_primary')};")
        self.results_summary.setStyleSheet(f"color: {c('text_secondary')};")

        # Results Summary Stat boxes
        stat_box_style = f"""
            QFrame {{
                background-color: {c('input_bg')};
                border: 1px solid {c('border')};
                border-radius: 8px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """
        self.stat_box_correct.setStyleSheet(stat_box_style)
        self.stat_correct_val.setStyleSheet(f"color: {c('success')};")
        self.stat_box_missed.setStyleSheet(stat_box_style)
        self.stat_missed_val.setStyleSheet(f"color: {c('error')};")

        # Action Buttons
        self.btn_retry.setStyleSheet(f"""
            QPushButton {{
                background-color: {c('accent')};
                color: #FFFFFF;
                border: none;
                border-radius: 19px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {c('accent_hover')};
            }}
        """)

        self.btn_dashboard.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {c('text_primary')};
                border: 1px solid {c('border')};
                border-radius: 19px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {c('input_bg')};
                border-color: {c('text_secondary')};
            }}
        """)

        if hasattr(self, 'btn_stop_quizzing') and self.btn_stop_quizzing:
            self.btn_stop_quizzing.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {c('error')};
                    border: 1px solid {c('error')};
                    border-radius: 18px;
                    font-size: 12px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {c('error_bg')};
                }}
            """)

        # Side panel cards
        side_card_style = f"""
            QFrame {{
                background-color: {c('input_bg')};
                border: 1px solid {c('border')};
                border-radius: 8px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """
        self.side_correct_card.setStyleSheet(side_card_style)
        self.side_missed_card.setStyleSheet(side_card_style)
        self.side_accuracy_card.setStyleSheet(side_card_style)

        self.lbl_side_correct.setStyleSheet(f"color: {c('success')};")
        self.lbl_side_missed.setStyleSheet(f"color: {c('error')};")
        self.lbl_side_acc.setStyleSheet(f"color: {c('text_primary')};")

        # Select active options update

        # Refresh repaint for circular ring
        self.results_ring.update()