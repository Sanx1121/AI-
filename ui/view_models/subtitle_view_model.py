"""Adapts core domain events to Qt-bindable state."""

from __future__ import annotations

import html

from PySide6.QtCore import Property, QObject, Signal

from core.events import PipelineState, PipelineStateEvent, SubtitleEvent, SubtitleEventType
from core.models import SubtitleLine, SubtitleStatus


class SubtitleViewModel(QObject):
    """Dual-zone subtitle state: white finalized history + gray live partial."""

    visible_lines_changed = Signal()
    pipeline_state_changed = Signal()
    status_message_changed = Signal()

    def __init__(
        self,
        max_visible_lines: int = 3,
        *,
        history_max_lines: int = 2,
        final_color: str = "#FFFFFF",
        partial_color: str = "#9EACB4",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._max_visible_lines = max_visible_lines
        self._history_max_lines = history_max_lines
        self._final_color = final_color
        self._partial_color = partial_color
        self._history_lines: list[str] = []
        self._live_text = ""
        self._pipeline_state = PipelineState.IDLE
        self._status_message = "就绪"

    @Property(list, notify=visible_lines_changed)
    def visible_lines(self) -> list[str]:
        lines = self._history_lines[-self._history_max_lines :]
        if self._live_text:
            lines = [*lines, self._live_text]
        return lines[-self._max_visible_lines :]

    @Property(str, notify=pipeline_state_changed)
    def pipeline_state(self) -> str:
        return self._pipeline_state.value

    @Property(str, notify=status_message_changed)
    def status_message(self) -> str:
        return self._status_message

    def on_subtitle_event(self, event: SubtitleEvent) -> None:
        if event.type == SubtitleEventType.CLEAR:
            self._history_lines.clear()
            self._live_text = ""
            self.visible_lines_changed.emit()
            return

        if event.line is None:
            return

        line = event.line
        text = line.translated_text.strip()
        if not text:
            return

        if line.status == SubtitleStatus.FINAL:
            self._commit_to_history(text)
            self._live_text = ""
        else:
            self._live_text = text

        self.visible_lines_changed.emit()

    def on_pipeline_state_changed(self, event: PipelineStateEvent) -> None:
        self._pipeline_state = event.state
        self._status_message = event.message or _state_label(event.state)
        self.pipeline_state_changed.emit()
        self.status_message_changed.emit()

    def get_display_text(self) -> str:
        """Plain-text fallback."""
        parts = self._history_lines[-self._history_max_lines :]
        if self._live_text:
            parts = [*parts, self._live_text]
        return "\n".join(parts[-self._max_visible_lines :])

    def get_display_html(self) -> str:
        parts: list[str] = []
        history = self._history_lines[-self._history_max_lines :]
        if history:
            parts.append(
                "<br/>".join(
                    f'<span style="color:{self._final_color};">{html.escape(line)}</span>'
                    for line in history
                )
            )
        if self._live_text:
            parts.append(
                f'<span style="color:{self._partial_color};">{html.escape(self._live_text)}</span>'
            )
        return "<br/>".join(parts)

    def _commit_to_history(self, text: str) -> None:
        if self._history_lines and self._history_lines[-1] == text:
            return
        self._history_lines.append(text)
        max_keep = max(self._history_max_lines * 2, self._max_visible_lines * 2)
        if len(self._history_lines) > max_keep:
            self._history_lines = self._history_lines[-max_keep:]


def _state_label(state: PipelineState) -> str:
    labels = {
        PipelineState.IDLE: "就绪",
        PipelineState.STARTING: "启动中…",
        PipelineState.RUNNING: "运行中",
        PipelineState.STOPPING: "停止中…",
        PipelineState.ERROR: "错误",
    }
    return labels.get(state, state.value)
