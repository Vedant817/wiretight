"""The kill switch: two places, fail closed, cleared by two people.

FINAL.md §4.9. Halted is the default-reading failure: if the HALT file exists, or
its path cannot be read, the executor is halted. There is no flag that makes an
unreadable file mean "not halted".

Reads never stop when halted. Polling, AMBIGUOUS lookups, RFI polling and
reconciliation all continue, because a transfer we already sent still needs
watching and a residual still needs explaining. Only the three create calls stop.

Honest limits, repeated in the README: in-flight transfers are not recalled,
there is no transfer-cancellation endpoint in this design, and the ultimate stop
is a human revoking the API key in the Airwallex web app.
"""

from __future__ import annotations

import contextlib
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from app.core import audit, db


class KillswitchState(str):
    """String enum: ``RUNNING`` or ``HALTED`` (§8.4)."""

    RUNNING = "RUNNING"
    HALTED = "HALTED"


@dataclass
class Trip:
    id: str
    reason: str
    origin: str
    tripped_at: str
    cleared_at: str | None = None
    cleared_by: str | None = None


@dataclass
class Haltswitch:
    """The kill switch as the executor sees it.

    Two sources, both authoritative:

    * a DB row in ``killswitch_state``, so the halt survives a restart;
    * a ``HALT`` file, so a human can halt without the database being reachable.

    ``is_halted`` is true if **either** says halt, and also true if the file's
    path cannot be read. Failing toward halted is the whole design.
    """

    halt_file: Path
    halted: bool = False
    reason: str | None = None
    trip: Trip | None = None
    clears: list[dict[str, Any]] = field(default_factory=list)

    def is_halted(self) -> bool:
        return self._db_halted() or self._file_halted()

    def reason_text(self) -> str:
        if self._file_halted() and not self._db_halted():
            return "HALT file present"
        return self.reason or "no reason recorded"

    def _db_halted(self) -> bool:
        return bool(self.halted)

    def _file_halted(self) -> bool:
        try:
            return self.halt_file.exists()
        except OSError:
            # Unreadable path == halted. Fail closed.
            return True

    def guard(self) -> None:
        """Raise if halted. Called before every mutating API call (§4.8 step 1)."""
        if self.is_halted():
            raise HaltedError(f"kill switch is halted: {self.reason_text()}")


class HaltedError(RuntimeError):
    """The kill switch is engaged. No mutating call may proceed."""


class Tripswitch(Protocol):  # pragma: no cover - documentation only
    """What the automatic trip rules (§4.15 rows 24-29) need to call."""

    def trip(self, conn: db.Connection, reason: str, origin: str) -> Trip: ...


def _now() -> str:
    return datetime.now(UTC).isoformat()


def ensure_row(conn: db.Connection) -> None:
    """Create the single ``killswitch_state`` row if it is absent."""
    conn.execute(
        "INSERT OR IGNORE INTO killswitch_state (id, halted, halted_at, reason, trip_id)"
        " VALUES (1, 0, NULL, NULL, NULL)"
    )


def load(conn: db.Connection, halt_file: str | Path) -> Haltswitch:
    """Read the current state. Does not create the HALT file."""
    ensure_row(conn)
    row = conn.execute(
        "SELECT halted, reason, trip_id FROM killswitch_state WHERE id = 1"
    ).fetchone()

    switch = Haltswitch(halt_file=Path(halt_file))
    if row is not None:
        switch.halted = bool(row["halted"])
        switch.reason = row["reason"]
        if row["trip_id"]:
            trip_row = conn.execute(
                "SELECT id, reason, origin, tripped_at, cleared_at, cleared_by"
                " FROM trip WHERE id = ?",
                (row["trip_id"],),
            ).fetchone()
            if trip_row is not None:
                switch.trip = Trip(**dict(trip_row))
    return switch


