"""T011: Test tenant config caching — real Supabase DB.

All tests use real Supabase DB connections (no mocks).

Tests verify:
- async_get_tenant loads real data from Supabase
- async_get_tenant caches results (second call is faster/uses cache)
- Cache invalidation works correctly
"""

from __future__ import annotations


import pytest

from src.config.tenant_config import TenantConfig


class TestTenantCachingRealDB:

    @pytest.mark.asyncio
    async def test_async_get_tenant_returns_real_config(self):
        """async_get_tenant should load real data from Supabase for 'flower_shop'."""
        from src.config import tenant_config as module

        # Clear cache to force fresh DB lookup
        module._tenant_cache.clear()
        module._db_config = None

        try:
            from src.config.tenant_config import async_get_tenant

            result = await async_get_tenant("flower_shop")

            assert isinstance(result, TenantConfig), (
                f"Expected TenantConfig, got {type(result).__name__}"
            )
            assert result.tenant_id == "flower_shop", (
                f"Expected tenant_id='flower_shop', got '{result.tenant_id}'"
            )
            assert result.business_name, "business_name should not be empty"
            assert result.agent.name, "agent name should not be empty"
        finally:
            module._tenant_cache.clear()
            module._db_config = None

    @pytest.mark.asyncio
    async def test_async_get_tenant_caches_result(self):
        """async_get_tenant should cache results — second call uses cache."""
        from src.config import tenant_config as module

        # Clear everything
        module._tenant_cache.clear()
        module._db_config = None

        try:
            from src.config.tenant_config import async_get_tenant

            # First call — hits DB
            result1 = await async_get_tenant("flower_shop")
            assert isinstance(result1, TenantConfig)

            # Check that cache entry exists
            assert "flower_shop" in module._tenant_cache, (
                "Cache should contain 'flower_shop' after first call"
            )

            # Second call — should use cache
            result2 = await async_get_tenant("flower_shop")
            assert isinstance(result2, TenantConfig)

            # Results should be identical
            assert result1.tenant_id == result2.tenant_id
            assert result1.business_name == result2.business_name
        finally:
            module._tenant_cache.clear()
            module._db_config = None

    @pytest.mark.asyncio
    async def test_invalidate_tenant_cache_clears_entry(self):
        """invalidate_tenant_cache should clear specific tenant's cache."""
        from src.config import tenant_config as module
        from src.config.tenant_config import async_get_tenant, invalidate_tenant_cache

        module._tenant_cache.clear()
        module._db_config = None

        try:
            # Load and cache
            await async_get_tenant("flower_shop")
            assert "flower_shop" in module._tenant_cache

            # Invalidate specific tenant
            invalidate_tenant_cache("flower_shop")
            assert "flower_shop" not in module._tenant_cache
        finally:
            module._tenant_cache.clear()
            module._db_config = None

    @pytest.mark.asyncio
    async def test_invalidate_all_caches_clears_everything(self):
        """invalidate_tenant_cache() with no args clears all entries."""
        from src.config import tenant_config as module
        from src.config.tenant_config import async_get_tenant, invalidate_tenant_cache

        module._tenant_cache.clear()
        module._db_config = None

        try:
            # Load two tenants
            await async_get_tenant("flower_shop")
            await async_get_tenant("tech_store")
            assert "flower_shop" in module._tenant_cache
            assert "tech_store" in module._tenant_cache

            # Clear all
            invalidate_tenant_cache()
            assert len(module._tenant_cache) == 0
        finally:
            module._tenant_cache.clear()
            module._db_config = None

    @pytest.mark.asyncio
    async def test_async_get_tenant_tech_store(self):
        """async_get_tenant should load real data from Supabase for 'tech_store'."""
        from src.config import tenant_config as module
        from src.config.tenant_config import async_get_tenant

        module._tenant_cache.clear()
        module._db_config = None

        try:
            result = await async_get_tenant("tech_store")

            assert isinstance(result, TenantConfig)
            assert result.tenant_id == "tech_store"
            assert result.business_name, "business_name should not be empty"
        finally:
            module._tenant_cache.clear()
            module._db_config = None
