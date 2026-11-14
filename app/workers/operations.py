"""Crash-safe run and planning orchestration through the genuine provider client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.api.operations import PlanInput
from app.core import audit, db, killswitch, packets, reconciliation, runtime_policy
from app.core.operators import utcnow
from app.core.process_lock import exclusive_process
from app.core.signing import SigningError

if TYPE_CHECKING:
    from app.workers.executor import Executor


def finish(conn: db.Connection, job_id: str, result: dict[str, Any]) -> None:
    conn.execute(
        "UPDATE provider_job SET state='DONE',result_json=?,error=NULL,updated_at=? "
        "WHERE id=? AND state='PENDING'",
        (audit.canonical_json(result), utcnow().isoformat(), job_id),
    )
    audit.append(conn, "operation.finished", {"job_id": job_id, **result})


def require_requester(conn: db.Connection, job_id: str) -> None:
    if not conn.execute(
        "SELECT 1 FROM provider_job j JOIN user u ON u.id=j.requested_by "
        "JOIN operator_auth a ON a.user_id=u.id WHERE j.id=? AND j.state='PENDING' "
        "AND a.enabled=1 AND u.role='approver'",
        (job_id,),
    ).fetchone():
        raise SigningError("Requesting approver is revoked or unavailable")


def perform(executor: Executor, job_id: str, request: dict[str, Any]) -> None:
    operation = request.get("operation")
    conn = executor.database.connection()
    require_requester(conn, job_id)
    if operation in {"RECONCILE_RUN", "CLOSE_RUN"}:
        if set(request) != {"operation", "run_id"} or not isinstance(request["run_id"], str):
            raise SigningError("Invalid reconciliation request")
        run_id = request["run_id"]
        matched = executor.reconcile_run(run_id)
        with exclusive_process(executor.lock_file), db.transaction(conn):
            require_requester(conn, job_id)
            if operation == "CLOSE_RUN":
                if not matched:
                    raise reconciliation.ReconciliationError(
                        "Resolve reconciliation exceptions first"
                    )
                if conn.execute(
                    "SELECT 1 FROM approval_packet WHERE json_extract(canonical_json,'$.run_id')=? "
                    "AND state IN ('OPEN','APPROVED') UNION ALL SELECT 1 FROM transfer_attempt "
                    "WHERE run_id=? AND COALESCE(wt_state,'UNOBSERVED') NOT IN "
                    "('FINAL','PRESUMED_SETTLED','REJECTED','CANCELLED_FAILED')",
                    (run_id, run_id),
                ).fetchone():
                    raise reconciliation.ReconciliationError(
                        "Run has unresolved approvals or transfers"
                    )
                conn.execute(
                    "UPDATE run SET state='CLOSED',finished_at=? WHERE id=?",
                    (utcnow().isoformat(), run_id),
                )
                audit.append(conn, "run.closed", {"run_id": run_id, "job_id": job_id})
            finish(conn, job_id, {"run_id": run_id, "matched": matched})
        audit.write_checkpoint(conn, executor.seal_dir, executor.key, reason="run-job-" + job_id)
        return
    with exclusive_process(executor.lock_file):
        executor._trust(conn)
        policy = runtime_policy.load_runtime_policy(conn, executor.policy_path, executor.passkeys)
        killswitch.load(conn, executor.halt_file).guard()
        if operation == "OPEN_RUN" and set(request) == {"operation"}:
            run_id = reconciliation.open_run(conn, executor.client, operation_id=job_id)
            with db.transaction(conn):
                require_requester(conn, job_id)
                finish(conn, job_id, {"run_id": run_id})
        elif operation == "PLAN_PAYMENT":
            terms = PlanInput.model_validate({k: v for k, v in request.items() if k != "operation"})
            live = executor._live(conn)
            with db.transaction(conn):
                require_requester(conn, job_id)
                # Re-read policy/bank/obligation state under the write lock.
                policy = runtime_policy.load_runtime_policy(
                    conn, executor.policy_path, executor.passkeys
                )
                payment = packets.build_payment(
                    conn,
                    **terms.model_dump(),
                    policy=policy,
                    passkeys=executor.passkeys,
                    vault=executor.vault,
                    rates=live.rates,
                )
                packet_id = packets.save_payment(conn, payment)
                finish(conn, job_id, {"packet_id": packet_id})
        else:
            raise SigningError("Unknown planning operation")
        audit.write_checkpoint(conn, executor.seal_dir, executor.key, reason="plan-job-" + job_id)


def reconcile_open_runs(executor: Executor) -> bool:
    """Poll/reconcile reads continue while halted; mismatches never become healthy."""
    conn = executor.database.connection()
    matched = True
    for row in conn.execute("SELECT id FROM run WHERE state='OPEN'").fetchall():
        matched = executor.reconcile_run(row["id"]) and matched
    return matched
