import os
import random
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QProgressBar, QGridLayout, QSizePolicy, QSpacerItem, QRadioButton, QButtonGroup,
    QGraphicsDropShadowEffect, QScrollArea,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF, QPropertyAnimation, QVariantAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QCursor, QFont, QColor, QPainter, QPen, QPixmap, QLinearGradient, QBrush

from components.layout.sidebar import Sidebar
from core.theme import c, is_dark, ThemeSignal
from core.ui_helpers import _set_font, _add_shadow
from modules.reference.constants import LETTER_METADATA
from modules.gesture_history.backend import log_quiz_result

print(f"[SignDesk] quiz UI loaded from: {__file__}")


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


class GestureCard(QFrame):
    """
    Clickable gesture image card used as a multiple-choice answer
    in the Multiple Choice Quiz mode. Features hover shadow animation.
    """
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedSize(190, 178)
        self._letter = ""
        self._interactive = True

        _layout = QVBoxLayout(self)
        _layout.setContentsMargins(10, 10, 10, 10)
        _layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.img_label.setStyleSheet("background: transparent; border: none;")
        _layout.addWidget(self.img_label)

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(10)
        self._shadow.setOffset(0, 2)
        self._shadow.setColor(QColor(0, 0, 0, 30))
        self.setGraphicsEffect(self._shadow)

    def set_image(self, letter: str, img_path: str):
        self._letter = letter
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    156, 138,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.img_label.setPixmap(scaled)
                return
        self.img_label.setText(f"Sign: {letter}")
        _set_font(self.img_label, size=22, bold=True)

    @property
    def letter(self) -> str:
        return self._letter

    def set_interactive(self, enabled: bool):
        self._interactive = enabled
        self.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor) if enabled
            else QCursor(Qt.CursorShape.ArrowCursor)
        )

    def mousePressEvent(self, event):
        if self._interactive and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        if self._interactive:
            self._shadow.setBlurRadius(22)
            self._shadow.setOffset(0, 6)
            self._shadow.setColor(QColor(0, 0, 0, 55))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._shadow.setBlurRadius(10)
        self._shadow.setOffset(0, 2)
        self._shadow.setColor(QColor(0, 0, 0, 30))
        super().leaveEvent(event)


def _lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
    """Linear interpolate between two QColors (matches the sidebar's fade)."""
    return QColor(
        int(c1.red()   + (c2.red()   - c1.red())   * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue()  + (c2.blue()  - c1.blue())  * t),
        int(c1.alpha() + (c2.alpha() - c1.alpha()) * t),
    )


