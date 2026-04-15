"""
config.py - Global Configuration Singleton
Manages global session states for modules like Webcam and TTS with JSON persistence.
"""

import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

class Config:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._init_defaults()
        return cls._instance
        
    def _init_defaults(self):
        self.webcam_enabled = True
        self.tts_enabled = True

    def load(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    data = json.load(f)
                    self.webcam_enabled = data.get("webcam_enabled", True)
                    self.tts_enabled = data.get("tts_enabled", True)
            except Exception as e:
                print(f"Error loading config.json: {e}")

    def save(self):
        data = {
            "webcam_enabled": self.webcam_enabled,
            "tts_enabled": self.tts_enabled
        }
        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving config.json: {e}")

config = Config()
