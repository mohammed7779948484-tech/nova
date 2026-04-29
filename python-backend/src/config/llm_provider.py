"""LLM provider factory.

Clean, modular provider system. Each tenant picks their provider
and model in config.yaml. Adding a new provider = one elif branch.

Supported providers:
  - openai   → ChatOpenAI  (gpt-4o-mini, gpt-4o, etc.)
  - anthropic → ChatAnthropic (claude-sonnet, claude-haiku, etc.)
  - google   → ChatGoogleGenerativeAI (gemini-2.0-flash, gemini-1.5-pro, etc.)

OpenAI-compatible endpoints (e.g. longcat.chat) are supported by
setting OPENAI_API_BASE in .env and using the "openai" provider.
"""

from __future__ import annotations

import os

from langchain_core.language_models import BaseChatModel

from src.config.tenant_config import TenantConfig


def create_llm(tenant_config: TenantConfig) -> BaseChatModel:
    """Create an LLM instance based on tenant config.

    The provider is determined by the ``llm.provider`` field in config.yaml.
    Each provider maps to a LangChain chat model class.

    For OpenAI-compatible endpoints (e.g. longcat.chat), set
    OPENAI_API_BASE in .env and use provider "openai" with the
    custom model name.
    """
    cfg = tenant_config.llm
    provider = cfg.provider.lower()

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        kwargs: dict = {
            "model": cfg.model,
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_tokens,
        }

        api_base = os.getenv("OPENAI_API_BASE", "")
        if api_base:
            kwargs["base_url"] = api_base

        api_key = os.getenv("OPENAI_API_KEY", "")
        if api_key:
            kwargs["api_key"] = api_key

        return ChatOpenAI(**kwargs)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=cfg.model,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=cfg.model,
            temperature=cfg.temperature,
            max_output_tokens=cfg.max_tokens,
        )

    raise ValueError(
        f"Unknown LLM provider: '{provider}'. "
        f"Supported: openai, anthropic, google"
    )
