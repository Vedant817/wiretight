"""Canonical payment terms rebuilt from persisted obligations and bank evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from decimal import ROUND_DOWN, Decimal
from statistics import median
from typing import Any, Literal
from uuid import UUID, uuid4, uuid5

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core import audit, callbacks, db, dupes, parsers, record_signing
from app.core.bank_details import DetailVault
from app.core.calendars import move_business_days
from app.core.operators import utcnow
from app.core.policy import LoadedPolicy
from app.core.signing import Passkeys
from app.money import parse_money, to_money_string


class PaymentBlockedError(RuntimeError):
    pass


class PaymentItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    obligation_id: str
    vendor_id: str
    vendor_name: str
    account_holder_name: str
    masked_destination: str
    tranche_no: int = Field(ge=1, le=2)
    attempt_no: int = Field(ge=1)
    request_id: str = Field(min_length=1, max_length=50)
    replaces_transfer_id: str | None = None
    beneficiary_nickname: str
    payee_version_id: str
    payee_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    details_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    open_change_request_ids: list[str]
    transfer_method: Literal["LOCAL", "SWIFT"]
    swift_charge_option: Literal["PAYER"] | None = None
    fee_paid_by: Literal["PAYER"] | None = None
    rail: Literal["ACH", "FPS", "SEPA", "SWIFT"]
    transfer_currency: Literal["USD", "EUR", "GBP"]
    transfer_amount: str = Field(pattern=r"^[0-9]+\.[0-9]{2}$")
    source_currency: Literal["USD", "EUR", "GBP"]
    reason: str
    reference: str
    latest_send_date: str
    cooling_off_until: str | None
    callback_record_sha256: str | None
    evidence_hashes: list[str]
    dup_check_sha256: str
    screening: Literal["OPERATOR_REVIEW_CLEAR"]

    @field_validator("transfer_amount")
    @classmethod
    def positive_amount(cls, value: str) -> str:
        if Decimal(value) <= 0:
            raise ValueError("Payment amount must be positive")
        return value


class PaymentPacket(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    kind: Literal["PAYMENT"] = "PAYMENT"
    packet_version: Literal[1] = 1
    created_at: str
    expires_at: str
    run_id: str
    items: list[PaymentItem] = Field(min_length=1, max_length=1)
    totals_by_currency: dict[str, str]
    funding_packets: list[str]
    policy_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    tier: Literal["T1", "T2"]
    required_approvers: int = Field(ge=1, le=2)
    max_validity_seconds: int = Field(ge=1, le=14400)


def compliance_terms(row: db.sqlite3.Row) -> dict[str, Any]:
    return {
        "kind": "COMPLIANCE_REVIEW",
        **{
            key: row[key]
            for key in (
                "id",
                "payee_version_id",
                "recorded_by",
                "result",
                "source",
                "evidence_sha256",
                "checked_at",
                "created_at",
                "payee_fingerprint",
                "details_sha256",
            )
        },
    }


def review_clear(conn: db.Connection, payee_id: str, passkeys: Passkeys) -> None:
    row = conn.execute(
        "SELECT r.*,u.role,a.enabled FROM compliance_review r JOIN user u ON u.id=r.recorded_by "
        "JOIN operator_auth a ON a.user_id=u.id WHERE "
        "r.payee_version_id=? ORDER BY r.created_at DESC LIMIT 1",
        (payee_id,),
    ).fetchone()
    if not row or not row["enabled"] or row["role"] != "ops" or row["result"] != "CLEAR":
        raise PaymentBlockedError("A current independent operator compliance review is required")
    payee = conn.execute(
        "SELECT p.fingerprint,d.sha256 FROM payee_version p "
        "JOIN protected_details d ON d.id=p.details_ref WHERE p.id=?",
        (payee_id,),
    ).fetchone()
    if (
        not payee
        or row["payee_fingerprint"] != payee["fingerprint"]
        or row["details_sha256"] != payee["sha256"]
    ):
        raise PaymentBlockedError("Compliance review does not cover this bank-detail version")
    checked = datetime.fromisoformat(row["checked_at"])
    if checked > utcnow() or utcnow() - checked > timedelta(days=1):
        raise PaymentBlockedError("Compliance review is expired")
    record_signing.verify_records(
        conn,
        passkeys,
        purpose="CALLBACK",
        subject_id="review:" + row["id"],
        record=compliance_terms(row),
        required=1,
    )


def _rate(rates: dict[str, Decimal], currency: str) -> Decimal:
    rate = rates.get(currency)
    if rate is None or not rate.is_finite() or rate <= 0:
        raise PaymentBlockedError("A live USD risk-basis rate is unavailable")
    return rate


def build_payment(
    conn: db.Connection,
    *,
    obligation_id: str,
    payee_id: str,
    tranche_no: int,
    run_id: str,
    policy: LoadedPolicy,
    passkeys: Passkeys,
    vault: DetailVault,
    rates: dict[str, Decimal],
    attempt_no: int | None = None,
    own_request_id: str | None = None,
    approval_created_at: datetime | None = None,
) -> PaymentPacket:
    obligation = conn.execute("SELECT * FROM obligation WHERE id=?", (obligation_id,)).fetchone()
    payee = conn.execute("SELECT * FROM payee_version WHERE id=?", (payee_id,)).fetchone()
    run = conn.execute("SELECT state FROM run WHERE id=?", (run_id,)).fetchone()
    if (
        not obligation
        or not payee
        or obligation["vendor_id"] != payee["vendor_id"]
        or not run
        or run["state"] != "OPEN"
    ):
        raise PaymentBlockedError("Obligation, supplier bank version or open run not found")
    if obligation["state"] not in {"READY", "PLANNED", "APPROVED"} or json.loads(
        obligation["flags"]
    ):
        raise PaymentBlockedError("Obligation is not eligible for payment")
    if payee["status"] not in {"PROPOSED", "ACTIVE_CAPPED", "ACTIVE"}:
        raise PaymentBlockedError("Bank details are not eligible for payment")
    details = vault.load(conn, payee["details_ref"])
    if details.fingerprint() != payee["fingerprint"] or details.currency != obligation["currency"]:
        raise PaymentBlockedError("Bank details changed or payment currency mismatches")
    review_clear(conn, payee_id, passkeys)
    rate = _rate(rates, obligation["currency"])
    own_lock = conn.execute(
        "SELECT obligation_id FROM duplicate_lock WHERE obligation_key=?",
        (dupes.obligation_key(payee["vendor_id"], obligation["invoice_no_norm"]),),
    ).fetchone()
    if not own_lock or own_lock["obligation_id"] != obligation_id:
        raise PaymentBlockedError("Obligation does not hold its duplicate lock")
    callback_hash = None
    effective_cooling = payee["cooling_off_until"]
    if payee["status"] != "ACTIVE":
        record = callbacks.verify_callback(conn, passkeys, payee_version_id=payee_id)
        rule = policy.policy["bank_change"]
        contact_age = datetime.fromisoformat(
            record["change_request_received_at"]
        ) - datetime.fromisoformat(record["contact_created_at"])
        if contact_age < timedelta(
            days=rule["callback_contact_min_age_days"]
        ) or utcnow() - datetime.fromisoformat(record["called_at"]) > timedelta(
            days=rule["callback_validity_days"]
        ):
            raise PaymentBlockedError("Callback does not satisfy the signed policy timing")
        callback_hash = hashlib.sha256(audit.canonical_json(record).encode()).hexdigest()
        required_until = max(
            datetime.fromisoformat(record["called_at"]),
            datetime.fromisoformat(record["change_request_received_at"]),
        ) + timedelta(hours=rule["cooling_off_hours"])
        if not payee["cooling_off_until"]:
            raise PaymentBlockedError("Bank details are still cooling off")
        effective_cooling = max(
            datetime.fromisoformat(payee["cooling_off_until"]), required_until
        ).isoformat()
        if datetime.fromisoformat(effective_cooling) > utcnow():
            raise PaymentBlockedError("Bank details are still cooling off")
    open_changes = conn.execute(
        "SELECT id,proposed_details_ref,status FROM payee_change_request WHERE vendor_id=? "
        "AND status IN ('RECEIVED','PENDING_CALLBACK','COOLING_OFF')",
        (payee["vendor_id"],),
    ).fetchall()
    if any(
        row["proposed_details_ref"] != payee["details_ref"] or row["status"] != "COOLING_OFF"
        for row in open_changes
    ):
        raise PaymentBlockedError("Supplier has unresolved bank-change requests")
    total = parse_money(obligation["amount"])
    final_history = [
        Decimal(row[0])
        for row in conn.execute(
            "SELECT amount_usd FROM transfer_attempt WHERE payee_version_id IN "
            "(SELECT id FROM payee_version WHERE vendor_id=?) AND "
            "wt_state='FINAL' AND amount_usd IS NOT NULL "
            "AND created_at>?",
            (payee["vendor_id"], (utcnow() - timedelta(days=365)).isoformat()),
        )
    ]
    cap_usd = Decimal(policy.policy["bank_change"]["first_payment_cap_usd"])
    if final_history:
        cap_usd = min(
            cap_usd,
            Decimal(median(final_history))
            * Decimal(policy.policy["bank_change"]["first_payment_cap_median_fraction"]),
        )
    buffer = Decimal(1) + Decimal(policy.policy["fx"]["drift_bp"]) / Decimal(10000)
    cap_native = (cap_usd / (rate * buffer)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    if payee["status"] != "ACTIVE" and total > cap_native:
        amounts = [cap_native, total - cap_native]
    else:
        amounts = [total]
    existing_split = conn.execute(
        "SELECT tranche_no,amount FROM obligation_tranche WHERE "
        "obligation_id=? ORDER BY tranche_no",
        (obligation_id,),
    ).fetchall()
    if existing_split:
        amounts = [Decimal(row["amount"]) for row in existing_split]
        if [row["tranche_no"] for row in existing_split] != list(range(1, len(amounts) + 1)) or sum(
            amounts
        ) != total:
            raise PaymentBlockedError("Stored tranches do not equal the obligation")
        if tranche_no == 1 and payee["status"] != "ACTIVE" and amounts[0] * rate > cap_usd:
            raise PaymentBlockedError("Live USD risk basis breaches the first-payment cap")
    if not 1 <= tranche_no <= len(amounts) or amounts[tranche_no - 1] <= 0:
        raise PaymentBlockedError("Invalid or empty payment tranche")
    if (
        tranche_no == 2
        and not conn.execute(
            "SELECT 1 FROM transfer_attempt WHERE obligation_id=? AND "
            "tranche_no=1 AND wt_state='FINAL'",
            (obligation_id,),
        ).fetchone()
    ):
        raise PaymentBlockedError("Tranche two is held until tranche one is FINAL")
    # Persist the split once. Changing risk basis cannot silently change a signed
    # or already-paid tranche; it needs explicit replanning.
    for number, amount in enumerate(amounts, 1):
        stored = conn.execute(
            "SELECT amount FROM obligation_tranche WHERE obligation_id=? AND tranche_no=?",
            (obligation_id, number),
        ).fetchone()
        text = to_money_string(amount, obligation["currency"])
        if stored and stored["amount"] != text:
            raise PaymentBlockedError("Tranche split changed; explicit replanning is required")
        if not stored:
            conn.execute(
                "INSERT INTO "
                "obligation_tranche(obligation_id,tranche_no,amount,currency,"
                "state,created_at) VALUES(?,?,?,?,?,?)",
                (
                    obligation_id,
                    number,
                    text,
                    obligation["currency"],
                    "READY" if number == 1 else "HELD_TRANCHE",
                    utcnow().isoformat(),
                ),
            )
    attempts = conn.execute(
        "SELECT * FROM transfer_attempt WHERE obligation_id=? ORDER BY attempt_no DESC",
        (obligation_id,),
    ).fetchall()
    attempts = [row for row in attempts if row["request_id"] != own_request_id]
    next_attempt = max((row["attempt_no"] for row in attempts), default=0) + 1
    if attempt_no is not None and attempt_no != next_attempt:
        raise PaymentBlockedError("Attempt sequence changed; prior sign-off cannot be replayed")
    if any(row["wt_state"] not in {"FINAL", "REJECTED", "CANCELLED_FAILED"} for row in attempts):
        raise PaymentBlockedError("An earlier payment attempt is still non-terminal or ambiguous")
    if any(row["tranche_no"] == tranche_no and row["wt_state"] == "FINAL" for row in attempts):
        raise PaymentBlockedError("This tranche is already paid and FINAL")
    number = (
        attempt_no
        if attempt_no is not None
        else (max((row["attempt_no"] for row in attempts), default=0) + 1)
    )
    namespace = conn.execute(
        "SELECT value FROM schema_meta WHERE key='request_namespace'"
    ).fetchone()
    if not namespace:
        raise PaymentBlockedError("Installation request namespace is missing")
    request_id = str(
        uuid5(UUID(namespace["value"]), f"transfer:{obligation_id}:t{tranche_no}:a{number}")
    )
    amount = amounts[tranche_no - 1]
    existing = conn.execute(
        "SELECT id,vendor_id,invoice_no_raw,amount,currency,due_date FROM obligation WHERE id<>?",
        (obligation_id,),
    ).fetchall()
    others = [
        dupes.Bill(
            obligation_id=row["id"],
            vendor_id=row["vendor_id"],
            invoice_no=row["invoice_no_raw"],
            amount=Decimal(row["amount"]),
            due_date=date.fromisoformat(row["due_date"]),
            amount_usd=Decimal(row["amount"]) * _rate(rates, row["currency"]),
        )
        for row in existing
    ]
    verdict = dupes.classify(
        candidate=dupes.Bill(
            obligation_id=obligation_id,
            vendor_id=payee["vendor_id"],
            invoice_no=obligation["invoice_no_raw"],
            amount=total,
            due_date=date.fromisoformat(obligation["due_date"]),
            amount_usd=total * rate,
        ),
        existing=others,
    )
    if verdict.hard_block:
        raise PaymentBlockedError("Exact duplicate invoice is blocked")
    vendor = conn.execute(
        "SELECT category,fraud_flagged_at,display_name FROM vendor WHERE id=?",
        (payee["vendor_id"],),
    ).fetchone()
    reason = policy.policy["vendor_category_reason"].get(vendor["category"])
    if (
        not reason
        or not parsers.parse_reason(reason).valid
        or not parsers.parse_reference(obligation["invoice_no_raw"]).valid
    ):
        raise PaymentBlockedError("Payment reason or reference requires review")
    tier: Literal["T1", "T2"] = (
        "T2"
        if payee["status"] != "ACTIVE"
        or details.method == "SWIFT"
        or verdict.t2_trigger
        or vendor["fraud_flagged_at"]
        or amount * rate >= Decimal(policy.policy["tiers"]["t2_threshold_usd"])
        else "T1"
    )
    bill = conn.execute(
        "SELECT document_sha256 FROM bill WHERE id=?", (obligation["bill_id"],)
    ).fetchone()
    if not bill:
        raise PaymentBlockedError("Invoice source evidence is missing")
    stored_details = conn.execute(
        "SELECT sha256 FROM protected_details WHERE id=?", (payee["details_ref"],)
    ).fetchone()
    item = PaymentItem(
        obligation_id=obligation_id,
        vendor_id=payee["vendor_id"],
        vendor_name=vendor["display_name"],
        account_holder_name=details.account_name,
        masked_destination=parsers.mask_account(details.iban or details.account_number),
        tranche_no=tranche_no,
        attempt_no=number,
        request_id=request_id,
        beneficiary_nickname="wt-" + payee_id,
        payee_version_id=payee_id,
        payee_fingerprint=payee["fingerprint"],
        details_sha256=stored_details["sha256"],
        open_change_request_ids=[row["id"] for row in open_changes],
        transfer_method=details.method,
        swift_charge_option="PAYER" if details.method == "SWIFT" else None,
        fee_paid_by="PAYER" if details.method == "SWIFT" else None,
        rail=details.rail(),
        transfer_currency=details.currency,
        transfer_amount=to_money_string(amount, details.currency),
        source_currency=details.currency,
        reason=reason,
        reference=obligation["invoice_no_raw"],
        latest_send_date=move_business_days(
            date.fromisoformat(obligation["due_date"]),
            -policy.policy["rails"]["flight_business_days"][details.rail()],
            details.rail(),
        ).isoformat(),
        cooling_off_until=effective_cooling,
        callback_record_sha256=callback_hash,
        evidence_hashes=[bill["document_sha256"]],
        dup_check_sha256=hashlib.sha256(
            audit.canonical_json(
                {
                    "kind": verdict.kind,
                    "against_id": verdict.against_id,
                    "window_total": verdict.window_total,
                }
            ).encode()
        ).hexdigest(),
        screening="OPERATOR_REVIEW_CLEAR",
    )
    created_at = approval_created_at or utcnow()
    return PaymentPacket(
        created_at=created_at.isoformat(),
        expires_at=(
            created_at + timedelta(hours=policy.policy["approvals"]["max_validity_hours"])
        ).isoformat(),
        run_id=run_id,
        items=[item],
        totals_by_currency={details.currency: item.transfer_amount},
        funding_packets=[],
        policy_sha256=policy.sha256,
        tier=tier,
        required_approvers=2 if tier == "T2" else 1,
        max_validity_seconds=policy.policy["approvals"]["max_validity_hours"] * 3600,
    )


def save_payment(conn: db.Connection, terms: PaymentPacket) -> str:
    raw = audit.canonical_json(terms.model_dump())
    digest = hashlib.sha256(raw.encode()).hexdigest()
    with db.transaction(conn):
        old = conn.execute(
            "SELECT id FROM approval_packet WHERE sha256=? AND state IN ('OPEN','APPROVED')",
            (digest,),
        ).fetchone()
        if old:
            return str(old["id"])
        conn.execute(
            "UPDATE approval_packet SET state='VOID' WHERE state IN ('OPEN','APPROVED') "
            "AND json_extract(canonical_json,'$.items[0].obligation_id')=?",
            (terms.items[0].obligation_id,),
        )
        packet_id = str(uuid4())
        now = utcnow()
        conn.execute(
            "INSERT INTO "
            "approval_packet(id,kind,canonical_json,sha256,tier,"
            "required_approvers,created_at,expires_at,state) "
            "VALUES(?,'PAYMENT',?,?,?,?,?,?,'OPEN')",
            (
                packet_id,
                raw,
                digest,
                terms.tier,
                terms.required_approvers,
                now.isoformat(),
                terms.expires_at,
            ),
        )
        audit.append(conn, "approval.created", {"packet_id": packet_id, "sha256": digest})
        return packet_id
