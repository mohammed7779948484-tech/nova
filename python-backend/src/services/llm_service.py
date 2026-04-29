"""LLM Service — retry with tenacity, circular fallback across models, graceful degradation.

Adopted from reference-template/app/services/llm/service.py:39-334.
Simplified for Nova Backend's single-graph architecture where
create_llm() produces a tenant-specific model.
"""

from __future__ import annotations

import asyncio
import structlog
from typing import Any

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)

GRACEFUL_FAILURE_MESSAGE = (
    "I'm experiencing technical difficulties. Please try again shortly."
)

MAX_RETRIES = 3
TOTAL_TIMEOUT = 60


class LLMService:
    """Service for managing LLM calls with retries and circular fallback.

    Architecture:
    - Manages a list of model factories (callable() -> BaseChatModel)
    - On persistent failure from one model, switches to the next
    - Re-binds tools after each model switch
    - On total failure, returns a graceful error message
    """

    def __init__(self) -> None:
        self._current_model_index: int = 0
        self._current_model: Any = None
        self._bound_tools: list = []
        self._models: list[dict[str, Any]] = []

    def register_model(self, name: str, factory: Any) -> None:
        """Register a model factory function.

        Args:
            name: Display name for the model.
            factory: Callable that returns a BaseChatModel instance.
        """
        self._models.append({"name": name, "factory": factory})

    def _build_model(self, index: int, tools: list | None = None) -> Any:
        """Instantiate a model from its factory, optionally binding tools."""
        entry = self._models[index]
        model = entry["factory"]()
        if tools:
            model = model.bind_tools(tools)
        return model

    def _build_current_model(self, tools: list | None = None) -> Any:
        """Build the model at the current index."""
        if not self._models:
            return None
        return self._build_model(self._current_model_index, tools)

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True,
    )
    async def _invoke_with_retry(
        self,
        model: Any,
        messages: list[BaseMessage],
        config: RunnableConfig | None = None,
    ) -> BaseMessage:
        """Invoke a model with automatic retry on transient errors."""
        return await model.ainvoke(messages, config=config)

    def _switch_to_next_model(self) -> bool:
        """Advance to the next model in the registry (circular).

        Returns:
            True on success, False if no models registered.
        """
        if not self._models:
            return False

        try:
            next_index = (self._current_model_index + 1) % len(self._models)
            old_name = self._models[self._current_model_index]["name"]
            new_name = self._models[next_index]["name"]
            logger.warning("switching_model", from_model=old_name, to_model=new_name)

            self._current_model_index = next_index
            self._current_model = self._build_model(
                next_index, self._bound_tools or None
            )
            return True
        except Exception:
            logger.exception("model_switch_failed")
            return False

    async def call(
        self,
        messages: list[BaseMessage],
        tenant_config: Any | None = None,
        config: RunnableConfig | None = None,
        tools: list | None = None,
    ) -> BaseMessage | str:
        """Call the LLM with retry and circular fallback.

        Args:
            messages: Conversation messages to send.
            tenant_config: Optional TenantConfig for creating model.
            config: Optional RunnableConfig for LangGraph.
            tools: Optional list of LangChain tools to bind.

        Returns:
            BaseMessage on success, or a graceful fallback string on total failure.
        """
        if tools:
            self._bound_tools = tools

        if self._current_model is None:
            model = self._build_current_model(self._bound_tools or None)
            if model is None:
                return GRACEFUL_FAILURE_MESSAGE
            self._current_model = model

        total = len(self._models)
        if total == 0:
            return GRACEFUL_FAILURE_MESSAGE

        models_tried = 0

        for _ in range(total):
            try:
                return await asyncio.wait_for(
                    self._invoke_with_retry(self._current_model, messages, config),
                    timeout=TOTAL_TIMEOUT,
                )
            except Exception:
                models_tried += 1
                logger.exception(
                    "llm_call_failed",
                    model=self._models[self._current_model_index]["name"],
                    tried=models_tried,
                    total=total,
                )

                if not self._switch_to_next_model():
                    break

        logger.error("all_models_exhausted", tried=models_tried)
        return GRACEFUL_FAILURE_MESSAGE


llm_service = LLMService()
