"""Postgres access for the backend (server-side service connection —
bypasses RLS by design; every write is audited). Connections are lazy so
that importing this module (and running the offline test suite) never
touches the database."""

from __future__ import annotations

import threading
from typing import Any

from .config import get_settings

_pool: Any = None
_pool_lock = threading.Lock()


def _get_pool() -> Any:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                settings = get_settings()
                if not settings.db_url:
                    raise RuntimeError("SUPABASE_DB_URL is not configured")
                from psycopg.rows import dict_row
                from psycopg_pool import ConnectionPool

                def _connection_alive(conn: Any) -> None:
                    # check must be a callable in psycopg_pool >= 3.2 (a
                    # string raises TypeError at checkout and the pool
                    # discards/retries forever -> PoolTimeout).
                    conn.execute("select 1")

                _pool = ConnectionPool(
                    conninfo=settings.db_url,
                    kwargs={"row_factory": dict_row, "sslmode": "require",
                            # PgBouncer transaction pooler cannot guarantee stable prepared statements.
                            "prepare_threshold": None},
                    min_size=1,
                    max_size=5,
                    # The transaction pooler drops idle connections: verify
                    # each connection is alive before handing it out.
                    max_idle=60,
                    check=_connection_alive,
                    open=True,
                )
    return _pool


def fetch_one(query: str, params: tuple | list = ()) -> dict[str, Any] | None:
    with _get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row else None


def fetch_all(query: str, params: tuple | list = ()) -> list[dict[str, Any]]:
    with _get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]


def execute(query: str, params: tuple | list = ()) -> None:
    with _get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
        conn.commit()
