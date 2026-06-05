"""Benchmark DashScope translation latency."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from infrastructure.config import load_config
from services.translation.factory import create_translator


async def main() -> None:
    config = load_config()
    translator = create_translator(config.translation)
    samples = [
        "I did not laugh after watching this video.",
        "The quick brown fox jumps over the lazy dog.",
    ]

    for text in samples:
        started = time.perf_counter()
        result = await translator.translate(
            text,
            source_lang=config.translation.source_language,
            target_lang=config.translation.target_language,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        print(f"{elapsed_ms:6.0f} ms  {text!r} -> {result!r}")

    if hasattr(translator, "aclose"):
        await translator.aclose()


if __name__ == "__main__":
    if not os.getenv("DASHSCOPE_API_KEY"):
        raise SystemExit("Set DASHSCOPE_API_KEY before running benchmark_translate.py")
    asyncio.run(main())
