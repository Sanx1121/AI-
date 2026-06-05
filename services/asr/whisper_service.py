"""Faster-Whisper ASR service."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from infrastructure.config import AsrConfig
from services.audio.utils import pcm_bytes_to_float32

logger = logging.getLogger(__name__)


def build_whisper_vad_parameters(config: AsrConfig) -> dict[str, float | int]:
    """Map app config to faster-whisper VadOptions-compatible dict."""
    return {
        "threshold": config.whisper_vad_threshold,
        "min_silence_duration_ms": config.whisper_vad_min_silence_ms,
        "speech_pad_ms": config.whisper_vad_speech_pad_ms,
    }


class WhisperASRService:
    """Loads Faster-Whisper and transcribes float32 mono audio."""

    def __init__(self, config: AsrConfig, executor=None) -> None:
        self._config = config
        self._executor = executor
        self._model: Any = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        if self._model is not None:
            return

        from faster_whisper import WhisperModel

        device, compute_type = self._resolve_device()
        logger.info(
            "Loading Faster-Whisper model=%s device=%s compute=%s vad_filter=%s",
            self._config.model_size,
            device,
            compute_type,
            self._config.vad_filter,
        )
        if self._config.vad_filter:
            logger.info(
                "Whisper VAD parameters: %s",
                build_whisper_vad_parameters(self._config),
            )
        self._model = WhisperModel(
            self._config.model_size,
            device=device,
            compute_type=compute_type,
        )
        logger.info("Faster-Whisper model ready")

    def transcribe_samples(
        self,
        samples: np.ndarray,
        *,
        sample_rate: int = 16000,
    ) -> str:
        self._ensure_loaded()
        audio = samples.astype(np.float32, copy=False).reshape(-1)
        if self._config.normalize_audio and audio.size:
            peak = float(np.max(np.abs(audio)))
            if peak > 1e-6:
                audio = (audio / peak).astype(np.float32)

        transcribe_kwargs: dict[str, Any] = {
            "language": self._config.language or None,
            "beam_size": 1,
            "best_of": 1,
            "temperature": 0.0,
            "vad_filter": self._config.vad_filter,
        }
        if self._config.vad_filter:
            transcribe_kwargs["vad_parameters"] = build_whisper_vad_parameters(
                self._config
            )

        segments, _info = self._model.transcribe(audio, **transcribe_kwargs)
        return " ".join(segment.text.strip() for segment in segments).strip()

    def transcribe_pcm(
        self,
        pcm: bytes,
        *,
        sample_rate: int = 16000,
    ) -> str:
        samples = pcm_bytes_to_float32(pcm)
        return self.transcribe_samples(samples, sample_rate=sample_rate)

    def _resolve_device(self) -> tuple[str, str]:
        device = self._config.device
        compute_type = self._config.compute_type
        if device != "auto":
            return device, compute_type

        try:
            import ctranslate2

            if ctranslate2.get_cuda_device_count() > 0:
                return "cuda", "float16" if compute_type == "default" else compute_type
        except Exception:
            pass
        return "cpu", "int8" if compute_type == "default" else compute_type

    def _ensure_loaded(self) -> None:
        if self._model is None:
            self.load()
