import time
from modules.gestures.comparator import LandmarkComparator
from modules.gestures.confidence import ConfidenceFilter, StabilityBuffer


class GestureRecognizer:
    """
    Recognizes ASL gestures by orchestrating:
      1. LandmarkComparator  — scores landmarks vs gesture library
      2. ConfidenceFilter    — rejects score < 0.45
      3. StabilityBuffer     — requires N consecutive frames
      4. HoldTimer           — requires gesture held for hold_seconds
    
    A gesture is only committed after being held continuously
    for hold_seconds. Accidental flashes are ignored.
    """

    CONFIDENCE_THRESHOLD = ConfidenceFilter.CONFIDENCE_THRESHOLD

    def __init__(
        self,
        stability_frames: int = 3,
        hold_seconds: float | None = None
    ):
        # ── Recognition pipeline ──────────────────────────────
        self._comparator = LandmarkComparator()
        self._filter     = ConfidenceFilter()
        self._stability  = StabilityBuffer(required_frames=stability_frames)

        # ── Internal state ────────────────────────────────────
        self._last_gesture    = None
        self._last_confidence = 0.0

        # ── Hold Timer state ──────────────────────────────────
        self._hold_seconds   = hold_seconds  # seconds to hold before commit
        self._hold_gesture   = None          # gesture currently being tracked
        self._hold_start     = None          # time.monotonic() when hold began
        self._hold_confirmed = False         # True once hold threshold is met
        self._last_committed = None          # last gesture sent to assembler

    # ── Public: main recognition entry point ──────────────────────────────────

    def recognize(self, landmarks) -> tuple[str | None, float]:
        """
        Full 4-stage recognition pipeline.
        Only returns a gesture after it has been held for hold_seconds.

        Args:
            landmarks: 21 (x, y, z) tuples from MediaPipe.

        Returns:
            (gesture, score) on confirmed commit.
            (None, 0.0) while holding, stabilizing, or on accidental flash.
        """
        # Stage 1 — Compare landmarks against gesture library
        raw_gesture, raw_score = self._comparator.best_match(landmarks)

        # ── Motion detection filter (distinguish I/J and D/Z) ──
        if raw_gesture in ["I", "J", "D", "Z"] and landmarks and len(landmarks) == 21:
            if not hasattr(self, "_history_landmarks"):
                self._history_landmarks = []
            
            # Track coordinates (x, y)
            self._history_landmarks.append([(lm[0], lm[1]) for lm in landmarks])
            if len(self._history_landmarks) > 10:
                self._history_landmarks.pop(0)

            if len(self._history_landmarks) >= 5:
                movement = 0.0
                # Track wrist (0), index tip (8), and pinky tip (20)
                for idx in [0, 8, 20]:
                    x_coords = [f[idx][0] for f in self._history_landmarks[-5:]]
                    y_coords = [f[idx][1] for f in self._history_landmarks[-5:]]
                    movement += (max(x_coords) - min(x_coords)) + (max(y_coords) - min(y_coords))

                # If movement is low, hand is stationary -> override motion-based signs
                is_moving = movement > 0.06
                if not is_moving:
                    if raw_gesture == "J":
                        raw_gesture = "I"
                    elif raw_gesture == "Z":
                        raw_gesture = "D"

        # Stage 2 — Confidence threshold filter
        filtered_gesture, filtered_score = self._filter.filter(
            raw_gesture, raw_score
        )

        # Stage 3 — Stability buffer (frame-level flicker prevention)
        stable_gesture, stable_score = self._stability.update(
            filtered_gesture, filtered_score
        )

        # Stage 4 — Hold timer (time-level accidental gesture prevention)
        if self._hold_seconds is None:
            if stable_gesture is not None:
                self._last_gesture    = stable_gesture
                self._last_confidence = stable_score
                return stable_gesture, stable_score
            return None, 0.0

        result = self._update_hold_timer(stable_gesture, stable_score)

        if result is not None:
            self._last_gesture    = result[0]
            self._last_confidence = result[1]
            return result

        return None, 0.0

    # ── Private: hold timer logic ─────────────────────────────────────────────

    def _update_hold_timer(
        self,
        gesture: str | None,
        score: float
    ) -> tuple[str, float] | None:
        """
        Tracks how long the current stable gesture has been held.
        Only commits after hold_seconds of continuous holding.

        Fixes applied:
          - Guard against string "None" being passed as a gesture name
          - Guard against empty string or whitespace-only strings
        """
        now = time.monotonic()

        # ── Bug 3 Fix: guard against string "None" or falsy values ───
        # Somewhere upstream str() or incorrect return passes "None"
        # as a gesture name. Normalize to actual Python None here.
        if not gesture or gesture == "None" or not gesture.strip():
            gesture = None

        # ── Gesture lost or changed → reset ───────────────────
        if gesture is None or gesture != self._hold_gesture:
            prev = self._hold_gesture
            self._hold_gesture   = gesture
            self._hold_start     = now if gesture else None
            self._hold_confirmed = False

            if prev and gesture:
                print(
                    f"[HoldTimer] Gesture changed: "
                    f"'{prev}' → '{gesture}' | Timer reset"
                )
            elif prev:
                print(f"[HoldTimer] Gesture lost: '{prev}' | Timer reset")
            elif gesture:
                # Only logs real gesture names now — never logs 'None'
                print(f"[HoldTimer] New gesture: '{gesture}' | Timer started")

            return None

        # ── Same gesture — measure elapsed time ───────────────
        elapsed   = now - self._hold_start
        remaining = max(0.0, self._hold_seconds - elapsed)

        # Still holding — not ready yet
        if elapsed < self._hold_seconds:
            print(
                f"[HoldTimer] Holding '{gesture}' | "
                f"{elapsed:.1f}s / {self._hold_seconds}s "
                f"({remaining:.1f}s remaining)"
            )
            return None

        # ── Hold threshold met ─────────────────────────────────
        if not self._hold_confirmed:
            self._hold_confirmed = True
            self._last_committed = gesture
            print(
                f"[HoldTimer] ✅ '{gesture}' confirmed after "
                f"{elapsed:.1f}s → committing to assembler"
            )
            return gesture, score

        # ── Already committed — suppress while hand is still held ──
        return None

    # ── Public: reset after commit ────────────────────────────────────────────

    def reset_hold(self):
        """
        Resets hold timer after a gesture is committed.
        Must be called by the detection UI after add_letter() fires,
        so the recognizer is ready for the next intentional gesture.
        """
        prev = self._hold_gesture
        self._hold_gesture   = None
        self._hold_start     = None
        self._hold_confirmed = False
        print(f"[HoldTimer] Reset after commit: '{prev}'")

    # ── Public: hold progress for UI progress bar ─────────────────────────────

    @property
    def hold_progress(self) -> float:
        """
        Hold progress as 0.0 – 1.0.
        Use this to drive a progress bar or countdown ring in the UI.

          0.0 = no gesture / just started
          0.5 = halfway through hold window
          1.0 = hold confirmed

        Example UI usage:
            progress = self.recognizer.hold_progress
            self._hold_bar.set(progress)  # CTkProgressBar.set()
        """
        if self._hold_start is None:
            return 0.0
        if self._hold_confirmed:
            return 1.0
        elapsed = time.monotonic() - self._hold_start
        return min(elapsed / self._hold_seconds, 1.0)

    # ── Convenience helpers ───────────────────────────────────────────────────

    @property
    def current_hold_gesture(self) -> str | None:
        """
        The gesture currently being tracked by the hold timer.

        Returns the gesture name if a hold is IN PROGRESS (not yet committed).
        Returns None if:
          - No gesture is being tracked
          - Hold has already been confirmed/committed

        Used by the UI to distinguish between:
          - "Still holding"   (show progress, don't insert space)
          - "Truly no gesture" (show unclear, safe to insert space)
        """
        if self._hold_confirmed:
            return None  # already committed — don't show again
        return self._hold_gesture  # None or gesture name mid-hold

    def is_low_confidence(self, confidence: float) -> bool:
        return self._filter.is_low_confidence(confidence)

    @property
    def last_gesture(self) -> str | None:
        return self._last_gesture

    @property
    def last_confidence(self) -> float:
        return self._last_confidence

    @property
    def available_gestures(self) -> list[str]:
        return self._comparator.gesture_names