class AnimatedButton(QPushButton):
    """
    QPushButton with the same smooth hover color-fade used by the navigation
    sidebar's NavItem (QVariantAnimation + OutCubic). It self-styles on every
    animation tick, so never call setStyleSheet() on it directly — use
    configure() and let the page re-apply on theme change.
    """
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._radius = 20
        self._font_size = 13
        self._border_w = 0
        self._idle_bg = QColor("#6C63FF")
        self._hover_bg = QColor("#5A52E0")
        self._idle_text = QColor("#FFFFFF")
        self._hover_text = QColor("#FFFFFF")
        self._border_col = QColor(0, 0, 0, 0)
        self._t = 0.0

        self._anim = QVariantAnimation()
        self._anim.setDuration(170)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_tick)
        self._apply(0.0)

    def configure(self, idle_bg, hover_bg, idle_text, hover_text,
                  border_col=None, border_w=0, radius=20, font_size=13):
        self._idle_bg = QColor(idle_bg)
        self._hover_bg = QColor(hover_bg)
        self._idle_text = QColor(idle_text)
        self._hover_text = QColor(hover_text)
        self._border_col = QColor(border_col) if border_col is not None else QColor(0, 0, 0, 0)
        self._border_w = border_w
        self._radius = radius
        self._font_size = font_size
        self._anim.stop()
        self._t = 0.0
        self._apply(0.0)

    def _on_tick(self, val):
        self._t = (val or 0) / 1000.0
        self._apply(self._t)

    @staticmethod
    def _rgba(col: QColor) -> str:
        return f"rgba({col.red()},{col.green()},{col.blue()},{col.alpha()})"

    def _apply(self, t: float):
        if not self.isEnabled():
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(130,130,140,38);
                    color: rgba(150,150,160,210);
                    border: {self._border_w}px solid rgba(130,130,140,60);
                    border-radius: {self._radius}px;
                    font-size: {self._font_size}px;
                    font-weight: bold;
                }}
            """)
            return
        bg = _lerp_color(self._idle_bg, self._hover_bg, t)
        tx = _lerp_color(self._idle_text, self._hover_text, t)
        border = f"{self._border_w}px solid {self._rgba(self._border_col)}" if self._border_w else "none"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._rgba(bg)};
                color: {self._rgba(tx)};
                border: {border};
                border-radius: {self._radius}px;
                font-size: {self._font_size}px;
                font-weight: bold;
            }}
        """)

    def enterEvent(self, event):
        if self.isEnabled():
            self._anim.stop()
            self._anim.setStartValue(int(self._t * 1000))
            self._anim.setEndValue(1000)
            self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.isEnabled():
            self._anim.stop()
            self._anim.setStartValue(int(self._t * 1000))
            self._anim.setEndValue(0)
            self._anim.start()
        super().leaveEvent(event)

    def changeEvent(self, event):
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.EnabledChange:
            self._anim.stop()
            self._t = 0.0
            self._apply(0.0)
        super().changeEvent(event)


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
        tb_layout = QHBoxLayout(topbar)
        tb_layout.setContentsMargins(28, 16, 28, 8)
        tb_layout.setSpacing(24)

        card = QFrame()
        card.setObjectName("welcomeCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        card.setStyleSheet(f"""
            QFrame#welcomeCard {{
                background-color: {c('info_bg')};
                border: 1px solid {c('welcome_border')};
                border-radius: 14px;
            }}
            QFrame#welcomeCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 14, 24, 14)
        card_layout.setSpacing(2)

        self.title_lbl = QLabel("Flashcard Recognition Quiz")
        self.title_lbl.setStyleSheet(f"color: {c('welcome_title')}; font-family: 'Segoe UI'; font-size: 24px; font-weight: bold;")
        card_layout.addWidget(self.title_lbl, 0, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        self.subtitle_lbl = QLabel("Practice and improve your gesture recognition accuracy")
        self.subtitle_lbl.setObjectName("headerSubtitle")
        _set_font(self.subtitle_lbl, size=11)
        card_layout.addWidget(self.subtitle_lbl, 0, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        
        tb_layout.addWidget(card, stretch=1)

        # Avatar
        self.avatar = QLabel(self._username[0].upper() if self._username else "?")
        self.avatar.setFixedSize(36, 36)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tb_layout.addWidget(self.avatar, 0, Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(topbar)

        # Split Section: Main Card on left, Status panel on right
        content_split = QWidget()
        content_layout = QHBoxLayout(content_split)
        content_layout.setContentsMargins(28, 8, 28, 24)
        content_layout.setSpacing(20)

        # Left Column: The Main Active Screen Card (scrollable so content never overlaps)
        self.main_card = QFrame()
        self.main_card.setObjectName("quizMainCard")
        main_card_outer = QVBoxLayout(self.main_card)
        main_card_outer.setContentsMargins(0, 0, 0, 0)
        main_card_outer.setSpacing(0)

        self._screens_scroll = QScrollArea()
        self._screens_scroll.setWidgetResizable(True)
        self._screens_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._screens_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._screens_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        screens_host = QWidget()
        screens_host.setStyleSheet("background: transparent;")
        self.card_layout = QVBoxLayout(screens_host)
        self.card_layout.setContentsMargins(24, 24, 24, 24)
        self.card_layout.setSpacing(20)

        self._screens_scroll.setWidget(screens_host)
        self._screens_scroll.viewport().setStyleSheet("background: transparent;")
        main_card_outer.addWidget(self._screens_scroll)
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
        self._build_mc_quiz_screen()
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
        self.mode_multiple_choice = QRadioButton("Multiple Choice Quiz")
        self.mode_multiple_choice.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.mode_camera = QRadioButton("Camera Practice Quiz")
        self.mode_camera.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.mode_flashcard)
        self.mode_group.addButton(self.mode_multiple_choice)
        self.mode_group.addButton(self.mode_camera)
        self.mode_flashcard.setChecked(True)

        mc_layout.addWidget(self.mode_flashcard)
        mc_layout.addWidget(self.mode_multiple_choice)
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
        self.btn_start.setFixedSize(200, 48)
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
            btn.setFixedSize(76, 56)
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

        # ── Reveal / Skip / Next action row ──────────────────────────────────
        fc_actions_row = QWidget()
        fc_actions_layout = QHBoxLayout(fc_actions_row)
        fc_actions_layout.setContentsMargins(0, 0, 0, 0)
        fc_actions_layout.setSpacing(16)
        fc_actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.fc_btn_reveal = AnimatedButton("Reveal")
        self.fc_btn_reveal.setFixedSize(116, 42)
        self.fc_btn_reveal.clicked.connect(self.reveal_fc_answer)
        fc_actions_layout.addWidget(self.fc_btn_reveal)

        self.fc_btn_skip = AnimatedButton("Skip")
        self.fc_btn_skip.setFixedSize(116, 42)
        self.fc_btn_skip.clicked.connect(self.skip_fc_question)
        fc_actions_layout.addWidget(self.fc_btn_skip)

        self.fc_btn_next = AnimatedButton("Next")
        self.fc_btn_next.setFixedSize(116, 42)
        self.fc_btn_next.setEnabled(False)
        self.fc_btn_next.clicked.connect(self.next_fc_question)
        fc_actions_layout.addWidget(self.fc_btn_next)

        layout.addWidget(fc_actions_row)
        layout.addSpacing(4)

        # Stop Quizzing Button
        self.btn_stop_quizzing = AnimatedButton("Stop Quizzing")
        self.btn_stop_quizzing.setFixedSize(140, 38)
        self.btn_stop_quizzing.clicked.connect(self.stop_quizzing)
        layout.addWidget(self.btn_stop_quizzing, 0, Qt.AlignmentFlag.AlignHCenter)

        self.card_layout.addWidget(self.quiz_widget)

    def _build_mc_quiz_screen(self):
        """Build the Multiple Choice quiz screen with gesture image cards."""
        self.mc_quiz_widget = QWidget()
        layout = QVBoxLayout(self.mc_quiz_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # ── Header Row: icon + label + pill counter ──────────────────────────
        hdr_row = QWidget()
        hdr_layout = QHBoxLayout(hdr_row)
        hdr_layout.setContentsMargins(0, 0, 0, 4)
        hdr_layout.setSpacing(8)

        mc_icon_lbl = QLabel("🎯")
        _set_font(mc_icon_lbl, size=16)
        hdr_layout.addWidget(mc_icon_lbl)

        self.mc_mode_lbl = QLabel("Multiple Choice")
        self.mc_mode_lbl.setObjectName("mcModeLbl")
        _set_font(self.mc_mode_lbl, size=13, bold=True)
        hdr_layout.addWidget(self.mc_mode_lbl)
        hdr_layout.addStretch()

        # Pill-shaped question counter
        self.mc_progress_pill = QFrame()
        self.mc_progress_pill.setObjectName("mcProgressPill")
        mc_pill_layout = QHBoxLayout(self.mc_progress_pill)
        mc_pill_layout.setContentsMargins(12, 4, 12, 4)
        mc_pill_layout.setSpacing(4)

        self.mc_progress_lbl = QLabel("Question 0 of 0")
        self.mc_progress_lbl.setObjectName("mcProgressLbl")
        _set_font(self.mc_progress_lbl, size=11, bold=True)
        mc_pill_layout.addWidget(self.mc_progress_lbl)

        hdr_layout.addWidget(self.mc_progress_pill)
        layout.addWidget(hdr_row)

        # ── Segmented Progress Bar ───────────────────────────────────────────
        self.mc_progress_bar = QuizProgressBar()
        layout.addWidget(self.mc_progress_bar)

        layout.addSpacing(4)

        # ── Question Label ───────────────────────────────────────────────────
        self.mc_question_lbl = QLabel("Which gesture is letter A?")
        self.mc_question_lbl.setObjectName("mcQuestionLbl")
        self.mc_question_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_font(self.mc_question_lbl, size=16, bold=True)
        layout.addWidget(self.mc_question_lbl)

        layout.addSpacing(4)

        # ── 2×2 Grid of Gesture Cards ────────────────────────────────────────
        cards_container = QWidget()
        cards_grid = QGridLayout(cards_container)
        cards_grid.setContentsMargins(0, 0, 0, 0)
        cards_grid.setSpacing(16)

        self.mc_cards: list[GestureCard] = []
        for i in range(4):
            card = GestureCard()
            card.setObjectName(f"mcCard_{i}")
            card.clicked.connect(lambda c=card: self.on_mc_card_selected(c))
            cards_grid.addWidget(card, i // 2, i % 2)
            self.mc_cards.append(card)

        cards_wrap = QWidget()
        cards_wrap_layout = QHBoxLayout(cards_wrap)
        cards_wrap_layout.setContentsMargins(0, 0, 0, 0)
        cards_wrap_layout.addStretch()
        cards_wrap_layout.addWidget(cards_container)
        cards_wrap_layout.addStretch()
        layout.addWidget(cards_wrap)

        layout.addSpacing(8)

        # ── Reveal & Skip Buttons Row ────────────────────────────────────────
        mc_actions_row = QWidget()
        mc_actions_layout = QHBoxLayout(mc_actions_row)
        mc_actions_layout.setContentsMargins(0, 0, 0, 0)
        mc_actions_layout.setSpacing(16)
        mc_actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.mc_btn_reveal = AnimatedButton("Reveal")
        self.mc_btn_reveal.setFixedSize(116, 42)
        self.mc_btn_reveal.clicked.connect(self.reveal_mc_answer)
        mc_actions_layout.addWidget(self.mc_btn_reveal)

        self.mc_btn_skip = AnimatedButton("Skip")
        self.mc_btn_skip.setFixedSize(116, 42)
        self.mc_btn_skip.clicked.connect(self.skip_mc_question)
        mc_actions_layout.addWidget(self.mc_btn_skip)

        self.mc_btn_next = AnimatedButton("Next")
        self.mc_btn_next.setFixedSize(116, 42)
        self.mc_btn_next.setEnabled(False)
        self.mc_btn_next.clicked.connect(self.next_mc_question)
        mc_actions_layout.addWidget(self.mc_btn_next)

        layout.addWidget(mc_actions_row)

        layout.addSpacing(4)

        # ── Stop Quizzing Button ─────────────────────────────────────────────
        self.mc_btn_stop = AnimatedButton("Stop Practicing")
        self.mc_btn_stop.setFixedSize(150, 38)
        self.mc_btn_stop.clicked.connect(self.stop_quizzing)
        layout.addWidget(self.mc_btn_stop, 0, Qt.AlignmentFlag.AlignHCenter)

        self.card_layout.addWidget(self.mc_quiz_widget)

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
        self.side_layout.setSpacing(6)

        # ── SESSION SCORE ────────────────────────────────────────────────────
        score_hdr = QLabel("SESSION SCORE")
        score_hdr.setStyleSheet(f"color: {c('text_muted')}; letter-spacing: 1px;")
        _set_font(score_hdr, size=9, bold=True)
        self.side_layout.addWidget(score_hdr)
        self.side_layout.addSpacing(2)

        # Score box layout grid
        score_grid_w = QWidget()
        score_grid_w.setStyleSheet("background: transparent; border: none;")
        score_grid = QGridLayout(score_grid_w)
        score_grid.setContentsMargins(0, 0, 0, 0)
        score_grid.setSpacing(6)

        # Correct Card
        self.side_correct_card = QFrame()
        self.side_correct_card.setObjectName("sideCorrectCard")
        scc_layout = QVBoxLayout(self.side_correct_card)
        scc_layout.setContentsMargins(6, 8, 6, 8)
        scc_layout.setSpacing(2)
        self.lbl_side_correct = QLabel("0")
        self.lbl_side_correct.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_font(self.lbl_side_correct, size=20, bold=True)
        self.lbl_correct_label = QLabel("Correct")
        self.lbl_correct_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_correct_label.setObjectName("scoreSubLabel")
        _set_font(self.lbl_correct_label, size=8)
        scc_layout.addWidget(self.lbl_side_correct)
        scc_layout.addWidget(self.lbl_correct_label)

        # Missed Card
        self.side_missed_card = QFrame()
        self.side_missed_card.setObjectName("sideMissedCard")
        smc_layout = QVBoxLayout(self.side_missed_card)
        smc_layout.setContentsMargins(6, 8, 6, 8)
        smc_layout.setSpacing(2)
        self.lbl_side_missed = QLabel("0")
        self.lbl_side_missed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_font(self.lbl_side_missed, size=20, bold=True)
        self.lbl_missed_label = QLabel("Missed")
        self.lbl_missed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_missed_label.setObjectName("scoreSubLabel")
        _set_font(self.lbl_missed_label, size=8)
        smc_layout.addWidget(self.lbl_side_missed)
        smc_layout.addWidget(self.lbl_missed_label)

        # Accuracy Card — horizontal inline
        self.side_accuracy_card = QFrame()
        self.side_accuracy_card.setObjectName("sideAccuracyCard")
        sac_layout = QHBoxLayout(self.side_accuracy_card)
        sac_layout.setContentsMargins(10, 6, 10, 6)
        sac_layout.setSpacing(8)
        lbl_a_lbl = QLabel("Accuracy")
        _set_font(lbl_a_lbl, size=10)
        lbl_a_lbl.setStyleSheet(f"color: {c('text_secondary')};")
        sac_layout.addWidget(lbl_a_lbl)
        sac_layout.addStretch()
        self.lbl_side_acc = QLabel("—")
        _set_font(self.lbl_side_acc, size=14, bold=True)
        sac_layout.addWidget(self.lbl_side_acc)

        score_grid.addWidget(self.side_correct_card, 0, 0)
        score_grid.addWidget(self.side_missed_card, 0, 1)
        score_grid.addWidget(self.side_accuracy_card, 1, 0, 1, 2)

        self.side_layout.addWidget(score_grid_w)

        # ── Divider ──────────────────────────────────────────────────────────
        div1 = QFrame()
        div1.setFixedHeight(1)
        div1.setStyleSheet(f"background-color: {c('border')};")
        self.side_layout.addSpacing(4)
        self.side_layout.addWidget(div1)
        self.side_layout.addSpacing(4)

        # ── CURRENT STREAK ───────────────────────────────────────────────────
        streak_lbl = QLabel("CURRENT STREAK")
        streak_lbl.setStyleSheet(f"color: {c('text_muted')}; letter-spacing: 1px;")
        _set_font(streak_lbl, size=9, bold=True)
        self.side_layout.addWidget(streak_lbl)
        self.side_layout.addSpacing(2)

        # Streak card (styled container)
        self.streak_card = QFrame()
        self.streak_card.setObjectName("streakCard")
        streak_card_layout = QHBoxLayout(self.streak_card)
        streak_card_layout.setContentsMargins(10, 8, 10, 8)
        streak_card_layout.setSpacing(8)

        self.lbl_streak_val = QLabel("0")
        self.lbl_streak_val.setStyleSheet(f"color: #F97316;")
        _set_font(self.lbl_streak_val, size=22, bold=True)
        streak_card_layout.addWidget(self.lbl_streak_val)

        lbl_streak_text = QLabel("correct in a row")
        lbl_streak_text.setStyleSheet(f"color: {c('text_secondary')};")
        _set_font(lbl_streak_text, size=9)
        streak_card_layout.addWidget(lbl_streak_text)
        streak_card_layout.addStretch()

        self.side_layout.addWidget(self.streak_card)

        # ── Divider ──────────────────────────────────────────────────────────
        div2 = QFrame()
        div2.setFixedHeight(1)
        div2.setStyleSheet(f"background-color: {c('border')};")
        self.side_layout.addSpacing(4)
        self.side_layout.addWidget(div2)
        self.side_layout.addSpacing(4)

        # ── FEEDBACK ─────────────────────────────────────────────────────────
        fb_lbl = QLabel("FEEDBACK")
        fb_lbl.setStyleSheet(f"color: {c('text_muted')}; letter-spacing: 1px;")
        _set_font(fb_lbl, size=9, bold=True)
        self.side_layout.addWidget(fb_lbl)
        self.side_layout.addSpacing(2)

        self.fb_box = QFrame()
        self.fb_box.setObjectName("feedbackBox")
        self.fb_box_layout = QVBoxLayout(self.fb_box)
        self.fb_box_layout.setContentsMargins(12, 10, 12, 10)
        self.fb_box_layout.setSpacing(3)

        self.fb_title = QLabel("Ready to Go!")
        self.fb_title.setWordWrap(True)
        _set_font(self.fb_title, size=11, bold=True)
        self.fb_sub = QLabel("Pick a mode and start")
        self.fb_sub.setWordWrap(True)
        _set_font(self.fb_sub, size=9)
        self.fb_box_layout.addWidget(self.fb_title)
        self.fb_box_layout.addWidget(self.fb_sub)

        self.side_layout.addWidget(self.fb_box)

        self.side_layout.addStretch()

    # ── Interactive States ─────────────────────────────────────────────────────

    def go_to_setup(self):
        self.setup_widget.show()
        self.quiz_widget.hide()
        self.mc_quiz_widget.hide()
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

        is_mc = self.mode_multiple_choice.isChecked()

        # Switch Screen to appropriate Quiz Screen
        self.setup_widget.hide()
        self.quiz_widget.setVisible(not is_mc)
        self.mc_quiz_widget.setVisible(is_mc)
        self.results_widget.hide()

        if is_mc:
            self.render_mc_question()
        else:
            self.render_question()

    def render_question(self):
        self.is_answered = False
        correct_letter = self.deck[self.current_idx]

        # Update Progress Counter and Segmented Bar
        _pct = round(((self.current_idx + 1) / self.deck_size) * 100) if self.deck_size else 0
        self.progress_lbl.setText(f"Question {self.current_idx + 1} of {self.deck_size}  ·  {_pct}%")
        self.progress_bar.configure(self.deck_size, self.answers)
        self.progress_bar.set_current(self.current_idx)

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
                    border-radius: 14px;
                    font-size: 18px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    border: 2px solid {c('accent')};
                    background-color: {c('info_bg')};
                    color: {c('welcome_title')};
                }}
                QPushButton:pressed {{
                    background-color: {c('border')};
                }}
            """)

        # Reset action buttons for the new question
        self.fc_btn_reveal.setEnabled(True)
        self.fc_btn_skip.setEnabled(True)
        self.fc_btn_next.setEnabled(False)

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
                        border-radius: 14px;
                        font-size: 18px;
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
                        border-radius: 14px;
                        font-size: 18px;
                        font-weight: bold;
                    }}
                """)
            else:
                # Normal style but disabled
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {c('bg_primary')};
                        color: {c('text_muted')};
                        border: 2px solid {c('border')};
                        border-radius: 14px;
                        font-size: 18px;
                        font-weight: bold;
                    }}
                """)

        # Update scoring
        if is_correct:
            self.streak += 1
            tip = LETTER_METADATA.get(correct_letter, {}).get("tip", "Well done!")
            self.set_feedback("correct", "Correct!", tip)
        else:
            self.streak = 0
            desc = LETTER_METADATA.get(correct_letter, {}).get("tip", "Keep practicing!")
            self.set_feedback("wrong", f"It was {correct_letter}!", desc)

        self.update_scores()

        # Wait for the user to advance manually via the Next button
        self.fc_btn_reveal.setEnabled(False)
        self.fc_btn_skip.setEnabled(False)
        self.fc_btn_next.setEnabled(True)

    def advance_quiz(self):
        self.current_idx += 1
        if self.current_idx >= self.deck_size:
            self.show_results()
        else:
            self.render_question()

    def reveal_fc_answer(self):
        """Reveal the correct letter without answering — counts as missed."""
        if self.is_answered:
            return
        self.is_answered = True

        correct_letter = self.deck[self.current_idx]
        self.answers[self.current_idx] = False  # counts as missed
        self.streak = 0
        self.progress_bar.configure(self.deck_size, self.answers)

        # Highlight the correct choice green, dim the rest
        for btn in self.choice_buttons:
            btn.setEnabled(False)
            if btn.text() == correct_letter:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {c('success_bg')};
                        color: {c('success')};
                        border: 2px solid {c('success')};
                        border-radius: 14px;
                        font-size: 18px;
                        font-weight: bold;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {c('bg_primary')};
                        color: {c('text_muted')};
                        border: 2px solid {c('border')};
                        border-radius: 14px;
                        font-size: 18px;
                        font-weight: bold;
                    }}
                """)

        self.fc_btn_reveal.setEnabled(False)
        self.fc_btn_skip.setEnabled(False)
        self.fc_btn_next.setEnabled(True)

        desc = LETTER_METADATA.get(correct_letter, {}).get("tip", "Keep practicing!")
        self.set_feedback("wrong", f"Answer: {correct_letter}", desc)
        self.update_scores()

    def skip_fc_question(self):
        """Skip the current question — counts as missed and moves straight on."""
        if self.is_answered:
            return
        self.is_answered = True

        self.answers[self.current_idx] = False  # counts as missed
        self.streak = 0
        self.progress_bar.configure(self.deck_size, self.answers)

        self.fc_btn_reveal.setEnabled(False)
        self.fc_btn_skip.setEnabled(False)

        self.update_scores()
        self.advance_quiz()

    def next_fc_question(self):
        """Manually advance to the next question (enabled after answering/revealing)."""
        if not self.is_answered:
            return
        self.advance_quiz()

    # ── Multiple Choice Mode Methods ─────────────────────────────────────────

    def render_mc_question(self):
        """Render the current question in Multiple Choice mode."""
        self.is_answered = False
        correct_letter = self.deck[self.current_idx]

        # Update progress
        _pct = round(((self.current_idx + 1) / self.deck_size) * 100) if self.deck_size else 0
        self.mc_progress_lbl.setText(f"Question {self.current_idx + 1} of {self.deck_size}  ·  {_pct}%")
        self.mc_progress_bar.configure(self.deck_size, self.answers)
        self.mc_progress_bar.set_current(self.current_idx)

        # Set question text
        self.mc_question_lbl.setText(f"Which gesture is letter {correct_letter}?")

        # Build 4 options: 1 correct + 3 incorrect
        other_letters = [ch for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if ch != correct_letter]
        incorrect = random.sample(other_letters, 3)
        options = [correct_letter] + incorrect
        random.shuffle(options)

        # Load images into cards
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) 
        for i, card in enumerate(self.mc_cards):
            letter = options[i]
            img_path = os.path.normpath(
                os.path.join(project_root, "assets", "reference", f"Sign_Language_{letter}.jpg")
            )
            card.set_image(letter, img_path)
            card.set_interactive(True)
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {c('bg_primary')};
                    border: 2px solid {c('border')};
                    border-radius: 12px;
                }}
            """)

        # Enable action buttons
        self.mc_btn_reveal.setEnabled(True)
        self.mc_btn_skip.setEnabled(True)
        self.mc_btn_next.setEnabled(False)

        self.set_feedback("neutral", "Your Turn!", f"Which gesture represents the letter {correct_letter}?")

    def on_mc_card_selected(self, selected_card):
        """Handle a gesture card selection in Multiple Choice mode."""
        if self.is_answered:
            return
        self.is_answered = True

        correct_letter = self.deck[self.current_idx]
        picked_letter = selected_card.letter
        is_correct = (picked_letter == correct_letter)

        self.answers[self.current_idx] = is_correct

        # Update segmented progress bar
        self.mc_progress_bar.configure(self.deck_size, self.answers)

        # Log to practice history
        if self.set_random.isChecked():
            set_label = "Random 10"
        elif self.set_all.isChecked():
            set_label = "Full Alphabet"
        else:
            set_label = "Shuffle All"
        log_quiz_result(
            username=self._username,
            source="multiple_choice_quiz",
            letter=correct_letter,
            result="correct" if is_correct else "missed",
            confidence=None,
            set_name=f"Multiple Choice Quiz — {set_label}",
        )

        # Disable all cards and highlight correct/incorrect
        for card in self.mc_cards:
            card.set_interactive(False)
            if card.letter == correct_letter:
                card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {c('success_bg')};
                        border: 3px solid {c('success')};
                        border-radius: 12px;
                    }}
                """)
            elif card is selected_card and not is_correct:
                card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {c('error_bg')};
                        border: 3px solid {c('error')};
                        border-radius: 12px;
                    }}
                """)
            else:
                card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {c('bg_primary')};
                        border: 2px solid {c('border')};
                        border-radius: 12px;
                    }}
                """)

        # Disable Reveal / Skip buttons; enable Next for manual advance
        self.mc_btn_reveal.setEnabled(False)
        self.mc_btn_skip.setEnabled(False)
        self.mc_btn_next.setEnabled(True)

        # Update scoring and feedback
        if is_correct:
            self.streak += 1
            tip = LETTER_METADATA.get(correct_letter, {}).get("tip", "Well done!")
            self.set_feedback("correct", "✓ Correct!", tip)
        else:
            self.streak = 0
            desc = LETTER_METADATA.get(correct_letter, {}).get("tip", "Keep practicing!")
            self.set_feedback("wrong", f"✗ Incorrect — Answer: {correct_letter}", desc)

        self.update_scores()

    def next_mc_question(self):
        """Manually advance to the next question (enabled after answering/revealing)."""
        if not self.is_answered:
            return
        self.advance_mc_quiz()

    def advance_mc_quiz(self):
        """Advance to next question or show results in MC mode."""
        self.current_idx += 1
        if self.current_idx >= self.deck_size:
            self.show_results()
        else:
            self.render_mc_question()

    def reveal_mc_answer(self):
        """Reveal the correct card without selecting — counts as missed."""
        if self.is_answered:
            return
        self.is_answered = True

        correct_letter = self.deck[self.current_idx]
        self.answers[self.current_idx] = False  # counts as missed
        self.streak = 0

        # Update progress bar
        self.mc_progress_bar.configure(self.deck_size, self.answers)

        # Highlight correct card green, dim others
        for card in self.mc_cards:
            card.set_interactive(False)
            if card.letter == correct_letter:
                card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {c('success_bg')};
                        border: 3px solid {c('success')};
                        border-radius: 12px;
                    }}
                """)
            else:
                card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {c('bg_primary')};
                        border: 2px solid {c('border')};
                        border-radius: 12px;
                    }}
                """)

        self.mc_btn_reveal.setEnabled(False)
        self.mc_btn_skip.setEnabled(False)
        self.mc_btn_next.setEnabled(True)

        desc = LETTER_METADATA.get(correct_letter, {}).get("tip", "Keep practicing!")
        self.set_feedback("wrong", f"Answer: {correct_letter}", desc)
        self.update_scores()

    def skip_mc_question(self):
        """Skip the current question — counts as missed."""
        if self.is_answered:
            return
        self.is_answered = True

        correct_letter = self.deck[self.current_idx]
        self.answers[self.current_idx] = False  # counts as missed
        self.streak = 0

        # Update progress bar
        self.mc_progress_bar.configure(self.deck_size, self.answers)

        self.mc_btn_reveal.setEnabled(False)
        self.mc_btn_skip.setEnabled(False)

        self.update_scores()

        # Skip moves straight on to the next question
        self.advance_mc_quiz()

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

        # Style box according to answer outcome (scoped selector so the
        # border never cascades onto the inner QLabels)
        if kind == "correct":
            self.fb_box.setStyleSheet(f"""
                QFrame#feedbackBox {{
                    background-color: {c('success_bg')};
                    border: 1px solid {c('success')};
                    border-radius: 8px;
                }}
                QFrame#feedbackBox QLabel {{ background: transparent; border: none; }}
            """)
            self.fb_title.setStyleSheet(f"color: {c('success')}; background: transparent; border: none;")
            self.fb_sub.setStyleSheet(f"color: {c('success')}; background: transparent; border: none;")
        elif kind == "wrong":
            self.fb_box.setStyleSheet(f"""
                QFrame#feedbackBox {{
                    background-color: {c('error_bg')};
                    border: 1px solid {c('error')};
                    border-radius: 8px;
                }}
                QFrame#feedbackBox QLabel {{ background: transparent; border: none; }}
            """)
            self.fb_title.setStyleSheet(f"color: {c('error')}; background: transparent; border: none;")
            self.fb_sub.setStyleSheet(f"color: {c('error')}; background: transparent; border: none;")
        else:
            # Neutral / Ready states
            self.fb_box.setStyleSheet(f"""
                QFrame#feedbackBox {{
                    background-color: {c('input_bg')};
                    border: 1px solid {c('border')};
                    border-radius: 8px;
                }}
                QFrame#feedbackBox QLabel {{ background: transparent; border: none; }}
            """)
            self.fb_title.setStyleSheet(f"color: {c('text_primary')}; background: transparent; border: none;")
            self.fb_sub.setStyleSheet(f"color: {c('text_secondary')}; background: transparent; border: none;")

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
        self.mc_quiz_widget.hide()
        self.results_widget.show()

        # Update tracker final state
        self.progress_lbl.setText("Session Complete")
        self.progress_bar.configure(self.deck_size, self.answers)
        self.progress_bar.set_current(self.deck_size)  # past last index — no active pulse

    def retry_quiz(self):
        self.start_quiz()

    def _themed_question(self, title: str, text: str) -> bool:
        """Yes/No confirmation dialog with guaranteed-readable (themed) text."""
        from PyQt6.QtWidgets import QMessageBox
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(text)
        box.setIcon(QMessageBox.Icon.Question)
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        box.setStyleSheet(f"""
            QMessageBox {{ background-color: {c('bg_primary')}; }}
            QMessageBox QLabel {{ color: {c('text_primary')}; background: transparent; }}
            QMessageBox QPushButton {{
                color: {c('text_primary')};
                background-color: {c('input_bg')};
                border: 1px solid {c('input_border')};
                border-radius: 6px;
                padding: 5px 18px;
                min-width: 64px;
                font-weight: bold;
            }}
            QMessageBox QPushButton:hover {{
                background-color: {c('border')};
                border-color: {c('accent')};
            }}
        """)
        return box.exec() == QMessageBox.StandardButton.Yes

    def stop_quizzing(self):
        if self._themed_question("Stop Quiz", "Are you sure you want to stop the quiz session?"):
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
        if self._themed_question("Logout", "Are you sure you want to log out?"):
            self._app.show_login()

    def _on_theme_changed(self, is_dark: bool):
        self._update_styles()

    def _style_action_btn(self, btn, kind: str):
        """Apply a themed, animated palette to an AnimatedButton (re-run on theme change)."""
        transparent = QColor(0, 0, 0, 0)
        if kind == "success":
            idle = QColor(c('success'))
            btn.configure(idle, idle.darker(118), QColor("#FFFFFF"), QColor("#FFFFFF"),
                          radius=20, font_size=13)
        elif kind == "accent":
            btn.configure(QColor(c('accent')), QColor(c('accent_hover')),
                          QColor("#FFFFFF"), QColor("#FFFFFF"), radius=20, font_size=13)
        elif kind == "outline":
            btn.configure(transparent, QColor(c('input_bg')),
                          QColor(c('text_primary')), QColor(c('accent')),
                          border_col=QColor(c('input_border')), border_w=1,
                          radius=20, font_size=13)
        elif kind == "danger":
            btn.configure(transparent, QColor(c('error_bg')),
                          QColor(c('error')), QColor(c('error')),
                          border_col=QColor(c('error')), border_w=1,
                          radius=18, font_size=12)

    def _update_styles(self):
        # ── Page background ──────────────────────────────────────────────────
        self.setStyleSheet(f"QWidget#flashcardQuizPage {{ background-color: {c('bg_primary')}; }}")

        # ── Header card ──────────────────────────────────────────────────────
        self.title_lbl.setStyleSheet(
            f"color: {c('welcome_title')}; font-family: 'Segoe UI'; font-size: 24px; font-weight: bold;"
        )
        if hasattr(self, 'subtitle_lbl'):
            self.subtitle_lbl.setStyleSheet(f"color: {c('text_secondary')}; background: transparent; border: none;")

        for welcome_card in self.findChildren(QFrame, "welcomeCard"):
            welcome_card.setStyleSheet(f"""
                QFrame#welcomeCard {{
                    background-color: {c('info_bg')};
                    border: 1px solid {c('welcome_border')};
                    border-radius: 14px;
                }}
                QFrame#welcomeCard QLabel {{ background: transparent; border: none; }}
            """)

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

        # ── Main card + side panel (soft elevation) ──────────────────────────
        self.main_card.setStyleSheet(f"""
            QFrame#quizMainCard {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 16px;
            }}
            QFrame#quizMainCard QLabel {{ background: transparent; border: none; }}
        """)
        _add_shadow(self.main_card, blur=18, opacity=22, offset_y=4)

        self.side_panel.setStyleSheet(f"""
            QFrame#quizSidePanel {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('border')};
                border-radius: 16px;
            }}
            QFrame#quizSidePanel QLabel {{ background: transparent; border: none; }}
        """)
        _add_shadow(self.side_panel, blur=18, opacity=22, offset_y=4)

        # ── Setup screen ─────────────────────────────────────────────────────
        setup_title = self.setup_widget.findChild(QLabel, "setupTitle")
        if setup_title:
            setup_title.setStyleSheet(f"color: {c('text_primary')};")
        setup_sub = self.setup_widget.findChild(QLabel, "setupSub")
        if setup_sub:
            setup_sub.setStyleSheet(f"color: {c('text_secondary')};")

        radio_style = f"""
            QRadioButton {{
                color: {c('text_primary')};
                spacing: 12px;
                font-size: 14px;
                padding: 7px 4px;
                background: transparent;
            }}
            QRadioButton::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 10px;
                border: 2px solid {c('input_border')};
                background-color: {c('bg_primary')};
            }}
            QRadioButton::indicator:hover {{
                border-color: {c('accent')};
            }}
            QRadioButton::indicator:checked {{
                border: 6px solid {c('accent')};
                background-color: {c('bg_primary')};
            }}
            QRadioButton:checked {{
                color: {c('welcome_title')};
                font-weight: bold;
            }}
        """
        for r_btn in [self.mode_flashcard, self.mode_multiple_choice, self.mode_camera,
                      self.set_random, self.set_all, self.set_shuffle]:
            r_btn.setStyleSheet(radio_style)

        for container in self.setup_widget.findChildren(QFrame, "settingsContainer"):
            container.setStyleSheet(f"""
                QFrame#settingsContainer {{
                    background-color: {c('input_bg')};
                    border: 1px solid {c('border')};
                    border-radius: 12px;
                }}
            """)

        for label_name in ["modeLabel", "setLabel"]:
            lbl = self.setup_widget.findChild(QLabel, label_name)
            if lbl:
                lbl.setStyleSheet(f"color: {c('text_muted')}; letter-spacing: 1px;")

        # ── Button system ────────────────────────────────────────────────────
        def primary_btn(color, hover, radius=12, fs=14):
            return f"""
                QPushButton {{
                    background-color: {color};
                    color: #FFFFFF;
                    border: none;
                    border-radius: {radius}px;
                    font-size: {fs}px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ background-color: {hover}; }}
                QPushButton:pressed {{ background-color: {hover}; padding-top: 1px; }}
                QPushButton:disabled {{ background-color: {c('border')}; color: {c('text_muted')}; }}
            """

        def outline_btn(radius=12, fs=12):
            return f"""
                QPushButton {{
                    background-color: transparent;
                    color: {c('text_primary')};
                    border: 1px solid {c('input_border')};
                    border-radius: {radius}px;
                    font-size: {fs}px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ background-color: {c('input_bg')}; border-color: {c('accent')}; }}
                QPushButton:pressed {{ background-color: {c('border')}; }}
            """

        def danger_btn(radius=12, fs=12):
            return f"""
                QPushButton {{
                    background-color: transparent;
                    color: {c('error')};
                    border: 1px solid {c('error')};
                    border-radius: {radius}px;
                    font-size: {fs}px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ background-color: {c('error_bg')}; }}
                QPushButton:pressed {{ background-color: {c('error_bg')}; padding-top: 1px; }}
            """

        self.btn_start.setStyleSheet(primary_btn(c('accent'), c('accent_hover'), radius=14, fs=15))

        # ── Quiz (flashcard) header ──────────────────────────────────────────
        self.quiz_mode_lbl.setStyleSheet(f"color: {c('text_primary')};")
        self.progress_pill.setStyleSheet(f"""
            QFrame#progressPill {{
                background-color: {c('info_bg')};
                border: 1px solid {c('welcome_border')};
                border-radius: 13px;
            }}
        """)
        self.progress_lbl.setStyleSheet(f"color: {c('welcome_title')}; background: transparent; border: none;")
        self.progress_bar.update()

        self.img_card.setStyleSheet(f"""
            QFrame#imgCard {{
                background-color: {c('input_bg')};
                border: 2px solid {c('border')};
                border-radius: 16px;
            }}
        """)

        # ── Results screen ───────────────────────────────────────────────────
        self.results_title.setStyleSheet(f"color: {c('text_primary')};")
        self.results_summary.setStyleSheet(f"color: {c('text_secondary')};")

        stat_box_style = f"""
            QFrame {{
                background-color: {c('input_bg')};
                border: 1px solid {c('border')};
                border-radius: 10px;
            }}
            QLabel {{ background: transparent; border: none; }}
        """
        self.stat_box_correct.setStyleSheet(stat_box_style)
        self.stat_correct_val.setStyleSheet(f"color: {c('success')};")
        self.stat_box_missed.setStyleSheet(stat_box_style)
        self.stat_missed_val.setStyleSheet(f"color: {c('error')};")

        self.btn_retry.setStyleSheet(primary_btn(c('accent'), c('accent_hover'), radius=12, fs=12))
        self.btn_dashboard.setStyleSheet(outline_btn(radius=12, fs=12))

        if hasattr(self, 'btn_stop_quizzing') and self.btn_stop_quizzing:
            self._style_action_btn(self.btn_stop_quizzing, "danger")
        if hasattr(self, 'fc_btn_reveal'):
            self._style_action_btn(self.fc_btn_reveal, "success")
        if hasattr(self, 'fc_btn_skip'):
            self._style_action_btn(self.fc_btn_skip, "outline")
        if hasattr(self, 'fc_btn_next'):
            self._style_action_btn(self.fc_btn_next, "accent")

        # ── Multiple Choice mode ─────────────────────────────────────────────
        if hasattr(self, 'mc_btn_stop') and self.mc_btn_stop:
            self._style_action_btn(self.mc_btn_stop, "danger")
        if hasattr(self, 'mc_btn_reveal'):
            self._style_action_btn(self.mc_btn_reveal, "success")
        if hasattr(self, 'mc_btn_skip'):
            self._style_action_btn(self.mc_btn_skip, "outline")
        if hasattr(self, 'mc_btn_next'):
            self._style_action_btn(self.mc_btn_next, "accent")
        if hasattr(self, 'mc_mode_lbl'):
            self.mc_mode_lbl.setStyleSheet(f"color: {c('text_primary')};")
        if hasattr(self, 'mc_progress_pill'):
            self.mc_progress_pill.setStyleSheet(f"""
                QFrame#mcProgressPill {{
                    background-color: {c('info_bg')};
                    border: 1px solid {c('welcome_border')};
                    border-radius: 13px;
                }}
            """)
        if hasattr(self, 'mc_progress_lbl'):
            self.mc_progress_lbl.setStyleSheet(
                f"color: {c('welcome_title')}; background: transparent; border: none;"
            )
        if hasattr(self, 'mc_progress_bar'):
            self.mc_progress_bar.update()
        if hasattr(self, 'mc_question_lbl'):
            self.mc_question_lbl.setStyleSheet(f"""
                color: {c('welcome_title')};
                background-color: {c('info_bg')};
                border: 1px solid {c('welcome_border')};
                border-radius: 12px;
                padding: 8px 16px;
            """)

        # ── Side panel: metric cards (uniform pure-white surface) ────────────
        metric_card_style = f"""
            QFrame {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('input_border')};
                border-radius: 12px;
            }}
            QLabel {{ background: transparent; border: none; }}
        """
        # All session-score cards share the same neutral surface as the
        # Current Streak card (uniform, no green/red tint on the background).
        self.side_correct_card.setStyleSheet(metric_card_style)
        self.side_missed_card.setStyleSheet(metric_card_style)
        self.side_accuracy_card.setStyleSheet(metric_card_style)

        self.lbl_side_correct.setStyleSheet(f"color: {c('success')};")
        self.lbl_side_missed.setStyleSheet(f"color: {c('error')};")
        self.lbl_side_acc.setStyleSheet(f"color: {c('text_primary')};")

        self.lbl_correct_label.setStyleSheet(f"color: {c('text_secondary')};")
        self.lbl_missed_label.setStyleSheet(f"color: {c('text_secondary')};")

        self.streak_card.setStyleSheet(f"""
            QFrame#streakCard {{
                background-color: {c('bg_primary')};
                border: 1px solid {c('input_border')};
                border-radius: 12px;
            }}
            QLabel {{ background: transparent; border: none; }}
        """)

        # Refresh repaint for circular ring
        self.results_ring.update()