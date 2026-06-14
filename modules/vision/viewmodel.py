import time
import random
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from core.config import config
from modules.vision.camera import CameraManager
from modules.vision.tracker import HandTracker
from modules.gestures.recognizer import GestureRecognizer
from modules.speech.word_assembler import word_assembler
from modules.speech.tts import TTSEngine
from modules.gesture_history.backend import log_quiz_result

class CameraPracticeViewModel(QObject):
    """
    ViewModel for the Camera Practice UI.
    Manages OpenCV/MediaPipe pipeline, recognition state, and session statistics.
    Emits signals that the UI binds to.
    """
    
    # State Signals
    frame_ready = pyqtSignal(object)
    fps_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str, str) # state ("idle", "detecting", "success", "error"), text
    confidence_updated = pyqtSignal(int, int) # current_pct, hold_pct
    feedback_updated = pyqtSignal(str, str, str) # type ("correct", "missed"), text, subtext
    score_updated = pyqtSignal(int, int, int) # correct, missed, accuracy
    progress_updated = pyqtSignal(int, int) # current_index, total
    target_updated = pyqtSignal(str) # new target letter
    session_completed = pyqtSignal(int, int, int, list) # correct, missed, accuracy, letter_results
    
    def __init__(self, username: str = ""):
        super().__init__()
        self._username = username
        
        # Configuration
        self.conf_threshold = config.get("gesture.confidence_threshold", 60.0) / 100.0
        self.hold_duration = config.get("gesture.timeout", 2.0)
        
        # Backend Engines
        self.camera = CameraManager()
        self.tracker = HandTracker()
        self.recognizer = GestureRecognizer(hold_seconds=self.hold_duration)

        # Wire up speech
        self._tts = TTSEngine()
        word_assembler.set_tts(self._tts)
        
        # Timer
        self.timer = QTimer(self)
        self.timer.setInterval(33) # ~30 FPS
        self.timer.timeout.connect(self._process_frame)
        
        # Session State
        self.is_running = False
        self.is_waiting_next = False
        self.target_letters = ["A", "B", "C", "D", "E"] # Default targets
        self.current_target_idx = 0
        self.correct_count = 0
        self.missed_count = 0
        self._last_announced_letter: str | None = None  # Prevent duplicate TTS announcements
        self._current_set_name: str = "Set 1 (A-E)"
        
        self._reset_session_state()

    def set_target_letters(self, letters: list[str], set_name: str = ""):
        """Sets the active gesture set."""
        if self.is_running:
            return
        self.target_letters = list(letters)
        self._current_set_name = set_name or self._current_set_name
        self._reset_session_state()

    def _reset_session_state(self):
        self.current_target_idx = 0
        self.correct_count = 0
        self.missed_count = 0
        self.is_waiting_next = False
        self._last_announced_letter = None
        # Per-letter outcome tracking: list of (letter, was_correct)
        self._letter_results: list[tuple[str, bool]] = []
        self._emit_score()
        self._emit_progress()
        if self.target_letters:
            self.target_updated.emit(self.target_letters[self.current_target_idx])
            self._announce_target_letter(self.target_letters[self.current_target_idx])
            
    def start(self):
        if self.is_running:
            return

        # Task 2: Check for HandTracker initialisation failure before
        # attempting to open the camera so a clear error is shown.
        if self.tracker.init_error:
            self.status_updated.emit(
                "error",
                f"Hand tracking unavailable: {self.tracker.init_error}",
            )
            return

        success, msg = self.camera.start()
        if not success:
            self.status_updated.emit("error", msg)
            return
            
        if self.target_letters:
            random.shuffle(self.target_letters)
            self._reset_session_state()
            
        self.is_running = True
        self.is_waiting_next = False
        self.timer.start()
        self.status_updated.emit("detecting", "Detecting...")
        
    def stop(self):
        self.is_running = False
        self.timer.stop()
        self.camera.stop()
        
        self.status_updated.emit("idle", "Detection stopped")
        self.confidence_updated.emit(0, 0)
        self.feedback_updated.emit("", "", "")
        self.frame_ready.emit(None)
        
        # Reset session counters so a fresh start begins at zero
        self.current_target_idx = 0
        self.correct_count = 0
        self.missed_count = 0
        self.is_waiting_next = False
        self._last_announced_letter = None
        self._letter_results = []
        
    def _process_frame(self):
        if not self.is_running:
            return
            
        success, frame, fps = self.camera.read_frame()
        if not success or frame is None:
            self.status_updated.emit("error", "Camera offline")
            return
            
        self.fps_updated.emit(int(fps))
        
        # Hand tracking
        hand_detected, landmarks, annotated_frame = self.tracker.process_frame(frame)
        
        # Display frame
        display_frame = annotated_frame if annotated_frame is not None else frame
        self.frame_ready.emit(display_frame)
        
        if self.is_waiting_next:
            return

        if hand_detected and landmarks:
            gesture, confidence = self.recognizer.recognize(landmarks)
            hold_pct = int(self.recognizer.hold_progress * 100)

            target = self.target_letters[self.current_target_idx]

            # Always show hold progress; show current confidence from the raw
            # CNN result cached inside recognize() — avoids a second
            # model.predict() call per frame (Fix #1: eliminate duplicate inference).
            raw_gesture, raw_conf = self.recognizer.last_raw_result
            current_pct = int(raw_conf * 100)

            self.confidence_updated.emit(current_pct, hold_pct)
            self.status_updated.emit("detecting", "Detecting...")

            if gesture:
                if gesture.upper() == target:
                    self._on_gesture_confirmed(target)
                else:
                    self._on_gesture_incorrect(gesture, target)
            else:
                hold_gesture = self.recognizer.current_hold_gesture
                if hold_gesture and hold_gesture.upper() == target:
                    self.feedback_updated.emit("correct", f"Seeing '{hold_gesture.upper()}'!", "Hold steady to confirm...")
                elif hold_gesture:
                    self.feedback_updated.emit("neutral", f"Seeing '{hold_gesture.upper()}'...", f"That's not {target}. Hold {target} instead.")
                elif raw_gesture and raw_gesture.upper() == target:
                    self.feedback_updated.emit("correct", f"Forming '{target}'...", "Hold steady to start timer")
                else:
                    self.feedback_updated.emit("", "", "")
        else:
            self.status_updated.emit("idle", "No hand visible")
            self.confidence_updated.emit(0, 0)
            self.feedback_updated.emit("", "", "")
            
    def _on_gesture_confirmed(self, gesture):
        self.correct_count += 1
        self._letter_results.append((gesture, True))
        self._emit_score()
        self.feedback_updated.emit("success", f"✅ Correct! Letter {gesture} recognized.", "Loading next letter...")

        # Log to practice history
        raw_conf = self.recognizer.hold_progress  # 0-1 hold progress used as proxy
        log_quiz_result(
            username=self._username,
            source="camera_practice",
            letter=gesture,
            result="correct",
            confidence=raw_conf if raw_conf > 0 else None,
            set_name=self._current_set_name,
        )

        # Send the confirmed letter to speech output
        word_assembler.add_letter(gesture)

        # Advance to next letter after 1s delay
        self.is_waiting_next = True
        QTimer.singleShot(1000, self._advance_after_delay)

    def _on_gesture_incorrect(self, gesture, target):
        self.missed_count += 1
        self._letter_results.append((target, False))
        self._emit_score()
        self.feedback_updated.emit("missed", f"❌ That's not {target}.", f"Saw '{gesture.upper()}'. Please try again.")

        # Log missed attempt
        log_quiz_result(
            username=self._username,
            source="camera_practice",
            letter=target,
            result="missed",
            confidence=None,
            set_name=self._current_set_name,
        )
        self.recognizer.reset_hold()

    def skip_letter(self):
        if not self.is_running or self.is_waiting_next:
            return
        target = self.target_letters[self.current_target_idx]
        self.missed_count += 1
        self._letter_results.append((target, False))
        self._emit_score()
        self.feedback_updated.emit("missed", "Skipped", "Moving to next letter...")

        # Log skipped attempt
        log_quiz_result(
            username=self._username,
            source="camera_practice",
            letter=target,
            result="skipped",
            confidence=None,
            set_name=self._current_set_name,
        )
        self.is_waiting_next = True
        QTimer.singleShot(1000, self._advance_after_delay)

    def _advance_after_delay(self):
        if not self.is_running:
            return
        self.is_waiting_next = False

        self.current_target_idx += 1
        if self.current_target_idx < len(self.target_letters):
            self._emit_progress()
            self.target_updated.emit(self.target_letters[self.current_target_idx])
            self._announce_target_letter(self.target_letters[self.current_target_idx])
            self.recognizer.reset_hold()
        else:
            # Session complete — flush any remaining letters to speech
            word_assembler.force_flush()
            
            # Capture final stats before stop() resets them
            final_correct = self.correct_count
            final_missed = self.missed_count
            final_results = list(self._letter_results)
            total = final_correct + final_missed
            acc = int((final_correct / total * 100)) if total > 0 else 0
            
            self.stop()
            
            # Emit completion signal with saved stats
            self.session_completed.emit(final_correct, final_missed, acc, final_results)
            self.status_updated.emit("success", "Session Complete")
            
    def _announce_target_letter(self, letter: str) -> None:
        """
        Speak 'Letter X' via TTS when a new target is displayed.
        Guarded by:
          - accessibility.audio_prompts config flag
          - speech.tts_enabled config flag (respected inside TTSEngine)
          - duplicate-announcement check (_last_announced_letter)
        Does not block the main thread — TTSEngine.speak() is async.
        """
        if letter == self._last_announced_letter:
            return
        if not config.get("accessibility.audio_prompts", True):
            return
        self._last_announced_letter = letter
        self._tts.speak(f"Letter {letter}")

    def _emit_score(self):
        total = self.correct_count + self.missed_count
        acc = int((self.correct_count / total * 100)) if total > 0 else 0
        self.score_updated.emit(self.correct_count, self.missed_count, acc)
        
    def _emit_progress(self):
        self.progress_updated.emit(self.current_target_idx + 1, len(self.target_letters))