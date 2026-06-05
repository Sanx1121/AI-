"""LRU translation cache with in-flight request deduplication."""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class _CacheEntry:
    text: str
    expires_at: float


class TranslationCache:
    def __init__(self, *, max_size: int = 500, ttl_sec: float = 3600.0) -> None:
        self._max_size = max(1, max_size)
        self._ttl_sec = max(1.0, ttl_sec)
        self._entries: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._inflight: dict[str, asyncio.Future[str]] = {}

    def _key(self, text: str, source_lang: str, target_lang: str) -> str:
        payload = f"{source_lang}|{target_lang}|{text.strip()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, text: str, *, source_lang: str, target_lang: str) -> str | None:
        cache_key = self._key(text, source_lang, target_lang)
        entry = self._entries.get(cache_key)
        if entry is None:
            return None
        if entry.expires_at <= time.monotonic():
            self._entries.pop(cache_key, None)
            return None
        self._entries.move_to_end(cache_key)
        return entry.text

    def put(
        self,
        text: str,
        translated: str,
        *,
        source_lang: str,
        target_lang: str,
    ) -> None:
        cache_key = self._key(text, source_lang, target_lang)
        self._entries[cache_key] = _CacheEntry(
            text=translated,
            expires_at=time.monotonic() + self._ttl_sec,
        )
        self._entries.move_to_end(cache_key)
        while len(self._entries) > self._max_size:
            self._entries.popitem(last=False)

    async def dedupe(
        self,
        text: str,
        *,
        source_lang: str,
        target_lang: str,
        translate_fn,
    ) -> str:
        cache_key = self._key(text, source_lang, target_lang)
        cached = self.get(text, source_lang=source_lang, target_lang=target_lang)
        if cached is not None:
            return cached

        inflight = self._inflight.get(cache_key)
        if inflight is not None:
            return await asyncio.shield(inflight)

        loop = asyncio.get_running_loop()
        future: asyncio.Future[str] = loop.create_future()
        self._inflight[cache_key] = future
        try:
            result = await translate_fn()
            self.put(
                text,
                result,
                source_lang=source_lang,
                target_lang=target_lang,
            )
            future.set_result(result)
            return result
        except Exception as exc:
            future.set_exception(exc)
            raise
        finally:
            self._inflight.pop(cache_key, None)
