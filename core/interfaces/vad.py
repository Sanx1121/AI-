"""Voice activity detection interface."""

from __future__ import annotations

from typing import Protocol


class IVAD(Protocol):
    def reset(self) -> None: ...

    def is_speech(self, frame_pcm: bytes) -> bool: ...
