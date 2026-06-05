"""PCM / float32 audio utilities."""

from __future__ import annotations

import numpy as np


def pcm_bytes_to_float32(pcm: bytes, *, channels: int = 1) -> np.ndarray:
    """Convert 16-bit PCM bytes to mono float32 in [-1, 1]."""
    samples = np.frombuffer(pcm, dtype=np.int16)
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1).astype(np.int16)
    return (samples.astype(np.float32) / 32768.0).clip(-1.0, 1.0)


def float32_to_pcm_bytes(samples: np.ndarray, *, channels: int = 1) -> bytes:
    """Convert float32 samples to 16-bit PCM bytes."""
    clipped = np.clip(samples, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype(np.int16)
    return pcm.tobytes()


def compute_rms(samples: np.ndarray) -> float:
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))


def resample_linear(
    samples: np.ndarray,
    *,
    source_rate: int,
    target_rate: int,
) -> np.ndarray:
    if source_rate == target_rate or samples.size == 0:
        return samples.astype(np.float32, copy=False)
    duration = samples.size / source_rate
    target_length = max(1, int(round(duration * target_rate)))
    source_times = np.linspace(0.0, duration, num=samples.size, endpoint=False)
    target_times = np.linspace(0.0, duration, num=target_length, endpoint=False)
    return np.interp(target_times, source_times, samples).astype(np.float32)
