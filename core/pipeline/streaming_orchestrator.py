"""Streaming pipeline: VAD utterances + Whisper partial/final ASR."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

from core.events import (
    PipelineState,
    PipelineStateEvent,
    SubtitleEvent,
    UtteranceSegmentEvent,
    UtteranceSegmentEventType,
)
from core.interfaces.audio_source import IAudioSource
from core.pipeline.vad_utterance_processor import VadUtteranceProcessor
from core.subtitle.subtitle_manager import SubtitleManager
from core.translation.translation_coordinator import TranslationCoordinator
from infrastructure.config import AppConfig
from services.asr.utterance_transcriber import UtteranceTranscriber

logger = logging.getLogger(__name__)

EventCallback = Callable[[SubtitleEvent | PipelineStateEvent], Awaitable[None]]


class StreamingPipelineOrchestrator:
    """Phase 2 balanced: VAD segmentation + Whisper partial/final."""

    def __init__(
        self,
        on_event: EventCallback,
        config: AppConfig,
        audio_source: IAudioSource,
        vad_processor: VadUtteranceProcessor,
        utterance_transcriber: UtteranceTranscriber,
        subtitle_manager: SubtitleManager | None = None,
        translation_coordinator: TranslationCoordinator | None = None,
    ) -> None:
        self._on_event = on_event
        self._config = config
        self._audio_source = audio_source
        self._vad_processor = vad_processor
        self._transcriber = utterance_transcriber
        self._subtitle_manager = subtitle_manager or SubtitleManager()
        self._translation = translation_coordinator
        self._task: asyncio.Task[None] | None = None
        self._partial_task: asyncio.Task[None] | None = None
        self._running = False
        self._active_utterance_id: str | None = None
        self._active_utterance = None

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        if self._running:
            return

        await self._emit(PipelineStateEvent(PipelineState.STARTING, "正在初始化…"))
        await self._emit(
            PipelineStateEvent(PipelineState.STARTING, "正在加载 Whisper 模型…")
        )
        await self._transcriber.warmup()

        self._running = True
        self._task = asyncio.create_task(self._run(), name="streaming-pipeline")
        await self._emit(
            PipelineStateEvent(PipelineState.RUNNING, "流式识别运行中")
        )

    async def stop(self) -> None:
        if not self._running:
            return

        await self._emit(PipelineStateEvent(PipelineState.STOPPING))
        self._running = False

        await self._stop_partial_loop()

        if self._audio_source is not None:
            try:
                await self._audio_source.stop()
            except Exception:
                logger.exception("Error stopping audio source")

        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        for event in self._vad_processor.flush(timestamp=time.monotonic()):
            await self._handle_utterance_event(event)

        if self._translation is not None:
            await self._translation.shutdown()

        clear_event = self._subtitle_manager.clear()
        await self._emit(clear_event)
        self._vad_processor.reset()
        await self._emit(PipelineStateEvent(PipelineState.IDLE, "就绪"))

    async def _run(self) -> None:
        try:
            await self._audio_source.start()
            async for chunk in self._audio_source.stream_chunks():
                if not self._running:
                    break
                segment_events = self._vad_processor.feed_pcm(
                    chunk.data,
                    timestamp=chunk.timestamp,
                )
                for event in segment_events:
                    await self._handle_utterance_event(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Streaming pipeline error")
            self._running = False
            await self._emit(
                PipelineStateEvent(PipelineState.ERROR, message=str(exc))
            )

    async def _handle_utterance_event(self, event: UtteranceSegmentEvent) -> None:
        if event.type == UtteranceSegmentEventType.START:
            await self._on_utterance_start(event)
        elif event.type == UtteranceSegmentEventType.END:
            await self._on_utterance_end(event)

    async def _on_utterance_start(self, event: UtteranceSegmentEvent) -> None:
        await self._stop_partial_loop()
        self._active_utterance = event.utterance
        self._active_utterance_id = event.utterance.id

        subtitle_event = self._subtitle_manager.on_utterance_event(event)
        if subtitle_event:
            await self._emit(subtitle_event)

        self._partial_task = asyncio.create_task(
            self._partial_loop(event.utterance),
            name=f"partial-{event.utterance.id[:8]}",
        )

    async def _on_utterance_end(self, event: UtteranceSegmentEvent) -> None:
        await self._stop_partial_loop()
        utterance = event.utterance
        self._active_utterance = None
        self._active_utterance_id = None

        try:
            segment = await self._transcriber.transcribe_final_from_ring(
                event,
                self._vad_processor.ring_buffer,
            )
        except Exception:
            logger.exception(
                "Final ASR failed for utterance %s",
                utterance.id[:8],
            )
            return

        if segment:
            await self._emit_subtitle(segment)

    async def _emit_subtitle(self, segment) -> None:
        subtitle_event = self._subtitle_manager.on_transcript(segment)
        if not subtitle_event:
            return

        await self._emit(subtitle_event)

        if (
            segment.is_final
            and self._translation is not None
            and subtitle_event.line is not None
        ):
            self._translation.schedule_final_translation(
                segment,
                line_id=subtitle_event.line.id,
                emit=self._emit,
            )

    async def _partial_loop(self, utterance) -> None:
        interval = self._config.utterance.partial_interval_ms / 1000.0
        ring = self._vad_processor.ring_buffer

        try:
            while self._running and self._active_utterance_id == utterance.id:
                loop_start = time.monotonic()
                try:
                    segment = await self._transcriber.transcribe_partial(
                        ring,
                        utterance.id,
                        audio_start_offset=utterance.audio_start_offset,
                        start_time=utterance.start_time,
                    )
                    if segment:
                        await self._emit_subtitle(segment)
                except Exception:
                    logger.exception(
                        "Partial ASR failed for utterance %s",
                        utterance.id[:8],
                    )
                elapsed = time.monotonic() - loop_start
                await asyncio.sleep(max(0.05, interval - elapsed))
        except asyncio.CancelledError:
            raise

    async def _stop_partial_loop(self) -> None:
        if self._partial_task is not None:
            self._partial_task.cancel()
            try:
                await self._partial_task
            except asyncio.CancelledError:
                pass
            self._partial_task = None

    async def _emit(self, event: SubtitleEvent | PipelineStateEvent) -> None:
        await self._on_event(event)
