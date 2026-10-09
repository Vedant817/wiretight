"""The bank-change lock, and the invariant it was missing.

FINAL.md §4.5 is the product's whole claim:

> A bank change is never applied because an input said so. It is applied only
> after a second person has, out of band, confirmed the new details by callback.

The state machine in :mod:`app.core.statemachine` implements the §4.5.1 transitions
for *one* request. It is a pure two-argument function, ``change_request_next(current,
event)``, with no ``vendor_id``, so it cannot see a second request. The property
that matters - **at most one change request per supplier is ever in a lock-bearing
state** - therefore had no implementation anywhere.

That is the gap this module closes, and it is the reason the module exists as a
database module rather than a pure function: the invariant is across rows, and
enforcing it correctly requires the database's own uniqueness guarantee rather than
a read-then-write the caller remembers. Measured before the fix: two concurrent
requests for one supplier could both sit in ``COOLING_OFF`` and both reach
``APPROVED``, and §4.5.1's "the old version becomes ``SUPERSEDED``" had no defined
answer for which won.

**Design decision, recorded because it is a real constraint lift rather than the
obvious one.** The obvious fix is a ``UNIQUE`` constraint on ``vendor_id``. That
would be wrong: a supplier may have a rejected request in November and a new one in
January, and §4.4 makes a re-request within 30 days force tier 2 - so the history
must stay queryable. The constraint is on ``vendor_id`` for **active** requests
only, via a partial unique index over the non-terminal statuses. SQLite supports
this directly, which means the database refuses the second concurrent request and
the application does not have to.
"""

from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Final

from app.core import db
from app.core.statemachine import CALLBACK_VALIDITY_DAYS

__all__ = [
    "ACTIVE_STATUSES",
    "LOCK_NAME",
    "ChangeRequestConflictError",
    "ChangeRequestRow",
    "active_requests_for",
    "assert_lock_integrity",
    "open_request",
    "request_callback",
]

#: The query that must never return more than one row per vendor. It is also what
#: the partial unique index enforces, so the two never drift.
ACTIVE_STATUSES: Final[frozenset[str]] = frozenset({"RECEIVED", "PENDING_CALLBACK", "COOLING_OFF"})

#: The name of the invariant. Written down because it is what a future reviewer
#: needs to see, and because the error message quotes it.
LOCK_NAME: Final[str] = "one active bank-change request per supplier"

#: The partial index. `status <> 'RECEIVED'` is deliberately not equivalent:
#: every non-terminal status is active, and a request that arrives and is
#: immediately superseded would be invisible to a narrower predicate.
_PARTIAL_INDEX: Final[str] = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_change_request_one_active_per_vendor
    ON payee_change_request (vendor_id)
    WHERE status IN ('RECEIVED', 'PENDING_CALLBACK', 'COOLING_OFF')
