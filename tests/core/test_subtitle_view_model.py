"""Tests for dual-zone SubtitleViewModel."""

from core.events import SubtitleEvent, SubtitleEventType
from core.models import SubtitleLine, SubtitleStatus
from ui.view_models.subtitle_view_model import SubtitleViewModel


def _line(text: str, *, status: SubtitleStatus, line_id: str = "line-1") -> SubtitleLine:
    return SubtitleLine(
        id=line_id,
        source_text=text,
        translated_text=text,
        start_time=0.0,
        end_time=1.0,
        status=status,
    )


def test_partial_renders_gray_and_final_renders_white():
    vm = SubtitleViewModel(
        final_color="#FFFFFF",
        partial_color="#9EACB4",
    )

    vm.on_subtitle_event(
        SubtitleEvent(
            type=SubtitleEventType.APPEND,
            line=_line("hello wor", status=SubtitleStatus.PARTIAL),
        )
    )
    html_partial = vm.get_display_html()
    assert "#9EACB4" in html_partial
    assert "hello wor" in html_partial
    assert "#FFFFFF" not in html_partial

    vm.on_subtitle_event(
        SubtitleEvent(
            type=SubtitleEventType.UPDATE,
            line=_line("hello world", status=SubtitleStatus.FINAL),
        )
    )
    html_final = vm.get_display_html()
    assert "#FFFFFF" in html_final
    assert "hello world" in html_final
    assert "#9EACB4" not in html_final
    assert vm._live_text == ""


def test_history_and_live_both_visible():
    vm = SubtitleViewModel(history_max_lines=2)

    vm.on_subtitle_event(
        SubtitleEvent(
            type=SubtitleEventType.UPDATE,
            line=_line("First sentence.", status=SubtitleStatus.FINAL, line_id="l1"),
        )
    )
    vm.on_subtitle_event(
        SubtitleEvent(
            type=SubtitleEventType.APPEND,
            line=_line("Second part", status=SubtitleStatus.PARTIAL, line_id="l2"),
        )
    )

    html_text = vm.get_display_html()
    assert "First sentence." in html_text
    assert "Second part" in html_text
    assert html_text.index("First sentence.") < html_text.index("Second part")
    assert html_text.count("#FFFFFF") >= 1
    assert html_text.count("#9EACB4") >= 1
