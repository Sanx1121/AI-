"""Tests for translation cache."""

import asyncio

import pytest

from services.translation.translation_cache import TranslationCache


@pytest.mark.asyncio
async def test_cache_returns_cached_value():
    cache = TranslationCache(max_size=10, ttl_sec=60.0)
    calls = 0

    async def translate_fn():
        nonlocal calls
        calls += 1
        return "你好"

    first = await cache.dedupe(
        "hello",
        source_lang="en",
        target_lang="zh",
        translate_fn=translate_fn,
    )
    second = await cache.dedupe(
        "hello",
        source_lang="en",
        target_lang="zh",
        translate_fn=translate_fn,
    )

    assert first == "你好"
    assert second == "你好"
    assert calls == 1


@pytest.mark.asyncio
async def test_inflight_requests_share_single_call():
    cache = TranslationCache(max_size=10, ttl_sec=60.0)
    calls = 0

    async def translate_fn():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return "你好"

    results = await asyncio.gather(
        cache.dedupe(
            "hello",
            source_lang="en",
            target_lang="zh",
            translate_fn=translate_fn,
        ),
        cache.dedupe(
            "hello",
            source_lang="en",
            target_lang="zh",
            translate_fn=translate_fn,
        ),
    )

    assert results == ["你好", "你好"]
    assert calls == 1
