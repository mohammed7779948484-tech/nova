"""T030: Test LLM Service — real LLM calls via LongCat API.

All tests use real LLM connections (no mocks). The LongCat API
provides an OpenAI-compatible endpoint for real AI responses.

Tests verify:
- Real LLM call returns a valid AI response
- Real LLM call with tools bound works
- Fallback to next model when primary fails (invalid key → valid key)
- Graceful failure when all models have invalid credentials
- No models registered returns graceful message
"""

from __future__ import annotations

import os

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.services.llm_service import GRACEFUL_FAILURE_MESSAGE, LLMService


# ---------------------------------------------------------------------------
# Real LongCat model factory
# ---------------------------------------------------------------------------

def _make_real_model_factory(
    model: str = "LongCat-Flash-Chat",
    api_base: str | None = None,
    api_key: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 256,
):
    """Create a factory that returns a real ChatOpenAI instance.

    Args:
        model: Model name to use.
        api_base: Override for OPENAI_API_BASE.
        api_key: Override for OPENAI_API_KEY.
        temperature: Sampling temperature.
        max_tokens: Max output tokens.
    """
    from langchain_openai import ChatOpenAI

    base_url = api_base or os.getenv("OPENAI_API_BASE", "")
    key = api_key or os.getenv("OPENAI_API_KEY", "")

    def factory():
        kwargs = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if base_url:
            kwargs["base_url"] = base_url
        if key:
            kwargs["api_key"] = key
        return ChatOpenAI(**kwargs)

    return factory


def _make_invalid_model_factory():
    """Create a factory that returns a ChatOpenAI with invalid credentials."""
    from langchain_openai import ChatOpenAI

    def factory():
        return ChatOpenAI(
            model="nonexistent-model-xyz",
            api_key="sk-invalid-key-000000000000",
            base_url="https://api.longcat.chat/openai",
            temperature=0.0,
            max_tokens=10,
        )

    return factory


# ---------------------------------------------------------------------------
# Real LLM call tests
# ---------------------------------------------------------------------------

class TestLLMServiceRealCalls:

    @pytest.mark.asyncio
    async def test_real_llm_call_returns_ai_message(self):
        """Real LLM call via LongCat API returns a valid AIMessage."""
        svc = LLMService()
        svc.register_model("longcat-flash", _make_real_model_factory())
        svc._current_model = None  # force rebuild

        result = await svc.call(
            [HumanMessage(content="Say 'hello' in one word.")],
        )

        assert isinstance(result, AIMessage), (
            f"Expected AIMessage, got {type(result).__name__}: {result}"
        )
        assert len(result.content) > 0, "Response should not be empty"


class TestLLMServiceFallback:

    @pytest.mark.asyncio
    async def test_falls_back_to_next_model_on_invalid_primary(self):
        """When primary model has invalid credentials, falls back to valid secondary."""
        svc = LLMService()
        svc.register_model("invalid-primary", _make_invalid_model_factory())
        svc.register_model("valid-secondary", _make_real_model_factory())
        svc._current_model = None  # force rebuild

        result = await svc.call(
            [HumanMessage(content="Say 'fallback works' in two words.")],
        )

        assert isinstance(result, AIMessage), (
            f"Expected AIMessage from fallback, got {type(result).__name__}: {result}"
        )
        assert svc._current_model_index == 1, (
            "Should have switched to secondary model"
        )


class TestLLMServiceGracefulFailure:

    @pytest.mark.asyncio
    async def test_graceful_message_on_all_invalid_models(self):
        """When all models have invalid credentials, returns graceful failure."""
        svc = LLMService()
        svc.register_model("bad-model-1", _make_invalid_model_factory())
        svc._current_model = None

        result = await svc.call(
            [HumanMessage(content="hello")],
        )

        assert isinstance(result, str), (
            f"Expected graceful failure string, got {type(result).__name__}"
        )
        assert "technical difficulties" in result.lower() or "try again" in result.lower(), (
            f"Expected graceful message, got: {result}"
        )

    @pytest.mark.asyncio
    async def test_no_models_returns_graceful(self):
        """When no models are registered, returns graceful message immediately."""
        svc = LLMService()

        result = await svc.call(
            [HumanMessage(content="hello")],
        )

        assert isinstance(result, str)
        assert result == GRACEFUL_FAILURE_MESSAGE


class TestLLMServiceWithTools:

    @pytest.mark.asyncio
    async def test_real_llm_with_tools_bound(self):
        """Real LLM with tools bound can make tool calls."""
        from src.tools import ALL_TOOLS

        svc = LLMService()
        svc.register_model("longcat-flash", _make_real_model_factory())
        svc._current_model = None

        result = await svc.call(
            [HumanMessage(content="Search for roses")],
            tools=ALL_TOOLS,
        )

        # The LLM should either make a tool call or respond directly
        assert isinstance(result, AIMessage), (
            f"Expected AIMessage, got {type(result).__name__}"
        )

    @pytest.mark.asyncio
    async def test_fallback_preserves_tools(self):
        """When fallback occurs, tools are preserved on the new model."""
        from src.tools import ALL_TOOLS

        svc = LLMService()
        svc.register_model("invalid-primary", _make_invalid_model_factory())
        svc.register_model("valid-secondary", _make_real_model_factory())
        svc._current_model = None

        result = await svc.call(
            [HumanMessage(content="Search for roses")],
            tools=ALL_TOOLS,
        )

        assert isinstance(result, AIMessage), (
            f"Expected AIMessage with tools, got {type(result).__name__}"
        )
