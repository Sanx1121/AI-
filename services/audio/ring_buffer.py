"""Fixed-capacity byte ring buffer for streaming audio."""

from __future__ import annotations


class RingBuffer:
    """Thread-unsafe ring buffer storing raw PCM bytes."""

    def __init__(self, capacity_bytes: int) -> None:
        self._capacity = max(capacity_bytes, 1)
        self._data = bytearray(self._capacity)
        self._write_pos = 0
        self._size = 0
        self._total_written = 0

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def size(self) -> int:
        return self._size

    @property
    def total_written(self) -> int:
        return self._total_written

    def write(self, pcm: bytes) -> None:
        if not pcm:
            return
        for byte in pcm:
            self._data[self._write_pos] = byte
            self._write_pos = (self._write_pos + 1) % self._capacity
            self._size = min(self._size + 1, self._capacity)
            self._total_written += 1

    def read_last(self, num_bytes: int) -> bytes:
        if num_bytes <= 0 or self._size == 0:
            return b""
        num_bytes = min(num_bytes, self._size)
        start = (self._write_pos - num_bytes) % self._capacity
        if start + num_bytes <= self._capacity:
            return bytes(self._data[start : start + num_bytes])
        first = self._capacity - start
        return bytes(self._data[start:]) + bytes(self._data[: num_bytes - first])

    def read_from_total_offset(self, total_offset: int, num_bytes: int) -> bytes:
        """Read bytes starting at absolute write offset (may be dropped if too old)."""
        if num_bytes <= 0:
            return b""
        oldest_kept = self._total_written - self._size
        if total_offset < oldest_kept:
            total_offset = oldest_kept
        end_total = min(total_offset + num_bytes, self._total_written)
        num_bytes = end_total - total_offset
        if num_bytes <= 0:
            return b""
        start_in_buffer = (self._write_pos - (self._total_written - total_offset)) % self._capacity
        return self._read_span(start_in_buffer, num_bytes)

    def clear(self) -> None:
        self._write_pos = 0
        self._size = 0

    def _read_span(self, start: int, length: int) -> bytes:
        if start + length <= self._capacity:
            return bytes(self._data[start : start + length])
        first = self._capacity - start
        return bytes(self._data[start:]) + bytes(self._data[: length - first])
