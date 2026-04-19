"""
word_assembler.py - Letter-to-Word Assembly Layer
Sits between gesture recognition and GlobalSpeechBuffer.
Collects individual letter gestures and assembles them into words
using a timeout window before pushing to speech_buffer.
"""

import threading
import time
from modules.speech.buffer import speech_buffer


# ── Pronunciation Map ─────────────────────────────────────────────────────────
# Maps short/ambiguous strings that pyttsx3 spells out letter by letter.
# KEY   = what WordAssembler produces (lowercased assembled letters)
# VALUE = phonetic equivalent pyttsx3 can read as one word
#
# Expand this map whenever you discover a new mispronunciation.
# ─────────────────────────────────────────────────────────────────────────────

PRONUNCIATION_MAP = {

    # ── Single letters ────────────────────────────────────────────────────────
    # pyttsx3 reads isolated single chars as letter names, not sounds
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
    # Short strings that look like initials to pyttsx3
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
    "no": "no",    # sometimes read as abbreviation
}


class WordAssembler:
    """
    Collects single-letter gestures and assembles them into words.

    Flow:
        Gesture recognized → assembler.add_letter("C")
                           → assembler.add_letter("A")
                           → assembler.add_letter("T")
                           → [timeout expires]
                           → speech_buffer.push("CAT")
                           → tts speaks "CAT"
    """

    def __init__(self, timeout: float = 2.0):
        """
        Args:
            timeout: Seconds of inactivity before flushing letters as a word.
                     Default is 2.0s — adjust based on your gesture speed.
        """
        self._letters: list[str] = []
        self._timeout = timeout
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._tts = None          # injected at startup
        self._live_speech = False # toggled by UI button

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

        Logic:
          1. Lowercase the word
          2. Check PRONUNCIATION_MAP for a phonetic match
          3. If found  → return phonetic version  e.g. "RA" → "rah"
          4. If not    → return lowercased word    e.g. "CAT" → "cat"

        NOTE: This only affects what pyttsx3 receives.
              The original uppercase word is kept in speech_buffer for UI display.
        """
        lowered = word.strip().lower()

        if not lowered:
            return ""

        if lowered in PRONUNCIATION_MAP:
            phonetic = PRONUNCIATION_MAP[lowered]
            print(
                f"[WordAssembler] Pronunciation: "
                f"'{lowered}' → '{phonetic}' (mapped)"
            )
            return phonetic

        print(f"[WordAssembler] Pronunciation: '{lowered}' (no map, using as-is)")
        return lowered

    def add_letter(self, letter: str):
        """
        Call this every time a gesture is recognized as a single letter.
        Resets the flush timer on each new letter.

        Args:
            letter: A single character, e.g. "C", "A", "T"
        """
        letter = letter.strip().upper()
        if not letter:
            return

        with self._lock:
            # Cancel the existing timer since a new letter just arrived
            if self._timer is not None:
                self._timer.cancel()

            self._letters.append(letter)
            print(f"[WordAssembler] Letter added: '{letter}' | Buffer: {self._letters}")

            # Start a fresh timeout — flush when user pauses
            self._timer = threading.Timer(self._timeout, self._flush)
            self._timer.daemon = True
            self._timer.start()

    def add_space(self):
        """
        Call this when a deliberate space/pause gesture is detected.
        Immediately flushes the current word and adds a space marker
        so multi-word phrases work correctly.
        """
        self._flush()

    def _flush(self):
        """
        Joins buffered letters into a word and pushes to speech_buffer.
        Called automatically on timeout or manually via add_space().
        """
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

            if not self._letters:
                return

            word = "".join(self._letters)   # "C" + "A" + "T" → "CAT"
            self._letters.clear()

        # Push uppercase to buffer — UI displays "CAT"
        speech_buffer.push(word)
        print(f"[WordAssembler] Pushed to buffer: '{word}' (UI displays this)")

        if self._live_speech:
            if self._tts is not None:
                speakable = self._to_speakable(word)   # "cat"
                print(f"[WordAssembler] Speaking: '{speakable}'")
                self._tts.speak(speakable)             # reads as one word ✅
            else:
                print("[WordAssembler] WARNING: TTS engine not injected!")
        else:
            print("[WordAssembler] Live speech OFF → skipping TTS.")

    def force_flush(self):
        """
        Public method to immediately flush without waiting for timeout.
        Useful for a 'speak now' button in your UI.
        """
        self._flush()

    def cancel(self):
        """Discard buffered letters without speaking — e.g. on clear/reset."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            self._letters.clear()


# Singleton — import this everywhere instead of instantiating directly
word_assembler = WordAssembler(timeout=2.0)
