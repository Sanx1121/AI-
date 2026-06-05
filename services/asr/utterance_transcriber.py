"""Utterance-level Whisper transcriber with partial/final tracks."""

from __future__ import annotations

import asyncio
import logging
import time

from core.events import UtteranceSegmentEvent
from core.models import TranscriptSegment
from infrastructure.config import AsrConfig, UtteranceConfig
from services.asr.partial_merge import merge_partial_text
from services.asr.whisper_service import WhisperASRService
from services.audio.ring_buffer import RingBuffer

logger = logging.getLogger(__name__)


def partial_read_window(
    *,
    total_written: int,
    audio_start_offset: int,
    sample_rate: int,
    partial_window_sec: float,
    min_partial_sec: float,
) -> tuple[int, int] | None:
    """Growing partial window from utterance start, capped at partial_window_sec."""
    min_bytes = int(min_partial_sec * sample_rate * 2)
    max_window_bytes = int(partial_window_sec * sample_rate * 2)
    total_span = total_written - audio_start_offset
    if total_span < min_bytes:
        return None

    read_len = min(total_span, max_window_bytes)
    read_offset = total_written - read_len
    return read_offset, read_len


class UtteranceTranscriber:
    """VAD + partial loop ASR using Faster-Whisper on ring-buffer windows."""

    def __init__(
        self,
        whisper: WhisperASRService,
        asr_config: AsrConfig,
        utterance_config: UtteranceConfig,
        *,
        sample_rate: int = 16000,
        executor=None,
    ) -> None:
        self._whisper = whisper
        self._asr_config = asr_config
        self._config = utterance_config
        self._sample_rate = sample_rate
        self._executor = executor
        self._last_text: dict[str, str] = {}

    async def warmup(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._whisper.load)

    async def transcribe_partial(
        self,
        ring: RingBuffer,
        utterance_id: str,
        *,
        audio_start_offset: int = 0,
        start_time: float = 0.0,
    ) -> TranscriptSegment | None:
        window = partial_read_window(
            total_written=ring.total_written,
            audio_start_offset=audio_start_offset,
            sample_rate=self._sample_rate,
            partial_window_sec=self._config.partial_window_sec,
            min_partial_sec=self._config.min_partial_sec,
        )
        if window is None:
            return None

        read_offset, read_len = window
        pcm = ring.read_from_total_offset(read_offset, read_len)
        if not pcm:
            return None

        text = await asyncio.get_running_loop().run_in_executor(
            self._executor,
            self._whisper.transcribe_pcm,
            pcm,
        )
        text = merge_partial_text(self._last_text.get(utterance_id, ""), text)
        if not text or text == self._last_text.get(utterance_id):
            return None

        self._last_text[utterance_id] = text
        logger.info("ASR partial (whisper): %s", text)
        return TranscriptSegment(
            text=text,
            start_time=start_time,
            end_time=time.monotonic(),
            is_final=False,
            utterance_id=utterance_id,
        )

    async def transcribe_final(
        self,
        event: UtteranceSegmentEvent,
    ) -> TranscriptSegment | None:
        utterance = event.utterance
        utterance_id = utterance.id
        previous = self._last_text.get(utterance_id, "")

        end_time = utterance.end_time or event.timestamp
        start_time = utterance.start_time
        self._last_text.pop(utterance_id, None)

        if previous:
            logger.info("ASR final (whisper): %s", previous)
            return TranscriptSegment(
                text=previous,
                start_time=start_time,
                end_time=end_time,
                is_final=True,
                utterance_id=utterance_id,
            )
        return None

    async def transcribe_final_from_ring(
        self,
        event: UtteranceSegmentEvent,
        ring: RingBuffer,
    ) -> TranscriptSegment | None:
        """Full utterance decode for higher final accuracy."""
        utterance = event.utterance
        utterance_id = utterance.id
        span = ring.total_written - utterance.audio_start_offset
        if span <= 0:
            return await self.transcribe_final(event)

        pcm = ring.read_from_total_offset(utterance.audio_start_offset, span)
        text = await asyncio.get_running_loop().run_in_executor(
            self._executor,
            self._whisper.transcribe_pcm,
            pcm,
        )
        self._last_text.pop(utterance_id, None)
        if not text:
            return None

        logger.info("ASR final (whisper): %s", text)
        return TranscriptSegment(
            text=text,
            start_time=utterance.start_time,
            end_time=utterance.end_time or event.timestamp,
            is_final=True,
            utterance_id=utterance_id,
        )
