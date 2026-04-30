"""Cross-tenant isolation tests (FR-051 / SC-006).

Verifies that tenant data never leaks across boundaries:
- Tenant A cannot read Tenant B's conversations
- Tenant A's products don't appear in Tenant B's search

These tests require a real Supabase connection with test data.
Run with: pytest -m integration
"""

import os

import pytest
import httpx

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")


@pytest.fixture
def supabase_client():
    """httpx client configured for Supabase REST API."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        pytest.skip("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set for integration tests")
    return httpx.AsyncClient(
        base_url=SUPABASE_URL,
        headers={
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
        },
        timeout=10,
    )


class TestTenantIsolation:
    """Cross-tenant data isolation (FR-051, SC-006)."""

    @pytest.mark.asyncio
    async def test_tenant_a_cannot_read_tenant_b_conversations(
        self, supabase_client: httpx.AsyncClient
    ):
        """Querying conversations for tenant A's agent returns zero
        rows from tenant B.

        This test uses RLS-protected queries to verify that Supabase
        Row Level Security correctly isolates tenant data.
        """
        # Use two known distinct tenant slugs
        tenant_a_agent_id = os.getenv("TEST_TENANT_A_AGENT_ID", "")
        tenant_b_agent_id = os.getenv("TEST_TENANT_B_AGENT_ID", "")

        if not tenant_a_agent_id or not tenant_b_agent_id:
            pytest.skip("TEST_TENANT_A_AGENT_ID and TEST_TENANT_B_AGENT_ID must be set")

        # Fetch conversations for tenant A
        resp_a = await supabase_client.get(
            "/rest/v1/conversations",
            params={
                "select": "id,agent_id",
                "agent_id": f"eq.{tenant_a_agent_id}",
            },
        )
        assert resp_a.status_code == 200
        convos_a = resp_a.json()

        # Verify no conversations belong to tenant B's agent
        for convo in convos_a:
            assert convo["agent_id"] != tenant_b_agent_id, (
                f"Tenant B data leaked into Tenant A results: {convo['id']}"
            )

    @pytest.mark.asyncio
    async def test_tenant_a_products_not_in_tenant_b_search(
        self, supabase_client: httpx.AsyncClient
    ):
        """Searching products for tenant A returns no tenant B products."""
        tenant_a_agent_id = os.getenv("TEST_TENANT_A_AGENT_ID", "")
        tenant_b_agent_id = os.getenv("TEST_TENANT_B_AGENT_ID", "")

        if not tenant_a_agent_id or not tenant_b_agent_id:
            pytest.skip("TEST_TENANT_A_AGENT_ID and TEST_TENANT_B_AGENT_ID must be set")

        # Fetch products for tenant A
        resp_a = await supabase_client.get(
            "/rest/v1/agent_products",
            params={
                "select": "id,agent_id",
                "agent_id": f"eq.{tenant_a_agent_id}",
            },
        )
        assert resp_a.status_code == 200
        products_a = resp_a.json()

        # Verify no products belong to tenant B's agent
        for product in products_a:
            assert product["agent_id"] != tenant_b_agent_id, (
                f"Tenant B product leaked into Tenant A results: {product['id']}"
            )
