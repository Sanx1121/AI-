"""Tests for RingBuffer."""

from services.audio.ring_buffer import RingBuffer


def test_write_and_read_last():
    ring = RingBuffer(100)
    ring.write(b"abcd")
    assert ring.read_last(4) == b"abcd"


def test_read_from_total_offset():
    ring = RingBuffer(100)
    ring.write(b"abcdef")
    offset = ring.total_written - 4
    assert ring.read_from_total_offset(offset, 4) == b"cdef"
