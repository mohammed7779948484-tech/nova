"""T011: Test tenant config caching.

PDCA Called Shot:
- test_async_get_tenant_caches_result: call async_get_tenant("flower_shop") twice
  with a mocked DB backend, verify the DB is called only once.
  Expected RED: AssertionError 2 != 1 (because no caching exists)
"""

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.config.tenant_config import TenantConfig, AgentConfig


@pytest.fixture()
def mock_agent_config():
    """Create a mock AgentConfig for DBTenantConfig to return."""
    from src.config.db_tenant_config import DBAgentConfig

    return DBAgentConfig(
        agent_id="test-uuid",
        tenant_id="test-tenant-uuid",
        tenant_slug="flower_shop",
        business_name="Flower Shop",
        language="en",
        name="Florist Bot",
        role="Sales Consultant",
        personality="You are a helpful florist.",
        rules=["Be polite"],
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        llm_temperature=0.7,
        llm_max_tokens=1024,
    )


class TestTenantCaching:

    @pytest.mark.asyncio
    async def test_async_get_tenant_caches_result(self, mock_agent_config):
        """async_get_tenant should cache results — DB called only once for 2 calls."""
        from src.config import tenant_config as module

        original_cache = module._tenant_cache.copy() if hasattr(module, '_tenant_cache') else {}

        call_count = 0

        async def mock_get_agent_by_slug(slug):
            nonlocal call_count
            call_count += 1
            return mock_agent_config

        with patch.object(module, "_get_db_config") as mock_get_db:
            db_instance = AsyncMock()
            db_instance.get_agent_by_slug = mock_get_agent_by_slug
            db_instance.agent_config_to_tenant_config = MagicMock(
                return_value={
                    "tenant_id": "flower_shop",
                    "business_name": "Flower Shop",
                    "language": "en",
                    "agent": {
                        "name": "Florist Bot",
                        "role": "Sales Consultant",
                        "personality": "You are a helpful florist.",
                        "rules": ["Be polite"],
                    },
                    "llm": {
                        "provider": "openai",
                        "model": "gpt-4o-mini",
                        "temperature": 0.7,
                        "max_tokens": 1024,
                    },
                    "features": {
                        "image_search": True,
                        "promotions": True,
                        "upsell": True,
                    },
                }
            )
            mock_get_db.return_value = db_instance

            from src.config.tenant_config import async_get_tenant

            try:
                result1 = await async_get_tenant("flower_shop")
                result2 = await async_get_tenant("flower_shop")

                assert call_count == 1, (
                    f"Expected DB to be called once, but was called {call_count} times"
                )
            finally:
                if hasattr(module, '_tenant_cache'):
                    module._tenant_cache.clear()