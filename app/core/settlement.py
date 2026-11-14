"""Conservative local settlement labels after actual financial reconciliation.

These labels implement the signed policy's assumed return windows. They are not
provider guarantees of irrevocability; subsequent failures must still reopen them.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.core import audit, db, packets
from app.core.calendars import move_business_days
from app.core.operators import utcnow
from app.core.policy import LoadedPolicy


def due_at(first_paid: datetime, rail: str, policy: LoadedPolicy) -> datetime:
    if first_paid.tzinfo is None:
        raise ValueError("Settlement timestamp requires timezone")
    rule = policy.policy["settlement"][rail]
    zone = ZoneInfo(
        {
            "ACH": "America/New_York",
            "FPS": "Europe/London",
            "SEPA": "Europe/Brussels",
            "SWIFT": "America/New_York",
        }[rail]
    )
    local = first_paid.astimezone(zone)
    days = rule["presumed_settled_business_days"] if rail == "SWIFT" else rule["business_days"]
    day = move_business_days(local.date(), days, rail)
    calendar_due = datetime.combine(day, local.timetz(), tzinfo=zone).astimezone(UTC)
    return max(calendar_due, first_paid + timedelta(hours=max(48, rule.get("min_hours", 48))))


def finalize_reconciled(conn: db.Connection, run_id: str, policy: LoadedPolicy) -> int:
    """Caller must reconcile and verify audited intents under the same writer lock."""
    changed = 0
    with db.transaction(conn):
        latest = conn.execute(
            "SELECT payload_json FROM audit_log WHERE kind='run.reconciled' "
            "AND json_extract(payload_json,'$.run_id')=? ORDER BY seq DESC LIMIT 1",
            (run_id,),
        ).fetchone()
        if not latest:
            return 0
        match = json.loads(latest[0])
        if not match["matched"] or utcnow() - datetime.fromisoformat(
            match["observed_at"]
        ) > timedelta(seconds=30):
            return 0
        for attempt in conn.execute(
            "SELECT * FROM transfer_attempt WHERE run_id=? AND awx_status='PAID' "
            "AND wt_state='PAID_PROVISIONAL'",
            (run_id,),
        ).fetchall():
            if not attempt["first_paid_at"] or attempt["amount_usd"] is None:
                continue
            packet = conn.execute(
                "SELECT canonical_json FROM approval_packet WHERE id=?", (attempt["packet_id"],)
            ).fetchone()
            terms = packets.PaymentPacket.model_validate_json(packet[0])
            item = terms.items[0]
            if utcnow() < due_at(
                datetime.fromisoformat(attempt["first_paid_at"]), item.rail, policy
            ):
                continue
            financial = [
                json.loads(row[0])
                for row in conn.execute(
                    "SELECT canonical_json FROM financial_posting WHERE run_id=?",
                    (run_id,),
                ).fetchall()
            ]
            associated = [row for row in financial if row["source_id"] == attempt["transfer_id"]]
            payouts = [
                row
                for row in associated
                if row["transaction_type"] == "PAYOUT"
                and row["source_type"] == "PAYOUT"
                and row["currency"] == item.source_currency
                and row.get("amount") is not None
                and abs(Decimal(str(row["amount"]))) == Decimal(item.transfer_amount)
                and Decimal(str(row["net"])) <= -Decimal(item.transfer_amount)
            ]
            if len(payouts) != 1 or any(
                row["transaction_type"] in {"PAYOUT_FAILURE", "PAYOUT_REVERSAL"}
                for row in associated
            ):
                continue
            payee = conn.execute(
                "SELECT * FROM payee_version WHERE id=?", (item.payee_version_id,)
            ).fetchone()
            if not payee or payee["status"] in {
                "SUSPENDED",
                "COMPLIANCE_HOLD",
                "REJECTED",
                "RETIRED",
            }:
                continue
            label = "PRESUMED_SETTLED" if item.rail == "SWIFT" else "FINAL"
            now = utcnow().isoformat()
            conn.execute(
                "UPDATE transfer_attempt SET wt_state=?,final_at=?,updated_at=? WHERE id=?",
                (label, now, now, attempt["id"]),
            )
            if label == "FINAL":
                conn.execute(
                    "UPDATE obligation_tranche SET state='FINAL' "
                    "WHERE obligation_id=? AND tranche_no=?",
                    (item.obligation_id, item.tranche_no),
                )
                remaining = conn.execute(
                    "SELECT 1 FROM obligation_tranche WHERE obligation_id=? AND state<>'FINAL'",
                    (item.obligation_id,),
                ).fetchone()
                conn.execute(
                    "UPDATE obligation SET state=?,updated_at=? WHERE id=?",
                    ("READY" if remaining else "CLOSED", now, item.obligation_id),
                )
                count = conn.execute(
                    "SELECT COUNT(*) FROM transfer_attempt "
                    "WHERE payee_version_id=? AND wt_state='FINAL'",
                    (item.payee_version_id,),
                ).fetchone()[0]
                conn.execute(
                    "UPDATE payee_version SET status=?,final_payment_count=?,"
                    "updated_at=? WHERE id=?",
                    (
                        "ACTIVE" if count >= 2 else "ACTIVE_CAPPED",
                        count,
                        now,
                        item.payee_version_id,
                    ),
                )
                requests = conn.execute(
                    "SELECT id,old_payee_version_id FROM payee_change_request "
                    "WHERE vendor_id=? AND proposed_details_ref=? AND status='COOLING_OFF'",
                    (item.vendor_id, payee["details_ref"]),
                ).fetchall()
                for request in requests:
                    conn.execute(
                        "UPDATE payee_change_request SET status='APPROVED',decided_at=? WHERE id=?",
                        (now, request["id"]),
                    )
                    if request["old_payee_version_id"]:
                        conn.execute(
                            "UPDATE payee_version SET status='SUPERSEDED',updated_at=? WHERE id=?",
                            (now, request["old_payee_version_id"]),
                        )
            audit.append(
                conn,
                "payout.settlement_labelled",
                {
                    "request_id": item.request_id,
                    "run_id": run_id,
                    "label": label,
                    "policy_sha256": policy.sha256,
                    "financial_id": payouts[0]["id"],
                    "return_window_is_policy_assumption": True,
                },
            )
            changed += 1
    return changed
