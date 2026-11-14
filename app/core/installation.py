"""Explicit local installation with real entity/roster and caller-chosen reserve."""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization

from app.core import audit, db
from app.core.operators import utcnow
from app.core.runtime_policy import validated_policy
from app.money import to_money_string


def default_policy(entity_id: str, roster: list[dict[str, Any]], reserve: str) -> dict[str, Any]:
    """Board safety defaults are controls; business identity and reserve are inputs."""
    return {
        "policy_version": "1",
        "entity_id": entity_id,
        "base_currency": "USD",
        "reserve_floor": {"USD": reserve},
        "roster": roster,
        "bank_change": {
            "cooling_off_hours": 72,
            "callback_contact_min_age_days": 30,
            "callback_validity_days": 7,
            "contact_provenance_min_invoice_age_days": 90,
            "first_payment_cap_usd": "2500.00",
            "first_payment_cap_median_fraction": "0.50",
            "cap_lift_final_payments": 2,
        },
        "t0": {
            "enabled": False,
            "per_payment_limit_usd": "2000.00",
            "min_final_payments": 3,
            "min_payment_fraction_of_limit": "0.25",
            "bank_details_unchanged_days": 60,
            "max_multiple_of_payee_median": "1.5",
            "disqualifiers": [
                "duplicate_suspicion",
                "EXTRACTION_CONFLICT",
                "HIDDEN_TEXT",
                "new_country",
                "contact_lt_30d",
                "unknown_sender",
                "SWIFT",
                "degraded_check",
                "cap_headroom",
            ],
        },
        "tiers": {"t2_threshold_usd": "10000.00", "t2_payee_7d_aggregate_usd": "10000.00"},
        "limits": {
            "per_run": {"t0_usd": "6000.00", "all_usd": "50000.00", "max_payments": 40},
            "per_day": {
                "t0_usd": "6000.00",
                "all_usd": "75000.00",
                "max_payments": 60,
                "max_runs": 2,
                "max_new_beneficiaries": 5,
                "calendar_tz": "Asia/Kolkata",
            },
            "per_payee_7d": {"t0_usd": "2000.00"},
            "per_payee_24h": {"max_t0": 1, "max_payments": 3},
            "per_approver_day_usd": "30000.00",
        },
        "approvals": {"max_validity_hours": 4, "challenge_ttl_seconds": 300},
        "fx": {"quote_validity": "HR_4", "quote_safety_margin_seconds": 120, "drift_bp": 25},
        "settlement": {
            "SEPA": {"business_days": 3, "calendar": "EUR_TARGET2", "min_hours": 48},
            "FPS": {"business_days": 3, "calendar": "GBP_ENGLAND", "min_hours": 48},
            "ACH": {"business_days": 2, "calendar": "USD_FED", "min_hours": 48},
            "SWIFT": {"final_by_timer": False, "presumed_settled_business_days": 10},
        },
        "ambiguous": {"escalate_after_days": 6},
        "killswitch": {
            "clock_skew_seconds": 120,
            "ambiguous_creates_per_run": 2,
            "ambiguous_creates_rolling_24h": 2,
            "failed_transfers_rolling_1h": 3,
            "extraction_conflicts_rolling_24h": 3,
            "clear_signatures": 2,
        },
        "rails": {
            "flight_business_days": {"SEPA": 2, "FPS": 1, "ACH": 2, "SWIFT": 3},
            "cutoff_local_time": {
                "SEPA": "14:00",
                "FPS": "14:00",
                "ACH": "14:00",
                "SWIFT": "12:00",
            },
            "fee_reservation_usd": {"SEPA": "5.00", "FPS": "5.00", "ACH": "5.00", "SWIFT": "30.00"},
        },
        "vendor_category_reason": {
            "freight": "freight",
            "manufacturing": "goods_purchased",
            "design_services": "professional_business_services",
            "software": "technical_services",
            "contractor": "professional_business_services",
        },
    }


def _exclusive_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def initialize(
    conn: db.Connection,
    *,
    legal_name: str,
    reserve_usd: str,
    policy_path: Path,
    key_dir: Path,
    seal_dir: Path,
) -> None:
    reserve = Decimal(reserve_usd)
    if reserve.is_finite() and reserve != reserve.quantize(Decimal("0.01")):
        raise ValueError("USD reserve floor must have at most two decimal places")
    if not legal_name.strip() or len(legal_name) > 200 or not reserve.is_finite() or reserve <= 0:
        raise ValueError("Enter the real legal name and a positive USD reserve floor")
    if policy_path.exists():
        raise ValueError("Policy file already exists; refusing to overwrite signed terms")
    roster = [
        dict(row)
        for row in conn.execute(
            "SELECT u.id,u.name,u.role,u.email FROM user u "
            "JOIN operator_auth a ON a.user_id=u.id WHERE a.enabled=1 ORDER BY u.id"
        )
    ]
    if sum(user["role"] == "approver" for user in roster) < 3 or not any(
        user["role"] == "ops" for user in roster
    ):
        raise ValueError("Provision at least three approvers and a separate ops operator first")
    with db.transaction(conn):
        rows = conn.execute("SELECT id,legal_name FROM entity").fetchall()
        if rows:
            if len(rows) != 1 or rows[0]["legal_name"] != legal_name.strip():
                raise ValueError("This database already belongs to a different business")
            entity_id = rows[0]["id"]
        else:
            entity_id = str(uuid4())
            conn.execute(
                "INSERT INTO entity(id,legal_name,base_currency,created_at) VALUES(?,?,'USD',?)",
                (entity_id, legal_name.strip(), utcnow().isoformat()),
            )
            conn.execute(
                "INSERT INTO schema_meta(key,value) VALUES('request_namespace',?)", (str(uuid4()),)
            )
            audit.append(conn, "installation.created", {"entity_id": entity_id})
    key_dir.mkdir(parents=True, exist_ok=True)
    private_path, public_path = key_dir / "audit_ed25519.pem", key_dir / "audit.public"
    if not private_path.exists():
        if public_path.exists():
            raise ValueError(
                "Audit private key missing; do not replace an established audit identity"
            )
        audit.save_private_key(audit.generate_key(), private_path)
    key = audit.load_private_key(private_path)
    public = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    if public_path.exists():
        if public_path.read_bytes() != public:
            raise ValueError("Audit public/private keys disagree")
    else:
        _exclusive_write(public_path, public)
    if not (key_dir / "details.key").exists():
        _exclusive_write(key_dir / "details.key", Fernet.generate_key())
    policy = default_policy(entity_id, roster, to_money_string(reserve, "USD"))
    _exclusive_write(policy_path, yaml.safe_dump(policy, sort_keys=False).encode())
    validated_policy(conn, policy_path)
    audit.write_checkpoint(conn, seal_dir, key, reason="installation")
