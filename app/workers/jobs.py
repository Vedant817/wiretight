"""Durable authenticated job requests; an unfinished job never authorizes a repost."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.core import audit
from app.core.operators import utcnow
from app.integrations.airwallex import ProviderError

if TYPE_CHECKING:
    from app.workers.executor import Executor


def process_actions(executor: Executor) -> None:
    from pydantic import ValidationError

    from app.core.killswitch import HaltedError
    from app.core.packets import PaymentBlockedError
    from app.core.policy import PolicyError
    from app.core.reconciliation import ReconciliationError
    from app.core.signing import SigningError
    from app.workers import fx, operations
    from app.workers.executor import ExecutionBlockedError

    conn = executor.database.connection()
    for row in conn.execute(
        "SELECT * FROM provider_job WHERE state='PENDING' "
        "AND kind IN ('EXECUTE','QUOTE','PLAN') ORDER BY created_at,id"
    ).fetchall():
        actor = conn.execute(
            "SELECT a.enabled,u.role FROM operator_auth a JOIN user u ON u.id=a.user_id "
            "WHERE user_id=?",
            (row["requested_by"],),
        ).fetchone()
        if not actor or not actor["enabled"] or actor["role"] != "approver":
            with executor.database.transaction() as tx:
                tx.execute(
                    "UPDATE provider_job SET state='FAILED',error='requester_revoked',"
                    "updated_at=? WHERE id=?",
                    (utcnow().isoformat(), row["id"]),
                )
            continue
        try:
            request = json.loads(row["request_json"])
            if not isinstance(request, dict):
                raise SigningError("Malformed job request")
            if row["kind"] == "PLAN":
                operations.perform(executor, row["id"], request)
                continue
            if set(request) != {"packet_id"} or not isinstance(request["packet_id"], str):
                raise SigningError("Malformed execution job")
            packet_id = request["packet_id"]
            if row["kind"] == "QUOTE":
                result = {"conversion_packet_id": fx.prepare(executor, packet_id)}
            else:
                packet = conn.execute(
                    "SELECT kind FROM approval_packet WHERE id=?", (packet_id,)
                ).fetchone()
                if not packet:
                    raise SigningError("Missing approved packet")
                state = (
                    fx.execute(executor, packet_id)
                    if packet["kind"] == "CONVERSION"
                    else executor.execute(packet_id)
                )
                result = {"execution_state": state}
            with executor.database.transaction() as tx:
                tx.execute(
                    "UPDATE provider_job SET state=?,result_json=?,error=NULL,"
                    "updated_at=? WHERE id=?",
                    (
                        "PENDING"
                        if result.get("execution_state") in {"AMBIGUOUS", "BENEFICIARY_READY"}
                        else "DONE",
                        audit.canonical_json(result),
                        utcnow().isoformat(),
                        row["id"],
                    ),
                )
                audit.append(tx, "execution.job_finished", {"job_id": row["id"], **result})
        except (
            SigningError,
            PaymentBlockedError,
            ExecutionBlockedError,
            fx.FXBlockedError,
            ProviderError,
            ReconciliationError,
            PolicyError,
            HaltedError,
            ValidationError,
            ValueError,
        ) as exc:
            category = (
                exc.category
                if isinstance(exc, ProviderError)
                else "approval_or_execution_guard_refused"
            )
            with executor.database.transaction() as tx:
                tx.execute(
                    "UPDATE provider_job SET state='FAILED',error=?,updated_at=? WHERE id=?",
                    (category, utcnow().isoformat(), row["id"]),
                )
                audit.append(
                    tx, "execution.job_refused", {"job_id": row["id"], "category": category}
                )
