"""Async tests for pipeline orchestrator demo mode."""

import asyncio

import pytest

from core.events import PipelineState, SubtitleEventType
from core.pipeline.orchestrator import PipelineOrchestrator


@pytest.mark.asyncio
async def test_demo_emits_subtitle_events():
    events: list = []

    async def capture(event):
        events.append(event)

    orchestrator = PipelineOrchestrator(on_event=capture, demo_mode=True)
    await orchestrator.start()

    # Wait for first demo line (3s interval); cancel early after first append
    for _ in range(50):
        await asyncio.sleep(0.1)
        if any(
            getattr(e, "type", None) == SubtitleEventType.APPEND for e in events
        ):
            break

    await orchestrator.stop()

    append_events = [e for e in events if getattr(e, "type", None) == SubtitleEventType.APPEND]
    state_values = [e.state for e in events if hasattr(e, "state")]

    assert len(append_events) >= 1
    assert PipelineState.STARTING in state_values
    assert PipelineState.RUNNING in state_values
