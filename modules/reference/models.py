# modules/reference/models.py
"""
Data model representing a single ASL Reference Letter.
"""
from dataclasses import dataclass

@dataclass
class ASLReferenceLetter:
    letter: str
    image_path: str
    description: str
    tip: str
