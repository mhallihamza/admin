"""Identity endpoint: returns what the verified token + DB say about the
caller — nothing from user input."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import AuthUser, get_current_user

router = APIRouter(prefix="/api", tags=["identity"])


@router.get("/me")
def me(user: AuthUser = Depends(get_current_user)) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "roles": user.roles,
        "disabled": user.disabled,
    }
