"""Windows WASAPI loopback audio capture via PyAudioWPatch."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

import numpy as np

from core.models import AudioChunk
from infrastructure.config import AudioConfig
from services.audio.utils import compute_rms, float32_to_pcm_bytes, resample_linear

logger = logging.getLogger(__name__)


def _import_pyaudiowpatch():
    try:
        import pyaudiowpatch as pyaudio
    except ImportError as exc:
        raise RuntimeError(
            "pyaudiowpatch is required for system audio capture. "
            "Install with: pip install pyaudiowpatch"
        ) from exc
    if not hasattr(pyaudio.PyAudio, "get_default_wasapi_loopback"):
        raise RuntimeError(
            "Plain pyaudio is installed instead of pyaudiowpatch. "
            "Run: pip uninstall pyaudio && pip install pyaudiowpatch"
        )
    return pyaudio


class SystemAudioCapture:
    """Capture system playback via WASAPI loopback (Windows)."""

    def __init__(self, config: AudioConfig) -> None:
        self._config = config
        self._queue: asyncio.Queue[AudioChunk | None] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._pyaudio_module: Any = None
        self._pyaudio: Any = None
        self._stream: Any = None
        self._chunk_index = 0
        self._silent_warnings = 0
        self._native_rate = 48000
        self._channels = 2

    async def start(self) -> None:
        pyaudio = _import_pyaudiowpatch()
        self._pyaudio_module = pyaudio
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue(maxsize=64)
        self._pyaudio = pyaudio.PyAudio()

        device = self._resolve_loopback_device(self._pyaudio)
        self._native_rate = int(device["defaultSampleRate"])
        self._channels = int(device["maxInputChannels"])
        frames_per_buffer = max(
            1, int(self._native_rate * self._config.feed_chunk_sec)
        )

        logger.info(
            "Audio capture started: %d Hz, %d ch → %d Hz mono (device: %s)",
            self._native_rate,
            self._channels,
            self._config.sample_rate,
            device["name"],
        )

        def callback(in_data, frame_count, time_info, status) -> tuple[Any, int]:
            if status:
                logger.debug("Audio stream status: %s", status)
            if self._loop is None or self._queue is None:
                return (None, pyaudio.paContinue)

            samples = np.frombuffer(in_data, dtype=np.float32)
            if self._channels > 1:
                samples = samples.reshape(-1, self._channels).mean(axis=1)
            resampled = resample_linear(
                samples.astype(np.float32),
                source_rate=self._native_rate,
                target_rate=self._config.sample_rate,
            )
            rms = compute_rms(resampled)
            self._chunk_index += 1
            if rms < self._config.silence_rms_threshold and self._chunk_index <= 10:
                self._silent_warnings += 1
                if self._silent_warnings <= 3:
                    logger.warning(
                        "Audio chunk #%d appears silent (rms=%.5f). "
                        "Set audio.loopback_device in config.",
                        self._chunk_index,
                        rms,
                    )
            elif self._chunk_index % 10 == 0:
                logger.info("Audio chunk #%d rms=%.5f", self._chunk_index, rms)

            chunk = AudioChunk(
                data=float32_to_pcm_bytes(resampled),
                timestamp=float(time_info.get("input_buffer_adc_time", 0.0)),
                sample_rate=self._config.sample_rate,
                channels=1,
            )
            try:
                self._loop.call_soon_threadsafe(self._enqueue, chunk)
            except RuntimeError:
                pass
            return (None, pyaudio.paContinue)

        self._stream = self._pyaudio.open(
            format=pyaudio.paFloat32,
            channels=self._channels,
            rate=self._native_rate,
            input=True,
            input_device_index=int(device["index"]),
            frames_per_buffer=frames_per_buffer,
            stream_callback=callback,
        )
        self._stream.start_stream()

    def _enqueue(self, chunk: AudioChunk) -> None:
        if self._queue is None:
            return
        try:
            self._queue.put_nowait(chunk)
        except asyncio.QueueFull:
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            self._queue.put_nowait(chunk)

    async def stop(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop_stream()
            except Exception:
                logger.exception("Error stopping audio stream")
            try:
                self._stream.close()
            except Exception:
                logger.exception("Error closing audio stream")
            self._stream = None

        if self._pyaudio is not None:
            try:
                self._pyaudio.terminate()
            except Exception:
                logger.exception("Error terminating PyAudio")
            self._pyaudio = None

        if self._queue is not None:
            await self._queue.put(None)
            self._queue = None

        logger.info("Audio capture stopped")

    async def stream_chunks(self) -> AsyncIterator[AudioChunk]:
        if self._queue is None:
            return
        while True:
            chunk = await self._queue.get()
            if chunk is None:
                break
            yield chunk

    def _resolve_loopback_device(self, pa: Any) -> dict[str, Any]:
        loopbacks = list(self._iter_loopback_devices(pa))
        for device in loopbacks:
            logger.info("  Available loopback: %s", device["name"])

        if self._config.loopback_device:
            for device in loopbacks:
                if self._config.loopback_device.lower() in device["name"].lower():
                    logger.info("Using loopback device: %s", device["name"])
                    return device
            raise RuntimeError(
                f"Loopback device not found: {self._config.loopback_device!r}. "
                f"Available: {[d['name'] for d in loopbacks]}"
            )

        if hasattr(pa, "get_default_wasapi_loopback"):
            device = pa.get_default_wasapi_loopback()
            logger.info("Using loopback device: %s", device["name"])
            return device

        if not loopbacks:
            raise RuntimeError(
                "No WASAPI loopback device found. "
                "Install pyaudiowpatch: pip install pyaudiowpatch"
            )

        logger.info("Using loopback device: %s", loopbacks[0]["name"])
        return loopbacks[0]

    @staticmethod
    def _iter_loopback_devices(pa: Any):
        if hasattr(pa, "get_loopback_device_info_generator"):
            yield from pa.get_loopback_device_info_generator()
            return

        for index in range(pa.get_device_count()):
            device = pa.get_device_info_by_index(index)
            if device.get("isLoopbackDevice") or "loopback" in device["name"].lower():
                yield device
