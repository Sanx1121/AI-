"""Tests for StreamingPipelineOrchestrator with mocks."""

from __future__ import annotations

import asyncio

import numpy as np
import pytest

from core.events import SubtitleEventType, UtteranceSegmentEvent
from core.models import AudioChunk, TranscriptSegment
from core.pipeline.streaming_orchestrator import StreamingPipelineOrchestrator
from core.pipeline.vad_utterance_processor import VadUtteranceProcessor
from core.subtitle.subtitle_manager import SubtitleManager
from dataclasses import replace

from infrastructure.config import AppConfig, UtteranceConfig
from services.audio.utils import float32_to_pcm_bytes
from services.vad.energy_vad import EnergyVAD


class MockAudioSource:
    def __init__(self, chunks: list[AudioChunk]) -> None:
        self._chunks = chunks

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def stream_chunks(self):
        for chunk in self._chunks:
            yield chunk


class MockUtteranceTranscriber:
    def __init__(self) -> None:
        self.partial_calls = 0
        self.final_calls = 0

    async def warmup(self) -> None:
        pass

    async def transcribe_partial(self, ring, utterance_id, **kwargs) -> TranscriptSegment | None:
        self.partial_calls += 1
        return TranscriptSegment(
            text="partial text",
            start_time=0.0,
            end_time=1.0,
            is_final=False,
            utterance_id=utterance_id,
        )

    async def transcribe_final_from_ring(self, event: UtteranceSegmentEvent, ring) -> TranscriptSegment | None:
        self.final_calls += 1
        return TranscriptSegment(
            text="final text",
            start_time=0.0,
            end_time=2.0,
            is_final=True,
            utterance_id=event.utterance.id,
        )


def _tone_chunks() -> list[AudioChunk]:
    chunks = []
    for i in range(8):
        t = np.linspace(0, 0.25, 4000, endpoint=False, dtype=np.float32)
        tone = (0.4 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        chunks.append(
            AudioChunk(
                data=float32_to_pcm_bytes(tone),
                timestamp=i * 0.25,
                sample_rate=16000,
                channels=1,
            )
        )
    silence = float32_to_pcm_bytes(np.zeros(4000, dtype=np.float32))
    for j in range(8, 16):
        chunks.append(
            AudioChunk(
                data=silence,
                timestamp=j * 0.25,
                sample_rate=16000,
                channels=1,
            )
        )
    return chunks


@pytest.mark.asyncio
async def test_streaming_pipeline_emits_partial_and_final():
    events: list = []

    async def capture(event):
        events.append(event)

    config = UtteranceConfig(
        vad_frame_ms=30,
        utterance_end_silence_ms=300,
        partial_interval_ms=100,
        use_silero_vad=False,
        energy_threshold=0.01,
    )
    app_config = replace(AppConfig(), utterance=config)

    vad = EnergyVAD(sample_rate=16000, frame_ms=30, energy_threshold=0.01)
    processor = VadUtteranceProcessor(config, sample_rate=16000, vad=vad)
    transcriber = MockUtteranceTranscriber()

    orchestrator = StreamingPipelineOrchestrator(
        on_event=capture,
        config=app_config,
        audio_source=MockAudioSource(_tone_chunks()),
        vad_processor=processor,
        utterance_transcriber=transcriber,
        subtitle_manager=SubtitleManager(),
    )

    await orchestrator.start()
    await asyncio.sleep(0.8)
    await orchestrator.stop()

    subtitle_events = [e for e in events if hasattr(e, "type") and isinstance(e.type, SubtitleEventType)]
    assert transcriber.final_calls >= 1
    assert len(subtitle_events) >= 1