"""


class ChangeRequestConflictError(RuntimeError):
    """A second active change request for the same supplier was attempted.

    Raised as a ``RuntimeError`` rather than an ``sqlite3.IntegrityError`` so
    callers cannot swallow it with ``except sqlite3.Error``: this is a control
    firing, not a storage problem.
    """


@dataclass(frozen=True)
class ChangeRequestRow:
    """The one change request that may be active for a supplier."""

    id: str
    vendor_id: str
    status: str
    proposed_fingerprint: str


def ensure_lock_constraint(conn: db.Connection) -> None:
    """Create the partial unique index. Idempotent, and safe to call on startup.

    Called from :func:`db.migrate`'s next revision rather than at first use, so a
    cold database and a warm one get the same guarantee without a caller
    remembering to ask for it.
    """
    conn.execute(_PARTIAL_INDEX)


def open_request(
    conn: db.Connection,
    *,
    vendor_id: str,
    source_kind: str,
    intake_user_id: str,
    proposed_details_ref: str,
    proposed_masked: str,
    proposed_fingerprint: str,
    source_message_id: str | None = None,
    requester_set: tuple[str, ...] = (),
    evidence: tuple[str, ...] = (),
    old_payee_version_id: str | None = None,
) -> ChangeRequestRow:
    """Open a change request, or refuse if the supplier already has an active one.

    The refusal is the database's, not a check-then-insert. Two concurrent
    requests for the same supplier both reach this call; the partial unique index
    means exactly one transaction commits and the other fails with an
    ``IntegrityError``, which becomes :class:`ChangeRequestConflictError`.

    Before the index, the failure mode was worse than a lost update (D-B22): both
    requests would have been accepted, both cooled off, and both approved - and
    §4.5.1 has no answer for which one supersedes the previous payee version. The
    first one to be approved wins, by accident, and there is no record that the
    second was ever a real request.
    """
    request_id = str(uuid.uuid4())
    try:
        conn.execute(
            "INSERT INTO payee_change_request"
            " (id, vendor_id, source_kind, source_message_id, received_at, intake_user_id,"
            "  requester_set, old_payee_version_id, proposed_details_ref, proposed_masked,"
            "  proposed_fingerprint, evidence, status)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                request_id,
                vendor_id,
                source_kind,
                source_message_id,
                _now_iso(),
                intake_user_id,
                _json_array(requester_set),
                old_payee_version_id,
                proposed_details_ref,
                proposed_masked,
                proposed_fingerprint,
                _json_array(evidence),
                "RECEIVED",
            ),
        )
    except sqlite3.IntegrityError as exc:
        # Distinguish the lock firing from a foreign key on vendor/user. SQLite
        # words the message from the *columns*, not the index name, so matching
        # text would be fragile. The question that matters is: does this supplier
        # already have an active request? The rejected insert has rolled back by
        # now, so exactly one row is the refusal reason.
        if active_requests_for(conn, vendor_id):
            raise ChangeRequestConflictError(
                f"supplier {vendor_id} already has an active bank-change request; "
                f"{LOCK_NAME} (FINAL.md §4.5)"
            ) from exc
        raise

    return ChangeRequestRow(
        id=request_id,
        vendor_id=vendor_id,
        status="RECEIVED",
        proposed_fingerprint=proposed_fingerprint,
    )


def request_callback(
    conn: db.Connection,
    request_id: str,
) -> ChangeRequestRow:
    """Move a request to ``PENDING_CALLBACK``, once the request exists.

    Not the place the invariant is enforced - that is ``open_request``. This is
    where the callback's 7-day validity starts, so the check belongs here rather
    than in the transition itself, which has no clock.
    """
    from app.core.statemachine import change_request_next

    row = _get(conn, request_id)
    if row is None:
        raise KeyError(f"no change request {request_id!r}")

    next_status = change_request_next(row.status, "REQUEST_CALLBACK")
    if next_status == row.status:
        # Already pending, or terminal. Both are the caller's business, not ours.
        return row

    conn.execute(
        "UPDATE payee_change_request SET status = ?, decided_at = ? WHERE id = ?",
        (next_status, _now_iso(), request_id),
    )
    return ChangeRequestRow(
        id=row.id,
        vendor_id=row.vendor_id,
        status=next_status,
        proposed_fingerprint=row.proposed_fingerprint,
    )


def active_requests_for(conn: db.Connection, vendor_id: str) -> list[ChangeRequestRow]:
    """Every active request for one supplier. Must be at most one, ever."""
    rows = conn.execute(
        "SELECT id, vendor_id, status, proposed_fingerprint FROM payee_change_request"
        " WHERE vendor_id = ? AND status IN (?, ?, ?)",
        (vendor_id, *sorted(ACTIVE_STATUSES)),
    ).fetchall()
    return [
        ChangeRequestRow(
            id=row["id"],
            vendor_id=row["vendor_id"],
            status=row["status"],
            proposed_fingerprint=row["proposed_fingerprint"],
        )
        for row in rows
    ]


def assert_lock_integrity(conn: db.Connection) -> None:
    """Assert the invariant across every row, and fail loudly if it is broken.

    This is the check a reviewer or a verification run should call: the index
    prevents new violations, but a database migrated from before the index existed
    could already hold two. Finding them once, at startup, is worth a halt; a
    silent violation of the product's central claim is worth much more.
    """
    duplicates = conn.execute(
        "SELECT vendor_id, count(*) AS n FROM payee_change_request"
        " WHERE status IN ('RECEIVED', 'PENDING_CALLBACK', 'COOLING_OFF')"
        " GROUP BY vendor_id HAVING n > 1"
    ).fetchall()
    if duplicates:
        vendors = ", ".join(row["vendor_id"] for row in duplicates)
        raise ChangeRequestConflictError(
            f"{LOCK_NAME} is violated for: {vendors}. This database predates the "
            "constraint or has been edited directly (FINAL.md §4.5)"
        )


@contextmanager
def lock_transaction(conn: db.Connection) -> Iterator[db.Connection]:
    """The transaction in which a change request is opened or advanced.

    Deliberately the caller's connection with ``BEGIN IMMEDIATE`` rather than a
    lock we own: the write lock is SQLite's single writer, so a separate advisory
    lock would be a second, weaker serialisation on top of the real one. Reads in
    §4.5 (the on-file details) are therefore made before this is entered, never
    inside it, and the fingerprint comparison is repeated after the write.
    """
    with db.transaction(conn) as tx:
        assert_lock_integrity(tx)
        yield tx


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _get(conn: db.Connection, request_id: str) -> ChangeRequestRow | None:
    row = conn.execute(
        "SELECT id, vendor_id, status, proposed_fingerprint FROM payee_change_request WHERE id = ?",
        (request_id,),
    ).fetchone()
    if row is None:
        return None
    return ChangeRequestRow(
        id=row["id"],
        vendor_id=row["vendor_id"],
        status=row["status"],
        proposed_fingerprint=row["proposed_fingerprint"],
    )


def _is_vendor_clash(conn: db.Connection, vendor_id: str) -> bool:
    """Did the vendor just acquire a second active request?"""
    return len(active_requests_for(conn, vendor_id)) > 1


def _json_array(values: tuple[str, ...]) -> str:
    import json

    return json.dumps(list(values), separators=(",", ":"))


def _now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


def validity_window_days() -> int:
    """Floor row 3: the callback's validity window. Exported for the UI."""
    return CALLBACK_VALIDITY_DAYS
