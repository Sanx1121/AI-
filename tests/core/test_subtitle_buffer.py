"""Tests for SubtitleBuffer."""

from core.models import SubtitleLine
from core.subtitle.buffer import SubtitleBuffer


def test_append_and_get_visible():
    buffer = SubtitleBuffer(max_lines=10)
    line = SubtitleLine(
        source_text="hello",
        translated_text="你好",
        start_time=0.0,
        end_time=5.0,
    )
    buffer.append(line)
    visible = buffer.get_visible(at_time=2.0)
    assert len(visible) == 1
    assert visible[0].translated_text == "你好"


def test_update_existing_line():
    buffer = SubtitleBuffer()
    line = SubtitleLine(
        source_text="hello",
        translated_text="你好",
        start_time=0.0,
        end_time=5.0,
        id="abc",
    )
    buffer.append(line)
    updated = SubtitleLine(
        source_text="hello world",
        translated_text="你好世界",
        start_time=0.0,
        end_time=5.0,
        id="abc",
    )
    assert buffer.update("abc", updated) is True
    assert buffer.lines[0].translated_text == "你好世界"


def test_clear():
    buffer = SubtitleBuffer()
    buffer.append(
        SubtitleLine(
            source_text="a",
            translated_text="甲",
            start_time=0.0,
            end_time=1.0,
        )
    )
    buffer.clear()
    assert buffer.lines == []
