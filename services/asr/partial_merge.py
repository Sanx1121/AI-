"""Merge streaming partial transcripts to reduce flicker."""

from __future__ import annotations


def merge_partial_text(previous: str, current: str) -> str:
    """Prefer stable prefix; accept natural extensions from the ASR."""
    previous = previous.strip()
    current = current.strip()
    if not current:
        return previous
    if not previous:
        return current
    if current == previous:
        return current
    if current.startswith(previous):
        return current
    if previous.startswith(current):
        return previous

    prev_words = previous.split()
    curr_words = current.split()
    if not prev_words or not curr_words:
        return current

    max_overlap = min(len(prev_words), len(curr_words))
    for size in range(max_overlap, 0, -1):
        if prev_words[-size:] == curr_words[:size]:
            merged = prev_words + curr_words[size:]
            return " ".join(merged)

    return current
