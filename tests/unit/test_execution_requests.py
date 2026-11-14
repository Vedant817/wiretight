"""Direct HTTP bypass tests against the real job route and approval verifier."""

# ruff: noqa: F811
import hashlib
import json
from datetime import datetime, timedelta

import pytest

from app.core import audit, operators
from app.workers.jobs import process_actions
from tests.unit.test_operators_signing import domain  # noqa: F401
from tests.unit.test_product_webhooks import service  # noqa: F401
from tests.unit.test_real_executor import execution  # noqa: F401


@pytest.fixture
def execution_service(execution, monkeypatch, request):
    executor = execution[0]
    monkeypatch.setenv("APP_DB_PATH", str(executor.database.path))
    monkeypatch.setenv("APP_POLICY_PATH", str(executor.policy_path))
    monkeypatch.setenv("APP_KEY_DIR", str(executor.key_dir))
    return request.getfixturevalue("service")


def login(client, index):
    result = client.post(
        "/api/login",
        json={"email": f"operator{index}@example.test", "password": f"test-password-{index}-long"},
    )
    assert result.status_code == 200
    return {"x-csrf-token": result.json()["csrf_token"]}


def unsigned_copy(conn, packet):
    value = json.loads(
        conn.execute("SELECT canonical_json FROM approval_packet WHERE id=?", (packet,)).fetchone()[
            0
        ]
    )
    value["created_at"] = (
        datetime.fromisoformat(value["created_at"]) + timedelta(seconds=1)
    ).isoformat()
    canonical = audit.canonical_json(value)
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    conn.execute(
        "INSERT INTO approval_packet(id,kind,canonical_json,sha256,tier,required_approvers,"
        "created_at,expires_at,state) SELECT 'unsigned',kind,?,?,"
        "tier,required_approvers,"
        "created_at,expires_at,'OPEN' FROM approval_packet WHERE id=?",
        (canonical, digest, packet),
    )


def test_direct_api_cannot_bypass_approval_and_self_approval_is_refused(
    execution, execution_service
):
    executor, provider, packet, _ = execution
    client = execution_service
    conn = executor.database.connection()
    unsigned_copy(conn, packet)
    assert client.post("/api/approvals/unsigned/execute").status_code == 401
    headers = login(client, 0)
    assert client.post("/api/approvals/unsigned/options", headers=headers).status_code == 409
    result = client.post(
        "/api/approvals/unsigned/execute",
        headers=headers,
        json={"approved": True, "signatures": ["forged"]},
    )
    assert result.status_code == 409
    assert client.post(f"/api/approvals/{packet}/execute").status_code == 401
    assert provider.posts == []
    assert conn.execute("SELECT COUNT(*) FROM provider_job").fetchone()[0] == 0


@pytest.mark.parametrize("forged", [False, True])
def test_replayed_or_forged_assertion_does_not_approve_or_queue(
    execution, execution_service, forged
):
    executor, provider, packet, _ = execution
    client = execution_service
    conn = executor.database.connection()
    unsigned_copy(conn, packet)
    headers = login(client, 1)
    prompt = client.post("/api/approvals/unsigned/options", headers=headers)
    assert prompt.status_code == 200
    user = conn.execute("SELECT id FROM user WHERE email='operator1@example.test'").fetchone()[0]
    previous = json.loads(
        conn.execute(
            "SELECT assertion FROM approval_signature WHERE packet_id=? AND approver_id=?",
            (packet, user),
        ).fetchone()[0]
    )
    credential = previous["credential"]
    if forged:
        credential["response"]["signature"] = "AAAA"
    result = client.post(
        "/api/passkeys/finish",
        headers=headers,
        json={"ceremony_id": prompt.json()["ceremony_id"], "credential": credential},
    )
    assert result.status_code == 409
    assert client.post("/api/approvals/unsigned/execute", headers=headers).status_code == 409
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM approval_signature WHERE packet_id='unsigned'"
        ).fetchone()[0]
        == 0
    )
    assert provider.posts == []


def test_duplicate_execution_requests_and_worker_retry_create_one_payout(
    execution, execution_service
):
    executor, provider, packet, _ = execution
    client = execution_service
    headers = login(client, 0)
    first = client.post(f"/api/approvals/{packet}/execute", headers=headers)
    assert first.status_code == 202, first.text
    assert client.post(f"/api/approvals/{packet}/execute", headers=headers).json() == first.json()
    process_actions(executor)
    process_actions(executor)
    job = client.get("/api/provider/jobs/" + first.json()["job_id"])
    assert job.json()["state"] == "DONE"
    assert json.loads(job.json()["result_json"])["execution_state"] == "SUBMITTED"
    assert client.post(f"/api/approvals/{packet}/execute", headers=headers).status_code == 409
    assert len([row for row in provider.posts if row[0] == "/transfers/create"]) == 1


def test_bank_change_during_renewed_cooling_refuses_queued_execution(execution, execution_service):
    from datetime import timedelta

    executor, provider, packet, _ = execution
    client = execution_service
    headers = login(client, 0)
    requested = client.post(f"/api/approvals/{packet}/execute", headers=headers)
    assert requested.status_code == 202
    conn = executor.database.connection()
    conn.execute(
        "UPDATE payee_version SET cooling_off_until=?,fingerprint=? WHERE id='payee'",
        ((operators.utcnow() + timedelta(hours=72)).isoformat(), "a" * 64),
    )
    process_actions(executor)
    assert (
        client.get("/api/provider/jobs/" + requested.json()["job_id"]).json()["state"] == "FAILED"
    )
    assert provider.posts == []
