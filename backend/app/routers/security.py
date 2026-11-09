"""Security gate endpoint + agent-token issuance.

POST /api/security/gate  — runs the central security gate and returns the
backend decision. Non-allow decisions are recorded as security incidents.

POST /api/gateway/token  — issues a short-lived agent token after checking
the permission tables. Denied requests are audited."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from .. import permissions
from ..audit import log_event, log_incident
from ..auth import AuthUser, get_current_user
from ..gateway import GatewayDenied, issue_agent_token
from ..rate_limit import client_key, rate_limiter
from ..security_gate import ALLOW, BLOCK, RESTRICT, REVIEW, run_security_gate
from ..validation import AgentTokenIn, SecurityGateIn
from ..config import get_settings

router = APIRouter(prefix="/api", tags=["security-gate"])


@router.post("/security/gate")
def security_gate(
    payload: SecurityGateIn,
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> dict:
    settings = get_settings()
    rate_limiter.check(
        f"gate:{client_key(request, user.id)}", settings.rate_limit_default_per_min
    )

    verdict = run_security_gate(payload, user)

    if verdict.decision != ALLOW:
        log_incident(
            user_id=user.id,
            source_ip=request.client.host if request.client else None,
            attack_type=(verdict.layer2 or {}).get("attack_type") or "GATE_LAYER1",
            risk_level={
                BLOCK: "HIGH",
                REVIEW: "HIGH",
                RESTRICT: "MEDIUM",
            }.get(verdict.decision, "MEDIUM"),
            decision=verdict.decision,
            reason=verdict.reason,
            metadata={
                "route": str(request.url.path),
                "flagged_text": getattr(payload, "text", ""),
            },
        )

    return {
        "decision": verdict.decision,
        "layer1_violations": verdict.layer1_violations,
        "layer2": verdict.layer2,
        "reason": verdict.reason,
    }


@router.post("/gateway/token")
def gateway_token(
    payload: AgentTokenIn,
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> dict:
    settings = get_settings()
    rate_limiter.check(
        f"gateway:{client_key(request, user.id)}", settings.rate_limit_default_per_min
    )
    try:
        token, ttl = issue_agent_token(
            user, payload.agent, payload.tool, payload.operation, payload.data_scope
        )
    except GatewayDenied as exc:
        log_event(
            actor_id=user.id,
            actor_role=user.roles[0] if user.roles else None,
            action="AGENT_TOKEN_DENIED",
            entity="tools",
            entity_id=payload.tool,
            ip=request.client.host if request.client else None,
            metadata={"agent": payload.agent, "reason": exc.detail},
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.detail) from exc

    return {"agent_token": token, "expires_in": ttl, "tool": payload.tool, "agent": payload.agent}
