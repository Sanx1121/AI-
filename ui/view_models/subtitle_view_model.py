"""Adapts core domain events to Qt-bindable state."""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal

from core.events import PipelineState, PipelineStateEvent, SubtitleEvent, SubtitleEventType
from core.models import SubtitleLine


class SubtitleViewModel(QObject):
    """Holds subtitle display state; UI widgets bind to its signals."""

    visible_lines_changed = Signal()
    pipeline_state_changed = Signal()
    status_message_changed = Signal()

    def __init__(self, max_visible_lines: int = 3, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._max_visible_lines = max_visible_lines
        self._lines: list[SubtitleLine] = []
        self._pipeline_state = PipelineState.IDLE
        self._status_message = "就绪"

    @Property(list, notify=visible_lines_changed)
    def visible_lines(self) -> list[str]:
        return [line.translated_text for line in self._lines[-self._max_visible_lines :]]

    @Property(str, notify=pipeline_state_changed)
    def pipeline_state(self) -> str:
        return self._pipeline_state.value

    @Property(str, notify=status_message_changed)
    def status_message(self) -> str:
        return self._status_message

    def on_subtitle_event(self, event: SubtitleEvent) -> None:
        if event.type == SubtitleEventType.CLEAR:
            self._lines.clear()
        elif event.type == SubtitleEventType.APPEND and event.line is not None:
            self._lines.append(event.line)
            if len(self._lines) > self._max_visible_lines * 2:
                self._lines = self._lines[-self._max_visible_lines * 2 :]
        elif event.type == SubtitleEventType.UPDATE and event.line is not None:
            for index, line in enumerate(self._lines):
                if line.id == event.line.id:
                    self._lines[index] = event.line
                    break
            else:
                self._lines.append(event.line)

        self.visible_lines_changed.emit()

    def on_pipeline_state_changed(self, event: PipelineStateEvent) -> None:
        self._pipeline_state = event.state
        self._status_message = event.message or _state_label(event.state)
        self.pipeline_state_changed.emit()
        self.status_message_changed.emit()

    def get_display_text(self) -> str:
        visible = self._lines[-self._max_visible_lines :]
        if not visible:
            return ""
        return "\n".join(line.translated_text for line in visible)


def _state_label(state: PipelineState) -> str:
    labels = {
        PipelineState.IDLE: "就绪",
        PipelineState.STARTING: "启动中…",
        PipelineState.RUNNING: "运行中",
        PipelineState.STOPPING: "停止中…",
        PipelineState.ERROR: "错误",
    }
    return labels.get(state, state.value)