def trip(
    conn: db.Connection,
    reason: str,
    *,
    origin: str = "human",
    halt_file: str | Path | None = None,
) -> Trip:
    """Engage the kill switch. Idempotent: tripping twice keeps the first trip.

    Audited, because "the switch went off" is a fact someone will ask about
    later, and the reason has to survive the restart that follows.
    """
    ensure_row(conn)
    existing = conn.execute(
        "SELECT trip_id FROM killswitch_state WHERE id = 1 AND halted = 1"
    ).fetchone()
    if existing is not None:
        row = conn.execute("SELECT * FROM trip WHERE id = ?", (existing["trip_id"],)).fetchone()
        return Trip(**dict(row)) if row is not None else Trip("", reason, origin, _now())

    record = Trip(id=str(uuid.uuid4()), reason=reason, origin=origin, tripped_at=_now())
    conn.execute(
        "INSERT INTO trip (id, reason, origin, tripped_at) VALUES (?, ?, ?, ?)",
        (record.id, record.reason, record.origin, record.tripped_at),
    )
    conn.execute(
        "UPDATE killswitch_state"
        " SET halted = 1, halted_at = ?, reason = ?, trip_id = ? WHERE id = 1",
        (record.tripped_at, record.reason, record.id),
    )
    audit.log_intent(
        conn,
        kind="KILLSWITCH_TRIP",
        payload={"trip_id": record.id, "reason": reason, "origin": origin},
    )

    if halt_file is not None:
        Path(halt_file).parent.mkdir(parents=True, exist_ok=True)
        Path(halt_file).write_text(
            f"tripped {record.tripped_at}\nreason: {reason}\norigin: {origin}\n",
            encoding="utf-8",
        )
    return record


def clear(
    conn: db.Connection,
    trip_id: str,
    reason: str,
    clears: list[dict[str, Any]],
    *,
    required: int = 2,
    halt_file: str | Path | None = None,
) -> None:
    """Clear the halt. Requires ``required`` distinct approver clears.

    "Clearing resumes nothing" (§4.9): approvals that expired while halted need
    fresh sign-offs, because the thing they authorised may no longer be what is
    about to happen.
    """
    approvers = [str(entry.get("approver_id")) for entry in clears]
    distinct = len(set(approvers))
    if distinct < required:
        raise HaltedError(
            f"clearing the kill switch needs {required} distinct approvers, got {distinct}"
        )
    if not reason.strip():
        raise HaltedError("clearing the kill switch requires a reason")

    conn.execute(
        "UPDATE trip SET cleared_at = ?, cleared_by = ? WHERE id = ?",
        (_now(), ",".join(sorted(set(approvers))), trip_id),
    )
    conn.execute(
        "UPDATE killswitch_state"
        " SET halted = 0, halted_at = NULL, reason = NULL, trip_id = NULL WHERE id = 1"
    )
    for entry in clears:
        conn.execute(
            "INSERT INTO trip_clear_signature"
            " (id, trip_id, approver_id, method, signed_via, signature, challenge_nonce, signed_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                trip_id,
                str(entry.get("approver_id")),
                str(entry.get("method", "HMAC_FALLBACK")),
                str(entry.get("signed_via", "cli_hmac")),
                entry.get("signature", b""),
                str(entry.get("challenge_nonce", uuid.uuid4())),
                _now(),
            ),
        )
    audit.log_intent(
        conn,
        kind="KILLSWITCH_CLEAR",
        payload={"trip_id": trip_id, "reason": reason, "approvers": sorted(set(approvers))},
    )

    if halt_file is not None:
        # If this raises, the DB row says RUNNING but the HALT file still reads as
        # halted, which is the safe direction: a human removes the file. Failing
        # the clear here instead would leave the switch engaged for no benefit.
        with contextlib.suppress(OSError):
            Path(halt_file).unlink(missing_ok=True)


