"""VAD-driven utterance segmentation with ring-buffered audio."""

from __future__ import annotations

import time
from uuid import uuid4

from core.events import UtteranceSegmentEvent, UtteranceSegmentEventType
from core.interfaces.vad import IVAD
from core.models import Utterance
from infrastructure.config import UtteranceConfig
from services.audio.ring_buffer import RingBuffer


class VadUtteranceProcessor:
    """Feed PCM chunks; emit utterance START/END events."""

    def __init__(
        self,
        config: UtteranceConfig,
        *,
        sample_rate: int = 16000,
        vad: IVAD,
    ) -> None:
        self._config = config
        self._sample_rate = sample_rate
        self._vad = vad
        capacity = int(config.ring_buffer_sec * sample_rate * 2)
        self._ring = RingBuffer(capacity)
        self._active: Utterance | None = None
        self._speech_frames = 0
        self._silence_frames = 0
        self._frame_ms = config.vad_frame_ms
        self._frames_for_end = max(
            1, int(config.utterance_end_silence_ms / config.vad_frame_ms)
        )
        self._max_frames = max(
            1, int(config.max_utterance_sec * 1000 / config.vad_frame_ms)
        )

    @property
    def ring_buffer(self) -> RingBuffer:
        return self._ring

    def reset(self) -> None:
        self._ring.clear()
        self._active = None
        self._speech_frames = 0
        self._silence_frames = 0
        if hasattr(self._vad, "reset"):
            self._vad.reset()

    def feed_pcm(self, pcm: bytes, *, timestamp: float) -> list[UtteranceSegmentEvent]:
        self._ring.write(pcm)
        events: list[UtteranceSegmentEvent] = []
        flags = self._consume_vad(pcm)
        for is_speech in flags:
            events.extend(self._handle_frame(is_speech, timestamp))
        return events

    def flush(self, *, timestamp: float | None = None) -> list[UtteranceSegmentEvent]:
        ts = timestamp if timestamp is not None else time.monotonic()
        events: list[UtteranceSegmentEvent] = []
        if self._active is not None:
            events.append(self._end_utterance(ts))
        return events

    def _consume_vad(self, pcm: bytes) -> list[bool]:
        if hasattr(self._vad, "consume"):
            return self._vad.consume(pcm)
        frame_bytes = int(self._sample_rate * self._frame_ms / 1000) * 2
        results: list[bool] = []
        offset = 0
        while offset + frame_bytes <= len(pcm):
            frame = pcm[offset : offset + frame_bytes]
            results.append(self._vad.is_speech(frame))
            offset += frame_bytes
        return results

    def _handle_frame(
        self,
        is_speech: bool,
        timestamp: float,
    ) -> list[UtteranceSegmentEvent]:
        events: list[UtteranceSegmentEvent] = []
        if is_speech:
            self._silence_frames = 0
            self._speech_frames += 1
            if self._active is None:
                pad_bytes = int(
                    self._config.speech_pad_ms / 1000 * self._sample_rate * 2
                )
                start_offset = max(0, self._ring.total_written - pad_bytes)
                self._active = Utterance(
                    id=uuid4().hex,
                    start_time=timestamp,
                    audio_start_offset=start_offset,
                )
                events.append(
                    UtteranceSegmentEvent(
                        type=UtteranceSegmentEventType.START,
                        utterance=self._active,
                        timestamp=timestamp,
                    )
                )
            elif self._speech_frames >= self._max_frames:
                events.append(self._end_utterance(timestamp))
        elif self._active is not None:
            self._silence_frames += 1
            if self._silence_frames >= self._frames_for_end:
                events.append(self._end_utterance(timestamp))
        return events

    def _end_utterance(self, timestamp: float) -> UtteranceSegmentEvent:
        assert self._active is not None
        utterance = Utterance(
            id=self._active.id,
            start_time=self._active.start_time,
            end_time=timestamp,
            audio_start_offset=self._active.audio_start_offset,
        )
        self._active = None
        self._speech_frames = 0
        self._silence_frames = 0
        return UtteranceSegmentEvent(
            type=UtteranceSegmentEventType.END,
            utterance=utterance,
            timestamp=timestamp,
        )
