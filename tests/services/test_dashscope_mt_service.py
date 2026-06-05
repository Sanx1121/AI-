"""Tests for DashScope MT translation service."""

from __future__ import annotations

import pytest
import httpx

from infrastructure.config import TranslationConfig
from services.translation.dashscope_mt_service import DashScopeMtTranslationService


@pytest.mark.asyncio
async def test_translate_parses_chat_completion_response():
    config = TranslationConfig(
        dashscope_base_url="https://example.test/compatible-mode/v1",
        dashscope_model="qwen-mt-lite",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        payload = request.read().decode("utf-8")
        assert "translation_options" in payload
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "我看到这个视频后没有笑"}}],
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    service = DashScopeMtTranslationService(
        config,
        api_key="test-key",
        client=client,
    )

    result = await service.translate(
        "I did not laugh after watching this video",
        source_lang="en",
        target_lang="zh",
    )
    assert result == "我看到这个视频后没有笑"
    await service.aclose()
