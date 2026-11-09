"""Admin reads and writes behind the real `/api/admin/*` endpoints.
All administrative mutations are explicitly audited."""

from __future__ import annotations

import uuid as uuid_mod
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from .. import db
from ..audit import log_event
from ..auth import AuthUser, require_roles

router = APIRouter(prefix="/api/admin", tags=["admin"])

_ADMINS = ("SYSTEM_ADMIN", "PLATFORM_SUPER_ADMIN")
_AUDIT_ROLES = ("SYSTEM_ADMIN", "PLATFORM_SUPER_ADMIN", "SECURITY_AUDITOR")
_AGENTS = ["SUPERVISOR", "PROCEDURE_AGENT", "LEGAL_RESEARCH_AGENT",
           "DOCUMENT_ADMIN_AGENT", "DETECTION_AGENT"]
_TOOLS = ["VECTOR_RETRIEVAL", "GRAPH_RETRIEVAL", "DOCUMENT_INDEX",
          "SECURITY_GATE", "HUMAN_HANDOFF"]


def _iso(value: Any) -> str:
    try:
        return value.isoformat().replace("+00:00", "")
    except Exception:
        return str(value)


# ---------------------------------------------------------------------------
# Audit feed (shared by security page + admin users page)
# ---------------------------------------------------------------------------
@router.get("/audit-events")
def list_audit_events(
    limit: int = Query(8, ge=1, le=100),
    action: str | None = None,
    user: AuthUser = Depends(require_roles(*_AUDIT_ROLES)),
) -> dict:
    params: list = []
    where = ""
    if action:
        where = " where a.action = %s"
        params.append(action)
    params.append(limit)
    rows = db.fetch_all(
        f"""
        select a.id, a.action, coalesce(p.email, 'system') as actor,
               a.entity, coalesce(a.entity_id, '') as detail, a.created_at
        from audit_events a
        left join profiles p on p.id = a.actor_id
        {where}
        order by a.created_at desc
        limit %s
        """,
        params,
    )
    return {"events": [{
        "id": str(r["id"]), "action": r["action"], "actor": r["actor"],
        "entity": r["entity"], "detail": r["detail"],
        "createdAt": _iso(r["created_at"]),
    } for r in rows]}


# ---------------------------------------------------------------------------
# Workflows monitor (executions are written by POST /api/logs/execution)
# ---------------------------------------------------------------------------
@router.get("/workflows")
def workflow_executions(user: AuthUser = Depends(require_roles(*_ADMINS))) -> dict:
    rows = db.fetch_all(
        """
        select id, entity_id as workflow, created_at,
               upper(coalesce(metadata->>'status', 'RUNNING')) as status,
               coalesce((metadata->>'duration_ms')::int, 0) as duration_ms
        from audit_events
        where action = 'WORKFLOW_EXECUTION'
        order by created_at desc
        limit 100
        """,
    )
    return {"workflows": [{
        "id": str(r["id"]), "workflow": r["workflow"] or "workflow",
        "status": r["status"] if r["status"] in {"SUCCESS", "ERROR", "RUNNING"} else "RUNNING",
        "durationMs": int(r["duration_ms"] or 0), "startedAt": _iso(r["created_at"]),
    } for r in rows]}


# ---------------------------------------------------------------------------
# Overview KPIs + chart source data
# ---------------------------------------------------------------------------
@router.get("/overview")
def admin_overview(user: AuthUser = Depends(require_roles(*_ADMINS))) -> dict:
    counts = db.fetch_one(
        """
        select
          (select count(*) from profiles) as users,
          (select count(*) from audit_events where action = 'CHAT_MESSAGE_ACCEPTED'
             and created_at >= date_trunc('day', now())) as requests_today,
          (select count(*) from security_incidents where decision = 'BLOCK') as blocked_requests,
          (select count(*) from audit_events where action = 'WORKFLOW_EXECUTION'
             and metadata->>'status' = 'ERROR') as workflow_errors
        """,
    ) or {}
    by_day = db.fetch_all(
        """
        with days as (select generate_series(current_date - 6, current_date, interval '1 day')::date as day)
        select to_char(d.day, 'DD/MM') as day,
               (select count(*) from audit_events a
                where a.action = 'CHAT_MESSAGE_ACCEPTED'
                  and a.created_at >= d.day and a.created_at < d.day + 1) as count
        from days d order by d.day
        """,
    )
    by_attack = db.fetch_all(
        """
        select coalesce(attack_type, 'GATE_LAYER1') as type, count(*) as count
        from security_incidents
        where decision in ('BLOCK', 'REVIEW', 'RESTRICT')
        group by coalesce(attack_type, 'GATE_LAYER1')
        order by count desc, type
        limit 10
        """,
    )
    return {
        "users": int(counts.get("users") or 0),
        "requestsToday": int(counts.get("requests_today") or 0),
        "blockedRequests": int(counts.get("blocked_requests") or 0),
        "workflowErrors": int(counts.get("workflow_errors") or 0),
        "requestsPerDay": [{"day": r["day"], "count": int(r["count"])} for r in by_day],
        "blockedByAttack": [{"type": r["type"], "count": int(r["count"])} for r in by_attack],
    }

