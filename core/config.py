"""
config.py - Global Configuration Singleton
Manages global session states for modules like Webcam and TTS with JSON persistence.
All settings are stored in a flat dict and serialised to config.json.
"""

import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

# ── Default settings matching the React reference ────────────
DEFAULT_SETTINGS = {
    # Appearance
    "appearance.theme": "system",
    "appearance.font_size": "medium",
    "appearance.show_landmark_overlay": True,

    # Gesture Recognition
    "gesture.confidence_threshold": 70,
    "gesture.timeout": 2.0,
    "gesture.show_confidence_indicator": True,

    # Speech Output
    "speech.tts_enabled": True,
    "speech.voice": "default",
    "speech.rate": 1.0,
    "speech.volume": 80,

    # Privacy & Data
    "privacy.gesture_history_log": False,
    "privacy.local_only_processing": True,

    # Accessibility
    "accessibility.screen_reader_support": True,

    # Webcam
    "webcam.auto_start_on_launch": True,
    "webcam.camera_source": "builtin",
    "webcam.resolution": "720p",
}


class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._data = dict(DEFAULT_SETTINGS)
        return cls._instance

    # ── Public access ─────────────────────────────────────
    def get(self, key: str, default=None):
        """Retrieve a setting value by dotted key."""
        return self._data.get(key, default if default is not None else DEFAULT_SETTINGS.get(key))

    def set(self, key: str, value):
        """Update a setting value (call save() to persist)."""
        self._data[key] = value

    # ── Legacy properties (backward compat) ──────────────
    @property
    def webcam_enabled(self):
        return self.get("webcam.auto_start_on_launch", True)

    @webcam_enabled.setter
    def webcam_enabled(self, value: bool):
        self.set("webcam.auto_start_on_launch", value)

    @property
    def tts_enabled(self):
        return self.get("speech.tts_enabled", True)

    @tts_enabled.setter
    def tts_enabled(self, value: bool):
        self.set("speech.tts_enabled", value)

    # ── Persistence ──────────────────────────────────────
    def load(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    saved = json.load(f)

                # Migrate legacy flat keys if present
                if "webcam_enabled" in saved and "webcam.auto_start_on_launch" not in saved:
                    saved["webcam.auto_start_on_launch"] = saved.pop("webcam_enabled")
                if "tts_enabled" in saved and "speech.tts_enabled" not in saved:
                    saved["speech.tts_enabled"] = saved.pop("tts_enabled")

                # Merge saved values on top of defaults
                for key in DEFAULT_SETTINGS:
                    if key in saved:
                        self._data[key] = saved[key]
            except Exception as e:
                print(f"Error loading config.json: {e}")

    def save(self):
        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump(self._data, f, indent=4)
        except Exception as e:
            print(f"Error saving config.json: {e}")

    def reset_all(self):
        """Restore every setting to its default value."""
        self._data = dict(DEFAULT_SETTINGS)

    def as_dict(self) -> dict:
        """Return a copy of all current settings."""
        return dict(self._data)


config = Config()
