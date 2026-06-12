# test_reference_repo.py
import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from modules.reference.repository import get_all_letters, get_letter, search_letters

def test_repository():
    # 1. Test get_all_letters
    all_letters = get_all_letters()
    print(f"Total letters: {len(all_letters)}")
    assert len(all_letters) == 26, f"Expected 26 letters, got {len(all_letters)}"
    print("First letter details:", all_letters[0])
    print("Last letter details:", all_letters[-1])

    # 2. Test get_letter
    a_letter = get_letter("A")
    print("Get letter 'A':", a_letter)
    assert a_letter is not None
    assert a_letter.letter == "A"
    print(f"Image path: {a_letter.image_path}")
    print(f"Image path exists for 'A': {os.path.exists(a_letter.image_path)}")
    assert os.path.exists(a_letter.image_path), f"Image path does not exist: {a_letter.image_path}"

    # 3. Test search_letters
    ok_gesture_search = search_letters("OK")
    print(f"Search 'OK': {[l.letter for l in ok_gesture_search]}")
    assert "F" in [l.letter for l in ok_gesture_search], "Expected 'F' to show in 'OK' tip search"

    print("All tests passed successfully!")

if __name__ == "__main__":
    test_repository()
