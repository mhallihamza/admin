"""Tool gateway.

Flow:
1. The user (verified session token) asks for an agent token:
   POST /api/gateway/token {agent, tool, operation, data_scope}.
   The backend checks tool_permissions (role × tool × operation × scope)
   and agent_permissions (agent × tool × operation) BEFORE issuing.
2. The agent calls a tool endpoint carrying BOTH the user token and the
   short-lived agent token (X-Agent-Token). The endpoint re-validates
   everything — defense in depth — and rejects + audits anything not
   allowed. Final decisions are always made here, never by the agent.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException, status

from . import permissions
from .auth import AuthUser, get_current_user
from .config import get_settings


@dataclass
class AgentTokenPayload:
    sub: str
    agent: str
    tool: str
    operation: str
    data_scope: str
    roles: list[str]
    jti: str


class GatewayDenied(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def issue_agent_token(
    user: AuthUser, agent: str, tool: str, operation: str, data_scope: str
) -> tuple[str, int]:
    if user.disabled:
        raise GatewayDenied("Account is disabled.")

    settings = get_settings()

    role_allowed = any(
        permissions.tool_permission_allowed(role, tool, operation, data_scope)
        for role in user.roles
    )
    if not role_allowed:
        raise GatewayDenied(f"Role is not allowed to use tool {tool}.")

    if not permissions.agent_permission_allowed(agent, tool, operation):
        raise GatewayDenied(f"Agent {agent} is not allowed to use tool {tool}.")

    now = int(__import__("time").time())
    payload = {
        "sub": user.id,
        "agent": agent,
        "tool": tool,
        "operation": operation,
        "data_scope": data_scope,
        "roles": user.roles,
        "iat": now,
        "exp": now + settings.agent_token_ttl_seconds,
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, settings.agent_token_secret, algorithm="HS256")
    return token, settings.agent_token_ttl_seconds


def verify_agent_token(token: str) -> AgentTokenPayload:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.agent_token_secret, algorithms=["HS256"]
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Agent token expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid agent token.") from exc

    for field in ("sub", "agent", "tool", "operation", "data_scope"):
        if not payload.get(field):
            raise HTTPException(status_code=401, detail="Invalid agent token payload.")

    return AgentTokenPayload(
        sub=payload["sub"],
        agent=payload["agent"],
        tool=payload["tool"],
        operation=payload["operation"],
        data_scope=payload["data_scope"],
        roles=payload.get("roles", []),
        jti=payload.get("jti", ""),
    )


def require_agent_token(tool: str):
    """Dependency for a tool endpoint: validates the agent token, re-checks
    the permission tables, and audits denials. Also requires the user
    session token to match the agent token subject."""

    def dependency(
        user: AuthUser = Depends(get_current_user),
        x_agent_token: str = Header(...),
    ) -> AgentTokenPayload:
        payload = verify_agent_token(x_agent_token)

        if payload.tool != tool:
            raise GatewayDenied("Agent token was not issued for this tool.")
        if payload.sub != user.id:
            raise GatewayDenied("Agent token does not belong to the calling user.")
        if user.disabled or not any(role in payload.roles for role in user.roles):
            raise GatewayDenied("Session role no longer matches the agent token.")

        role_allowed = any(
            permissions.tool_permission_allowed(role, payload.tool, payload.operation, payload.data_scope)
            for role in user.roles
        )
        agent_allowed = permissions.agent_permission_allowed(
            payload.agent, payload.tool, payload.operation
        )
        if not (role_allowed and agent_allowed):
            from . import audit

            audit.log_event(
                actor_id=user.id,
                actor_role=user.roles[0] if user.roles else None,
                action="TOOL_DENIED",
                entity="tools",
                entity_id=payload.tool,
                metadata={"agent": payload.agent, "operation": payload.operation},
            )
            raise GatewayDenied("Permission denied for this tool call.")

        return payload

    return dependency
