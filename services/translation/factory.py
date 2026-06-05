"""Factory for translation service instances."""

from __future__ import annotations

import logging
import os

from core.interfaces.translator import ITranslator
from infrastructure.config import TranslationConfig
from services.translation.dashscope_mt_service import DashScopeMtTranslationService

logger = logging.getLogger(__name__)


class PassthroughTranslator:
    """No-op translator used when translation is disabled or unavailable."""

    async def translate(
        self,
        text: str,
        *,
        source_lang: str = "en",
        target_lang: str = "zh",
        context: str = "",
    ) -> str:
        return text.strip()


def create_translator(config: TranslationConfig) -> ITranslator:
    if not config.enabled:
        logger.info("Translation disabled in config")
        return PassthroughTranslator()

    if config.provider != "dashscope_mt":
        logger.warning(
            "Unsupported translation provider %r; using passthrough",
            config.provider,
        )
        return PassthroughTranslator()

    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    if not api_key:
        logger.warning("DASHSCOPE_API_KEY not set; translation will fall back to English")
        return PassthroughTranslator()

    return DashScopeMtTranslationService(config, api_key=api_key)
