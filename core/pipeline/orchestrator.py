"""Pipeline orchestrator — coordinates async stages and emits domain events."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

from core.events import (
    PipelineState,
    PipelineStateEvent,
    SubtitleEvent,
    SubtitleEventType,
)
from core.models import SubtitleLine, SubtitleStatus
from core.subtitle.buffer import SubtitleBuffer

logger = logging.getLogger(__name__)

EventCallback = Callable[[SubtitleEvent | PipelineStateEvent], Awaitable[None]]

# Demo subtitles for Phase 1 static text verification.
_DEMO_LINES: list[tuple[str, str]] = [
    (
        "Welcome to this technical presentation.",
        "欢迎观看本次技术分享。",
    ),
    (
        "Today we will explore real-time AI translation.",
        "今天我们将探讨实时 AI 翻译。",
    ),
    (
        "This demo verifies the subtitle overlay pipeline.",
        "此演示用于验证字幕叠加流水线。",
    ),
    (
        "Phase 2 will connect live audio and ASR.",
        "Phase 2 将接入实时音频与语音识别。",
    ),
]


class PipelineOrchestrator:
    """Manages pipeline lifecycle. Phase 1 runs a demo subtitle loop."""

    def __init__(
        self,
        on_event: EventCallback,
        *,
        demo_mode: bool = True,
    ) -> None:
        self._on_event = on_event
        self._demo_mode = demo_mode
        self._buffer = SubtitleBuffer()
        self._task: asyncio.Task[None] | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        if self._running:
            return

        await self._emit(PipelineStateEvent(PipelineState.STARTING))
        self._running = True
        self._task = asyncio.create_task(self._run(), name="pipeline")
        await self._emit(PipelineStateEvent(PipelineState.RUNNING))

    async def stop(self) -> None:
        if not self._running:
            return

        await self._emit(PipelineStateEvent(PipelineState.STOPPING))
        self._running = False

        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        self._buffer.clear()
        await self._emit(SubtitleEvent(type=SubtitleEventType.CLEAR))
        await self._emit(PipelineStateEvent(PipelineState.IDLE))

    async def _run(self) -> None:
        try:
            if self._demo_mode:
                await self._run_demo()
            else:
                # Phase 2+: wire AudioStage → ASRStage → TranslationStage
                raise NotImplementedError("Live pipeline available from Phase 2")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Pipeline error")
            await self._emit(
                PipelineStateEvent(PipelineState.ERROR, message=str(exc))
            )
            self._running = False

    async def _run_demo(self) -> None:
        """Emit demo subtitle lines to verify UI wiring."""
        base_time = time.monotonic()
        for index, (source, translated) in enumerate(_DEMO_LINES):
            if not self._running:
                break

            line = SubtitleLine(
                source_text=source,
                translated_text=translated,
                start_time=base_time + index * 3.0,
                end_time=base_time + (index + 1) * 3.0,
                status=SubtitleStatus.FINAL,
            )
            self._buffer.append(line)
            await self._emit(
                SubtitleEvent(
                    type=SubtitleEventType.APPEND,
                    line=line,
                    timestamp=time.monotonic(),
                )
            )
            await asyncio.sleep(3.0)

        if self._running:
            await asyncio.sleep(1.0)
            self._running = False
            self._buffer.clear()
            await self._emit(SubtitleEvent(type=SubtitleEventType.CLEAR))
            await self._emit(PipelineStateEvent(PipelineState.IDLE))

    async def _emit(self, event: SubtitleEvent | PipelineStateEvent) -> None:
        await self._on_event(event)
