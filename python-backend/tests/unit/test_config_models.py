"""T007: Test AgentConfig name collision fix.

PDCA Called Shot:
- test_agent_config_and_db_agent_config_are_distinct: verify AgentConfig
  (from tenant_config) and DBAgentConfig (from db_tenant_config) are different classes.
  Expected RED: ImportError: cannot import name 'DBAgentConfig'
- test_db_agent_config_has_instructions_field: verify DBAgentConfig has
  instructions: list[str] field.
  Expected RED: same ImportError
"""

import dataclasses

import pytest

from src.config.tenant_config import AgentConfig


class TestAgentConfigDistinct:

    def test_agent_config_and_db_agent_config_are_distinct(self):
        """AgentConfig (YAML) and DBAgentConfig (DB) must be different classes."""
        from src.config.db_tenant_config import DBAgentConfig

        assert AgentConfig is not DBAgentConfig, (
            "AgentConfig and DBAgentConfig should be distinct classes"
        )

    def test_db_agent_config_has_instructions_field(self):
        """DBAgentConfig must have an instructions: list[str] field."""
        from src.config.db_tenant_config import DBAgentConfig

        field_names = {f.name for f in dataclasses.fields(DBAgentConfig)}
        assert "instructions" in field_names, (
            f"DBAgentConfig missing 'instructions' field. Got: {field_names}"
        )