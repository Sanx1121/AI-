"""Tests for partial transcript merge."""

from services.asr.partial_merge import merge_partial_text


def test_merge_extends_text():
    assert merge_partial_text("hello", "hello world") == "hello world"


def test_merge_keeps_longer_stable_prefix():
    assert merge_partial_text("hello world", "hello") == "hello world"


def test_merge_overlapping_words():
    result = merge_partial_text("hello beautiful", "beautiful day")
    assert result == "hello beautiful day"
