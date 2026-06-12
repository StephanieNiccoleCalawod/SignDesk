"""
comparator.py - Landmark Comparison Engine
Now delegates to CNNPredictor instead of rule-based library.
Maps to: Sprint 4 T-002
"""

from modules.gestures.cnn_predictor import CNNPredictor


class LandmarkComparator:
    """
    Drop-in wrapper around CNNPredictor.
    Keeps the same interface so recognizer.py needs zero changes.
    """

    def __init__(self, gesture_library=None):
        # gesture_library param kept for backward compatibility
        # but is no longer used — CNN handles recognition now
        self._predictor = CNNPredictor()

    def compare_all(self, landmarks) -> list[tuple[str, float]]:
        gesture, score = self._predictor.best_match(landmarks)
        if gesture is None:
            return []
        return [(gesture, score)]

    def best_match(self, landmarks) -> tuple[str | None, float]:
        return self._predictor.best_match(landmarks)

    @property
    def gesture_count(self) -> int:
        return self._predictor.gesture_count

    @property
    def gesture_names(self) -> list[str]:
        return self._predictor.gesture_names