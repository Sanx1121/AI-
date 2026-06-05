"""Translation service interface."""

from __future__ import annotations

from typing import Protocol


class ITranslator(Protocol):
    async def translate(self, text: str, context: str = "") -> str: ...
