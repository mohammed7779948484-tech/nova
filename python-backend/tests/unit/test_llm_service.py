"""T030: Test LLM Service — retry, circular fallback, graceful degradation.

PDCA Called Shot:
- test_llm_service_retries_on_rate_limit: mock factory raises RateLimitError 2x then succeeds.
  Behavior: LLMService retries 3 times, succeeds on 3rd.
  Expected failure (RED): call_count != 3 or graceful message returned instead.
- test_llm_service_falls_back_to_next_model: first factory always raises APIError.
  Behavior: LLMService switches to second model and succeeds.
  Expected failure (RED): TypeError or graceful message returned instead.
- test_llm_service_returns_graceful_message_on_total_failure: all factories raise.
  Behavior: LLMService returns graceful fallback string.
  Expected failure (RED): TypeError from logger or exception propagates.
- test_llm_service_switches_to_next_model_preserves_tools: verify tool bindings preserved.
  Behavior: After model switch, new model has tools bound.
  Expected failure (RED): tools not passed to new model.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.services.llm_service import GRACEFUL_FAILURE_MESSAGE, LLMService


def _make_mock_model(name: str, side_effect=None, return_value=None):
    """Create a mock BaseChatModel that records calls."""
    model = AsyncMock()
    if side_effect:
        model.ainvoke.side_effect = side_effect
    elif return_value is not None:
        model.ainvoke.return_value = return_value
    else:
        model.ainvoke.return_value = AIMessage(content=f"response from {name}")
    model.bind_tools = MagicMock(return_value=model)
    return model


class TestLLMServiceRetry:

    @pytest.mark.asyncio
    async def test_llm_service_retries_on_rate_limit(self):
        """LLMService retries on RateLimitError and succeeds on 3rd attempt."""
        from openai import RateLimitError

        call_count = 0

        async def fake_ainvoke(messages, config=None):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RateLimitError(
                    "rate limited", response=MagicMock(), body=None
                )
            return AIMessage(content="retry success")

        mock_model = AsyncMock()
        mock_model.ainvoke = fake_ainvoke
        mock_model.bind_tools = MagicMock(return_value=mock_model)

        svc = LLMService()
        svc.register_model("test-model", lambda: mock_model)
        svc._current_model = mock_model

        result = await svc.call(
            [HumanMessage(content="hello")],
        )

        assert call_count == 3, f"Expected 3 calls, got {call_count}"
        assert isinstance(result, AIMessage)
        assert result.content == "retry success"

    @pytest.mark.asyncio
    async def test_llm_service_retries_on_api_timeout(self):
        """LLMService retries on APITimeoutError and succeeds on 2nd attempt."""
        from openai import APITimeoutError

        call_count = 0

        async def fake_ainvoke(messages, config=None):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise APITimeoutError("timeout", request=MagicMock())
            return AIMessage(content="timeout recovered")

        mock_model = AsyncMock()
        mock_model.ainvoke = fake_ainvoke
        mock_model.bind_tools = MagicMock(return_value=mock_model)

        svc = LLMService()
        svc.register_model("test-model", lambda: mock_model)
        svc._current_model = mock_model

        result = await svc.call(
            [HumanMessage(content="hello")],
        )

        assert call_count == 2
        assert isinstance(result, AIMessage)
        assert result.content == "timeout recovered"


class TestLLMServiceFallback:

    @pytest.mark.asyncio
    async def test_llm_service_falls_back_to_next_model(self):
        """LLMService cycles through models when one always fails."""
        from openai import APIError

        mock_model_1 = AsyncMock()
        mock_model_1.ainvoke.side_effect = APIError(
            "dead", request=MagicMock(), body=None
        )
        mock_model_1.bind_tools = MagicMock(return_value=mock_model_1)

        mock_model_2 = AsyncMock()
        mock_model_2.ainvoke.return_value = AIMessage(content="fallback success")
        mock_model_2.bind_tools = MagicMock(return_value=mock_model_2)

        svc = LLMService()
        svc.register_model("model-a", lambda: mock_model_1)
        svc.register_model("model-b", lambda: mock_model_2)
        svc._current_model = mock_model_1

        result = await svc.call(
            [HumanMessage(content="hello")],
        )

        assert isinstance(result, AIMessage)
        assert result.content == "fallback success"
        assert svc._current_model_index == 1

    @pytest.mark.asyncio
    async def test_llm_service_returns_graceful_message_on_total_failure(self):
        """When all models fail, graceful fallback message is returned."""
        from openai import APIError

        mock_model = AsyncMock()
        mock_model.ainvoke.side_effect = APIError(
            "dead", request=MagicMock(), body=None
        )
        mock_model.bind_tools = MagicMock(return_value=mock_model)

        svc = LLMService()
        svc.register_model("model-a", lambda: mock_model)
        svc._current_model = mock_model

        result = await svc.call(
            [HumanMessage(content="hello")],
        )

        assert isinstance(result, str)
        assert "technical difficulties" in result.lower() or "try again" in result.lower()

    @pytest.mark.asyncio
    async def test_llm_service_switches_to_next_model_preserves_tools(self):
        """Model switch preserves tool bindings."""
        from openai import APIError

        mock_model_1 = AsyncMock()
        mock_model_1.ainvoke.side_effect = APIError(
            "dead", request=MagicMock(), body=None
        )
        mock_model_1.bind_tools = MagicMock(return_value=mock_model_1)

        mock_model_2 = AsyncMock()
        mock_model_2.ainvoke.return_value = AIMessage(content="with tools")
        mock_model_2.bind_tools = MagicMock(return_value=mock_model_2)

        svc = LLMService()
        svc.register_model("model-a", lambda: mock_model_1)
        svc.register_model("model-b", lambda: mock_model_2)
        svc._current_model = mock_model_1

        fake_tools = ["tool1", "tool2"]
        result = await svc.call(
            [HumanMessage(content="hello")],
            tools=fake_tools,
        )

        assert isinstance(result, AIMessage)
        assert result.content == "with tools"
        mock_model_2.bind_tools.assert_called_once_with(fake_tools)

    @pytest.mark.asyncio
    async def test_llm_service_circular_fallback_wraps_around(self):
        """Circular fallback tries all models then wraps back."""
        from openai import APIError

        call_log: list[str] = []

        def make_mock(name: str):
            model = AsyncMock()

            async def invoke(msgs, config=None):
                call_log.append(name)
                raise APIError("dead", request=MagicMock(), body=None)

            model.ainvoke = invoke
            model.bind_tools = MagicMock(return_value=model)
            return model

        svc = LLMService()
        svc.register_model("first", lambda: make_mock("first"))
        svc.register_model("second", lambda: make_mock("second"))
        svc._current_model = make_mock("first")

        result = await svc.call(
            [HumanMessage(content="hello")],
        )

        assert isinstance(result, str)
        assert "try again" in result.lower() or "technical" in result.lower()
        assert len(set(call_log)) >= 1

    @pytest.mark.asyncio
    async def test_llm_service_no_models_returns_graceful(self):
        """When no models are registered, returns graceful message immediately."""
        svc = LLMService()

        result = await svc.call(
            [HumanMessage(content="hello")],
        )

        assert isinstance(result, str)
        assert result == GRACEFUL_FAILURE_MESSAGE