# ---------------------------------------------------------------------------
# Users & roles (read all/write role, disable — audited)
# ---------------------------------------------------------------------------
@router.get("/users")
def list_users(user: AuthUser = Depends(require_roles(*_ADMINS))) -> dict:
    rows = db.fetch_all(
        """
        select p.id, p.email, p.full_name, p.disabled, p.created_at,
               coalesce(array_agg(ur.role::text order by ur.role::text)
                        filter (where ur.role is not null), array[]::text[]) as roles
        from profiles p
        left join user_roles ur on ur.user_id = p.id
        group by p.id, p.email, p.full_name, p.disabled, p.created_at
        order by p.created_at asc
        limit 500
        """,
    )
    return {"users": [{
        "id": str(r["id"]), "email": r["email"], "fullName": r["full_name"],
        "roles": list(r["roles"] or []), "disabled": bool(r["disabled"]),
        "createdAt": _iso(r["created_at"]),
    } for r in rows]}


class RolePatch(BaseModel):
    role: str


class DisabledPatch(BaseModel):
    disabled: bool


@router.patch("/users/{user_id}/role")
def set_user_role(user_id: str, payload: RolePatch,
                  user: AuthUser = Depends(require_roles(*_ADMINS))) -> dict:
    role = payload.role.upper()
    allowed = {"CITIZEN", "EMPLOYEE", "CONTENT_APPROVER", "SYSTEM_ADMIN",
               "SECURITY_AUDITOR", "PLATFORM_SUPER_ADMIN", "VISITOR"}
    if role not in allowed:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Rôle invalide")
    try:
        candidate = str(uuid_mod.UUID(user_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user id invalide") from exc

    # Remplacement unique des rôles (expérience actuelle à rôle unique).
    row = db.fetch_one(
        """
        with del as (delete from user_roles where user_id = %s),
        ins as (
            insert into user_roles (user_id, role, granted_by)
            select %s, %s, %s
            where exists (select 1 from profiles where id = %s)
            returning user_id
        )
        select user_id from ins
        """,
        (candidate, candidate, role, user.id, candidate),
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    log_event(actor_id=user.id, actor_role=user.roles[0] if user.roles else None,
              action="ROLE_CHANGED", entity="user_roles", entity_id=candidate,
              metadata={"role": role})
    rows = db.fetch_all("select role::text as role from user_roles where user_id = %s order by role::text", (candidate,))
    return {"roles": [r["role"] for r in rows]}


@router.patch("/users/{user_id}/disabled")
def set_user_disabled(user_id: str, payload: DisabledPatch,
                      user: AuthUser = Depends(require_roles(*_ADMINS))) -> dict:
    try:
        candidate = str(uuid_mod.UUID(user_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user id invalide") from exc
    if candidate == user.id and payload.disabled:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Vous ne pouvez pas vous désactiver vous-même.")

    row = db.fetch_one(
        "update profiles set disabled = %s, updated_at = now() where id = %s returning id",
        (payload.disabled, candidate),
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    log_event(actor_id=user.id, actor_role=user.roles[0] if user.roles else None,
              action="USER_DISABLED" if payload.disabled else "USER_ENABLED",
              entity="profiles", entity_id=candidate)
    return {"disabled": payload.disabled}


# ---------------------------------------------------------------------------
# Agent × tool permission matrix (agent_permissions)
# ---------------------------------------------------------------------------
@router.get("/permissions")
def list_agent_permissions(user: AuthUser = Depends(require_roles(*_ADMINS))) -> dict:
    placeholders = ", ".join(["%s"] * len(_AGENTS))
    rows = db.fetch_all(
        f"""
        select a.agent_key as agent, t.tool_key as tool, p.allowed
        from unnest(array[{placeholders}]) as a(agent_key)
        cross join unnest(array[{', '.join(['%s'] * len(_TOOLS))}]) as t(tool_key)
        left join agent_permissions p
          on p.agent_key = a.agent_key and p.tool_key = t.tool_key and p.operation = 'execute'
        order by a.agent_key, t.tool_key
        """,
        [*_AGENTS, *_TOOLS],
    )
    return {"permissions": [{
        "id": f"{r['agent']}:{r['tool']}:execute", "agent": r["agent"],
        "tool": r["tool"], "operation": "execute",
        "allowed": bool(r["allowed"]) if r["allowed"] is not None else False,
    } for r in rows]}


class PermissionPatch(BaseModel):
    agent: str
    tool: str
    operation: str = "execute"
    allowed: bool


@router.put("/permissions")
def set_agent_permission(payload: PermissionPatch, user: AuthUser = Depends(require_roles(*_ADMINS))) -> dict:
    agent = payload.agent.upper()
    tool = payload.tool.upper()
    operation = payload.operation.lower()
    if agent not in _AGENTS or tool not in _TOOLS or operation != "execute":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Permission hors matrice")

    db.execute(
        """
        insert into agent_permissions (agent_key, tool_key, operation, allowed, updated_by)
        values (%s, %s, %s, %s, %s)
        on conflict (agent_key, tool_key, operation)
        do update set allowed = excluded.allowed, updated_by = excluded.updated_by, updated_at = now()
        """,
        (agent, tool, operation, payload.allowed, user.id),
    )
    log_event(actor_id=user.id, actor_role=user.roles[0] if user.roles else None,
              action="PERMISSION_TOGGLED", entity="agent_permissions",
              entity_id=f"{agent}:{tool}:{operation}",
              metadata={"allowed": payload.allowed})
    return {"id": f"{agent}:{tool}:{operation}", "agent": agent, "tool": tool,
            "operation": operation, "allowed": payload.allowed}
