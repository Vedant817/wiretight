"""Authenticated manual intake with evidence and server-derived ownership/times."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core import audit, db, dupes, evidence, lock, operators, parsers, vendors
from app.core.bank_details import BankDetails, DetailVault
from app.core.policy import LoadedPolicy


class IntakeError(ValueError):
    pass


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class VendorInput(StrictInput):
    legal_name: str = Field(min_length=1, max_length=200)
    display_name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=80)
    tax_id: str | None = Field(default=None, min_length=1, max_length=80)


class ContactInput(StrictInput):
    phone: str = Field(pattern=r"^\+[1-9][0-9]{7,14}$")
    provenance: Literal["contract", "prior_invoice", "website", "registry"]
    evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class BankInput(StrictInput):
    details: BankDetails
    evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class InvoiceInput(StrictInput):
    vendor_id: str = Field(min_length=1, max_length=128)
    invoice_number: str = Field(min_length=1, max_length=128)
    amount: str = Field(pattern=r"^[0-9]{1,12}\.[0-9]{2}$")
    currency: Literal["USD", "GBP", "EUR"]
    due_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @field_validator("amount")
    @classmethod
    def positive(cls, value: str) -> str:
        if Decimal(value) <= 0:
            raise ValueError("Invoice amount must be positive")
        return value

    @field_validator("due_date")
    @classmethod
    def valid_date(cls, value: str) -> str:
        return date.fromisoformat(value).isoformat()

    @field_validator("invoice_number")
    @classmethod
    def valid_reference(cls, value: str) -> str:
        if not parsers.parse_invoice_no(value).valid or not parsers.parse_reference(value).valid:
            raise ValueError("Invoice number must be a valid payment reference")
        return value


class ReviewInput(StrictInput):
    result: Literal["CLEAR", "HIT", "ERROR"]
    source: str = Field(min_length=1, max_length=1000)
    evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    checked_at: str = Field(min_length=20, max_length=40)

    @field_validator("checked_at")
    @classmethod
    def aware(cls, value: str) -> str:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError("Review time requires a timezone")
        return parsed.astimezone(UTC).isoformat()


def _vendor(conn: db.Connection, vendor_id: str) -> db.sqlite3.Row:
    row: db.sqlite3.Row | None = conn.execute(
        "SELECT * FROM vendor WHERE id=?", (vendor_id,)
    ).fetchone()
    if not row:
        raise IntakeError("Supplier does not exist")
    return row


def add_vendor(
    conn: db.Connection,
    session: operators.Session,
    body: VendorInput,
    policy: LoadedPolicy,
) -> str:
    name = vendors.normalise_legal_name(body.legal_name)
    if not name or body.category not in policy.policy["vendor_category_reason"]:
        raise IntakeError("Supplier legal name or policy category is invalid")
    with db.transaction(conn):
        operators.require_active(conn, session)
        if conn.execute(
            "SELECT id FROM vendor WHERE legal_name_norm=? OR (? IS NOT NULL AND tax_id=?)",
            (name, body.tax_id, body.tax_id),
        ).fetchone():
            raise IntakeError("Supplier legal name or tax identifier is already on file")
        identifier = str(uuid4())
        conn.execute(
            "INSERT INTO vendor(id,legal_name_norm,display_name,tax_id,category,created_at) "
            "VALUES(?,?,?,?,?,?)",
            (
                identifier,
                name,
                body.display_name,
                body.tax_id,
                body.category,
                operators.utcnow().isoformat(),
            ),
        )
        audit.append(conn, "supplier.created", {"vendor_id": identifier, "by": session.user_id})
        return identifier


def add_contact(
    conn: db.Connection,
    session: operators.Session,
    vendor_id: str,
    body: ContactInput,
    *,
    historical_created_at: datetime | None = None,
) -> str:
    """Only the local administrator import may supply historical master dates.

    Web input has no historical_created_at field. A claimed master date is
    retained with the source hash and actual import time, never a phone-call proof.
    """
    now = operators.utcnow()
    created = historical_created_at or now
    if created.tzinfo is None or created > now:
        raise IntakeError("Historical master date must be timezone-aware and in the past")
    with db.transaction(conn):
        operators.require_active(conn, session)
        _vendor(conn, vendor_id)
        evidence.require(conn, body.evidence_sha256)
        if conn.execute(
            "SELECT id FROM vendor_contact WHERE vendor_id=? AND value_norm=? AND active=1",
            (vendor_id, body.phone[1:]),
        ).fetchone():
            raise IntakeError("Active supplier contact is already on file")
        identifier = str(uuid4())
        conn.execute(
            "INSERT INTO vendor_contact(id,vendor_id,kind,value,value_norm,provenance,source_ref,"
            "created_at,provenance_sha256,imported_at) VALUES(?,?,'phone',?,?,?,?,?,?,?)",
            (
                identifier,
                vendor_id,
                body.phone,
                body.phone[1:],
                body.provenance,
                body.evidence_sha256,
                created.astimezone(UTC).isoformat(),
                body.evidence_sha256,
                now.isoformat(),
            ),
        )
        audit.append(
            conn,
            "supplier.contact_added",
            {
                "vendor_id": vendor_id,
                "contact_id": identifier,
                "by": session.user_id,
                "provenance_sha256": body.evidence_sha256,
                "master_created_at": created.isoformat(),
                "imported_at": now.isoformat(),
                "historical_import": historical_created_at is not None,
            },
        )
        return identifier


def propose_bank(
    conn: db.Connection,
    vault: DetailVault,
    session: operators.Session,
    vendor_id: str,
    body: BankInput,
) -> dict[str, str]:
    text = evidence.bank_request_text(conn, vault, body.evidence_sha256)
    if evidence.require(conn, body.evidence_sha256)["media_type"] == "application/json":
        try:
            text = json.dumps(json.loads(text), ensure_ascii=False)
        except ValueError:
            raise IntakeError("Source JSON is malformed") from None
    phones = {
        re.sub(r"[^0-9]", "", value) for value in re.findall(r"\+?[0-9][0-9 ().-]{6,}[0-9]", text)
    }
    markers = ["source_sha256:" + body.evidence_sha256] + [
        "phone_sha256:" + hashlib.sha256(phone.encode()).hexdigest() for phone in sorted(phones)
    ]
    with lock.lock_transaction(conn):
        operators.require_active(conn, session)
        vendor = _vendor(conn, vendor_id)
        if vendors.normalise_legal_name(body.details.company_name) != vendor["legal_name_norm"]:
            raise IntakeError("Bank beneficiary company must match the supplier legal name")
        fingerprint = body.details.fingerprint()
        if conn.execute(
            "SELECT 1 FROM payee_version WHERE vendor_id=? AND fingerprint=? AND "
            "status NOT IN ('REJECTED','RETIRED')",
            (vendor_id, fingerprint),
        ).fetchone():
            raise IntakeError("These bank details are already on file")
        old = conn.execute(
            "SELECT id FROM payee_version WHERE vendor_id=? "
            "AND status IN ('ACTIVE','ACTIVE_CAPPED')",
            (vendor_id,),
        ).fetchall()
        if len(old) > 1:
            raise IntakeError(
                "Supplier has conflicting active bank versions; resolve before intake"
            )
        details_ref = vault.store(conn, body.details)
        masked = parsers.mask_account(body.details.iban or body.details.account_number)
        now = operators.utcnow().isoformat()
        payee_id = str(uuid4())
        conn.execute(
            "INSERT INTO payee_version(id,vendor_id,fingerprint,details_ref,masked,method,rail,"
            "country,currency,status,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,'PROPOSED',?,?)",
            (
                payee_id,
                vendor_id,
                fingerprint,
                details_ref,
                masked,
                body.details.method,
                body.details.rail(),
                body.details.country,
                body.details.currency,
                now,
                now,
            ),
        )
        request = lock.open_request(
            conn,
            vendor_id=vendor_id,
            source_kind="upload",
            intake_user_id=session.user_id,
            proposed_details_ref=details_ref,
            proposed_masked=masked,
            proposed_fingerprint=fingerprint,
            source_message_id=body.evidence_sha256,
            requester_set=(session.user_id,),
            evidence=tuple(markers),
            old_payee_version_id=old[0]["id"] if old else None,
        )
        lock.request_callback(conn, request.id)
        audit.append(
            conn,
            "bank_change.received",
            {
                "request_id": request.id,
                "payee_version_id": payee_id,
                "vendor_id": vendor_id,
                "fingerprint": fingerprint,
                "source_sha256": body.evidence_sha256,
                "by": session.user_id,
            },
        )
        return {
            "request_id": request.id,
            "payee_version_id": payee_id,
            "status": "PENDING_CALLBACK",
        }


def add_invoice(conn: db.Connection, session: operators.Session, body: InvoiceInput) -> str:
    with db.transaction(conn):
        operators.require_active(conn, session)
        _vendor(conn, body.vendor_id)
        evidence.require(conn, body.evidence_sha256)
        key = dupes.obligation_key(body.vendor_id, body.invoice_number)
        if conn.execute("SELECT 1 FROM duplicate_lock WHERE obligation_key=?", (key,)).fetchone():
            raise IntakeError("Exact duplicate invoice is blocked")
        bill_id, identifier = str(uuid4()), str(uuid4())
        now = operators.utcnow().isoformat()
        conn.execute(
            "INSERT INTO bill(id,source_kind,source_ref,document_sha256,raw_json,"
            "ingested_by,ingested_at) "
            "VALUES(?,'manual',?,?,?,?,?)",
            (
                bill_id,
                body.evidence_sha256,
                body.evidence_sha256,
                audit.canonical_json(body.model_dump()),
                session.user_id,
                now,
            ),
        )
        conn.execute(
            "INSERT INTO obligation(id,vendor_id,invoice_no_norm,invoice_no_raw,amount,currency,"
            "due_date,state,requester_set,bill_id,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?,'READY',?,?,?,?)",
            (
                identifier,
                body.vendor_id,
                parsers.normalise_invoice_no(body.invoice_number),
                body.invoice_number,
                body.amount,
                body.currency,
                body.due_date,
                json.dumps([session.user_id]),
                bill_id,
                now,
                now,
            ),
        )
        conn.execute(
            "INSERT INTO duplicate_lock(obligation_key,obligation_id,created_at) VALUES(?,?,?)",
            (key, identifier, now),
        )
        audit.append(
            conn,
            "invoice.received",
            {
                "obligation_id": identifier,
                "bill_id": bill_id,
                "source_sha256": body.evidence_sha256,
                "by": session.user_id,
            },
        )
        return identifier


def review_record(
    conn: db.Connection,
    session: operators.Session,
    payee_id: str,
    body: ReviewInput,
) -> dict[str, Any]:
    if session.role != "ops":
        raise IntakeError("An operations operator must record the compliance review")
    checked = datetime.fromisoformat(body.checked_at)
    if checked > operators.utcnow() or (operators.utcnow() - checked).total_seconds() > 86400:
        raise IntakeError("Review must have occurred within the last 24 hours")
    evidence.require(conn, body.evidence_sha256)
    payee = conn.execute(
        "SELECT p.*,d.sha256 FROM payee_version p JOIN protected_details d ON d.id=p.details_ref "
        "WHERE p.id=?",
        (payee_id,),
    ).fetchone()
    if not payee or payee["status"] in {"REJECTED", "RETIRED", "SUPERSEDED"}:
        raise IntakeError("Bank-detail version is unavailable for review")
    return {
        "kind": "COMPLIANCE_REVIEW",
        "id": str(uuid4()),
        "payee_version_id": payee_id,
        "recorded_by": session.user_id,
        **body.model_dump(),
        "created_at": operators.utcnow().isoformat(),
        "payee_fingerprint": payee["fingerprint"],
        "details_sha256": payee["sha256"],
    }
