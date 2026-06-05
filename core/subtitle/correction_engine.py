"""Correction engine interface — full implementation in a later phase."""

from __future__ import annotations

from typing import Protocol

from core.models import SubtitleLine, TranscriptSegment


class ICorrectionEngine(Protocol):
    def revise(
        self,
        history: list[SubtitleLine],
        new_segment: TranscriptSegment,
    ) -> list[SubtitleLine]: ...


class PassThroughCorrectionEngine:
    """MVP stub: returns empty list (no corrections)."""

    def revise(
        self,
        history: list[SubtitleLine],
        new_segment: TranscriptSegment,
    ) -> list[SubtitleLine]:
        return []
