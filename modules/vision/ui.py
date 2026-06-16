from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout, QComboBox, QDialog, QMessageBox, QScrollArea, QStackedWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QCursor, QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from core.theme import c
from theme.typography import SIZE_XS, SIZE_SM, SIZE_MD, SIZE_LG
from components.base_page import BasePage
from components.layout.sidebar import Sidebar
from components.cards.base_card import BaseCard
from components.cards.stat_card import StatCard
from components.camera.camera_feed_widget import CameraFeedWidget
from components.camera.landmark_overlay import LandmarkOverlay
from components.camera.fps_badge import FPSBadge
from components.camera.detection_status_widget import DetectionStatusWidget
from components.indicators.progress_bar import ProgressBar
from modules.vision.viewmodel import CameraPracticeViewModel

class CameraPracticePage(BasePage):
    """
    Camera Practice UI
    Matches the signdesk_camera_practice_ui mockup perfectly.
    """
    def __init__(self, parent=None, app=None, username: str = "", target_letter: str = None):
        super().__init__(parent, app, username)
        
        self.viewmodel = CameraPracticeViewModel(username=username)
        
        try:
            from core.theme import ThemeSignal
            ThemeSignal.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass
        
        self.network_manager = QNetworkAccessManager(self)
        self.network_manager.finished.connect(self._on_image_downloaded)
        
        self.gesture_sets = {
            "Set 1 (A-E)": ["A", "B", "C", "D", "E"],
            "Set 2 (F-J)": ["F", "G", "H", "I", "J"],
            "Set 3 (K-O)": ["K", "L", "M", "N", "O"],
            "Set 4 (P-T)": ["P", "Q", "R", "S", "T"],
            "Set 5 (U-Z)": ["U", "V", "W", "X", "Y", "Z"],
            "Vowels": ["A", "E", "I", "O", "U"],
            "All Letters": list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        }
        
        self._build_ui()
        self._bind_viewmodel()
        
        # Pre-select set containing target_letter if provided
        if target_letter:
            target_letter_upper = target_letter.upper().strip()
            found_set = False
            for set_name, letters in self.gesture_sets.items():
                if set_name != "All Letters" and target_letter_upper in letters:
                    self.set_selector.setCurrentText(set_name)
                    found_set = True
                    break
            
            # Explicitly practice the single target letter initially
            self.viewmodel.set_target_letters([target_letter_upper])
        else:
            self._on_set_changed()
        
    def activate(self):
        super().activate()
        # Reset the page to a clean initial state every time user enters
        self._reset_ui_to_initial_state()
        
    def deactivate(self):
        super().deactivate()
        # Stop camera, timer, and all detection
        self.viewmodel.stop()
        
        # Process any pending Qt events/signals from the pipeline to prevent
        # queued frame_ready / status_updated signals from firing after we hide
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        # Clear the camera feed display
        if hasattr(self, 'camera_feed'):
            self.camera_feed.clear()
        
        # Reset the UI back to initial state
        self._reset_ui_to_initial_state()
    
    def _reset_ui_to_initial_state(self):
        """Reset all UI elements to their initial/idle state."""
        # Reset score display
        if hasattr(self, 'stat_correct'):
            self.stat_correct.set_value("0")
        if hasattr(self, 'stat_missed'):
            self.stat_missed.set_value("0")
        if hasattr(self, 'stat_acc'):
            self.stat_acc.set_value("0%")
        if hasattr(self, 'score_pill'):
            self.score_pill.setText("0 correct")
        
        # Reset confidence indicators
        if hasattr(self, 'status_widget'):
            self.status_widget.status_pill.set_state("idle", "Ready")
            self.status_widget.current_conf.set_value(0)
            self.status_widget.hold_conf.set_value(0)
        
        # Reset progress
        if hasattr(self, 'prog_lbl'):
            self.prog_lbl.setText("Letter 1 of 5")
        if hasattr(self, 'prog_bar'):
            self.prog_bar.setValue(0)
        
        # Reset feedback box
        if hasattr(self, 'fb_title'):
            self.fb_title.setText("Ready")
        if hasattr(self, 'fb_sub'):
            self.fb_sub.setText("Press start")
            self.fb_sub.setStyleSheet(f"color: {c('success')}; font-size: 10px;")
        if hasattr(self, 'fb_icon'):
            self.fb_icon.setText("✓")
            self.fb_icon.setStyleSheet(f"background-color: {c('success')}; color: #FFFFFF; border-radius: 12px; font-weight: bold;")
        if hasattr(self, 'fb_box'):
            self.fb_box.show()
        
        # Reset FPS badge
        if hasattr(self, 'fps_badge'):
            self.fps_badge.set_fps(0)
        
        # Reset landmark overlay
        if hasattr(self, 'landmark_overlay'):
            self.landmark_overlay.set_detected(False)
        
        # Ensure live feed panel is visible (not the placeholder)
        if hasattr(self, 'feed_stack'):
            self.feed_stack.setCurrentIndex(0)
        
    def _on_set_changed(self):
        if not hasattr(self, 'set_selector'):
            return
        current_set_name = self.set_selector.currentText()
        letters = self.gesture_sets.get(current_set_name, ["A", "B", "C", "D", "E"])
        self.viewmodel.set_target_letters(letters, set_name=current_set_name)
        
    def _build_ui(self):
        # Lay out directly in main vertical layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.layout = main_layout
        
        self._build_topbar()
        self._build_content()

    def _on_navigation_requested(self, key: str):
        if key == "dashboard":
            self.app.show_dashboard(self.username)
        elif key == "camera":
            pass # Already here
        elif key == "flashcards":
            self.app.show_flashcard_quiz(self.username)
        elif key == "reference":
            self.app.show_reference_chart(self.username)
        elif key == "settings":
            self.app.show_settings(self.username)
        elif key == "history":
            self.app.show_gesture_history(self.username)

    def _on_logout(self):
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Logout", "Are you sure you want to log out?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.app.show_login()
        
    def _build_topbar(self):
        self.topbar = QWidget()
        self.topbar.setStyleSheet("background: transparent; border: none;")
        
        layout = QHBoxLayout(self.topbar)
        layout.setContentsMargins(28, 16, 28, 8)
        layout.setSpacing(24)
        
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
        card_layout.setContentsMargins(24, 18, 24, 18)

        self.topbar_title = QLabel("Camera Practice")
        self.topbar_title.setStyleSheet(f"color: {c('welcome_title')}; font-family: 'Segoe UI'; font-size: 26px; font-weight: bold;")
        
        card_layout.addWidget(self.topbar_title, 0, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(card, stretch=1)
        
        self.set_selector = QComboBox()
        self.set_selector.setStyleSheet(f"""
            QComboBox {{
                background-color: {c('input_bg')};
                color: {c('text_primary')};
                border: 1px solid {c('border')};
                border-radius: 6px;
                padding: 4px 24px 4px 10px;
                margin-left: 10px;
                font-size: {SIZE_MD}px;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {c('bg_primary')};
                color: {c('text_primary')};
                border: 1px solid {c('border')};
                selection-background-color: {c('accent')};
                selection-color: #FFFFFF;
                outline: none;
            }}
        """)
        self.set_selector.addItems(list(self.gesture_sets.keys()))
        self.set_selector.currentIndexChanged.connect(self._on_set_changed)
        layout.addWidget(self.set_selector)

        # Audio prompts toggle button (target letter announcements)
        from core.config import config as _cfg
        _audio_on = _cfg.get("accessibility.audio_prompts", True)
        self.btn_audio = QPushButton("Audio On" if _audio_on else "Audio Off")
        self.btn_audio.setCheckable(True)
        self.btn_audio.setChecked(_audio_on)
        self.btn_audio.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_audio.setFixedHeight(28)
        self.btn_audio.setStyleSheet(self._audio_btn_style(_audio_on))
        self.btn_audio.toggled.connect(self._on_audio_toggled)
        layout.addWidget(self.btn_audio)

        # Speak Output toggle button (sentence TTS)
        _tts_on = _cfg.get("speech.tts_enabled", True)
        self.btn_speak = QPushButton("Speak On" if _tts_on else "Speak Off")
        self.btn_speak.setCheckable(True)
        self.btn_speak.setChecked(_tts_on)
        self.btn_speak.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_speak.setFixedHeight(28)
        self.btn_speak.setStyleSheet(self._audio_btn_style(_tts_on))
        self.btn_speak.toggled.connect(self._on_speak_toggled)
        layout.addWidget(self.btn_speak)
        
        layout.addStretch()
        
        # Session Badge (Progress + Score)
        session_badge = QWidget()
        sb_layout = QHBoxLayout(session_badge)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(12)
        
        # Progress Wrap
        prog_wrap = QWidget()
        pw_layout = QHBoxLayout(prog_wrap)
        pw_layout.setContentsMargins(0, 0, 0, 0)
        pw_layout.setSpacing(8)
        
        self.prog_lbl = QLabel("Letter 1 of 5")
        self.prog_lbl.setStyleSheet(f"color: {c('text_secondary')}; font-size: {SIZE_MD}px; border: none;")
        
        self.prog_bar = ProgressBar()
        self.prog_bar.setFixedWidth(120)
        
        pw_layout.addWidget(self.prog_lbl)
        pw_layout.addWidget(self.prog_bar)
        
        # Score Pill
        self.score_pill = QLabel("0 correct")
        self.score_pill.setStyleSheet(f"""
            background-color: {c('score_pill_bg')};
            border: 1px solid {c('score_pill_border')};
            color: {c('score_pill_text')};
            font-size: {SIZE_MD}px;
            font-weight: bold;
            padding: 4px 10px;
            border-radius: 14px;
        """)
        
        # Stop Practice Button
        self.btn_stop_practice = QPushButton("Stop Practice")
        self.btn_stop_practice.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_stop_practice.setFixedSize(110, 28)
        self.btn_stop_practice.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {c('error')};
                border: 1px solid {c('error')};
                border-radius: 14px;
                font-size: {SIZE_SM}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {c('error_bg')};
            }}
        """)
        self.btn_stop_practice.clicked.connect(self.stop_practice)

        sb_layout.addWidget(prog_wrap)
        sb_layout.addWidget(self.score_pill)
        sb_layout.addWidget(self.btn_stop_practice)
        
        layout.addWidget(session_badge)
        self.layout.addWidget(self.topbar)

    def _build_content(self):
        content = QWidget()
        c_layout = QHBoxLayout(content)
        c_layout.setContentsMargins(16, 16, 16, 16)
        c_layout.setSpacing(14)
        
        self._build_left_panel(c_layout)
        self._build_center_panel(c_layout)
        self._build_right_panel(c_layout)
        
        self.layout.addWidget(content, stretch=1)
        
    def _build_left_panel(self, parent_layout):
        card = BaseCard()
        card.setFixedWidth(220)
        
        self.left_panel_hdr = QLabel("TARGET LETTER")
        self.left_panel_hdr.setStyleSheet(f"color: {c('text_secondary')}; font-size: {SIZE_XS}px; font-weight: bold; letter-spacing: 0.8px; margin-bottom: 10px;")
        
        self.target_letter_lbl = QLabel("A")
        self.target_letter_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.target_letter_lbl.setStyleSheet(f"color: {c('text_primary')}; font-size: 72px; font-weight: bold;")
        
        self.asl_box = QWidget()
        self.asl_box.setFixedSize(130, 130)
        self.asl_box.setStyleSheet(f"""
            background-color: {c('card_bg_secondary')};
            border: 1.5px dashed {c('text_muted')};
            border-radius: 10px;
        """)
        asl_layout = QVBoxLayout(self.asl_box)
        asl_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.asl_image_lbl = QLabel("ASL reference\nimage")
        self.asl_image_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.asl_image_lbl.setStyleSheet(f"color: {c('text_muted')}; font-size: {SIZE_XS}px;")
        asl_layout.addWidget(self.asl_image_lbl)
        
        # Center the asl box
        box_wrap = QWidget()
        bw_layout = QHBoxLayout(box_wrap)
        bw_layout.setContentsMargins(0,0,0,0)
        bw_layout.addWidget(self.asl_box, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.target_hint = QLabel("Form the letter A in front of the camera and hold it steady")
        self.target_hint.setWordWrap(True)
        self.target_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.target_hint.setStyleSheet(f"color: {c('text_secondary')}; font-size: {SIZE_MD}px; margin-top: 10px; line-height: 1.4;")
        
        card.layout.addWidget(self.left_panel_hdr)
        card.layout.addWidget(self.target_letter_lbl)
        card.layout.addWidget(box_wrap)
        card.layout.addWidget(self.target_hint)
        card.layout.addStretch()
        
        parent_layout.addWidget(card)
        
    def _build_center_panel(self, parent_layout):
        card = BaseCard()
        
        # Header
        hdr = QWidget()
        hdr_layout = QHBoxLayout(hdr)
        hdr_layout.setContentsMargins(0, 0, 0, 10)
        
        self.center_panel_hdr = QLabel("LIVE DETECTION")
        self.center_panel_hdr.setStyleSheet(f"color: {c('text_secondary')}; font-size: {SIZE_XS}px; font-weight: bold; letter-spacing: 0.8px;")
        
        self.fps_badge = FPSBadge()
        
        hdr_layout.addWidget(self.center_panel_hdr)
        hdr_layout.addStretch()
        hdr_layout.addWidget(self.fps_badge)
        
        # Feed / Placeholder stack
        self.feed_stack = QStackedWidget()

        # ── Page 0: live camera feed ──────────────────────────
        feed_wrap = QWidget()
        feed_layout = QVBoxLayout(feed_wrap)
        feed_layout.setContentsMargins(0, 0, 0, 0)

        self.camera_feed = CameraFeedWidget()
        self.landmark_overlay = LandmarkOverlay(self.camera_feed)

        feed_layout.addWidget(self.camera_feed)

        # ── Page 1: webcam-disabled placeholder ───────────────
        placeholder = self._build_webcam_placeholder()

        self.feed_stack.addWidget(feed_wrap)    # index 0 — live feed
        self.feed_stack.addWidget(placeholder)  # index 1 — unavailable card
        self.feed_stack.setCurrentIndex(0)
        
        # Footer
        ftr = QWidget()
        ftr_layout = QHBoxLayout(ftr)
        ftr_layout.setContentsMargins(0, 10, 0, 0)
        ftr_layout.setSpacing(8)
        
        self.btn_start = QPushButton("Start")
        self.btn_start.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_start.setStyleSheet(f"""
            QPushButton {{
                background-color: {c('success')}; color: #FFFFFF;
                border: 1px solid transparent;
                border-radius: 8px; font-size: {SIZE_MD}px; font-weight: bold; padding: 7px 16px;
            }}
            QPushButton:hover {{
                background-color: {c('success_bg')}; color: {c('success')};
                border-color: {c('success')};
            }}
        """)
        self.btn_start.clicked.connect(self.viewmodel.start)
        
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_stop.setStyleSheet(f"""
            QPushButton {{
                background-color: {c('error_bg')}; color: {c('error')};
                border: 1px solid transparent;
                border-radius: 8px; font-size: {SIZE_MD}px; font-weight: bold; padding: 7px 16px;
            }}
            QPushButton:hover {{
                background-color: {c('error')}; color: #FFFFFF;
            }}
        """)
        self.btn_stop.clicked.connect(self.viewmodel.stop)

        self.btn_skip = QPushButton("Skip")
        self.btn_skip.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_skip.setStyleSheet(f"""
            QPushButton {{
                background-color: {c('badge_gray_bg')}; color: {c('text_primary')};
                border: 1px solid {c('border')};
                border-radius: 8px; font-size: {SIZE_MD}px; font-weight: bold; padding: 7px 16px;
            }}
            QPushButton:hover {{
                background-color: {c('input_bg')};
                border-color: {c('text_secondary')};
            }}
        """)
        self.btn_skip.clicked.connect(self.viewmodel.skip_letter)
        
        ftr_layout.addWidget(self.btn_start, 1)
        ftr_layout.addWidget(self.btn_stop, 1)
        ftr_layout.addWidget(self.btn_skip, 1)
        
        card.layout.addWidget(hdr)
        card.layout.addWidget(self.feed_stack, 1)
        card.layout.addWidget(ftr)
        
        parent_layout.addWidget(card, stretch=1)
        
    def _build_right_panel(self, parent_layout):
        card = BaseCard()
        card.setFixedWidth(200)
        
        self.status_widget = DetectionStatusWidget()
        card.layout.addWidget(self.status_widget)
        
        # Session Score Grid
        self.right_panel_score_hdr = QLabel("SESSION SCORE")
        self.right_panel_score_hdr.setStyleSheet(f"color: {c('text_secondary')}; font-size: {SIZE_XS}px; font-weight: bold; letter-spacing: 0.8px; margin-top: 14px;")
        card.layout.addWidget(self.right_panel_score_hdr)
        
        grid_wrap = QWidget()
        grid = QGridLayout(grid_wrap)
        grid.setContentsMargins(0, 8, 0, 0)
        grid.setSpacing(6)
        
        self.stat_correct = StatCard("Correct", "0")
        self.stat_missed = StatCard("Missed", "0")
        self.stat_acc = StatCard("Accuracy", "0%")
        
        grid.addWidget(self.stat_correct, 0, 0)
        grid.addWidget(self.stat_missed, 0, 1)
        grid.addWidget(self.stat_acc, 1, 0, 1, 2)
        
        card.layout.addWidget(grid_wrap)
        
        # Feedback
        self.right_panel_fb_hdr = QLabel("FEEDBACK")
        self.right_panel_fb_hdr.setStyleSheet(f"color: {c('text_secondary')}; font-size: {SIZE_XS}px; font-weight: bold; letter-spacing: 0.8px; margin-top: 14px;")
        card.layout.addWidget(self.right_panel_fb_hdr)
        
        self.fb_box = QWidget()
        self.fb_box.setStyleSheet(f"background-color: {c('score_pill_bg')}; border: 1px solid {c('score_pill_border')}; border-radius: 8px;")
        fb_layout = QHBoxLayout(self.fb_box)
        fb_layout.setContentsMargins(8, 8, 8, 8)
        fb_layout.setSpacing(7)
        
        self.fb_icon = QLabel("✓")
        self.fb_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.fb_icon.setFixedSize(24, 24)
        self.fb_icon.setStyleSheet(f"background-color: {c('success')}; color: #FFFFFF; border-radius: 12px; font-weight: bold;")
        
        fb_text_wrap = QWidget()
        fb_tw_layout = QVBoxLayout(fb_text_wrap)
        fb_tw_layout.setContentsMargins(0,0,0,0)
        fb_tw_layout.setSpacing(0)
        
        self.fb_title = QLabel("Ready")
        self.fb_title.setStyleSheet(f"color: {c('score_pill_text')}; font-size: 11px; font-weight: bold;")
        self.fb_sub = QLabel("Press start")
        self.fb_sub.setStyleSheet(f"color: {c('success')}; font-size: 10px;")
        
        fb_tw_layout.addWidget(self.fb_title)
        fb_tw_layout.addWidget(self.fb_sub)
        
        fb_layout.addWidget(self.fb_icon)
        fb_layout.addWidget(fb_text_wrap, 1)
        
        card.layout.addWidget(self.fb_box)
        card.layout.addStretch()
        
        parent_layout.addWidget(card)

    def _audio_btn_style(self, is_on: bool) -> str:
        if is_on:
            return f"""
                QPushButton {{
                    background-color: {c('accent')};
                    color: #FFFFFF;
                    border: 1px solid {c('accent')};
                    border-radius: 6px;
                    font-size: {SIZE_SM}px;
                    font-weight: bold;
                    padding: 0 10px;
                    margin-left: 8px;
                }}
                QPushButton:hover {{ background-color: {c('accent_hover')}; }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: transparent;
                    color: {c('text_secondary')};
                    border: 1px solid {c('border')};
                    border-radius: 6px;
                    font-size: {SIZE_SM}px;
                    font-weight: bold;
                    padding: 0 10px;
                    margin-left: 8px;
                }}
                QPushButton:hover {{ background-color: {c('input_bg')}; }}
            """

    def _on_audio_toggled(self, checked: bool) -> None:
        from core.config import config as _cfg
        _cfg.set("accessibility.audio_prompts", checked)
        _cfg.save()
        self.btn_audio.setText("Audio On" if checked else "Audio Off")
        self.btn_audio.setStyleSheet(self._audio_btn_style(checked))

    def _on_speak_toggled(self, checked: bool) -> None:
        from core.config import config as _cfg
        _cfg.set("speech.tts_enabled", checked)
        _cfg.save()
        self.btn_speak.setText("Speak On" if checked else "Speak Off")
        self.btn_speak.setStyleSheet(self._audio_btn_style(checked))

    def _build_webcam_placeholder(self) -> QWidget:
        """
        Returns a centered placeholder card displayed whenever webcam access
        is unavailable (disabled in Settings, permissions denied, or no device).
        Provides a direct 'Open Settings' shortcut so the user can resolve the issue.
        """
        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        outer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("webcamPlaceholder")
        card.setFixedWidth(340)
        card.setStyleSheet(f"""
            QFrame#webcamPlaceholder {{
                background-color: {c('card_bg_secondary')};
                border: 1.5px dashed {c('border')};
                border-radius: 12px;
                padding: 8px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel("📷")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 40px; border: none; background: transparent;")

        title_lbl = QLabel("Camera Unavailable")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet(
            f"color: {c('text_primary')}; font-size: 16px; font-weight: bold; border: none; background: transparent;"
        )

        desc_lbl = QLabel("Camera Practice requires webcam access.")
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(
            f"color: {c('text_secondary')}; font-size: 13px; border: none; background: transparent;"
        )

        reasons_lbl = QLabel(
            "Possible reasons:\n"
            "  •  Webcam is disabled in Settings\n"
            "  •  Camera permissions are denied\n"
            "  •  No webcam was detected"
        )
        reasons_lbl.setWordWrap(True)
        reasons_lbl.setStyleSheet(
            f"color: {c('text_muted')}; font-size: 12px; line-height: 1.6; border: none; background: transparent;"
        )

        hint_lbl = QLabel("You can enable webcam access in Settings.")
        hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_lbl.setWordWrap(True)
        hint_lbl.setStyleSheet(
            f"color: {c('text_secondary')}; font-size: 12px; border: none; background: transparent;"
        )

        btn_open_settings = QPushButton("Open Settings")
        btn_open_settings.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_open_settings.setFixedHeight(36)
        btn_open_settings.setStyleSheet(f"""
            QPushButton {{
                background-color: {c('accent')};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                padding: 0 20px;
            }}
            QPushButton:hover {{
                background-color: {c('accent_hover')};
            }}
        """)
        btn_open_settings.clicked.connect(
            lambda: self._on_navigation_requested("settings")
        )

        layout.addWidget(icon_lbl)
        layout.addWidget(title_lbl)
        layout.addWidget(desc_lbl)
        layout.addWidget(reasons_lbl)
        layout.addWidget(hint_lbl)
        layout.addSpacing(4)
        layout.addWidget(btn_open_settings, 0, Qt.AlignmentFlag.AlignCenter)

        outer_layout.addWidget(card)
        return outer

    def _show_camera_placeholder(self) -> None:
        """Switch the center panel to the webcam-unavailable placeholder."""
        if hasattr(self, "feed_stack"):
            self.feed_stack.setCurrentIndex(1)

    def _hide_camera_placeholder(self) -> None:
        """Switch the center panel back to the live camera feed."""
        if hasattr(self, "feed_stack"):
            self.feed_stack.setCurrentIndex(0)

    def _bind_viewmodel(self):
        self.viewmodel.frame_ready.connect(self.camera_feed.set_frame)
        self.viewmodel.fps_updated.connect(self.fps_badge.set_fps)
        self.viewmodel.status_updated.connect(self._on_status_updated)
        self.viewmodel.confidence_updated.connect(self._on_confidence_updated)
        self.viewmodel.feedback_updated.connect(self._on_feedback_updated)
        self.viewmodel.score_updated.connect(self._on_score_updated)
        self.viewmodel.progress_updated.connect(self._on_progress_updated)
        self.viewmodel.target_updated.connect(self._on_target_updated)
        self.viewmodel.session_completed.connect(self._show_completion_dialog)
        
    def _on_status_updated(self, state, text):
        self.status_widget.status_pill.set_state(state, text)
        self.landmark_overlay.set_detected(state == "detecting")

        # Camera errors → show the webcam-unavailable placeholder card.
        # Any non-error state while the placeholder is visible → restore feed.
        _CAMERA_ERROR_KEYWORDS = ("disabled", "not detected", "permission denied", "unavailable", "offline", "failed")
        is_camera_error = state == "error" and any(kw in text.lower() for kw in _CAMERA_ERROR_KEYWORDS)
        if is_camera_error:
            self._show_camera_placeholder()
        elif state != "error":
            self._hide_camera_placeholder()
        
    def _on_confidence_updated(self, current, hold):
        self.status_widget.current_conf.set_value(current)
        self.status_widget.hold_conf.set_value(hold)
        
    def _on_feedback_updated(self, fb_type, text, subtext):
        self._last_fb_type = fb_type
        if not text:
            self.fb_box.hide()
            return
            
        self.fb_box.show()
        self.fb_title.setText(text)
        self.fb_sub.setText(subtext)

        # Style/Color the feedback box and icon dynamically
        if fb_type == "success" or fb_type == "correct":
            self.fb_icon.setText("✓")
            self.fb_icon.setStyleSheet(f"background-color: {c('success')}; color: #FFFFFF; border-radius: 12px; font-weight: bold;")
            self.fb_sub.setStyleSheet(f"color: {c('success')}; font-size: 10px;")
        elif fb_type == "missed":
            self.fb_icon.setText("✗")
            self.fb_icon.setStyleSheet(f"background-color: {c('error')}; color: #FFFFFF; border-radius: 12px; font-weight: bold;")
            self.fb_sub.setStyleSheet(f"color: {c('error')}; font-size: 10px;")
        else: # neutral / placeholder states
            self.fb_icon.setText("✓" if fb_type == "correct" else "i")
            self.fb_icon.setStyleSheet(f"background-color: {c('info')}; color: #FFFFFF; border-radius: 12px; font-weight: bold;")
            self.fb_sub.setStyleSheet(f"color: {c('text_secondary')}; font-size: 10px;")
        
    def _on_score_updated(self, correct, missed, acc):
        self.score_pill.setText(f"{correct} correct")
        self.stat_correct.set_value(str(correct))
        self.stat_missed.set_value(str(missed))
        self.stat_acc.set_value(f"{acc}%")
        
    def _on_progress_updated(self, current, total):
        self.prog_lbl.setText(f"Letter {current} of {total}")
        self.prog_bar.setValue(int((current / total) * 100))
        
    def _on_target_updated(self, letter):
        self.target_letter_lbl.setText(letter)
        self.target_hint.setText(f"Form the letter {letter} in front of the camera and hold it steady")
        
        # Resolve the absolute project root directory
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        local_path = os.path.normpath(
            os.path.join(project_root, "assets", "reference", f"Sign_Language_{letter}.jpg")
        )
        
        self.asl_image_lbl.setPixmap(QPixmap())
        self.asl_image_lbl.setText("")
        
        if os.path.exists(local_path):
            pixmap = QPixmap(local_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.asl_image_lbl.setPixmap(pixmap)
                return
                
        # Fallback text if missing
        self.asl_image_lbl.setText(f"Sign {letter}")
        _set_font(self.asl_image_lbl, size=18, bold=True)

    def _on_image_downloaded(self, reply):
        # Stub for compatibility, not used in local rendering
        reply.deleteLater()

    def _show_completion_dialog(self, correct: int, missed: int, accuracy: int, letter_results: list):
        dialog = SessionCompleteDialog(self, correct, missed, accuracy, letter_results)
        result = dialog.exec()
        if result == 1:
            # Practice Again
            self.viewmodel.start()
        elif result == 2:
            # Next Letter Set
            current_idx = self.set_selector.currentIndex()
            if current_idx + 1 < self.set_selector.count():
                self.set_selector.setCurrentIndex(current_idx + 1)
                self.viewmodel.start()
            else:
                QMessageBox.information(self, "All Complete", "Congratulations! You have completed all letter sets.")
        elif result == 3:
            # Return to Dashboard
            self.app.show_dashboard(self.username)

    def stop_practice(self):
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Stop Practice", "Are you sure you want to stop this practice session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Capture scores before stop() resets them
            correct = self.viewmodel.correct_count
            missed = self.viewmodel.missed_count
            letter_results = list(self.viewmodel._letter_results)
            
            self.viewmodel.stop()
            
            total = correct + missed
            if total > 0:
                acc = int((correct / total * 100))
                self._show_completion_dialog(correct, missed, acc, letter_results)
            else:
                self.app.show_dashboard(self.username)

    def _on_theme_changed(self, is_dark: bool):
        self._update_styles()

    def _update_styles(self):
        # Update Topbar
        if hasattr(self, 'topbar') and self.topbar:
            self.topbar.setStyleSheet("background: transparent; border: none;")
        if hasattr(self, 'topbar_title') and self.topbar_title:
            self.topbar_title.setStyleSheet(f"color: {c('welcome_title')}; font-family: 'Segoe UI'; font-size: 26px; font-weight: bold;")
            for welcome_card in self.findChildren(QFrame, "welcomeCard"):
                welcome_card.setStyleSheet(f"""
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
        if hasattr(self, 'set_selector') and self.set_selector:
            self.set_selector.setStyleSheet(f"""
                QComboBox {{
                    background-color: {c('input_bg')};
                    color: {c('text_primary')};
                    border: 1px solid {c('border')};
                    border-radius: 6px;
                    padding: 4px 24px 4px 10px;
                    margin-left: 10px;
                    font-size: {SIZE_MD}px;
                }}
                QComboBox::drop-down {{
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 20px;
                    border-left: none;
                }}
                QComboBox QAbstractItemView {{
                    background-color: {c('bg_primary')};
                    color: {c('text_primary')};
                    border: 1px solid {c('border')};
                    selection-background-color: {c('accent')};
                    selection-color: #FFFFFF;
                    outline: none;
                }}
            """)
        if hasattr(self, 'prog_lbl') and self.prog_lbl:
            self.prog_lbl.setStyleSheet(f"color: {c('text_secondary')}; font-size: {SIZE_MD}px; border: none;")
        if hasattr(self, 'score_pill') and self.score_pill:
            self.score_pill.setStyleSheet(f"""
                background-color: {c('score_pill_bg')};
                border: 1px solid {c('score_pill_border')};
                color: {c('score_pill_text')};
                font-size: {SIZE_MD}px;
                font-weight: bold;
                padding: 4px 10px;
                border-radius: 14px;
            """)
        
        # Update Left Panel
        if hasattr(self, 'left_panel_hdr') and self.left_panel_hdr:
            self.left_panel_hdr.setStyleSheet(f"color: {c('text_secondary')}; font-size: {SIZE_XS}px; font-weight: bold; letter-spacing: 0.8px; margin-bottom: 10px;")
        if hasattr(self, 'target_letter_lbl') and self.target_letter_lbl:
            self.target_letter_lbl.setStyleSheet(f"color: {c('text_primary')}; font-size: 72px; font-weight: bold;")
        if hasattr(self, 'asl_box') and self.asl_box:
            self.asl_box.setStyleSheet(f"""
                background-color: {c('card_bg_secondary')};
                border: 1.5px dashed {c('text_muted')};
                border-radius: 10px;
            """)
        if hasattr(self, 'asl_image_lbl') and self.asl_image_lbl:
            self.asl_image_lbl.setStyleSheet(f"color: {c('text_muted')}; font-size: {SIZE_XS}px;")
        if hasattr(self, 'target_hint') and self.target_hint:
            self.target_hint.setStyleSheet(f"color: {c('text_secondary')}; font-size: {SIZE_MD}px; margin-top: 10px; line-height: 1.4;")
        
        # Update Center Panel
        if hasattr(self, 'center_panel_hdr') and self.center_panel_hdr:
            self.center_panel_hdr.setStyleSheet(f"color: {c('text_secondary')}; font-size: {SIZE_XS}px; font-weight: bold; letter-spacing: 0.8px;")
        if hasattr(self, 'btn_start') and self.btn_start:
            self.btn_start.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c('success')}; color: #FFFFFF;
                    border: 1px solid transparent;
                    border-radius: 8px; font-size: {SIZE_MD}px; font-weight: bold; padding: 7px 16px;
                }}
                QPushButton:hover {{
                    background-color: {c('success_bg')}; color: {c('success')};
                    border-color: {c('success')};
                }}
            """)
        if hasattr(self, 'btn_stop') and self.btn_stop:
            self.btn_stop.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c('error_bg')}; color: {c('error')};
                    border: 1px solid transparent;
                    border-radius: 8px; font-size: {SIZE_MD}px; font-weight: bold; padding: 7px 16px;
                }}
                QPushButton:hover {{
                    background-color: {c('error')}; color: #FFFFFF;
                }}
            """)
        if hasattr(self, 'btn_skip') and self.btn_skip:
            self.btn_skip.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c('badge_gray_bg')}; color: {c('text_primary')};
                    border: 1px solid {c('border')};
                    border-radius: 8px; font-size: {SIZE_MD}px; font-weight: bold; padding: 7px 16px;
                }}
                QPushButton:hover {{
                    background-color: {c('input_bg')};
                    border-color: {c('text_secondary')};
                }}
            """)
        
        # Update Right Panel
        if hasattr(self, 'right_panel_score_hdr') and self.right_panel_score_hdr:
            self.right_panel_score_hdr.setStyleSheet(f"color: {c('text_secondary')}; font-size: {SIZE_XS}px; font-weight: bold; letter-spacing: 0.8px; margin-top: 14px;")
        if hasattr(self, 'right_panel_fb_hdr') and self.right_panel_fb_hdr:
            self.right_panel_fb_hdr.setStyleSheet(f"color: {c('text_secondary')}; font-size: {SIZE_XS}px; font-weight: bold; letter-spacing: 0.8px; margin-top: 14px;")
        if hasattr(self, 'fb_box') and self.fb_box:
            self.fb_box.setStyleSheet(f"background-color: {c('score_pill_bg')}; border: 1px solid {c('score_pill_border')}; border-radius: 8px;")
        if hasattr(self, 'fb_title') and self.fb_title:
            self.fb_title.setStyleSheet(f"color: {c('score_pill_text')}; font-size: 11px; font-weight: bold;")
        
        if hasattr(self, 'btn_stop_practice') and self.btn_stop_practice:
            self.btn_stop_practice.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {c('error')};
                    border: 1px solid {c('error')};
                    border-radius: 14px;
                    font-size: {SIZE_SM}px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {c('error_bg')};
                }}
            """)

        # Trigger feedback update to set the correct state and icons
        if hasattr(self, 'fb_sub') and self.fb_sub:
            self._on_feedback_updated(getattr(self, '_last_fb_type', 'neutral'), self.fb_title.text(), self.fb_sub.text())

        if hasattr(self, 'btn_audio') and self.btn_audio:
            self.btn_audio.setStyleSheet(self._audio_btn_style(self.btn_audio.isChecked()))

        if hasattr(self, 'btn_speak') and self.btn_speak:
            self.btn_speak.setStyleSheet(self._audio_btn_style(self.btn_speak.isChecked()))



class SessionCompleteDialog(QDialog):
    """
    Modal dialog shown when a camera practice session ends.
    Uses core.theme tokens so colors always match the app theme.
    """
    def __init__(self, parent, correct: int, missed: int, accuracy: int,
                 letter_results: list | None = None):
        super().__init__(parent)
        self.setWindowTitle("Practice Session Complete")
        self.setModal(True)
        dialog_height = 480 if letter_results else 320
        self.setFixedSize(420, dialog_height)

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {c("bg_primary")};
                border: 1px solid {c("border")};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Header — no emoji
        title = QLabel("Practice Session Complete")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"color: {c('text_primary')}; font-size: 16px; font-weight: bold;"
        )
        layout.addWidget(title)

        # Stats frame
        stats_frame = QFrame()
        stats_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {c("input_bg")};
                border: 1px solid {c("border")};
                border-radius: 8px;
            }}
            QLabel {{ background: transparent; border: none; }}
        """)
        sf_layout = QGridLayout(stats_frame)
        sf_layout.setContentsMargins(16, 12, 16, 12)
        sf_layout.setSpacing(10)

        def _sl(text, color):
            l = QLabel(text)
            l.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold;")
            return l

        sf_layout.addWidget(_sl("Correct",       c("text_secondary")), 0, 0)
        sf_layout.addWidget(_sl(str(correct),    c("success")),         0, 1, Qt.AlignmentFlag.AlignRight)
        sf_layout.addWidget(_sl("Missed",        c("text_secondary")), 1, 0)
        sf_layout.addWidget(_sl(str(missed),     c("error")),           1, 1, Qt.AlignmentFlag.AlignRight)
        sf_layout.addWidget(_sl("Accuracy",      c("text_secondary")), 2, 0)
        sf_layout.addWidget(_sl(f"{accuracy}%",  c("text_primary")),   2, 1, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(stats_frame)

        # Per-letter breakdown
        if letter_results:
            breakdown_lbl = QLabel("Results by Letter")
            breakdown_lbl.setStyleSheet(
                f"color: {c('text_secondary')}; font-size: 11px; font-weight: bold;"
            )
            layout.addWidget(breakdown_lbl)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setFixedHeight(110)
            scroll.setStyleSheet(f"""
                QScrollArea {{
                    background-color: {c("input_bg")};
                    border: 1px solid {c("border")};
                    border-radius: 8px;
                }}
                QScrollBar:vertical {{ width: 6px; background: transparent; }}
            """)

            grid_widget = QWidget()
            grid_widget.setStyleSheet("background: transparent;")
            grid_layout = QGridLayout(grid_widget)
            grid_layout.setContentsMargins(12, 8, 12, 8)
            grid_layout.setSpacing(6)

            cols = 5
            for i, (letter, was_correct) in enumerate(letter_results):
                mark   = "+" if was_correct else "-"
                color  = c("success") if was_correct else c("error")
                bg     = c("success_bg") if was_correct else c("error_bg")
                cell   = QLabel(f"{letter}  {mark}")
                cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cell.setFixedSize(60, 28)
                cell.setStyleSheet(f"""
                    color: {color}; background-color: {bg};
                    border: 1px solid {color}; border-radius: 6px;
                    font-size: 12px; font-weight: bold;
                """)
                grid_layout.addWidget(cell, i // cols, i % cols)

            scroll.setWidget(grid_widget)
            layout.addWidget(scroll)

        # Buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_again = QPushButton("Practice Again")
        self.btn_again.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_again.setFixedHeight(38)
        self.btn_again.setStyleSheet(f"""
            QPushButton {{
                background-color: {c("accent")};
                color: #FFFFFF; border: none;
                border-radius: 8px; font-weight: bold; font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {c("accent_hover")}; }}
        """)
        self.btn_again.clicked.connect(lambda: self.done(1))
        btn_layout.addWidget(self.btn_again)

        self.btn_next = QPushButton("Next Letter Set")
        self.btn_next.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_next.setFixedHeight(38)
        self.btn_next.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {c("text_primary")};
                border: 1px solid {c("border")}; border-radius: 8px;
                font-weight: bold; font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {c("input_bg")}; border-color: {c("text_secondary")};
            }}
        """)
        self.btn_next.clicked.connect(lambda: self.done(2))
        btn_layout.addWidget(self.btn_next)

        self.btn_dash = QPushButton("Return to Dashboard")
        self.btn_dash.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_dash.setFixedHeight(30)
        self.btn_dash.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {c("text_secondary")};
                border: none; text-decoration: underline; font-size: 12px;
            }}
            QPushButton:hover {{ color: {c("text_primary")}; }}
        """)
        self.btn_dash.clicked.connect(lambda: self.done(3))
        btn_layout.addWidget(self.btn_dash)

        layout.addLayout(btn_layout)