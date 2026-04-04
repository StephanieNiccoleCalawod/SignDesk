"""
mapper.py - Gesture-to-Text Mapper
Maps to: Sprint 5 T-001

Converts recognized gesture labels into human-readable text characters.
Extensible design for future word/phrase mappings.
"""

# ──────────────────────────────────────────────────────────────
# GESTURE → TEXT MAPPING
# ──────────────────────────────────────────────────────────────
# Maps each ASL gesture label to its text output character.
# J and Z are excluded (motion-required, not supported in
# single-frame recognition).

GESTURE_TO_TEXT = {
    "A": "A",
    "B": "B",
    "C": "C",
    "D": "D",
    "E": "E",
    "F": "F",
    "G": "G",
    "H": "H",
    "I": "I",
    "K": "K",
    "L": "L",
    "M": "M",
    "N": "N",
    "O": "O",
    "P": "P",
    "Q": "Q",
    "R": "R",
    "S": "S",
    "T": "T",
    "U": "U",
    "V": "V",
    "W": "W",
    "X": "X",
    "Y": "Y",
}


def map_gesture_to_text(gesture: str | None) -> str:
    """
    Convert a gesture label to its corresponding text character.

    Args:
        gesture: Gesture name from the recognizer (e.g. "A", "B").
                 May be None if no gesture is recognized.

    Returns:
        The mapped text character, or empty string if the gesture
        is unknown or None.
    """
    if gesture is None:
        return ""
    return GESTURE_TO_TEXT.get(gesture, "")
