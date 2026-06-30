# -*- coding: utf-8 -*-
"""Tests for AI provider base classes.

Verifies:
- NoOpProvider implementation
- Provider interface compliance
- Token counting
- Availability check
"""
import pytest

from bot.ai.core.base_provider import AIProvider, NoOpProvider


@pytest.fixture
def noop_provider():
    """Create NoOpProvider instance."""
    return NoOpProvider()


def test_noop_provider_is_subclass(noop_provider):
    """Verify NoOpProvider implements AIProvider."""
    assert isinstance(noop_provider, AIProvider)


def test_noop_provider_properties(noop_provider):
    """Verify NoOpProvider properties."""
    assert noop_provider.provider_name == "noop"
    assert noop_provider.model_name == "noop-model-v1"
    assert noop_provider.max_context_tokens == 4096


@pytest.mark.asyncio
async def test_noop_provider_initialize(noop_provider):
    """Verify initialization works."""
    await noop_provider.initialize()
    assert True  # No exception = success


@pytest.mark.asyncio
async def test_noop_provider_shutdown(noop_provider):
    """Verify shutdown works."""
    await noop_provider.shutdown()
    assert True  # No exception = success


@pytest.mark.asyncio
async def test_noop_provider_is_available(noop_provider):
    """Verify availability check."""
    available = await noop_provider.is_available()
    assert available is True


@pytest.mark.asyncio
async def test_noop_provider_generate(noop_provider):
    """Verify generate method returns proper structure."""
    result = await noop_provider.generate(
        system_prompt="You are a test AI",
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.7,
    )

    # Verify response structure
    assert isinstance(result, dict)
    assert "response" in result
    assert "tokens_used" in result
    assert "model" in result
    assert "provider" in result
    assert "raw_response" in result

    # Verify values
    assert isinstance(result["response"], str)
    assert isinstance(result["tokens_used"], int)
    assert result["model"] == "noop-model-v1"
    assert result["provider"] == "noop"


@pytest.mark.asyncio
async def test_noop_provider_count_tokens(noop_provider):
    """Verify token counting."""
    text = "This is a test string"
    tokens = await noop_provider.count_tokens(text)
    assert isinstance(tokens, int)
    assert tokens > 0
    # Rough estimate: ~1 token per 4 chars
    assert tokens == len(text) // 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
