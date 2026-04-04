"""
Tests for SentenceBuilder.
Maps to Sprint 6 SD005 requirements.
"""
import pytest
from modules.sentence.builder import SentenceBuilder

def test_initialization():
    sb = SentenceBuilder(timeout=2.0)
    assert sb.timeout == 2.0
    assert sb.get_current() == ""
    assert sb.should_finalize(10.0) is False

def test_sequential_accumulation():
    sb = SentenceBuilder(timeout=2.0)
    sb.add_gesture("A", 1.0)
    sb.add_gesture("B", 1.5)
    assert sb.get_current() == "AB"

def test_timeout_based_finalization():
    sb = SentenceBuilder(timeout=2.0)
    sb.add_gesture("H", 1.0)
    sb.add_gesture("E", 1.5)
    
    # At 2.0s: 2.0 - 1.5 = 0.5 < 2.0, so no finalization
    assert sb.should_finalize(2.0) is False
    
    # At 3.5s: 3.5 - 1.5 = 2.0 >= 2.0, so finalization
    assert sb.should_finalize(3.5) is True
    assert sb.finalize() == "HE"

def test_buffer_reset_after_finalization():
    sb = SentenceBuilder(timeout=2.0)
    sb.add_gesture("W", 1.0)
    assert sb.get_current() == "W"
    sb.reset()
    assert sb.get_current() == ""
    assert sb.should_finalize(5.0) is False

def test_no_finalization_if_buffer_empty():
    sb = SentenceBuilder(timeout=2.0)
    assert sb.should_finalize(100.0) is False
    assert sb.finalize() == ""

def test_multiple_sentences_in_sequence():
    sb = SentenceBuilder(timeout=2.0)
    
    # Sentence 1: "NO"
    sb.add_gesture("N", 1.0)
    sb.add_gesture("O", 1.5)
    assert sb.should_finalize(3.5) is True
    assert sb.finalize() == "NO"
    sb.reset()
    
    # Sentence 2: "YES"
    sb.add_gesture("Y", 4.0)
    sb.add_gesture("E", 4.2)
    sb.add_gesture("S", 4.6)
    
    assert sb.should_finalize(6.0) is False
    assert sb.should_finalize(7.0) is True
    assert sb.finalize() == "YES"
