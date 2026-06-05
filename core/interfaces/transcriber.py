"""ASR transcriber interface."""

from __future__ import annotations

from typing import Protocol

from core.models import AudioChunk, TranscriptSegment


class ITranscriber(Protocol):
    async def transcribe(self, chunk: AudioChunk) -> TranscriptSegment: ...
