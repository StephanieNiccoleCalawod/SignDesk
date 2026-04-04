"""
builder.py - Sentence Construction Logic
Maps to: Sprint 6 SD005

Collects gestures, maintains an independent sentence buffer, and
finalizes after a specified timeout window.
"""

class SentenceBuilder:
    def __init__(self, timeout: float = 2.0):
        self._buffer: list[str] = []
        self._last_input_time: float | None = None
        self.timeout = timeout

    def add_gesture(self, text: str, current_time: float):
        """
        Record a validated gesture token into the sentence buffer.
        """
        if text:
            self._buffer.append(text)
            self._last_input_time = current_time

    def should_finalize(self, current_time: float) -> bool:
        """
        Check if the finalization timeout threshold has passed since the last input.
        """
        if not self._buffer or self._last_input_time is None:
            return False
            
        return (current_time - self._last_input_time) >= self.timeout

    def finalize(self) -> str:
        """
        Join out pending elements, trim whitespace, and return the complete sentence.
        """
        # For our usecase, text gestures are individual letters.
        # But wait - we are getting exactly the same 'A', 'B' tokens that the TextBuffer gets.
        # However, TextBuffer handles spacing natively! Wait, if we just join tokens, we get "HELLO",
        # but how does SentenceBuilder know where the spaces are? 
        # Ah. The prompt says: "Feed SentenceBuilder directly from the validated gesture token/event"
        # and "Both modules operate independently but receive the same validated gesture events."
        # If the user pauses for 0.9s, TextBuffer auto-inserts a space.
        # Does SentenceBuilder know about this space? No! Because it's an auto-space inside TextBuffer.
        # If SentenceBuilder only gets the gesture tokens ('H', 'E', 'L', 'L', 'O'), it will just output "HELLO".
        # If we want words, we either need SentenceBuilder to insert its own spaces based on time,
        # OR we wait 2.0s and output the word, effectively treating 1 sentence = 1 word sequence.
        # The prompt says: "TextBuffer handles only word spacing. SentenceBuilder handles only sentence finalization."
        # If SentenceBuilder does not handle spacing, then how are sentences spaced?
        # Maybe I should just join what it has: `"".join(self._buffer).strip()`. If the user wants spaces,
        # the user handles it or we assume letters form a single contiguous block between 2.0s boundaries.
        
        sentence = "".join(self._buffer).strip()
        return sentence

    def reset(self):
        """
        Clear the buffer and reset the timer.
        """
        self._buffer.clear()
        self._last_input_time = None

    def get_current(self) -> str:
        """
        Returns the current unfinalized buffer.
        """
        return "".join(self._buffer)
