"""SQLite access and `PRAGMA user_version` migrations.

FINAL.md §8.1: SQLite, ``user_version`` migrations, ``foreign_keys=ON``, WAL.

This module is the only place in the project that opens a database file. It
holds no business logic and makes no policy decisions.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Final

#: Incremented whenever ``schema.sql`` gains a migration step.
SCHEMA_VERSION: Final[int] = 1

_SCHEMA_PATH: Final[Path] = Path(__file__).with_name("schema.sql")

#: ``sqlite3.Row`` by name, so tests and callers read columns by name.
Connection = sqlite3.Connection


def connect(path: str | Path, *, read_only: bool = False) -> Connection:
    """Open ``path``, create the schema, and return a configured connection.

    WAL and ``foreign_keys=ON`` are set on every connection, not once at
    startup: SQLite scopes both to the connection.
    """
    if not read_only:
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    # Durability matters more than throughput: a lost audit entry is a lost
    # record of intent to move money.
    conn.execute("PRAGMA synchronous = FULL")

    if not read_only:
        migrate(conn)
    return conn


def user_version(conn: Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def migrate(conn: Connection) -> None:
    """Apply migrations up to :data:`SCHEMA_VERSION`. Idempotent.

    Step 1 creates the whole schema from ``schema.sql``. Later steps are added
    as new ``if version < N`` blocks; a step must never rewrite an existing
    table, because the audit chain already references what was written.
    """
    current = user_version(conn)

    if current < 1:
        conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.execute(f"PRAGMA user_version = {1}")

    if user_version(conn) != SCHEMA_VERSION:
        raise RuntimeError(
            f"schema is at version {user_version(conn)}, expected {SCHEMA_VERSION}. "
            "A downgrade is not supported; the audit chain references what was written."
        )


@contextmanager
def transaction(conn: Connection) -> Iterator[Connection]:
    """Run a block as one transaction.

    The executor consumes an approval and records INTENT in the same
    transaction (§4.7). Either both happen or neither does.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def is_locked_error(exc: BaseException) -> bool:
    """True for SQLite's "database is locked" family.

    §4.16: a locked or unavailable database halts the executor rather than
    proceeding on stale balances.
    """
    message = str(exc).lower()
    return "database is locked" in message or "database table is locked" in message
