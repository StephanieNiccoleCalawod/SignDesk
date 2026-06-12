# modules/reference/repository.py

import os
from .models import ASLReferenceLetter
from .constants import LETTER_METADATA

# Resolve the absolute project root directory
# modules/reference/repository.py is nested two folders deep under the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _get_image_path(letter: str) -> str:
    """Returns the absolute path to the local ASL reference image for a given letter."""
    return os.path.normpath(
        os.path.join(PROJECT_ROOT, "assets", "reference", f"Sign_Language_{letter}.jpg")
    )

def get_all_letters() -> list[ASLReferenceLetter]:
    """
    Retrieve details for all 26 letters of the ASL manual alphabet
    sorted in alphabetical order.
    """
    letters = []
    for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        meta = LETTER_METADATA[char]
        letters.append(ASLReferenceLetter(
            letter=char,
            image_path=_get_image_path(char),
            description=meta["description"],
            tip=meta["tip"]
        ))
    return letters

def get_letter(letter: str) -> ASLReferenceLetter | None:
    """
    Retrieve details for a single ASL letter. Returns None if the letter is invalid.
    """
    letter_clean = letter.upper().strip()
    if len(letter_clean) != 1 or letter_clean not in LETTER_METADATA:
        return None
        
    meta = LETTER_METADATA[letter_clean]
    return ASLReferenceLetter(
        letter=letter_clean,
        image_path=_get_image_path(letter_clean),
        description=meta["description"],
        tip=meta["tip"]
    )

def search_letters(query: str) -> list[ASLReferenceLetter]:
    """
    Search for letters matching the query in their character name, description, or tip.
    Search is case-insensitive. Returns all letters if query is empty.
    """
    if not query:
        return get_all_letters()
        
    query_lower = query.lower().strip()
    results = []
    for letter_obj in get_all_letters():
        if (query_lower in letter_obj.letter.lower() or 
            query_lower in letter_obj.description.lower() or 
            query_lower in letter_obj.tip.lower()):
            results.append(letter_obj)
    return results
