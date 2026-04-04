"""
tts.py - Text-to-Speech integration
Maps to: Sprint 6 SD005

Provides a non-blocking TTS engine to speak finalized sentences.
"""

import threading
import pyttsx3

class TTSEngine:
    def __init__(self):
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

    def _speak_worker(self, text: str):
        if not self._available:
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

    def speak(self, text: str):
        """
        Asynchronously speak the given text without blocking the main UI thread.
        """
        if not text or not text.strip():
            return
            
        thread = threading.Thread(target=self._speak_worker, args=(text,), daemon=True)
        thread.start()

# Provide a singleton instance for ease of use
tts_engine = TTSEngine()
