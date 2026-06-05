"""Domain data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4


class SubtitleStatus(str, Enum):
    PARTIAL = "partial"
    FINAL = "final"
    CORRECTED = "corrected"


@dataclass(frozen=True, slots=True)
class AudioChunk:
    data: bytes
    timestamp: float
    sample_rate: int = 16000
    channels: int = 1


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    text: str
    start_time: float
    end_time: float
    is_final: bool = True
    confidence: float = 1.0
    id: str = field(default_factory=lambda: uuid4().hex)


@dataclass(frozen=True, slots=True)
class SubtitleLine:
    source_text: str
    translated_text: str
    start_time: float
    end_time: float
    status: SubtitleStatus = SubtitleStatus.FINAL
    id: str = field(default_factory=lambda: uuid4().hex)
