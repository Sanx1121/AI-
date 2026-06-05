"""Energy-threshold VAD fallback."""

from __future__ import annotations

import numpy as np

from services.audio.utils import pcm_bytes_to_float32


class EnergyVAD:
    def __init__(
        self,
        *,
        sample_rate: int = 16000,
        frame_ms: int = 30,
        energy_threshold: float = 0.015,
    ) -> None:
        self._frame_bytes = int(sample_rate * frame_ms / 1000) * 2
        self._energy_threshold = energy_threshold
        self._leftover = b""

    def reset(self) -> None:
        self._leftover = b""

    @property
    def frame_bytes(self) -> int:
        return self._frame_bytes

    def consume(self, pcm: bytes) -> list[bool]:
        self._leftover += pcm
        results: list[bool] = []
        while len(self._leftover) >= self._frame_bytes:
            frame = self._leftover[: self._frame_bytes]
            self._leftover = self._leftover[self._frame_bytes :]
            results.append(self.is_speech(frame))
        return results

    def is_speech(self, frame_pcm: bytes) -> bool:
        samples = pcm_bytes_to_float32(frame_pcm)
        energy = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
        return energy >= self._energy_threshold
