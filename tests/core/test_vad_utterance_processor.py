"""Tests for VAD utterance processor."""

import numpy as np

from core.events import UtteranceSegmentEventType
from infrastructure.config import UtteranceConfig
from core.pipeline.vad_utterance_processor import VadUtteranceProcessor
from services.audio.utils import float32_to_pcm_bytes
from services.vad.energy_vad import EnergyVAD


def _tone_pcm(duration_sec: float = 0.5, *, amplitude: float = 0.5) -> bytes:
    samples = int(16000 * duration_sec)
    t = np.linspace(0, duration_sec, samples, endpoint=False, dtype=np.float32)
    tone = (amplitude * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    return float32_to_pcm_bytes(tone)


def test_vad_detects_speech_and_end():
    config = UtteranceConfig(
        vad_frame_ms=30,
        utterance_end_silence_ms=120,
        use_silero_vad=False,
        energy_threshold=0.01,
    )
    vad = EnergyVAD(sample_rate=16000, frame_ms=30, energy_threshold=0.01)
    processor = VadUtteranceProcessor(config, sample_rate=16000, vad=vad)

    events = []
    for _ in range(6):
        events.extend(processor.feed_pcm(_tone_pcm(0.1), timestamp=1.0))
    silence = float32_to_pcm_bytes(np.zeros(1600, dtype=np.float32))
    for _ in range(8):
        events.extend(processor.feed_pcm(silence, timestamp=2.0))

    starts = [e for e in events if e.type == UtteranceSegmentEventType.START]
    ends = [e for e in events if e.type == UtteranceSegmentEventType.END]
    assert len(starts) >= 1
    assert len(ends) >= 1
