"""Tests for TranslationCoordinator final_only mode."""

from __future__ import annotations

import asyncio

import pytest

from core.events import (
    SubtitleEventType,
    UtteranceSegmentEvent,
    UtteranceSegmentEventType,
)
from core.models import SubtitleStatus, TranscriptSegment, Utterance
from core.subtitle.subtitle_manager import SubtitleManager
from core.translation.translation_coordinator import TranslationCoordinator
from infrastructure.config import TranslationConfig


class MockTranslator:
    def __init__(self, translated: str = "你好世界") -> None:
        self.calls: list[str] = []
        self._translated = translated

    async def translate(
        self,
        text: str,
        *,
        source_lang: str = "en",
        target_lang: str = "zh",
        context: str = "",
    ) -> str:
        self.calls.append(text)
        await asyncio.sleep(0.01)
        return self._translated


@pytest.mark.asyncio
async def test_final_only_schedules_translation_update():
    manager = SubtitleManager()
    translator = MockTranslator("你好世界")
    config = TranslationConfig(enabled=True, mode="final_only")
    coordinator = TranslationCoordinator(translator, config, manager)
    emitted: list = []

    async def emit(event):
        emitted.append(event)

    manager.on_utterance_event(
        UtteranceSegmentEvent(
            type=UtteranceSegmentEventType.START,
            utterance=Utterance(id="utt-1", start_time=0.0),
        )
    )
    segment = TranscriptSegment(
        text="hello world",
        start_time=0.0,
        end_time=1.0,
        is_final=True,
        utterance_id="utt-1",
    )
    initial = manager.on_transcript(segment)
    assert initial is not None
    assert initial.line.translated_text == "hello world"

    coordinator.schedule_final_translation(
        segment,
        line_id=initial.line.id,
        emit=emit,
    )
    await asyncio.sleep(0.1)

    assert translator.calls == ["hello world"]
    assert len(emitted) == 1
    assert emitted[0].type == SubtitleEventType.UPDATE
    assert emitted[0].line.status == SubtitleStatus.CORRECTED
    assert emitted[0].line.translated_text == "你好世界"
