"""
Unit tests for text output formatting, buffering, and mapping.
Maps to Sprint 5 SD005 T-007.
"""
import pytest
import time
from unittest.mock import patch
from modules.text.mapper import map_gesture_to_text
from modules.text.buffer import TextBuffer

# ──────────────────────────────────────────────────────────────
# Mapper Tests
# ──────────────────────────────────────────────────────────────

def test_mapper_valid_gesture():
    assert map_gesture_to_text("A") == "A"
    assert map_gesture_to_text("Z") == ""  # Z not in GESTURE_TO_TEXT by default

def test_mapper_unknown_or_none():
    assert map_gesture_to_text("UNKNOWN") == ""
    assert map_gesture_to_text(None) == ""

# ──────────────────────────────────────────────────────────────
# Buffer Append and Operations
# ──────────────────────────────────────────────────────────────

def test_buffer_append_single():
    buf = TextBuffer()
    assert buf.is_empty
    buf.append("A")
    assert buf.get() == "A"
    assert len(buf) == 1

def test_buffer_append_if_new_deduplication():
    buf = TextBuffer()
    assert buf.append_if_new("A") is True
    assert buf.append_if_new("A") is False  # duplicate
    assert buf.append_if_new("A") is False
    assert buf.get() == "A"
    # Even after debounce time, deduplication prevents same gesture
    with patch("time.monotonic", return_value=time.monotonic() + 1.0):
        assert buf.append_if_new("A") is False

def test_buffer_clear():
    buf = TextBuffer()
    buf.append("Hello")
    buf.clear()
    assert buf.get() == ""
    assert buf.is_empty

def test_sequence_building():
    buf = TextBuffer()
    with patch("time.monotonic", side_effect=[1.0, 2.0, 3.0]):
        buf.append_if_new("A")
        buf.append_if_new("B")
        buf.append_if_new("C")
    assert buf.get() == "ABC"

# ──────────────────────────────────────────────────────────────
# Debounce Tests
# ──────────────────────────────────────────────────────────────

def test_debounce_rapid_switching():
    buf = TextBuffer()
    # Simulate rapid switching A -> B -> A -> B within debounce window
    with patch("time.monotonic", side_effect=[1.0, 1.1, 1.2, 1.3]):
        assert buf.append_if_new("A") is True   # Appended at 1.0
        assert buf.append_if_new("B") is False  # 1.1 - 1.0 = 0.1 < 0.6
        assert buf.append_if_new("A") is False  # 1.2 - 1.0 = 0.2 < 0.6
        assert buf.append_if_new("B") is False  # 1.3 - 1.0 = 0.3 < 0.6
    assert buf.get() == "A"

def test_debounce_normal_pace():
    buf = TextBuffer()
    # Simulate normal pace > DEBOUNCE_SECONDS (0.6s)
    with patch("time.monotonic", side_effect=[1.0, 1.7, 2.4]):
        assert buf.append_if_new("A") is True   # Appended at 1.0
        assert buf.append_if_new("B") is True   # 1.7 - 1.0 = 0.7 >= 0.6
        assert buf.append_if_new("C") is True   # 2.4 - 1.7 = 0.7 >= 0.6
    assert buf.get() == "ABC"

# ──────────────────────────────────────────────────────────────
# Auto-space Tests
# ──────────────────────────────────────────────────────────────

def test_auto_space_pause_inserts_space():
    buf = TextBuffer()
    # At time 1.0, append A
    with patch("time.monotonic", return_value=1.0):
        buf.append_if_new("A")
    
    # At time 3.0 (2 seconds later, > SPACE_DELAY_SECONDS), loop calls maybe_insert_space
    with patch("time.monotonic", return_value=3.0):
        assert buf.maybe_insert_space() is True
    
    assert buf.get() == "A "

    # Now append B
    with patch("time.monotonic", return_value=3.5):
        buf.append_if_new("B")
    
    assert buf.get() == "A B"

def test_auto_space_no_double_spaces():
    buf = TextBuffer()
    with patch("time.monotonic", return_value=1.0):
        buf.append_if_new("A")
    
    with patch("time.monotonic", return_value=3.0):
        assert buf.maybe_insert_space() is True
        # Second call should return False since it already ends with space
        assert buf.maybe_insert_space() is False
    
    assert buf.get() == "A "

def test_auto_space_no_leading_space():
    buf = TextBuffer()
    assert buf.is_empty
    # Even if time advances, don't insert space on empty buffer
    with patch("time.monotonic", return_value=10.0):
        assert buf.maybe_insert_space() is False
    assert buf.get() == ""
