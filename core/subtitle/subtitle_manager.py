"""Subtitle lifecycle manager for utterance-based streaming ASR."""

from __future__ import annotations

import time

from core.events import SubtitleEvent, SubtitleEventType, UtteranceSegmentEvent, UtteranceSegmentEventType
from core.models import SubtitleLine, SubtitleStatus, TranscriptSegment
from core.subtitle.buffer import SubtitleBuffer


class SubtitleManager:
    """Maps utterance + transcript events to subtitle UI events."""

    def __init__(self, buffer: SubtitleBuffer | None = None) -> None:
        self._buffer = buffer or SubtitleBuffer()
        self._active_line_id: str | None = None
        self._last_text: dict[str, str] = {}

    @property
    def buffer(self) -> SubtitleBuffer:
        return self._buffer

    def on_utterance_event(self, event: UtteranceSegmentEvent) -> SubtitleEvent | None:
        if event.type == UtteranceSegmentEventType.START:
            self._active_line_id = event.utterance.id
            return None
        return None

    def on_transcript(self, segment: TranscriptSegment) -> SubtitleEvent | None:
        if not segment.text.strip() and not segment.is_final:
            return None

        utterance_id = segment.utterance_id or segment.id
        line_id = self._active_line_id or utterance_id
        text = segment.text.strip()
        status = SubtitleStatus.FINAL if segment.is_final else SubtitleStatus.PARTIAL

        if not segment.is_final and self._last_text.get(line_id) == text:
            return None

        self._last_text[line_id] = text
        line = SubtitleLine(
            id=line_id,
            source_text=text,
            translated_text=text,
            start_time=segment.start_time,
            end_time=segment.end_time,
            status=status,
        )

        if segment.is_final:
            self._active_line_id = None
            self._last_text.pop(line_id, None)

        existing = any(item.id == line_id for item in self._buffer.lines)
        event_type = SubtitleEventType.UPDATE if existing else SubtitleEventType.APPEND
        if existing:
            self._buffer.update(line_id, line)
        else:
            self._buffer.append(line)

        return SubtitleEvent(
            type=event_type,
            line=line,
            timestamp=time.monotonic(),
        )

    def clear(self) -> SubtitleEvent:
        self._buffer.clear()
        self._active_line_id = None
        self._last_text.clear()
        return SubtitleEvent(type=SubtitleEventType.CLEAR, timestamp=time.monotonic())
