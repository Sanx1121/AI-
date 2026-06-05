"""Async translation scheduling for subtitle events."""

from __future__ import annotations

import asyncio
import logging
import time

from core.interfaces.translator import ITranslator
from core.models import TranscriptSegment
from core.subtitle.subtitle_manager import SubtitleManager
from infrastructure.config import TranslationConfig
from services.translation.translation_cache import TranslationCache

logger = logging.getLogger(__name__)


class TranslationCoordinator:
    """Translates FINAL segments without blocking ASR."""

    def __init__(
        self,
        translator: ITranslator,
        config: TranslationConfig,
        subtitle_manager: SubtitleManager,
        *,
        cache: TranslationCache | None = None,
    ) -> None:
        self._translator = translator
        self._config = config
        self._subtitle_manager = subtitle_manager
        self._cache = cache or TranslationCache(
            max_size=config.cache_size,
            ttl_sec=config.cache_ttl_sec,
        )
        self._tasks: set[asyncio.Task[None]] = set()

    @property
    def enabled(self) -> bool:
        return self._config.enabled and self._config.mode == "final_only"

    def schedule_final_translation(
        self,
        segment: TranscriptSegment,
        *,
        line_id: str,
        emit,
    ) -> None:
        if not self.enabled or not segment.is_final:
            return

        text = segment.text.strip()
        if not text:
            return

        task = asyncio.create_task(
            self._translate_final(segment, line_id=line_id, emit=emit),
            name=f"translate-{line_id[:8]}",
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _translate_final(self, segment: TranscriptSegment, *, line_id: str, emit) -> None:
        text = segment.text.strip()
        started = time.monotonic()

        async def _call_api() -> str:
            last_error: Exception | None = None
            attempts = max(1, self._config.max_retries + 1)
            for attempt in range(attempts):
                try:
                    return await self._translator.translate(
                        text,
                        source_lang=self._config.source_language,
                        target_lang=self._config.target_language,
                    )
                except Exception as exc:
                    last_error = exc
                    if attempt + 1 >= attempts:
                        break
                    await asyncio.sleep(0.05)
            assert last_error is not None
            raise last_error

        try:
            translated = await self._cache.dedupe(
                text,
                source_lang=self._config.source_language,
                target_lang=self._config.target_language,
                translate_fn=_call_api,
            )
        except Exception:
            logger.exception("Translation failed for line %s", line_id[:8])
            return

        elapsed_ms = (time.monotonic() - started) * 1000.0
        logger.info(
            "Translated line %s in %.0f ms",
            line_id[:8],
            elapsed_ms,
        )

        update_event = self._subtitle_manager.apply_translation(line_id, translated)
        if update_event is not None:
            await emit(update_event)

    async def shutdown(self) -> None:
        if not self._tasks:
            return
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
