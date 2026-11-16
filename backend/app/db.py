"""Database access: connection pool, the per-request connection dependency, and the migration runner.

Every connection runs in autocommit mode. Code that writes wraps its statements in
`with conn.transaction():`, so they are committed together or rolled back together.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

BACKEND_DIR = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = BACKEND_DIR / "migrations"
SEED_FILE = BACKEND_DIR / "seed" / "demo.sql"
MIGRATION_LOCK_ID = 424242  # any constants; they make two app instances take turns migrating / seeding
SEED_LOCK_ID = 424243

_pool: ConnectionPool | None = None


def connect(database_url: str) -> psycopg.Connection:
    """A standalone connection (scripts and tests): autocommit, rows returned as dicts."""
    return psycopg.connect(database_url, autocommit=True, row_factory=dict_row)


def open_pool(database_url: str) -> None:
    global _pool
    _pool = ConnectionPool(database_url, min_size=1, max_size=10,
                           kwargs={"autocommit": True, "row_factory": dict_row}, open=True)


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def get_pool() -> ConnectionPool:
    if _pool is None:
        raise RuntimeError("The database pool is not open.")
    return _pool


def get_conn() -> Iterator[psycopg.Connection]:
    """FastAPI dependency: lend one pooled connection to a request, then return it to the pool."""
    with get_pool().connection() as conn:
        yield conn


def run_migrations(conn: psycopg.Connection, migrations_dir: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply every migrations/*.sql file not applied yet, in name order. Returns the names applied now."""
    applied_now: list[str] = []
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (MIGRATION_LOCK_ID,))
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations ("
                     "version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())")
        done = {row["version"] for row in conn.execute("SELECT version FROM schema_migrations")}
        for path in sorted(migrations_dir.glob("*.sql")):
            if path.name in done:
                continue
            conn.execute(path.read_text(encoding="utf-8"))  # whole file, no parameters: multi-statement is allowed
            conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.name,))
            applied_now.append(path.name)
    return applied_now


def seed_demo(conn: psycopg.Connection, force: bool = False) -> bool:
    """Load seed/demo.sql. Without `force` it does nothing (returns False) if any user exists.
    With `force` it first DELETES ALL DATA (every table except schema_migrations)."""
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (SEED_LOCK_ID,))
        if force:
            tables = [r["tablename"] for r in conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename <> 'schema_migrations'")]
            conn.execute(sql.SQL("TRUNCATE {} RESTART IDENTITY CASCADE").format(
                sql.SQL(", ").join(map(sql.Identifier, tables))))
        elif conn.execute("SELECT EXISTS (SELECT 1 FROM users) AS has_users").fetchone()["has_users"]:
            return False
        conn.execute(SEED_FILE.read_text(encoding="utf-8"))
    return True
