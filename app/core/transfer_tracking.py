"""Fold validated provider observations without inventing settlement or refunds."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.core import audit, db, killswitch, statemachine
from app.core.bank_details import DetailVault
from app.core.operators import utcnow


def observe(conn: db.Connection, vault: DetailVault, data: dict[str, Any]) -> None:
    with db.transaction(conn):
        row = conn.execute(
            "SELECT * FROM transfer_attempt WHERE request_id=?", (data["request_id"],)
        ).fetchone()
        if not row:
            raise ValueError("Provider payout has no local attempt")
        folded = statemachine.apply_transfer_observation(
            awx_status=data["status"],
            failure_type=data.get("failure_type"),
            failure_reason=data.get("failure_reason"),
            current_awx_status=row["awx_status"],
            current_failure_type=row["failure_type"],
            current_failure_reason=row["failure_reason"],
            wt_state=row["wt_state"],
        )
        state = statemachine.wt_next(row["wt_state"], awx_status=folded.awx_status)
        failed = data["status"] in {"FAILED", "CANCELLED"}
        compliance = failed and any(
            killswitch.is_compliance_failure(value)
            for value in (data.get("failure_type"), folded.failure_type)
        )
        if failed and row["wt_state"] in {"FINAL", "PRESUMED_SETTLED", "REOPENED"}:
            state = "REOPENED"
        now = utcnow().isoformat()
        first_paid = row["first_paid_at"] or (now if data["status"] == "PAID" else None)
        conn.execute(
            "UPDATE transfer_attempt SET transfer_id=?,awx_status=?,wt_state=?,failure_type=?,"
            "failure_reason=?,first_paid_at=?,updated_at=? WHERE id=?",
            (
                data["id"],
                folded.awx_status,
                state,
                folded.failure_type,
                folded.failure_reason,
                first_paid,
                now,
                row["id"],
            ),
        )
        conn.execute(
            "INSERT INTO transfer_observation(id,transfer_id,observed_at,awx_status,raw_json) "
            "VALUES(?,?,?,?,?)",
            (str(uuid4()), data["id"], now, data["status"], vault.encrypt_json(data)),
        )
        kind = (
            "PAYOUT_FAILURE"
            if failed
            else "UNKNOWN_STATUS"
            if folded.unknown_status_incident
            else None
        )
        if kind:
            if not conn.execute(
                "SELECT 1 FROM incident WHERE obligation_id=? AND kind=? AND closed_at IS NULL",
                (row["obligation_id"], kind),
            ).fetchone():
                conn.execute(
                    "INSERT INTO incident(id,obligation_id,payee_version_id,kind,severity,"
                    "detail,opened_at) "
                    "VALUES(?,?,?,?,'critical',?,?)",
                    (
                        str(uuid4()),
                        row["obligation_id"],
                        row["payee_version_id"],
                        kind,
                        audit.canonical_json({"transfer_id": data["id"], "status": data["status"]}),
                        now,
                    ),
                )
            conn.execute(
                "UPDATE obligation SET state=?,updated_at=? WHERE id=?",
                (
                    "HOLD: PAYOUT_FAILURE" if failed else "HOLD: UNKNOWN_STATUS",
                    now,
                    row["obligation_id"],
                ),
            )
            conn.execute(
                "UPDATE payee_version SET status=CASE WHEN status='COMPLIANCE_HOLD' THEN status "
                "ELSE 'SUSPENDED' END,updated_at=? WHERE id=?",
                (now, row["payee_version_id"]),
            )
        if compliance:
            # A provider restriction cannot be cleared by a generic retry or a
            # local halt clear. Keep the destination blocked independently.
            conn.execute(
                "UPDATE payee_version SET status='COMPLIANCE_HOLD',updated_at=? WHERE id=?",
                (now, row["payee_version_id"]),
            )
            conn.execute(
                "UPDATE obligation SET state='HOLD: COMPLIANCE_HOLD',updated_at=? WHERE id=?",
                (now, row["obligation_id"]),
            )
            conn.execute(
                "UPDATE approval_packet SET state='VOID' WHERE state IN ('OPEN','APPROVED') "
                "AND json_extract(canonical_json,'$.items[0].payee_version_id')=?",
                (row["payee_version_id"],),
            )
            killswitch.trip(
                conn, "Provider payout compliance restriction", origin="provider_compliance"
            )
        audit.append(
            conn,
            "payout.observed",
            {
                "request_id": data["request_id"],
                "transfer_id": data["id"],
                "status": data["status"],
                "wt_state": state,
                "regression": folded.regression,
                "failure_captured": bool(folded.failure_type),
            },
        )
