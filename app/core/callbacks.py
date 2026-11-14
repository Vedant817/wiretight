"""Real operator callback records and executor-side evidence verification."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core import audit, db, oob, record_signing
from app.core.operators import Session, utcnow
from app.core.signing import Passkeys, SigningError


class CallbackInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    contact_id: str = Field(min_length=1, max_length=128)
    vendor_person_name: str = Field(min_length=1, max_length=120)
    vendor_person_role: str = Field(min_length=1, max_length=120)
    called_at: str = Field(min_length=20, max_length=40)
    outcome: Literal["CONFIRMED", "DENIED", "NO_ANSWER"]
    readback_last4_ok: bool
    readback_name_ok: bool
    attachment_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @field_validator("called_at")
    @classmethod
    def aware_time(cls, value: str) -> str:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError("Callback time requires a timezone")
        return parsed.astimezone(UTC).isoformat()


def _contact(row: db.sqlite3.Row) -> oob.Contact:
    return oob.Contact(
        id=row["id"],
        vendor_id=row["vendor_id"],
        kind=row["kind"],
        value_norm=row["value_norm"],
        provenance=row["provenance"],
        created_at=datetime.fromisoformat(row["created_at"]),
        changed_at=datetime.fromisoformat(row["changed_at"]) if row["changed_at"] else None,
        active=bool(row["active"]),
    )


def build_record(
    conn: db.Connection, session: Session, request_id: str, body: CallbackInput
) -> dict[str, Any]:
    request = conn.execute(
        "SELECT * FROM payee_change_request WHERE id=?", (request_id,)
    ).fetchone()
    if not request or request["status"] not in {
        "RECEIVED",
        "PENDING_CALLBACK",
        "COOLING_OFF",
        "APPROVED",
    }:
        raise SigningError("Bank-change request is unavailable")
    oob.check_recorder(
        recorded_by_role=session.role,
        recorded_by_id=session.user_id,
        requester_set=json.loads(request["requester_set"]),
        intake_user_id=request["intake_user_id"],
    )
    contact = conn.execute(
        "SELECT * FROM vendor_contact WHERE id=? AND vendor_id=?",
        (body.contact_id, request["vendor_id"]),
    ).fetchone()
    if not contact or contact["kind"] != "phone":
        raise SigningError("Select an independent phone contact from the supplier master")
    received = datetime.fromisoformat(request["received_at"])
    called = datetime.fromisoformat(body.called_at)
    now = utcnow()
    if called > now or now - called > timedelta(days=7):
        raise SigningError("Callback must have occurred within the last seven days")
    if contact["changed_at"] and datetime.fromisoformat(
        contact["changed_at"]
    ) > received - timedelta(days=30):
        raise SigningError("Contact changed too recently or after the request")
    contacts = [
        _contact(row)
        for row in conn.execute(
            "SELECT * FROM vendor_contact WHERE vendor_id=?", (request["vendor_id"],)
        ).fetchall()
    ]
    oob.check_contact(
        contact=_contact(contact),
        change_request_received_at=received,
        other_contacts_for_vendor=contacts,
        thread_artefacts=json.loads(request["evidence"]),
    )
    oob.check_timing(called_at=called, change_request_received_at=received)
    oob.check_readback(
        outcome=body.outcome,
        readback_last4_ok=body.readback_last4_ok,
        readback_name_ok=body.readback_name_ok,
    )
    if contact["provenance"] == "document":
        raise SigningError("A number supplied in the change document cannot confirm it")
    if contact["provenance"] == "prior_invoice" and received - datetime.fromisoformat(
        contact["created_at"]
    ) < timedelta(days=90):
        raise SigningError(
            "Invoice contact provenance must predate the request by at least 90 days"
        )
    record = body.model_dump()
    record.update(
        kind="CALLBACK",
        change_request_id=request_id,
        recorded_by=session.user_id,
        vendor_id=request["vendor_id"],
        proposed_fingerprint=request["proposed_fingerprint"],
        proposed_details_ref=request["proposed_details_ref"],
        contact_created_at=contact["created_at"],
        contact_changed_at=contact["changed_at"],
        contact_value_sha256=hashlib.sha256(contact["value_norm"].encode()).hexdigest(),
    )
    return record


def callback_subject(record: dict[str, Any]) -> str:
    return (
        str(record["change_request_id"])
        + ":"
        + hashlib.sha256(audit.canonical_json(record).encode()).hexdigest()
    )


def begin_callback(
    conn: db.Connection,
    session: Session,
    passkeys: Passkeys,
    *,
    request_id: str,
    body: CallbackInput,
) -> dict[str, Any]:
    with db.transaction(conn):
        record = build_record(conn, session, request_id, body)
        return record_signing.begin_record(
            conn,
            session,
            passkeys,
            purpose="CALLBACK",
            subject_id=callback_subject(record),
            record=record,
        )


def apply_callback(
    conn: db.Connection,
    session: Session,
    passkeys: Passkeys,
    *,
    request_id: str,
    body: CallbackInput,
    ceremony_id: str,
    credential: dict[str, Any],
    cooling_hours: int = 72,
) -> str:
    with db.transaction(conn):
        record = build_record(conn, session, request_id, body)
        record_id = record_signing.finish_record(
            conn,
            session,
            passkeys,
            purpose="CALLBACK",
            subject_id=callback_subject(record),
            record=record,
            ceremony_id=ceremony_id,
            credential=credential,
        )
        signed = conn.execute("SELECT * FROM signed_record WHERE id=?", (record_id,)).fetchone()
        request = conn.execute(
            "SELECT * FROM payee_change_request WHERE id=?", (request_id,)
        ).fetchone()
        now = utcnow().isoformat()
        callback_id = str(uuid4())
        conn.execute(
            "INSERT INTO callback_verification(id,change_request_id,contact_id,recorded_by,"
            "vendor_person_name,"
            "vendor_person_role,called_at,readback_last4_ok,readback_name_ok,outcome,"
            "attachment_sha256,"
            "record_sha256,recorder_signature,recorder_nonce,signing_method,signed_via,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,'WEBAUTHN','ui_passkey',?)",
            (
                callback_id,
                request_id,
                body.contact_id,
                session.user_id,
                body.vendor_person_name,
                body.vendor_person_role,
                body.called_at,
                body.readback_last4_ok,
                body.readback_name_ok,
                body.outcome,
                body.attachment_sha256,
                signed["sha256"],
                signed["assertion"],
                signed["nonce"],
                now,
            ),
        )
        if body.outcome == "CONFIRMED":
            until = oob.cooling_off_until(
                callback_confirmed_at=datetime.fromisoformat(body.called_at),
                change_request_received_at=datetime.fromisoformat(request["received_at"]),
                cooling_off_hours=cooling_hours,
            ).isoformat()
            conn.execute(
                "UPDATE payee_change_request SET status='COOLING_OFF' WHERE id=?", (request_id,)
            )
            conn.execute(
                "UPDATE payee_version SET cooling_off_until=?,updated_at=? "
                "WHERE details_ref=? AND vendor_id=?",
                (until, now, request["proposed_details_ref"], request["vendor_id"]),
            )
        elif body.outcome == "DENIED":
            conn.execute(
                "UPDATE payee_change_request SET status='REJECTED',decided_at=? WHERE id=?",
                (now, request_id),
            )
            conn.execute(
                "UPDATE payee_version SET status='REJECTED',updated_at=? WHERE details_ref=?",
                (now, request["proposed_details_ref"]),
            )
            conn.execute(
                "UPDATE vendor SET fraud_flagged_at=? WHERE id=?", (now, request["vendor_id"])
            )
        audit.append(
            conn,
            "callback.recorded",
            {
                "callback_id": callback_id,
                "request_id": request_id,
                "outcome": body.outcome,
                "record_sha256": signed["sha256"],
            },
        )
        return callback_id


def verify_callback(
    conn: db.Connection, passkeys: Passkeys, *, payee_version_id: str
) -> dict[str, Any]:
    payee = conn.execute("SELECT * FROM payee_version WHERE id=?", (payee_version_id,)).fetchone()
    if not payee:
        raise SigningError("Payee version not found")
    request = conn.execute(
        "SELECT * FROM payee_change_request WHERE vendor_id=? AND proposed_details_ref=? "
        "ORDER BY received_at DESC LIMIT 1",
        (payee["vendor_id"], payee["details_ref"]),
    ).fetchone()
    if not request or request["status"] not in {"COOLING_OFF", "APPROVED"}:
        raise SigningError("Payee needs a confirmed independent callback")
    row = conn.execute(
        "SELECT * FROM signed_record WHERE purpose='CALLBACK' "
        "AND json_extract(canonical_json,'$.change_request_id')=? ORDER BY signed_at DESC LIMIT 1",
        (request["id"],),
    ).fetchone()
    if not row:
        raise SigningError("Signed callback evidence missing")
    record: dict[str, Any] = json.loads(row["canonical_json"])
    if (
        record.get("outcome") != "CONFIRMED"
        or record.get("proposed_fingerprint") != payee["fingerprint"]
    ):
        raise SigningError("Callback did not confirm these bank details")
    body = CallbackInput.model_validate({key: record[key] for key in CallbackInput.model_fields})
    session = Session(row["user_id"], "", "ops", "")
    if build_record(conn, session, request["id"], body) != record:
        raise SigningError("Callback evidence changed after signature")
    record_signing.verify_records(
        conn,
        passkeys,
        purpose="CALLBACK",
        subject_id=callback_subject(record),
        record=record,
        required=1,
    )
    callback = conn.execute(
        "SELECT * FROM callback_verification WHERE change_request_id=? AND record_sha256=? "
        "AND recorded_by=?",
        (request["id"], row["sha256"], row["user_id"]),
    ).fetchone()
    if not callback:
        raise SigningError("Callback row does not match signed evidence")
    for field in CallbackInput.model_fields:
        if callback[field] != record[field]:
            raise SigningError("Callback row fields disagree with signed evidence")
    if (
        callback["recorder_signature"] != row["assertion"]
        or callback["recorder_nonce"] != row["nonce"]
    ):
        raise SigningError("Callback row signature evidence changed")
    return record
