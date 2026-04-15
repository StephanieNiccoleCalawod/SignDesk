"""
tts.py - Text-to-Speech integration
Maps to: Sprint 6 SD005

Provides a non-blocking TTS engine to speak finalized sentences.
"""

import threading
import pyttsx3

class TTSEngine:
    def __init__(self, on_error=None):
        self._available = False
        self.on_error = on_error
        self._init_engine()
        
    def _init_engine(self):
        try:
            # We initialize locally within the thread to avoid COM/thread dispatch issues on Windows
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)
            self._available = True
        except Exception as e:
            print(f"TTS initialization failed: {e}")
            self._available = False
            if self.on_error:
                self.on_error("Audio output device not detected. Please connect a speaker or audio device.")

    def _speak_worker(self, text: str):
        from core.config import config
        if not config.tts_enabled:
            return

        if not self._available:
            if self.on_error:
                self.on_error("Audio output device not detected. Please connect a speaker or audio device.")
            return
            
        try:
            # Re-initialize engine in thread to be safe with pyttsx3
            # pyttsx3's runAndWait MUST be called in the same thread it was initialized
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)
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
            
        thread = threading.Thread(target=self._speak_worker, args=(text,), daemon=True)
        thread.start()
