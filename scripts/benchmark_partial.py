#!/usr/bin/env python3
"""Benchmark average latency of one Whisper partial transcription."""

from __future__ import annotations

import asyncio
import statistics
import sys
import time
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from infrastructure.config import load_config
from services.asr.utterance_transcriber import UtteranceTranscriber
from services.asr.whisper_service import WhisperASRService
from services.audio.ring_buffer import RingBuffer
from services.audio.utils import float32_to_pcm_bytes

DEFAULT_WAV = (
    ROOT
    / "resources"
    / "models"
    / "sherpa-onnx-streaming-zipformer-en-20M-2023-02-17-mobile"
    / "test_wavs"
    / "0.wav"
)


def load_wav_pcm(path: Path, *, target_rate: int = 16000) -> bytes:
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

    import numpy as np

    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    if sample_rate != target_rate:
        from services.audio.utils import resample_linear

        samples = resample_linear(
            samples,
            source_rate=sample_rate,
            target_rate=target_rate,
        )
    return float32_to_pcm_bytes(samples)


async def benchmark(*, runs: int = 5, warmup: int = 1) -> None:
    config = load_config()
    wav = DEFAULT_WAV
    if not wav.is_file():
        raise FileNotFoundError(f"Test wav not found: {wav}")

    pcm = load_wav_pcm(wav, target_rate=config.audio.sample_rate)
    sample_rate = config.audio.sample_rate
    max_window_bytes = int(config.utterance.partial_window_sec * sample_rate * 2)

    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="bench-asr")
    whisper = WhisperASRService(config.asr, executor=executor)
    transcriber = UtteranceTranscriber(
        whisper,
        config.asr,
        config.utterance,
        sample_rate=sample_rate,
        executor=executor,
    )

    print("=== Partial ASR Benchmark ===")
    print(f"model_size     : {config.asr.model_size}")
    print(f"device         : {config.asr.device}")
    print(f"vad_filter     : {config.asr.vad_filter}")
    print(f"partial_window : {config.utterance.partial_window_sec}s ({max_window_bytes} bytes)")
    print(f"partial_interval: {config.utterance.partial_interval_ms}ms")
    print(f"test_wav       : {wav.name}")
    print(f"audio_duration : {len(pcm) / (sample_rate * 2):.2f}s")
    print()

    t0 = time.perf_counter()
    await transcriber.warmup()
    warmup_load_s = time.perf_counter() - t0
    print(f"model warmup   : {warmup_load_s:.2f}s")
    print()

    ring = RingBuffer(int(config.utterance.ring_buffer_sec * sample_rate * 2))
    ring.write(pcm)
    utterance_id = "bench-utt"
    audio_start_offset = max(0, ring.total_written - len(pcm))

    durations: list[float] = []
    texts: list[str] = []

    total_iters = warmup + runs
    for index in range(total_iters):
        start = time.perf_counter()
        segment = await transcriber.transcribe_partial(
            ring,
            utterance_id,
            audio_start_offset=audio_start_offset,
            start_time=0.0,
        )
        elapsed = time.perf_counter() - start
        if index >= warmup:
            durations.append(elapsed)
            texts.append(segment.text if segment else "")
            text_repr = repr(segment.text) if segment else "''"
            print(f"run {index - warmup + 1:2d}: {elapsed*1000:7.0f} ms  text={text_repr}")

    executor.shutdown(wait=True)

    if not durations:
        print("No timed runs completed.")
        return

    avg_ms = statistics.mean(durations) * 1000
    print()
    print("--- Summary ---")
    print(f"runs           : {len(durations)}")
    print(f"average        : {avg_ms:.0f} ms")
    print(f"median         : {statistics.median(durations)*1000:.0f} ms")
    print(f"min            : {min(durations)*1000:.0f} ms")
    print(f"max            : {max(durations)*1000:.0f} ms")
    if len(durations) > 1:
        print(f"stdev          : {statistics.stdev(durations)*1000:.0f} ms")
    print(f"interval cfg   : {config.utterance.partial_interval_ms} ms")
    if avg_ms > config.utterance.partial_interval_ms:
        print(
            "note: average partial > partial_interval_ms → "
            "effective rate is limited by inference, not the timer."
        )


def main() -> int:
    runs = 5
    if len(sys.argv) > 1:
        runs = int(sys.argv[1])
    asyncio.run(benchmark(runs=runs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
