"""Human halt clearing through two fresh, domain-bound passkey decisions."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from app.core import audit, db, record_signing
from app.core.operators import Session, utcnow
from app.core.signing import Passkeys, SigningError


def clear_record(conn: db.Connection, reason: str) -> tuple[str, dict[str, Any]]:
    if not reason.strip() or len(reason) > 1000:
        raise SigningError("Clearing a halt requires a reason of at most 1000 characters")
    active = conn.execute("SELECT halted,trip_id FROM killswitch_state WHERE id=1").fetchone()
    if not active or not active["halted"] or not active["trip_id"]:
        raise SigningError("There is no active database halt to clear")
    trip = conn.execute("SELECT cleared_at FROM trip WHERE id=?", (active["trip_id"],)).fetchone()
    if not trip or trip["cleared_at"]:
        raise SigningError("Active halt references missing or already-cleared trip evidence")
    record = {"kind": "CLEAR", "trip_id": active["trip_id"], "reason": reason.strip()}
    candidates = conn.execute(
        "SELECT canonical_json AS record_json FROM signed_record WHERE purpose='CLEAR' "
        "UNION ALL SELECT record_json FROM signing_challenge "
        "WHERE purpose='CLEAR' AND consumed_at IS NULL"
    ).fetchall()
    for candidate in candidates:
        if not candidate["record_json"]:
            continue
        prior = json.loads(candidate["record_json"])
        if (
            prior.get("trip_id") == record["trip_id"]
            and prior.get("reason") == record["reason"]
            and prior.get("expires_at")
            and datetime.fromisoformat(prior["expires_at"]) > utcnow()
        ):
            record = prior
            break
    else:
        record.update(
            round_id=str(uuid4()),
            created_at=utcnow().isoformat(),
            expires_at=(utcnow() + timedelta(hours=4)).isoformat(),
        )
    subject = (
        str(active["trip_id"])
        + ":"
        + hashlib.sha256(audit.canonical_json(record).encode()).hexdigest()
    )
    return subject, record


def finish_clear(
    conn: db.Connection,
    session: Session,
    passkeys: Passkeys,
    *,
    reason: str,
    ceremony_id: str,
    credential: dict[str, Any],
) -> bool:
    with db.transaction(conn):
        subject, record = clear_record(conn, reason)
        record_signing.finish_record(
            conn,
            session,
            passkeys,
            purpose="CLEAR",
            subject_id=subject,
            record=record,
            ceremony_id=ceremony_id,
            credential=credential,
        )
        count = conn.execute(
            "SELECT COUNT(*) FROM signed_record WHERE purpose='CLEAR' AND subject_id=?", (subject,)
        ).fetchone()[0]
        if count < 2:
            return False
        approvers = record_signing.verify_records(
            conn, passkeys, purpose="CLEAR", subject_id=subject, record=record, required=2
        )
        now = utcnow().isoformat()
        conn.execute(
            "UPDATE trip SET cleared_at=?,cleared_by=? WHERE id=?",
            (now, ",".join(approvers), record["trip_id"]),
        )
        conn.execute(
            "UPDATE killswitch_state SET halted=0,halted_at=NULL,reason=NULL,trip_id=NULL "
            "WHERE id=1"
        )
        audit.append(conn, "halt.cleared", {**record, "approvers": approvers})
        # Never remove a filesystem HALT marker here: it can represent a newer
        # human halt. Its local removal is a separate explicit operator action.
        return True