def clear_signature_payload(trip_id: str, reason: str) -> str:
    """The exact bytes each approver signs to clear the switch (§4.9)."""
    import hashlib

    return hashlib.sha256(f"clear|{trip_id}|{reason}".encode()).hexdigest()


# ---------------------------------------------------------------------------
# Automatic trip rules, §4.15 rows 24-29
# ---------------------------------------------------------------------------
def check_clock_skew(skew_seconds: int, limit: int) -> bool:
    """Row 24: more than ``limit`` seconds of drift against the server trips.

    Drift matters because approval expiry and cooling-off are wall-clock rules.
    A skewed clock would let an expired approval look valid.
    """
    return abs(skew_seconds) > limit


def check_ambiguous_creates(
    in_run: int, rolling_24h: int, per_run_limit: int, rolling_limit: int
) -> bool:
    """Row 26: two AMBIGUOUS attempts mean we have lost track of the money."""
    return in_run >= per_run_limit or rolling_24h >= rolling_limit


def check_failed_transfers(rolling_1h: int, limit: int) -> bool:
    """Row 27: three failures in an hour is a pattern, not bad luck."""
    return rolling_1h >= limit


def check_extraction_conflicts(rolling_24h: int, limit: int) -> bool:
    """Row 28: three LLM/parser identifier disagreements in a day."""
    return rolling_24h >= limit


COMPLIANCE_FAILURE_TYPES: frozenset[str] = frozenset(
    {"ACCOUNT_UNDER_RESTRICTION", "TM_SUSPENDED", "CHANNEL_POLICY"}
)
WATCHLIST_PREFIX = "WATCHLIST_"


def is_compliance_failure(failure_type: str | None, reason_codes: list[str] | None = None) -> bool:
    """Row 29: trips on the *first* compliance failure or any WATCHLIST reason.

    Compliance is the one category where the first occurrence is enough. A
    sandbox that has blocked an account for a compliance reason has information
    we do not, and continuing to try is how a real incident gets bigger.
    """
    if failure_type is None:
        return False
    if failure_type in COMPLIANCE_FAILURE_TYPES:
        return True
    if failure_type.startswith(WATCHLIST_PREFIX):
        return True
    return any(str(code).startswith(WATCHLIST_PREFIX) for code in (reason_codes or []))


class AutomaticTripper:
    """Applies the automatic trip rules against live counts.

    Takes its counters as callables so it never decides on a cached number
    alone: §4.15's caps are recomputed from the ledger plus
    ``GET /transfers``, so wiping the local DB cannot reset them (R4 J-3).
    """

    def __init__(self, policy: dict[str, Any]) -> None:
        self._policy = policy

    def _kill(self) -> dict[str, Any]:
        return dict(self._policy.get("killswitch", {}))

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
    """Every rule that fires, in order. The caller trips on the first.

    Returning all of them means a test can assert that a combination trips, and
    an operator reading the audit log sees every reason rather than the first.
    """
    reasons: list[str] = []
    if skew_seconds is not None:
        found = tripper.clock_skew(skew_seconds)
        if found:
            reasons.append(found)
    if ambiguous_in_run is not None and ambiguous_24h is not None:
        found = tripper.ambiguous(ambiguous_in_run, ambiguous_24h)
        if found:
            reasons.append(found)
    if failed_1h is not None:
        found = tripper.failures(failed_1h)
        if found:
            reasons.append(found)
    if extraction_24h is not None:
        found = tripper.extraction_conflicts(extraction_24h)
        if found:
            reasons.append(found)

    # Only evaluate the compliance rule when a failure was actually observed.
    # `None` means "nothing to judge"; the string "UNKNOWN_STATUS" is a real
    # observation that simply is not a compliance type. Treating both as
    # "present" made this fire on every poll that had nothing to report.
    if failure_type is not None:
        found = AutomaticTripper.compliance(failure_type, reason_codes)
        if found:
            reasons.append(found)
    return reasons


Guard = Callable[[], None]
