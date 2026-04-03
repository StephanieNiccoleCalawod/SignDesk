"""
comparator.py - Landmark Comparison Engine
Compares detected hand landmarks against the ASL gesture library.
Maps to: Sprint 4 T-002

Takes 21 MediaPipe hand landmarks and scores each gesture definition
in the library, returning ranked results.
"""

from modules.gestures.library import ASL_GESTURES, get_finger_states, get_finger_curl


class LandmarkComparator:
    """
    Compares a set of 21 hand landmarks against every gesture in the
    ASL gesture library and returns scored results.

    This module is purely computational — no UI, no state, no side effects.
    """

    def __init__(self, gesture_library: dict | None = None):
        """
        Args:
            gesture_library: dict mapping gesture names to check functions.
                             Defaults to the full ASL_GESTURES registry.
        """
        self._library = gesture_library or ASL_GESTURES

    def compare_all(self, landmarks) -> list[tuple[str, float]]:
        """
        Scores every gesture in the library against the given landmarks.

        Args:
            landmarks: List of 21 (x, y, z) tuples from MediaPipe.

        Returns:
            List of (gesture_name, score) tuples, sorted descending by score.
            Only includes gestures with score > 0.
        """
        if landmarks is None or len(landmarks) != 21:
            return []

        results = []
        for gesture_name, check_fn in self._library.items():
            try:
                score = check_fn(landmarks)
                if score > 0.0:
                    results.append((gesture_name, score))
            except Exception:
                continue

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def best_match(self, landmarks) -> tuple[str | None, float]:
        """
        Returns the single highest-scoring gesture match.

        Args:
            landmarks: List of 21 (x, y, z) tuples from MediaPipe.

        Returns:
            (gesture_name, score) for the best match.
            (None, 0.0) if no gesture scores above 0.
        """
        ranked = self.compare_all(landmarks)
        if ranked:
            return ranked[0]
        return None, 0.0

    @property
    def gesture_count(self) -> int:
        """Number of gestures in the loaded library."""
        return len(self._library)

    @property
    def gesture_names(self) -> list[str]:
        """List of all recognizable gesture names."""
        return list(self._library.keys())
