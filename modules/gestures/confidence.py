"""
confidence.py - Confidence Threshold Filter & Stability Buffer
Maps to: Sprint 4 T-003

Provides two mechanisms to ensure recognition quality:
1. ConfidenceFilter — rejects scores below configurable thresholds
2. StabilityBuffer — requires N consecutive frames of the same gesture
   before confirming, preventing flicker between gestures
"""


class ConfidenceFilter:
    """
    Filters gesture recognition results based on confidence thresholds.

    Two thresholds:
    - MIN_REPORT_THRESHOLD (0.45): Below this, the gesture is completely
      ignored — returns None. Prevents false positives (SD003-AC3).
    - CONFIDENCE_THRESHOLD (0.60): Between MIN_REPORT and this, the gesture
      is reported but flagged as low-confidence (SD004-AC3).
    """

    CONFIDENCE_THRESHOLD = 0.60
    MIN_REPORT_THRESHOLD = 0.45

    def filter(self, gesture: str | None, score: float) -> tuple[str | None, float]:
        """
        Apply threshold filtering.

        Args:
            gesture: Gesture name from comparator (or None).
            score: Confidence score [0.0 – 1.0].

        Returns:
            (gesture, score) if above MIN_REPORT_THRESHOLD.
            (None, 0.0) if below MIN_REPORT_THRESHOLD.
        """
        if gesture is None or score < self.MIN_REPORT_THRESHOLD:
            return None, 0.0
        return gesture, score

    def is_low_confidence(self, score: float) -> bool:
        """
        Returns True if the score is below the warning threshold.
        SD004-AC3: Scores below 60% show low-confidence warning.
        """
        return score < self.CONFIDENCE_THRESHOLD

    def is_valid(self, score: float) -> bool:
        """Returns True if the score is above MIN_REPORT_THRESHOLD."""
        return score >= self.MIN_REPORT_THRESHOLD


class StabilityBuffer:
    """
    Requires a gesture to be recognized for N consecutive frames
    before confirming it. Prevents flickering between similar gestures.

    Once a gesture is stable, it remains the "last known" gesture
    until a new stable gesture replaces it.
    """

    def __init__(self, required_frames: int = 3):
        """
        Args:
            required_frames: Number of consecutive frames needed to confirm.
        """
        self._required = required_frames
        self._current_gesture = None
        self._count = 0
        self._last_confirmed = None
        self._last_confirmed_score = 0.0

    def update(self, gesture: str | None, score: float) -> tuple[str | None, float]:
        """
        Feed a frame's recognition result into the buffer.

        Args:
            gesture: Recognized gesture name (or None).
            score: Confidence score.

        Returns:
            (gesture, score) if the gesture is stable (confirmed).
            Last confirmed gesture if still stabilizing.
            (None, 0.0) if no gesture is confirmed yet.
        """
        if gesture is None:
            self._reset()
            return None, 0.0

        if gesture == self._current_gesture:
            self._count += 1
        else:
            self._current_gesture = gesture
            self._count = 1

        if self._count >= self._required:
            self._last_confirmed = gesture
            self._last_confirmed_score = score
            return gesture, score

        # Still stabilizing — return last confirmed if available
        if self._last_confirmed is not None:
            return self._last_confirmed, self._last_confirmed_score
        return None, 0.0

    def _reset(self):
        """Resets the stability counter (gesture lost)."""
        self._current_gesture = None
        self._count = 0

    @property
    def last_confirmed(self) -> str | None:
        """Last gesture that passed stability check."""
        return self._last_confirmed

    @property
    def last_confirmed_score(self) -> float:
        return self._last_confirmed_score

    @property
    def is_stabilizing(self) -> bool:
        """True if a gesture is being tracked but not yet confirmed."""
        return self._current_gesture is not None and self._count < self._required
