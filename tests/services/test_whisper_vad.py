"""Tests for Whisper VAD parameter mapping."""

from infrastructure.config import AsrConfig
from services.asr.whisper_service import build_whisper_vad_parameters


def test_build_whisper_vad_parameters():
    config = AsrConfig(
        vad_filter=True,
        whisper_vad_threshold=0.4,
        whisper_vad_min_silence_ms=600,
        whisper_vad_speech_pad_ms=250,
    )
    params = build_whisper_vad_parameters(config)
    assert params["threshold"] == 0.4
    assert params["min_silence_duration_ms"] == 600
    assert params["speech_pad_ms"] == 250
