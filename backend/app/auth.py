"""Authentication: verifies the Supabase access token from the
Authorization header. Identity and roles ALWAYS come from the verified
token + database lookup — never from user input or request bodies.

Verification mode: network check against Supabase /auth/v1/user (the
project uses legacy symmetric JWT keys and no JWKS is exposed), with a
short TTL cache. The service role key stays server-side.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import db
from .config import get_settings

logger = logging.getLogger("app.auth")

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthUser:
    id: str
    email: str
    roles: list[str] = field(default_factory=list)
    disabled: bool = False

    def has_any_role(self, *roles: str) -> bool:
        return any(role in self.roles for role in roles)


class TokenVerifier:
    """Verifies access tokens against Supabase with a small TTL cache."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[dict | None, float]] = {}

    def _cached(self, token: str) -> dict | None | None:
        entry = self._cache.get(token)
        if not entry:
            return None
        user, expires_at = entry
        if time.monotonic() > expires_at:
            self._cache.pop(token, None)
            return None
        return user

    def verify(self, token: str) -> dict:
        settings = get_settings()
        if not settings.supabase_url or not settings.service_role_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication is not configured on the server.",
            )

        cached = self._cached(token)
        if cached is not None:
            return cached

        try:
            response = httpx.get(
                f"{settings.supabase_url}/auth/v1/user",
                headers={
                    "apikey": settings.service_role_key,
                    "Authorization": f"Bearer {token}",
                },
                timeout=5.0,
            )
        except httpx.HTTPError as exc:  # network failure — fail closed
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unreachable.",
            ) from exc

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = response.json()
        self._cache[token] = (user, time.monotonic() + settings.auth_verify_cache_seconds)
        return user


verifier = TokenVerifier()


def load_user_roles(user_id: str) -> tuple[list[str], bool]:
    """Roles + disabled flag, read from the database (RLS tables, service connection)."""
    try:
        profile = db.fetch_one(
            "select disabled from profiles where id = %s", (user_id,)
        )
        role_rows = db.fetch_all(
            "select role from user_roles where user_id = %s", (user_id,)
        )
    except Exception as exc:  # DB unavailable — fail closed
        logger.exception("Role lookup failed for user %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authorization store unreachable.",
        ) from exc
    roles = [row["role"] for row in role_rows]
    disabled = bool(profile["disabled"]) if profile else False
    return roles, disabled


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthUser:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = verifier.verify(credentials.credentials)
    user_id = payload.get("id") or payload.get("sub") or ""
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload.")
    email = payload.get("email") or ""
    roles, disabled = load_user_roles(user_id)
    return AuthUser(id=user_id, email=email, roles=roles, disabled=disabled)


def require_roles(*allowed: str):
    """Role-based authorization dependency. Fails closed (403)."""

    def dependency(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.disabled:
            raise HTTPException(status_code=403, detail="Account is disabled.")
        if not user.has_any_role(*allowed):
            raise HTTPException(status_code=403, detail="Insufficient role.")
        return user

    return dependency
