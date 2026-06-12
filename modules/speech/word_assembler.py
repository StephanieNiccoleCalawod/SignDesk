"""
word_assembler.py - Letter-to-Word Assembly Layer
Sits between gesture recognition and GlobalSpeechBuffer.
Collects individual letter gestures and assembles them into words
using a timeout window before pushing to speech_buffer.
"""

import threading
from modules.speech.buffer import speech_buffer


# ── Pronunciation Map ─────────────────────────────────────────────────────────
PRONUNCIATION_MAP = {

    # ── Single letters ────────────────────────────────────────────────────────
    "a": "ay",
    "b": "bee",
    "c": "see",
    "d": "dee",
    "e": "ee",
    "f": "ef",
    "g": "jee",
    "h": "aych",
    "i": "eye",
    "j": "jay",
    "k": "kay",
    "l": "el",
    "m": "em",
    "n": "en",
    "o": "oh",
    "p": "pee",
    "q": "cue",
    "r": "ar",
    "s": "es",
    "t": "tee",
    "u": "you",
    "v": "vee",
    "w": "double-you",
    "x": "ex",
    "y": "why",
    "z": "zee",

    # ── Two-letter combos ─────────────────────────────────────────────────────
    "ba": "bah",
    "ca": "kah",
    "da": "dah",
    "fa": "fah",
    "ga": "gah",
    "ha": "hah",
    "ja": "jah",
    "ka": "kah",
    "la": "lah",
    "ma": "mah",
    "na": "nah",
    "pa": "pah",
    "ra": "rah",
    "sa": "sah",
    "ta": "tah",
    "va": "vah",
    "wa": "wah",
    "ya": "yah",
    "za": "zah",

    # ── Common short words pyttsx3 misreads ───────────────────────────────────
    "ok": "okay",
    "dr": "doctor",
    "mr": "mister",
    "ms": "miss",
    "st": "street",
    "vs": "versus",
    "no": "no",
    "hi": "hi",
    "he": "he",
    "me": "me",
    "we": "we",
    "be": "be",
}


class WordAssembler:
    """
    Collects single-letter gestures and assembles them into words.

    Flow:
        Gesture recognized → assembler.add_letter("H")
                           → assembler.add_letter("I")
                           → [timeout expires]
                           → suggest_word("HI") → "HI" ✅
                           → speech_buffer.push("HI")
                           → tts speaks "hi"
    """

    def __init__(self, timeout: float = 2.0):
        self._letters: list[str] = []
        self._timeout = timeout
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._tts = None
        self._live_speech = False

    def set_tts(self, tts_engine):
        """Inject TTSEngine after instantiation to avoid circular imports."""
        self._tts = tts_engine
        print("[WordAssembler] TTS engine injected.")

    def set_live_speech(self, enabled: bool):
        """Called by the Live Speech toggle button in the detection UI."""
        self._live_speech = enabled
        print(f"[WordAssembler] Live speech set to: {enabled}")

    def _to_speakable(self, word: str) -> str:
        """
        Converts an assembled word into a pyttsx3-friendly speakable form.
        """
        lowered = word.strip().lower()

        if not lowered:
            return ""

        if lowered in PRONUNCIATION_MAP:
            phonetic = PRONUNCIATION_MAP[lowered]
            print(f"[WordAssembler] Pronunciation: '{lowered}' → '{phonetic}' (mapped)")
            return phonetic

        print(f"[WordAssembler] Pronunciation: '{lowered}' (no map, using as-is)")
        return lowered

    def _suggest_word(self, word: str) -> str:
        """
        Checks if the assembled letters form a real word.
        If not, returns the closest suggestion.
        If no suggestion found, returns the original letters.
        """
        lowered = word.lower()

        try:
            import enchant
            d = enchant.Dict("en_US")

            # Exact match — use as is
            if d.check(lowered):
                print(f"[WordAssembler] '{word}' is a valid word ✅")
                return word

            # Get suggestions
            suggestions = d.suggest(lowered)
            if suggestions:
                best = suggestions[0]
                print(f"[WordAssembler] '{word}' not found → suggested '{best}'")
                return best

        except Exception as e:
            print(f"[WordAssembler] Enchant unavailable: {e}")

        # No suggestion — return original
        return word

    def add_letter(self, letter: str):
        """
        Call this every time a gesture is recognized as a single letter.
        Resets the flush timer on each new letter.
        """
        letter = letter.strip().upper()
        if not letter:
            return

        with self._lock:
            if self._timer is not None:
                self._timer.cancel()

            self._letters.append(letter)
            print(f"[WordAssembler] Letter added: '{letter}' | Buffer: {self._letters}")

            self._timer = threading.Timer(self._timeout, self._flush)
            self._timer.daemon = True
            self._timer.start()

    def add_space(self):
        """
        Called on pause or no-gesture. Only flushes if letters exist
        and no timer is already running — prevents premature word breaks.
        """
        with self._lock:
            if not self._letters:
                return
            if self._timer is not None:
                return
        self._flush()

    def _flush(self):
        """
        Joins buffered letters into a word, runs word suggestion,
        pushes to speech_buffer, and speaks the result.
        Always speaks regardless of Live Speech toggle.
        """
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

            if not self._letters:
                return

            word = "".join(self._letters)
            self._letters.clear()

        # Run word suggestion
        final_word = self._suggest_word(word)

        # Push to buffer — UI displays the word
        speech_buffer.push(final_word)
        print(f"[WordAssembler] Pushed to buffer: '{final_word}'")

        if self._tts is not None:
            speakable = self._to_speakable(final_word.lower())
            print(f"[WordAssembler] Speaking: '{speakable}'")
            self._tts.speak(speakable)
        else:
            print("[WordAssembler] WARNING: TTS engine not injected!")

    def force_flush(self):
        """Immediately flush without waiting for timeout."""
        self._flush()

    def cancel(self):
        """Discard buffered letters without speaking — e.g. on clear/reset."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            self._letters.clear()


# Singleton — import this everywhere instead of instantiating directly
word_assembler = WordAssembler(timeout=4.0)