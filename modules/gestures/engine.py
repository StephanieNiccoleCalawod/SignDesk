"""
engine.py - Backward-Compatibility Shim
Maps to: SD003 (Gesture Recognition), SD004 (Confidence Indicator)

This module re-exports GestureRecognizer from the refactored
recognizer.py so that existing imports continue to work:

    from modules.gestures.engine import GestureRecognizer  # still works

The actual implementation now lives in:
    - modules/gestures/comparator.py  (landmark comparison)
    - modules/gestures/confidence.py  (threshold filtering + stability)
    - modules/gestures/recognizer.py  (orchestrator)
"""

# Re-export the refactored GestureRecognizer at its original import path
from modules.gestures.recognizer import GestureRecognizer  # noqa: F401

__all__ = ["GestureRecognizer"]
