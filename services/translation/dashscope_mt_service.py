"""DashScope Qwen-MT translation via OpenAI-compatible API."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from infrastructure.config import TranslationConfig

logger = logging.getLogger(__name__)

_QWEN_MT_LANG = {
    "en": "English",
    "zh": "Chinese",
    "auto": "auto",
}


def _to_qwen_lang(code: str) -> str:
    normalized = code.strip().lower()
    return _QWEN_MT_LANG.get(normalized, code)


class DashScopeMtTranslationService:
    """Translate text using DashScope Qwen-MT and an API key."""

    def __init__(
        self,
        config: TranslationConfig,
        *,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=config.timeout_sec)

    async def translate(
        self,
        text: str,
        *,
        source_lang: str = "en",
        target_lang: str = "zh",
        context: str = "",
    ) -> str:
        stripped = text.strip()
        if not stripped:
            return ""

        if not self._api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is not configured")

        payload: dict[str, Any] = {
            "model": self._config.dashscope_model,
            "messages": [{"role": "user", "content": stripped}],
            "translation_options": {
                "source_lang": _to_qwen_lang(source_lang),
                "target_lang": _to_qwen_lang(target_lang),
            },
        }
        if context.strip():
            payload["translation_options"]["context"] = context.strip()

        url = f"{self._config.dashscope_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        response = await self._client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return str(content).strip()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
