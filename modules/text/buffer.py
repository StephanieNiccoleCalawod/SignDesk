"""
buffer.py - Text Output Buffer
Maps to: Sprint 5 T-002

Stores and builds text output dynamically from recognized gestures.
Includes:
  1. Deduplication — prevents repeated same-gesture spam
  2. Time-based debounce — rejects rapid gesture switching noise
  3. Auto word spacing — inserts space after sustained pause
"""

import time


class TextBuffer:
    """
    Accumulates gesture-to-text output with intelligent filtering.

    Three layers of protection against noisy output:
    - Deduplication: same gesture repeated → ignored
    - Debounce: new gesture within DEBOUNCE_SECONDS → ignored
    - Stability: upstream StabilityBuffer (3-frame) already filters flicker

    Auto-space feature inserts a word separator after the user pauses
    (lowers hand) for SPACE_DELAY_SECONDS.
    """

    DEBOUNCE_SECONDS = 0.6      # minimum seconds between accepting new gestures
    SPACE_DELAY_SECONDS = 0.9   # seconds of inactivity before auto-inserting space

    def __init__(self):
        self._text = ""
        self._last_gesture = None
        self._last_append_time = 0.0

    def append(self, value: str) -> None:
        """
        Append raw text to the buffer unconditionally.

        Args:
            value: Text string to append.
        """
        if value:
            self._text += value

    def append_if_new(self, gesture: str) -> bool:
        """
        Append a gesture's text only if it passes deduplication and debounce.

        Args:
            gesture: The gesture character to append (e.g. "A").

        Returns:
            True if the gesture was accepted and appended.
            False if it was rejected (duplicate or debounced).
        """
        if not gesture:
            return False

        now = time.monotonic()

        # Deduplication: same gesture repeated consecutively → skip
        if gesture == self._last_gesture:
            return False

        # Debounce: new gesture arrived too quickly → skip
        if self._last_append_time > 0 and (now - self._last_append_time) < self.DEBOUNCE_SECONDS:
            return False

        # Accept the gesture
        self._text += gesture
        self._last_gesture = gesture
        self._last_append_time = now
        return True

    def maybe_insert_space(self) -> bool:
        """
        Insert a space if enough time has passed since the last gesture.

        Called every frame from the update loop when no gesture is active.
        Enables natural word separation without a dedicated "space" gesture.

        Returns:
            True if a space was inserted, False otherwise.
        """
        if not self._text or self._text.endswith(" "):
            return False  # empty buffer or already has trailing space

        if self._last_append_time > 0 and \
                (time.monotonic() - self._last_append_time) >= self.SPACE_DELAY_SECONDS:
            self._text += " "
            return True

        return False

    def backspace(self) -> None:
        """Remove the last character from the buffer."""
        if self._text:
            self._text = self._text[:-1]

    def clear(self) -> None:
        """Reset the buffer to empty state."""
        self._text = ""
        self._last_gesture = None
        self._last_append_time = 0.0

    def get(self) -> str:
        """Returns the current accumulated text."""
        return self._text

    @property
    def last_gesture(self) -> str | None:
        """The last gesture that was successfully appended."""
        return self._last_gesture

    @property
    def is_empty(self) -> bool:
        """True if the buffer contains no text."""
        return len(self._text) == 0

    def __len__(self) -> int:
        """Number of characters in the buffer."""
        return len(self._text)

    def __repr__(self) -> str:
        return f"TextBuffer(text={self._text!r}, last={self._last_gesture!r})"
