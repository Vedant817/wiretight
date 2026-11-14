"""Run and planning requests use the actual executor and client boundary."""

# ruff: noqa: F811
import json
from uuid import uuid4

from app.core import audit, operators, reconciliation
from app.workers.jobs import process_actions
from tests.unit.test_operators_signing import domain  # noqa: F401
from tests.unit.test_real_executor import execution  # noqa: F401


def enqueue(executor, request):
    conn = executor.database.connection()
    user = conn.execute("SELECT id FROM user WHERE email='operator0@example.test'").fetchone()[0]
    identifier = str(uuid4())
    now = operators.utcnow().isoformat()
    conn.execute(
        "INSERT INTO provider_job(id,kind,requested_by,request_json,state,created_at,updated_at) "
        "VALUES(?,'PLAN',?,?,'PENDING',?,?)",
        (identifier, user, audit.canonical_json(request), now, now),
    )
    return identifier


def result(executor, identifier):
    row = (
        executor.database.connection()
        .execute("SELECT * FROM provider_job WHERE id=?", (identifier,))
        .fetchone()
    )
    return dict(row)


def test_planning_and_reconciliation_jobs_use_real_guards_and_are_durable(execution):
    executor, provider, packet_id, terms = execution
    job = enqueue(
        executor,
        {
            "operation": "PLAN_PAYMENT",
            "run_id": terms.run_id,
            "obligation_id": "o",
            "payee_id": "payee",
            "tranche_no": 1,
        },
    )
    process_actions(executor)
    planned = result(executor, job)
    assert planned["state"] == "DONE", planned
    new_packet = json.loads(planned["result_json"])["packet_id"]
    assert new_packet == packet_id
    assert (
        executor.database.connection()
        .execute("SELECT state FROM approval_packet WHERE id=?", (new_packet,))
        .fetchone()[0]
        == "APPROVED"
    )
    process_actions(executor)
    assert result(executor, job) == planned
    assert provider.posts == []
    recon = enqueue(executor, {"operation": "RECONCILE_RUN", "run_id": terms.run_id})
    process_actions(executor)
    # The test's historical run baseline is deliberately not provider-sourced.
    assert result(executor, recon)["state"] == "FAILED"


def test_open_run_crash_before_job_ack_reuses_original_provider_baseline(execution):
    executor, provider, _, _ = execution
    conn = executor.database.connection()
    conn.execute("UPDATE run SET state='CLOSED'")
    job = enqueue(executor, {"operation": "OPEN_RUN"})
    # Commit the original baseline, then emulate process death before job acknowledgement.
    assert reconciliation.open_run(conn, executor.client, operation_id=job) == job
    baseline = conn.execute("SELECT opening_balances FROM run WHERE id=?", (job,)).fetchone()[0]
    provider.balance = "1.00"
    process_actions(executor)
    assert result(executor, job)["state"] == "DONE"
    assert (
        conn.execute("SELECT opening_balances FROM run WHERE id=?", (job,)).fetchone()[0]
        == baseline
    )
    assert conn.execute("SELECT COUNT(*) FROM run WHERE id=?", (job,)).fetchone()[0] == 1
    provider.balance = json.loads(baseline)["USD"]
    close_job = enqueue(executor, {"operation": "CLOSE_RUN", "run_id": job})
    process_actions(executor)
    assert result(executor, close_job)["state"] == "DONE"
    assert conn.execute("SELECT state FROM run WHERE id=?", (job,)).fetchone()[0] == "CLOSED"
    assert provider.posts == []


def test_plan_during_cooling_and_revoked_requester_are_refused(execution):
    executor, provider, _, terms = execution
    conn = executor.database.connection()
    conn.execute("UPDATE payee_version SET cooling_off_until='2099-01-01T00:00:00+00:00'")
    job = enqueue(
        executor,
        {
            "operation": "PLAN_PAYMENT",
            "run_id": terms.run_id,
            "obligation_id": "o",
            "payee_id": "payee",
            "tranche_no": 1,
        },
    )
    process_actions(executor)
    assert result(executor, job)["state"] == "FAILED"
    conn.execute(
        "UPDATE operator_auth SET enabled=0 WHERE user_id IN "
        "(SELECT id FROM user WHERE email='operator0@example.test')"
    )
    revoked = enqueue(executor, {"operation": "OPEN_RUN"})
    process_actions(executor)
    assert result(executor, revoked)["error"] == "requester_revoked"
    assert provider.posts == []


def test_malformed_job_payload_fails_closed_without_money(execution):
    executor, provider, _, _ = execution
    job = enqueue(executor, {"operation": "OPEN_RUN"})
    executor.database.connection().execute(
        "UPDATE provider_job SET request_json='[]' WHERE id=?", (job,)
    )
    process_actions(executor)
    assert result(executor, job)["state"] == "FAILED"
    assert provider.posts == []
