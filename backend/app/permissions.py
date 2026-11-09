"""Permission lookups for the tool gateway, backed by the agent_permissions
and tool_permissions tables. Isolated in one module so tests can swap the
data source without touching the gateway logic."""

from __future__ import annotations

from . import db


def tool_permission_allowed(role: str, tool: str, operation: str, data_scope: str) -> bool:
    row = db.fetch_one(
        """
        select allowed from tool_permissions
        where tool_key = %s and role::text = %s and operation = %s and data_scope = %s
        """,
        (tool, role, operation, data_scope),
    )
    return bool(row and row["allowed"])


def agent_permission_allowed(agent: str, tool: str, operation: str) -> bool:
    row = db.fetch_one(
        """
        select allowed from agent_permissions
        where agent_key = %s and tool_key = %s and operation = %s
        """,
        (agent, tool, operation),
    )
    return bool(row and row["allowed"])
