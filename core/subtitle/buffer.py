"""Maintains an ordered list of subtitle lines with update support."""

from __future__ import annotations

from core.models import SubtitleLine


class SubtitleBuffer:
    def __init__(self, max_lines: int = 64) -> None:
        self._lines: list[SubtitleLine] = []
        self._max_lines = max_lines

    @property
    def lines(self) -> list[SubtitleLine]:
        return list(self._lines)

    def append(self, line: SubtitleLine) -> None:
        self._lines.append(line)
        if len(self._lines) > self._max_lines:
            self._lines = self._lines[-self._max_lines :]

    def update(self, line_id: str, line: SubtitleLine) -> bool:
        for index, existing in enumerate(self._lines):
            if existing.id == line_id:
                self._lines[index] = line
                return True
        return False

    def get_visible(self, at_time: float, count: int = 3) -> list[SubtitleLine]:
        visible = [
            line
            for line in self._lines
            if line.start_time <= at_time <= line.end_time
            or line.end_time >= at_time
        ]
        return visible[-count:]

    def clear(self) -> None:
        self._lines.clear()
