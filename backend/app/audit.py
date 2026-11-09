"""Audit logging: every security-relevant decision is written to the
audit_events table; security gate rejections also to security_incidents.
Writes go through the server-side connection (service role)."""

from __future__ import annotations

from typing import Any

from . import db


def log_event(
    actor_id: str | None,
    actor_role: str | None,
    action: str,
    entity: str,
    entity_id: str | None = None,
    ip: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    db.execute(
        """
        insert into audit_events (actor_id, actor_role, action, entity, entity_id, ip, metadata)
        values (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            actor_id,
            actor_role,
            action,
            entity,
            entity_id,
            ip,
            __import__("json").dumps(metadata or {}),
        ),
    )


def log_incident(
    user_id: str | None,
    source_ip: str | None,
    attack_type: str,
    risk_level: str,
    decision: str,
    reason: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    db.execute(
        """
        insert into security_incidents
            (user_id, source_ip, attack_type, risk_level, decision, reason, metadata)
        values (%s, %s, %s, %s::risk_level, %s, %s, %s)
        """,
        (
            user_id,
            source_ip,
            attack_type,
            risk_level,
            decision,
            reason,
            __import__("json").dumps(metadata or {}),
        ),
    )
