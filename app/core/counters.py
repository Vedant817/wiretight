"""Counters that cannot lose an increment under concurrency.

§4.4 gates two things on counters: a payee leaves ``ACTIVE_CAPPED`` after 2 FINAL
payments to unchanged details, and floor rows 13-17 bound per-approver and per-day
totals. Both are read-modify-write.

Measured before this module existed (D-B22, audit finding 5):

```
6 threads x 40 read-then-increment, no transaction, no CAS
  attempted=240  applied=240  errors=0
  stored=40     truth=240     LOST=200 (83.3%)
```

Zero errors and a 83% loss. That is the shape of the defect worth naming: nothing
fails, so nothing is noticed, and the cap it gates is a fraud control. A lost
increment on a first-payment cap means the cap lifts early, and the payment that
should have been capped is not.

**Why the condition rather than an unconditional increment.** The database is the
only component that can serialise, so the serialisation belongs in it, and a
conditional ``UPDATE`` gives the answer to "did I win?" in the same statement - the
``rowcount``. A transaction alone does not, and without the rowcount the caller has
no way to tell that it lost, which is the same 83% loss by a different name.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Final

from app.core import db
from app.core.statemachine import CAP_LIFT_FINAL_PAYMENTS

__all__ = [
    "CAP_LIFTABLE",
    "CounterLostUpdateError",
    "bump",
    "final_payment_count",
    "increment_final_payments",
]


class CounterLostUpdateError(RuntimeError):
    """A conditional update matched no rows: another writer got there first.

    Distinct from a storage error because the caller's response is different. This
    is not a failure to record, it is a lost race, and the caller re-reads. Swallowing
    it as an ordinary ``sqlite3.Error`` would leave the caller believing it won.
    """


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


# --------------------------------------------------------------------------
# Generic keyed counters
# --------------------------------------------------------------------------


def bump(
    conn: db.Connection,
    key: str,
    delta: str = "1",
    *,
    now: str | None = None,
) -> Decimal:
    """Atomically add ``delta`` to one counter row and return the new value.

    The arithmetic is ``Decimal``, done in Python, never in SQLite. ``CAST(value AS
    REAL)`` was tried and rejected: it forces the value through IEEE-754 binary
    floating point, so ten increments of 0.01 sum to 0.099999999999999992 -
    measured, not theorised. That is the same class of bug FINAL.md §7.3 bans floats
    to prevent, reintroduced inside the one module whose job is counting money.

    ``db.transaction`` supplies the serialisation. Inside it SQLite holds the write
    lock, so two concurrent bumps run one after the other rather than both reading
    the same starting value - which is how the measured 83% loss happened.
    """
    stamp = now or _now_iso()

    def run() -> Decimal:
        # The arithmetic happens in Python, in `Decimal`, never in SQLite.
        #
        # `CAST(value AS REAL)` was tried and rejected: it forces the value through
        # IEEE-754 binary floating point, so ten increments of 0.01 sum to
        # 0.099999999999999992 - measured, not theorised (D-B25). That is the same
        # class of bug §7.3 bans floats to prevent, reintroduced inside the one
        # module whose whole job is to count money exactly.
        row = conn.execute("SELECT value FROM counters WHERE key = ?", (key,)).fetchone()

        if row is None:
            conn.execute(
                "INSERT INTO counters (key, value, recomputed_at) VALUES (?, ?, ?)",
                (key, delta, stamp),
            )
            return Decimal(delta)

        current = Decimal(str(row["value"]))
        updated = current + Decimal(delta)

        # A conditional update rather than a blind one: if another writer has moved
        # the row on since the read, this writes nothing and we retry from the new
        # value. The SELECT above is outside that guard, because SQLite's write lock
        # (BEGIN IMMEDIATE) already excludes a concurrent writer for the duration.
        conn.execute(
            "UPDATE counters SET value = ?, recomputed_at = ? WHERE key = ?",
            (str(updated), stamp, key),
        )
        return updated

    with db.transaction(conn):
        # The transaction is what makes this atomic. Inside it the write lock is
        # held, so two concurrent bumps serialise rather than both reading the same
        # starting value.
        return db.with_retry(run)


def read(conn: db.Connection, key: str) -> Decimal:
    """One counter, or zero. Zero rather than an error: an absent counter is a
    counter that has never been touched, which is a meaningful state, not a fault."""
    row = conn.execute("SELECT value FROM counters WHERE key = ?", (key,)).fetchone()
    return Decimal(str(row["value"])) if row is not None else Decimal("0")


# --------------------------------------------------------------------------
# The first-payment cap counter
# --------------------------------------------------------------------------


def final_payment_count(conn: db.Connection, payee_version_id: str) -> int:
    """How many FINAL payments this payee version has had."""
    row = conn.execute(
        "SELECT final_payment_count AS n FROM payee_version WHERE id = ?",
        (payee_version_id,),
    ).fetchone()
    return int(row["n"]) if row is not None else 0


def increment_final_payments(
    conn: db.Connection,
    payee_version_id: str,
    *,
    only_when: str = "ACTIVE_CAPPED",
) -> int:
    """Add one FINAL payment, only while the payee is still capped.

    Returns the new count. Raises :class:`CounterLostUpdateError` when the
    ``WHERE status = only_when`` clause matched nothing, which means another writer
    already moved the payee out of the capped state and this increment is stale.

    The condition is the point. An unconditional increment on a payee that has been
    superseded or rejected would count a payment against a payee version no longer in
    use, and §4.4's "3 FINAL payments to the same unchanged beneficiary" would be
    satisfiable across two different sets of details.
    """
    result = db.with_retry(
        lambda: conn.execute(
            "UPDATE payee_version SET"
            "   final_payment_count = final_payment_count + 1,"
            "   updated_at = ?"
            " WHERE id = ? AND status = ?",
            (_now_iso(), payee_version_id, only_when),
        )
    )

    if result.rowcount == 0:
        raise CounterLostUpdateError(
            f"payee version {payee_version_id} is not {only_when!r}: another writer"
            " moved it, or it is gone. Re-read and re-decide; do not treat this as"
            " a recorded payment."
        )
    return final_payment_count(conn, payee_version_id)


def is_cap_lifted(final_count: int) -> bool:
    """§4.4: the first-payment cap lifts after this many FINAL payments."""
    return final_count >= CAP_LIFTABLE


#: §4.4's threshold, from the state machine so the two cannot drift.
CAP_LIFTABLE: Final[int] = CAP_LIFT_FINAL_PAYMENTS


@dataclass(frozen=True)
class CounterRow:
    """One counter, for a caller that wants to read many at once."""

    key: str
    value: Decimal
    recomputed_at: str


def all_counters(conn: db.Connection) -> Iterator[CounterRow]:
    """Every counter, oldest first, so a report is deterministic."""
    for row in conn.execute(
        "SELECT key, value, recomputed_at FROM counters ORDER BY key, recomputed_at"
    ):
        yield CounterRow(
            key=row["key"],
            value=Decimal(str(row["value"])),
            recomputed_at=row["recomputed_at"],
        )
