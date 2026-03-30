"""
engine.py - Gesture Recognition Engine
Compares detected landmarks against the ASL gesture library.
Maps to: SD003 (Gesture Recognition), SD004 (Confidence Indicator)
"""

from modules.gestures.library import ASL_GESTURES


class GestureRecognizer:
    """
    Recognizes ASL gestures by comparing hand landmarks against
    the stored gesture library.

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

    # Minimum confidence to accept a gesture (SD004-AC3: below this = low-confidence)
    CONFIDENCE_THRESHOLD = 0.60

    # Minimum confidence to report any gesture at all (SD003-AC3: ignore invalid)
    MIN_REPORT_THRESHOLD = 0.45

    def __init__(self):
        self._gesture_library = ASL_GESTURES
        self._last_gesture = None
        self._last_confidence = 0.0
        self._stable_gesture = None
        self._stable_count = 0
        self._stability_required = 3  # Frames of same gesture before confirming

    def recognize(self, landmarks) -> tuple[str | None, float]:
        """
        Compares landmarks against all gestures in the library.

        Args:
            landmarks: List of 21 (x, y, z) tuples from MediaPipe.

        Returns:
            (gesture_name, confidence) if a gesture is recognized above MIN_REPORT_THRESHOLD.
            (None, 0.0) if no valid gesture is detected (SD003-AC3).
        """
        if landmarks is None or len(landmarks) != 21:
            self._last_gesture = None
            self._last_confidence = 0.0
            return None, 0.0

        best_gesture = None
        best_score = 0.0

        # Compare against every gesture in the library (SD003-AC1)
        for gesture_name, check_fn in self._gesture_library.items():
            try:
                score = check_fn(landmarks)
                if score > best_score:
                    best_score = score
                    best_gesture = gesture_name
            except Exception:
                continue

        # Ignore invalid gestures below minimum threshold (SD003-AC3)
        if best_score < self.MIN_REPORT_THRESHOLD:
            self._reset_stability()
            self._last_gesture = None
            self._last_confidence = 0.0
            return None, 0.0

        # Stability check: require the same gesture for consecutive frames
        # This prevents flickering between gestures
        if best_gesture == self._stable_gesture:
            self._stable_count += 1
        else:
            self._stable_gesture = best_gesture
            self._stable_count = 1

        if self._stable_count >= self._stability_required:
            self._last_gesture = best_gesture
            self._last_confidence = best_score
            return best_gesture, best_score

        # Still stabilizing — return last known or none
        if self._last_gesture is not None:
            return self._last_gesture, self._last_confidence
        return None, 0.0

    def _reset_stability(self):
        """Resets the stability counter."""
        self._stable_gesture = None
        self._stable_count = 0

    def is_low_confidence(self, confidence: float) -> bool:
        """
        Returns True if the confidence is below the warning threshold.
        SD004-AC3: Scores below 60% show low-confidence warning.
        """
        return confidence < self.CONFIDENCE_THRESHOLD

    @property
    def last_gesture(self) -> str | None:
        return self._last_gesture

    @property
    def last_confidence(self) -> float:
        return self._last_confidence

    @property
    def available_gestures(self) -> list[str]:
        """Returns the list of all recognizable gesture names."""
        return list(self._gesture_library.keys())
