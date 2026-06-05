"""Silero VAD wrapper (optional, requires torch)."""

from __future__ import annotations

import logging

import numpy as np

from services.audio.utils import pcm_bytes_to_float32

logger = logging.getLogger(__name__)


class SileroVAD:
    def __init__(
        self,
        *,
        sample_rate: int = 16000,
        frame_ms: int = 30,
        threshold: float = 0.45,
    ) -> None:
        self._sample_rate = sample_rate
        self._frame_bytes = int(sample_rate * frame_ms / 1000) * 2
        self._threshold = threshold
        self._leftover = b""
        self._model = None
        self._utils = None

    def reset(self) -> None:
        self._leftover = b""
        if self._model is not None:
            self._model.reset_states()

    @property
    def frame_bytes(self) -> int:
        return self._frame_bytes

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        import torch

        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            trust_repo=True,
        )
        self._model = model
        self._utils = utils

    def consume(self, pcm: bytes) -> list[bool]:
        self._leftover += pcm
        results: list[bool] = []
        while len(self._leftover) >= self._frame_bytes:
            frame = self._leftover[: self._frame_bytes]
            self._leftover = self._leftover[self._frame_bytes :]
            results.append(self.is_speech(frame))
        return results

    def is_speech(self, frame_pcm: bytes) -> bool:
        self._ensure_loaded()
        import torch

        samples = pcm_bytes_to_float32(frame_pcm)
        tensor = torch.from_numpy(samples)
        prob = self._model(tensor, self._sample_rate).item()
        return prob >= self._threshold
