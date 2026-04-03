"""
recognizer.py - Gesture Recognition Orchestrator
Maps to: Sprint 4 T-004 (Recognition Pipeline Integration)

Thin orchestrator that wires together:
  1. LandmarkComparator — scores landmarks against gesture library
  2. ConfidenceFilter   — rejects low-confidence matches
  3. StabilityBuffer    — prevents frame-to-frame flicker

Public API is identical to the original engine.py GestureRecognizer
so that vision/ui.py requires zero changes.
"""

from modules.gestures.comparator import LandmarkComparator
from modules.gestures.confidence import ConfidenceFilter, StabilityBuffer


class GestureRecognizer:
    """
    Recognizes ASL gestures by orchestrating comparison, filtering,
    and stability buffering.

    Acceptance Criteria:
    - SD003-AC1: System compares detected landmarks against stored ASL gesture library
    - SD003-AC2: Valid gestures are recognized and labeled correctly on screen
    - SD003-AC3: Invalid or unmatched movements are ignored — no output
    - SD003-AC4: System achieves ≥85% recognition accuracy on predefined gesture set
    - SD003-AC5: Recognition operates fully offline
    - SD004-AC1: Confidence percentage displayed beside recognized gesture
    - SD004-AC2: Score updates in real time with every detection
    - SD004-AC3: Scores below 60% show low-confidence warning
    - SD004-AC4: Indicator is always visible during active recognition
    """

    # Expose thresholds at class level for backward compat with vision/ui.py
    CONFIDENCE_THRESHOLD = ConfidenceFilter.CONFIDENCE_THRESHOLD

    def __init__(self, stability_frames: int = 3):
        self._comparator = LandmarkComparator()
        self._filter = ConfidenceFilter()
        self._stability = StabilityBuffer(required_frames=stability_frames)
        self._last_gesture = None
        self._last_confidence = 0.0

    def recognize(self, landmarks) -> tuple[str | None, float]:
        """
        Full recognition pipeline: compare → filter → stabilize.

        Args:
            landmarks: List of 21 (x, y, z) tuples from MediaPipe.

        Returns:
            (gesture_name, confidence) if a gesture is recognized.
            (None, 0.0) if no valid gesture is detected.
        """
        # Step 1: Compare landmarks against gesture library
        raw_gesture, raw_score = self._comparator.best_match(landmarks)

        # Step 2: Apply confidence threshold filter
        filtered_gesture, filtered_score = self._filter.filter(
            raw_gesture, raw_score)

        # Step 3: Apply stability buffer (prevents flicker)
        stable_gesture, stable_score = self._stability.update(
            filtered_gesture, filtered_score)

        # Update last-known state
        if stable_gesture is not None:
            self._last_gesture = stable_gesture
            self._last_confidence = stable_score

        return stable_gesture, stable_score

    def is_low_confidence(self, confidence: float) -> bool:
        """
        Returns True if the confidence is below the warning threshold.
        SD004-AC3: Scores below 60% show low-confidence warning.
        """
        return self._filter.is_low_confidence(confidence)

    @property
    def last_gesture(self) -> str | None:
        return self._last_gesture

    @property
    def last_confidence(self) -> float:
        return self._last_confidence

    @property
    def available_gestures(self) -> list[str]:
        """Returns the list of all recognizable gesture names."""
        return self._comparator.gesture_names
