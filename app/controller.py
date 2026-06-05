"""Connects UI commands to the async pipeline via QtAsyncBridge."""

from __future__ import annotations

import asyncio
import logging

from core.events import PipelineState, PipelineStateEvent, SubtitleEvent
from core.pipeline.orchestrator import PipelineOrchestrator
from infrastructure.qt_async_bridge import QtAsyncBridge
from ui.view_models.subtitle_view_model import SubtitleViewModel

logger = logging.getLogger(__name__)


class AppController:
    def __init__(
        self,
        bridge: QtAsyncBridge,
        view_model: SubtitleViewModel,
        *,
        demo_mode: bool = True,
    ) -> None:
        self._bridge = bridge
        self._view_model = view_model
        self._orchestrator = PipelineOrchestrator(
            on_event=self._handle_pipeline_event,
            demo_mode=demo_mode,
        )
        self._start_task: asyncio.Task[None] | None = None

    @property
    def is_running(self) -> bool:
        return self._orchestrator.is_running

    def start_pipeline(self) -> None:
        if self._orchestrator.is_running:
            return
        logger.info("Starting pipeline")
        self._start_task = self._bridge.run_coroutine(
            self._orchestrator.start(),
            on_error=self._on_start_error,
        )

    def stop_pipeline(self) -> None:
        if not self._orchestrator.is_running:
            return
        logger.info("Stopping pipeline")
        self._bridge.run_coroutine(
            self._orchestrator.stop(),
            on_error=self._on_stop_error,
        )

    async def _handle_pipeline_event(
        self,
        event: SubtitleEvent | PipelineStateEvent,
    ) -> None:
        if isinstance(event, SubtitleEvent):
            self._bridge.emit_to_main_thread(
                self._view_model.on_subtitle_event,
                event,
            )
        else:
            self._bridge.emit_to_main_thread(
                self._view_model.on_pipeline_state_changed,
                event,
            )

    def _on_start_error(self, exc: Exception) -> None:
        logger.error("Failed to start pipeline: %s", exc)
        self._view_model.on_pipeline_state_changed(
            PipelineStateEvent(state=PipelineState.ERROR, message=str(exc))
        )

    def _on_stop_error(self, exc: Exception) -> None:
        logger.error("Failed to stop pipeline: %s", exc)
