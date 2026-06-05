"""Tests for growing partial read window."""

from services.asr.utterance_transcriber import partial_read_window


def test_growing_window_from_utterance_start():
    sr = 16000
    start = 1000
    # 0.5s into utterance -> read from start, 0.5s
    result = partial_read_window(
        total_written=start + int(0.5 * sr * 2),
        audio_start_offset=start,
        sample_rate=sr,
        partial_window_sec=3.0,
        min_partial_sec=0.25,
    )
    assert result == (start, int(0.5 * sr * 2))


def test_window_caps_at_partial_window_sec():
    sr = 16000
    start = 0
    total = int(5.0 * sr * 2)
    max_bytes = int(3.0 * sr * 2)
    result = partial_read_window(
        total_written=total,
        audio_start_offset=start,
        sample_rate=sr,
        partial_window_sec=3.0,
        min_partial_sec=0.25,
    )
    assert result == (total - max_bytes, max_bytes)


def test_too_short_returns_none():
    assert (
        partial_read_window(
            total_written=1000,
            audio_start_offset=900,
            sample_rate=16000,
            partial_window_sec=3.0,
            min_partial_sec=0.25,
        )
        is None
    )
