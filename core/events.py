"""Domain events emitted by the pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.models import SubtitleLine, Utterance


class SubtitleEventType(str, Enum):
    APPEND = "append"
    UPDATE = "update"
    CLEAR = "clear"


class PipelineState(str, Enum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class PipelineStage(str, Enum):
    AUDIO = "audio"
    ASR = "asr"
    TRANSLATION = "translation"


@dataclass(frozen=True, slots=True)
class SubtitleEvent:
    type: SubtitleEventType
    line: SubtitleLine | None = None
    timestamp: float = 0.0


@dataclass(frozen=True, slots=True)
class PipelineStateEvent:
    state: PipelineState
    message: str | None = None


@dataclass(frozen=True, slots=True)
class ErrorEvent:
    stage: PipelineStage
    error: Exception
    recoverable: bool = True


class UtteranceSegmentEventType(str, Enum):
    START = "start"
    END = "end"


@dataclass(frozen=True, slots=True)
class UtteranceSegmentEvent:
    type: UtteranceSegmentEventType
    utterance: Utterance
    timestamp: float = 0.0
