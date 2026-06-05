"""Tests for SubtitleManager."""

import time

from core.events import SubtitleEventType, UtteranceSegmentEvent, UtteranceSegmentEventType
from core.models import SubtitleStatus, TranscriptSegment, Utterance
from core.subtitle.subtitle_manager import SubtitleManager


def _start_event(utterance_id: str = "utt-1") -> UtteranceSegmentEvent:
    utterance = Utterance(id=utterance_id, start_time=1.0)
    return UtteranceSegmentEvent(
        type=UtteranceSegmentEventType.START,
        utterance=utterance,
        timestamp=time.monotonic(),
    )


def test_utterance_start_does_not_append_empty_line():
    manager = SubtitleManager()
    assert manager.on_utterance_event(_start_event()) is None


def test_partial_then_update():
    manager = SubtitleManager()
    manager.on_utterance_event(_start_event())

    partial = TranscriptSegment(
        text="hello",
        start_time=1.0,
        end_time=1.5,
        is_final=False,
        utterance_id="utt-1",
    )
    event1 = manager.on_transcript(partial)
    assert event1 is not None
    assert event1.type == SubtitleEventType.APPEND
    assert event1.line.status == SubtitleStatus.PARTIAL
    assert event1.line.translated_text == ""
    assert event1.line.source_text == "hello"

    partial2 = TranscriptSegment(
        text="hello world",
        start_time=1.0,
        end_time=2.0,
        is_final=False,
        utterance_id="utt-1",
    )
    event2 = manager.on_transcript(partial2)
    assert event2.type == SubtitleEventType.UPDATE


def test_final_locks_line():
    manager = SubtitleManager()
    manager.on_utterance_event(_start_event())
    manager.on_transcript(
        TranscriptSegment(
            text="hello",
            start_time=1.0,
            end_time=1.5,
            is_final=False,
            utterance_id="utt-1",
        )
    )
    final = manager.on_transcript(
        TranscriptSegment(
            text="hello world",
            start_time=1.0,
            end_time=3.0,
            is_final=True,
            utterance_id="utt-1",
        )
    )
    assert final is not None
    assert final.line.status == SubtitleStatus.FINAL


def test_apply_translation_updates_line():
    manager = SubtitleManager()
    manager.on_utterance_event(_start_event())
    final = manager.on_transcript(
        TranscriptSegment(
            text="hello world",
            start_time=1.0,
            end_time=3.0,
            is_final=True,
            utterance_id="utt-1",
        )
    )
    assert final is not None

    corrected = manager.apply_translation(final.line.id, "你好世界")
    assert corrected is not None
    assert corrected.line.translated_text == "你好世界"
    assert corrected.line.source_text == "hello world"
    assert corrected.line.status == SubtitleStatus.CORRECTED
