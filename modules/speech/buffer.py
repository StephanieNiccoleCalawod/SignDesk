"""
buffer.py - Global Speech Buffer
Serves as the communication bridge between Gesture Translator and Speech Output.
"""

import threading

class GlobalSpeechBuffer:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GlobalSpeechBuffer, cls).__new__(cls)
                cls._instance._sentences = []
                cls._instance._buffer_lock = threading.Lock()
        return cls._instance

    def push(self, sentence: str):
        with self._buffer_lock:
            if sentence and sentence.strip():
                self._sentences.append(sentence.strip())

    def get_all(self) -> list[str]:
        with self._buffer_lock:
            return list(self._sentences)

    def pop(self) -> str | None:
        with self._buffer_lock:
            if self._sentences:
                return self._sentences.pop(0)
            return None

    def clear(self):
        with self._buffer_lock:
            self._sentences.clear()

speech_buffer = GlobalSpeechBuffer()
