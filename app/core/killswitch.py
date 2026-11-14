"""The kill switch: two sources, fail closed, cleared by two signed people.

FINAL.md §4.9, §4.15 rows 24-30.

Halted is the default-reading failure. If the HALT file exists, **or its path
cannot be read**, the executor is halted. There is no flag that makes an
unreadable file mean "not halted".

Reads never stop when halted. Polling, AMBIGUOUS lookups, RFI polling and
reconciliation all continue, because a transfer already sent still needs
watching and a residual still needs explaining. Only the three create calls stop.

Four properties were wrong in the first version and are the reason this module
re-reads rather than snapshots. Each was found by review, not by the spec:

1. ``guard()`` used a DB flag captured at load time, so a switch object held for
   the length of a run never saw a later trip. §4.8 step 1 is called before
   *every* mutating call.
2. ``clear()`` accepted any caller-supplied ``trip_id``, so replaying an old
   trip's id cleared a newer, unrelated incident.
3. ``clear()`` ran outside a transaction and wrote ``halted = 0`` first, so a
   failure midway left the switch reading RUNNING with the incident still open.
4. ``clear()`` counted distinct approver *strings* and never verified a single
   signature, though §4.9 requires each approver to sign
   ``sha256("clear|" + trip_id + "|" + reason)``.

Honest limits, repeated in the README: in-flight transfers are not recalled,
there is no transfer-cancellation endpoint in this design, and the ultimate stop
is a human revoking the API key in the Airwallex web app.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from app.core import audit, db

RUNNING: Final[str] = "RUNNING"
HALTED: Final[str] = "HALTED"

_HALT_UPDATE: Final[str] = (
    "UPDATE killswitch_state SET halted = 1, halted_at = ?, reason = ?, trip_id = ? WHERE id = 1"
)


class HaltedError(RuntimeError):
    """The kill switch is engaged. No mutating call may proceed."""


@dataclass
class Trip:
    id: str
    reason: str
    origin: str
    tripped_at: str
    cleared_at: str | None = None
    cleared_by: str | None = None


def _now() -> str:
    return datetime.now(UTC).isoformat()


class Haltswitch:
    """The kill switch as the executor sees it.

    Two authoritative sources: a DB row (survives a restart) and a ``HALT`` file
    (a human can halt without the database). Either says halt, and so does an
    unreadable file path.

    Neither source is cached. :meth:`is_halted` re-reads both on every call,
    because ``guard()`` runs before *every* mutating API call: a snapshot taken at
    executor start would miss a trip raised mid-run, which is exactly when the
    switch matters most.
    """

    def __init__(self, conn: db.Connection, halt_file: str | Path) -> None:
        self._conn = conn
        self.halt_file = Path(halt_file)

    def _db_row(self) -> Any:
        return self._conn.execute(
            "SELECT halted, reason, trip_id FROM killswitch_state WHERE id = 1"
        ).fetchone()

    def _db_halted(self) -> bool:
        row = self._db_row()
        return bool(row["halted"]) if row is not None else False

    def _file_halted(self) -> bool:
        try:
            return self.halt_file.exists()
        except OSError:
            # Unreadable path == halted. Fail closed, always.
            return True

    def is_halted(self) -> bool:
        return self._db_halted() or self._file_halted()

    def reason_text(self) -> str:
        if self._file_halted() and not self._db_halted():
            return "HALT file present"
        row = self._db_row()
        if row is not None and row["reason"]:
            return str(row["reason"])
        return "no reason recorded"

    def active_trip_id(self) -> str | None:
        row = self._db_row()
        return row["trip_id"] if row is not None else None

    def guard(self) -> None:
        """Raise if halted. Called before every mutating API call (§4.8 step 1)."""
        if self.is_halted():
            raise HaltedError(f"kill switch is halted: {self.reason_text()}")

    def assert_may_mutate(self) -> None:
        """Explicit alias for :meth:`guard`, for call sites that read better."""
        self.guard()


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
def ensure_row(conn: db.Connection) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO killswitch_state (id, halted, halted_at, reason, trip_id)"
        " VALUES (1, 0, NULL, NULL, NULL)"
    )


def load(conn: db.Connection, halt_file: str | Path) -> Haltswitch:
    """A switch bound to the connection. Reads state fresh on every call."""
    ensure_row(conn)
    return Haltswitch(conn, halt_file)


def _write_halt_file(halt_file: str | Path | None, record: Trip) -> None:
    if halt_file is None:
        return
    Path(halt_file).parent.mkdir(parents=True, exist_ok=True)
    Path(halt_file).write_text(
        f"tripped {record.tripped_at}\nreason: {record.reason}\norigin: {record.origin}\n",
        encoding="utf-8",
    )


def _insert_trip(conn: db.Connection, record: Trip) -> None:
    conn.execute(
        "INSERT INTO trip (id, reason, origin, tripped_at) VALUES (?, ?, ?, ?)",
        (record.id, record.reason, record.origin, record.tripped_at),
    )
    conn.execute(_HALT_UPDATE, (record.tripped_at, record.reason, record.id))
    audit.log_intent(
        conn,
        kind="KILLSWITCH_TRIP",
        payload={"trip_id": record.id, "reason": record.reason, "origin": record.origin},
    )


def trip(
    conn: db.Connection,
    reason: str,
    *,
    origin: str = "human",
    halt_file: str | Path | None = None,
) -> Trip:
    """Engage the kill switch. Idempotent: tripping twice keeps the first trip.

    A ``killswitch_state.trip_id`` pointing at a missing trip row is treated as
    **halted**, not as "no trip". The earlier version returned an empty Trip and
    left ``halted`` alone, which fails toward RUNNING.

    **The read, the decision, the trip row, the state update and the audit entry
    are one transaction.** Three separate defects were measured here (D-B21), and
    each of them was reachable by one operator:

    * The audit append ran in its *own* transaction after the state was already
      committed. Forcing it to fail left the switch engaged and durable, with a
      trip row and a reason, and **zero** rows in the append-only log.
      ``audit.verify()`` reported ``ok=True, checked=0`` — a halted system whose
      every audit control reported clean. FINAL.md §14(b) requires the log
      before the act; that held for transfers and not for the kill switch.
    * The read-decide-write was not atomic, so four concurrent calls produced six
      ``trip`` rows and six ``Trip`` objects with six different ids. Five of the
      six ids the system handed back could never be cleared — an operator who
      tripped, read the id, and cleared it was refused with "not the active trip",
      leaving the switch stuck in HALTED with no in-band route out.
    * ``_write_halt_file`` is deliberately **outside** the transaction: it is
      filesystem I/O, and holding the single write lock across it would stall
      every other writer. Ordering here is load-bearing, so it is asserted by
      :class:`TestTripIsAtomic`.
    """
    record, needs_file = _trip_locked(conn, reason, origin)

    # Outside the transaction, on purpose. See the docstring.
    if needs_file:
        _write_halt_file(halt_file, record)
    return record


def _trip_locked(conn: db.Connection, reason: str, origin: str) -> tuple[Trip, bool]:
    """The whole read-decide-write. Returns the trip and whether to write the file."""
    ensure_row(conn)

    def decide() -> tuple[Trip, bool]:
        row = conn.execute("SELECT halted, trip_id FROM killswitch_state WHERE id = 1").fetchone()

        if row is not None and row["halted"]:
            if row["trip_id"]:
                existing = conn.execute(
                    "SELECT * FROM trip WHERE id = ?", (row["trip_id"],)
                ).fetchone()
                if existing is not None:
                    return Trip(**dict(existing)), False

                # Dangling pointer: the DB was tampered with. Fail toward halted and
                # record a fresh trip so the state becomes self-consistent again.
                recovered = Trip(
                    id=str(uuid.uuid4()),
                    reason=f"{reason} (recovered from a dangling trip id)",
                    origin="recovery",
                    tripped_at=_now(),
                )
                _insert_trip(conn, recovered)
                conn.execute(
                    "UPDATE killswitch_state SET reason = ? WHERE id = 1", (recovered.reason,)
                )
                return recovered, True

            # Halted with no trip id: nothing to recover, nothing to do.
            return (
                Trip(id="", reason=str(row["reason"] or reason), origin=origin, tripped_at=_now()),
                False,
            )

        fresh = Trip(id=str(uuid.uuid4()), reason=reason, origin=origin, tripped_at=_now())
        _insert_trip(conn, fresh)
        return fresh, True

    # Joins an enclosing transaction if the caller opened one, so an audit entry
    # written by the caller commits or rolls back with the halt.
    with db.transaction(conn):
        return decide()


# ---------------------------------------------------------------------------
# Automatic trip rules, §4.15 rows 24-29
# ---------------------------------------------------------------------------
def check_clock_skew(skew_seconds: int, limit: int) -> bool:
    """Row 24. Drift matters because approval expiry and cooling-off are
    wall-clock rules: a skewed clock would let an expired approval look valid."""
    return abs(skew_seconds) > limit


def check_ambiguous_creates(
    in_run: int, rolling_24h: int, per_run_limit: int, rolling_limit: int
) -> bool:
    """Row 26. Two AMBIGUOUS attempts mean we have lost track of the money."""
    return in_run >= per_run_limit or rolling_24h >= rolling_limit


def check_failed_transfers(rolling_1h: int, limit: int) -> bool:
    """Row 27. Three failures in an hour is a pattern, not bad luck."""
    return rolling_1h >= limit


def check_extraction_conflicts(rolling_24h: int, limit: int) -> bool:
    """Row 28. Three LLM/parser identifier disagreements in a day."""
    return rolling_24h >= limit


COMPLIANCE_FAILURE_TYPES: Final[frozenset[str]] = frozenset(
    {"ACCOUNT_UNDER_RESTRICTION", "TM_SUSPENDED", "CHANNEL_POLICY"}
)
WATCHLIST_PREFIX = "WATCHLIST_"


def is_compliance_failure(failure_type: str | None, reason_codes: list[str] | None = None) -> bool:
    """Row 29, on the *first* occurrence.

    Compliance is the one category where one is enough. A sandbox that has blocked
    an account for a compliance reason has information we do not, and continuing
    is how a real incident gets bigger.
    """
    if failure_type is None:
        return False
    if failure_type in COMPLIANCE_FAILURE_TYPES:
        return True
    if failure_type.startswith(WATCHLIST_PREFIX):
        return True
    return any(str(code).startswith(WATCHLIST_PREFIX) for code in (reason_codes or []))


@dataclass
class AutomaticTripper:
    """Applies the automatic trip rules against live counts.

    Takes its counters as arguments rather than reading a cache, because §4.15's
    caps are recomputed from the ledger plus ``GET /transfers``: wiping the local
    DB must not reset them (R4 J-3).
    """

    policy: dict[str, Any] = field(default_factory=dict)

    def _kill(self) -> dict[str, Any]:
        return dict(self.policy.get("killswitch", {}))

    def clock_skew(self, skew_seconds: int) -> str | None:
        limit = int(self._kill().get("clock_skew_seconds", 120))
        if check_clock_skew(skew_seconds, limit):
            return f"clock skew {skew_seconds}s exceeds {limit}s (FINAL.md §4.15 r24)"
        return None

    def ambiguous(self, in_run: int, rolling_24h: int) -> str | None:
        limits = self._kill()
        if check_ambiguous_creates(
            in_run,
            rolling_24h,
            int(limits.get("ambiguous_creates_per_run", 2)),
            int(limits.get("ambiguous_creates_rolling_24h", 2)),
        ):
            return (
                f"AMBIGUOUS creates reached {in_run} in this run / {rolling_24h} in 24h "
                "(FINAL.md §4.15 r26)"
            )
        return None

    def failures(self, rolling_1h: int) -> str | None:
        limit = int(self._kill().get("failed_transfers_rolling_1h", 3))
        if check_failed_transfers(rolling_1h, limit):
            return f"{rolling_1h} FAILED transfers in 1h (FINAL.md §4.15 r27)"
        return None

    def extraction_conflicts(self, rolling_24h: int) -> str | None:
        limit = int(self._kill().get("extraction_conflicts_rolling_24h", 3))
        if check_extraction_conflicts(rolling_24h, limit):
            return f"{rolling_24h} EXTRACTION_CONFLICT items in 24h (FINAL.md §4.15 r28)"
        return None

    @staticmethod
    def compliance(failure_type: str | None, reason_codes: list[str] | None = None) -> str | None:
        if is_compliance_failure(failure_type, reason_codes):
            return (
                f"compliance failure {failure_type}"
                f"{' + ' + str(reason_codes) if reason_codes else ''} "
                "(FINAL.md §4.15 r29)"
            )
        return None


def evaluate_rules(
    tripper: AutomaticTripper,
    *,
    skew_seconds: int | None = None,
    ambiguous_in_run: int | None = None,
    ambiguous_24h: int | None = None,
    failed_1h: int | None = None,
    extraction_24h: int | None = None,
    failure_type: str | None = None,
    reason_codes: list[str] | None = None,
) -> list[str]:
    """Every rule that fires, in row order 24..29. The caller trips on the first.

    The order is the spec's, not the order of the keyword arguments, so the audit
    log reads in the same order as FINAL.md §4.15. ``None`` for an input means
    "nothing observed to judge", which is distinct from a real observation that
    is not a compliance type.
    """
    reasons: list[str] = []

    if skew_seconds is not None:  # r24
        found = tripper.clock_skew(skew_seconds)
        if found:
            reasons.append(found)

    if ambiguous_in_run is not None and ambiguous_24h is not None:  # r26
        found = tripper.ambiguous(ambiguous_in_run, ambiguous_24h)
        if found:
            reasons.append(found)

    if failed_1h is not None:  # r27
        found = tripper.failures(failed_1h)
        if found:
            reasons.append(found)

    if extraction_24h is not None:  # r28
        found = tripper.extraction_conflicts(extraction_24h)
        if found:
            reasons.append(found)

    if failure_type is not None:  # r29
        found = AutomaticTripper.compliance(failure_type, reason_codes)
        if found:
            reasons.append(found)

    return reasons
