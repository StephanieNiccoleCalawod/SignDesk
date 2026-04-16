"""
tts.py - Text-to-Speech integration
Maps to: Sprint 6 SD005

Provides a non-blocking TTS engine to speak finalized sentences.
Supports male/female voice selection, rate, and volume from config.
"""

import threading
import pyttsx3


def get_available_voices() -> list[dict]:
    """
    Returns available system voices as a list of dicts:
      { "id": str, "name": str, "gender": str }

    Gender is inferred from the voice name since pyttsx3 does not
    expose a reliable gender field on all platforms.
    """
    try:
        engine = pyttsx3.init()
        raw = engine.getProperty("voices")
        engine.stop()

        result = []
        for v in raw:
            name_lower = v.name.lower()
            if any(w in name_lower for w in ("zira", "female", "woman", "hazel", "susan", "eva")):
                gender = "female"
            elif any(w in name_lower for w in ("david", "male", "man", "george", "mark", "james")):
                gender = "male"
            else:
                gender = "unknown"
            result.append({"id": v.id, "name": v.name, "gender": gender})
        return result
    except Exception:
        return []


def _resolve_voice_id(engine, preference: str) -> str | None:
    """
    Given a preference string ("default", "female", "male"),
    returns the best matching voice id or None to keep the default.
    """
    if preference == "default":
        return None

    voices = engine.getProperty("voices")
    female_keywords = ("zira", "female", "woman", "hazel", "susan", "eva")
    male_keywords   = ("david", "male", "man", "george", "mark", "james")

    keywords = female_keywords if preference == "female" else male_keywords

    for v in voices:
        if any(kw in v.name.lower() for kw in keywords):
            return v.id

    # Fallback: if looking for female pick any non-first voice; for male pick first
    if voices:
        return voices[1].id if preference == "female" and len(voices) > 1 else voices[0].id

    return None


class TTSEngine:
    def __init__(self, on_error=None):
        self._available = False
        self.on_error = on_error
        self._init_engine()

    def _init_engine(self):
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 150)
            self._available = True
        except Exception as e:
            print(f"TTS initialization failed: {e}")
            self._available = False
            if self.on_error:
                self.on_error(
                    "Audio output device not detected. "
                    "Please connect a speaker or audio device."
                )

    def _speak_worker(self, text: str):
        from core.config import config

        if not config.tts_enabled:
            return

        if not self._available:
            if self.on_error:
                self.on_error(
                    "Audio output device not detected. "
                    "Please connect a speaker or audio device."
                )
            return

        try:
            # Re-initialize in thread — required by pyttsx3 on Windows (COM threading)
            engine = pyttsx3.init()

            # ── Rate ──────────────────────────────────────────
            # config stores a multiplier (0.5 – 2.0); base rate is 150 wpm
            rate_mult = config.get("speech.rate", 1.0)
            engine.setProperty("rate", int(150 * rate_mult))

            # ── Volume ────────────────────────────────────────
            # config stores 0 – 100; pyttsx3 expects 0.0 – 1.0
            volume = config.get("speech.volume", 80)
            engine.setProperty("volume", volume / 100.0)

            # ── Voice ─────────────────────────────────────────
            # config stores "default" | "female" | "male"
            preference = config.get("speech.voice", "default")
            voice_id = _resolve_voice_id(engine, preference)
            if voice_id:
                engine.setProperty("voice", voice_id)

            engine.say(text)
            engine.runAndWait()

        except Exception as e:
            print(f"TTS speak failed: {e}")
            if self.on_error:
                self.on_error("Text-to-Speech engine failed to generate audio output.")

    def speak(self, text: str):
        """
        Asynchronously speak the given text without blocking the main UI thread.
        """
        if not text or not text.strip():
            if self.on_error:
                self.on_error("No text available for speech conversion.")
            return

        thread = threading.Thread(
            target=self._speak_worker, args=(text,), daemon=True
        )
        thread.start()
