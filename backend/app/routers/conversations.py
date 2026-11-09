"""Citizen conversation list — backed by the conversations/messages tables.
Ownership is re-checked in the service connection; RLS policies keep the
browser path equivalent."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import db
from ..auth import AuthUser, require_roles

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("")
def list_conversations(user: AuthUser = Depends(require_roles("CITIZEN", "EMPLOYEE", "CONTENT_APPROVER", "SYSTEM_ADMIN", "PLATFORM_SUPER_ADMIN"))) -> dict:
    rows = db.fetch_all(
        """
        select c.id, c.title, c.updated_at,
               (select count(*) from messages m where m.conversation_id = c.id) as message_count
        from conversations c
        where c.user_id = %s
        order by c.updated_at desc, c.created_at desc
        limit 100
        """,
        (user.id,),
    )
    return {
        "conversations": [
            {
                "id": str(row["id"]),
                "title": row["title"],
                "updated_at": row["updated_at"].isoformat() if hasattr(row["updated_at"], "isoformat") else str(row["updated_at"]),
                "message_count": int(row["message_count"] or 0),
            }
            for row in rows
        ]
    }
