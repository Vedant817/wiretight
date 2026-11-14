"""Historical HMAC clear fixture. Never imported by the application."""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from app.core import audit, db
from app.core.killswitch import *  # noqa: F403
from app.core.killswitch import HaltedError, _now, ensure_row


@dataclass
class ClearRequest:
    """One approver's signed agreement to clear the switch."""

    approver_id: str
    signature: bytes
    nonce: str
    method: str = "HMAC_FALLBACK"
    signed_via: str = "cli_hmac"

    def expected_signature(self, trip_id: str, reason: str) -> bytes:
        """HMAC over the §4.9 payload. Compared in constant time by the caller."""
        payload = clear_signature_payload(trip_id, reason).encode("ascii")
        return hmac.new(_approver_key(self.approver_id), payload, hashlib.sha256).digest()


TEST_KEY_SEED: Final[bytes] = b"wiretight-killswitch-test-seed"


def _approver_key(approver_id: str) -> bytes:
    return hashlib.sha256(TEST_KEY_SEED + approver_id.encode("utf-8")).digest()


def clear_signature_payload(trip_id: str, reason: str) -> str:
    """The exact bytes each approver signs to clear the switch (§4.9).

    ``sha256("clear|" + trip_id + "|" + reason)``. The delimiters matter: without
    them ``("ab", "c")`` and ``("a", "bc")`` would produce the same preimage.
    """
    return hashlib.sha256(f"clear|{trip_id}|{reason}".encode()).hexdigest()


def sign_clear(
    trip_id: str, reason: str, approver_id: str, *, nonce: str | None = None
) -> ClearRequest:
    """Produce a valid :class:`ClearRequest`. For tests and the CLI fallback."""
    request = ClearRequest(approver_id=approver_id, signature=b"", nonce=nonce or str(uuid.uuid4()))
    request.signature = request.expected_signature(trip_id, reason)
    return request


def _as_clear_request(value: ClearRequest | dict[str, Any]) -> ClearRequest:
    if isinstance(value, ClearRequest):
        return value
    return ClearRequest(
        approver_id=str(value.get("approver_id", "")),
        signature=value.get("signature", b""),
        nonce=str(value.get("challenge_nonce") or value.get("nonce") or uuid.uuid4()),
        method=str(value.get("method", "HMAC_FALLBACK")),
        signed_via=str(value.get("signed_via", "cli_hmac")),
    )


def clear(
    conn: db.Connection,
    trip_id: str,
    reason: str,
    clears: Sequence[ClearRequest | dict[str, Any]],
    *,
    required: int = 2,
    halt_file: str | Path | None = None,
    verify_signatures: bool = True,
) -> None:
    """Clear the halt. Requires ``required`` distinct, **verified** approver clears.

    Everything is checked before anything is written, and the write is a single
    transaction:

    * ``trip_id`` must be the trip that is *currently* active, so an old trip's id
      cannot be replayed to wave through a newer incident;
    * the approvers must be distinct and at least ``required`` of them;
    * each signature must verify over ``sha256("clear|" + trip_id + "|" + reason)``.

    Verifying first means a bad signature cannot leave a half-cleared switch, and
    the transaction means a failure part-way rolls back rather than leaving
    ``halted = 0`` with the incident still open.
    """
    if not reason.strip():
        raise HaltedError("clearing the kill switch requires a reason")

    requests = [_as_clear_request(value) for value in clears]
    approvers = [request.approver_id for request in requests]
    distinct = len(set(approvers))
    if distinct < required:
        raise HaltedError(
            f"clearing the kill switch needs {required} distinct approvers, got {distinct}"
        )

    ensure_row(conn)
    active = conn.execute("SELECT trip_id FROM killswitch_state WHERE id = 1").fetchone()
    active_id = active["trip_id"] if active is not None else None
    if active_id != trip_id:
        raise HaltedError(
            f"trip {trip_id!r} is not the active trip (active: {active_id!r}); "
            "clearing a stale trip would wave through an unresolved incident"
        )

    if verify_signatures:
        for request in requests:
            expected = request.expected_signature(trip_id, reason)
            if not hmac.compare_digest(expected, request.signature):
                raise HaltedError(
                    f"clear signature from {request.approver_id} does not verify over "
                    f"sha256(clear|{trip_id}|{reason}); the incident or reason changed"
                )

    with db.transaction(conn):
        conn.execute(
            "UPDATE trip SET cleared_at = ?, cleared_by = ? WHERE id = ?",
            (_now(), ",".join(sorted(set(approvers))), trip_id),
        )
        for request in requests:
            conn.execute(
                "INSERT INTO trip_clear_signature"
                " (id, trip_id, approver_id, method, signed_via, signature,"
                " challenge_nonce, signed_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(uuid.uuid4()),
                    trip_id,
                    request.approver_id,
                    request.method,
                    request.signed_via,
                    request.signature,
                    request.nonce,
                    _now(),
                ),
            )
        conn.execute(
            "UPDATE killswitch_state"
            " SET halted = 0, halted_at = NULL, reason = NULL, trip_id = NULL WHERE id = 1"
        )
        audit.log_intent(
            conn,
            kind="KILLSWITCH_CLEAR",
            payload={
                "trip_id": trip_id,
                "reason": reason,
                "approvers": sorted(set(approvers)),
            },
        )

    if halt_file is not None:
        # If this raises, the DB says RUNNING but the HALT file still reads as
        # halted, which is the safe direction: a human removes the file.
        with contextlib.suppress(OSError):
            Path(halt_file).unlink(missing_ok=True)
