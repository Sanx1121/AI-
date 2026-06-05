"""Audio source interface."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from core.models import AudioChunk


class IAudioSource(Protocol):
    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    def stream_chunks(self) -> AsyncIterator[AudioChunk]: ...
