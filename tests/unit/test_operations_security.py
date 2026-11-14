"""Real HTTP security boundaries, including a stale browser ceremony after cancellation."""

# ruff: noqa: F811
import io
import json
import logging

import pytest

from app.core import signing
from app.logging_config import RedactedJSON
from tests.support.authenticator import Authenticator
from tests.unit.test_execution_requests import login
from tests.unit.test_operators_signing import domain  # noqa: F401
from tests.unit.test_product_webhooks import service  # noqa: F401


@pytest.fixture
def operator_service(domain, monkeypatch, request):
    monkeypatch.setenv("APP_DB_PATH", str(domain[0].path))
    return request.getfixturevalue("service")


@pytest.mark.parametrize(
    "path,body",
    [
        ("/api/approvals/p/options", None),
        ("/api/approvals/p/execute", None),
        ("/api/approvals/p/quote", None),
        ("/api/approvals/p/cancel", {"reason": "not authorized"}),
        ("/api/runs", None),
        ("/api/plans", {"run_id": "r", "obligation_id": "o", "payee_id": "b", "tranche_no": 1}),
        ("/api/runs/r/reconcile", None),
        ("/api/runs/r/close", None),
        ("/api/policy/options", None),
    ],
)
def test_non_approver_cannot_reach_any_money_authority(operator_service, domain, path, body):
    client = operator_service
    headers = login(client, 3)
    result = client.post(path, headers=headers, json=body)
    assert result.status_code in {403, 409}, result.text
    conn = domain[0].connection()
    assert conn.execute("SELECT COUNT(*) FROM provider_job").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM approval_consumption").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM approval_signature").fetchone()[0] == 0


@pytest.mark.parametrize("token", [None, "forged-csrf-token"])
@pytest.mark.parametrize(
    "path,body",
    [
        ("/api/approvals/p/options", None),
        ("/api/approvals/p/execute", None),
        ("/api/approvals/p/quote", None),
        ("/api/approvals/p/cancel", {"reason": "cancel"}),
        ("/api/passkeys/finish", {"ceremony_id": "untrusted", "credential": {}}),
    ],
)
def test_csrf_approval_and_execution_refused(operator_service, domain, token, path, body):
    client = operator_service
    login(client, 1)
    headers = {} if token is None else {"x-csrf-token": token}
    result = client.post(path, headers=headers, json=body)
    assert result.status_code == 401
    conn = domain[0].connection()
    assert conn.execute("SELECT COUNT(*) FROM provider_job").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM approval_signature").fetchone()[0] == 0


def test_approve_in_stale_tab_after_other_tab_cancel_fails(operator_service, domain):
    client = operator_service
    headers = login(client, 1)
    device = Authenticator()
    registration = client.post("/api/passkeys/register/options", headers=headers).json()
    result = client.post(
        "/api/passkeys/finish",
        headers=headers,
        json={
            "ceremony_id": registration["ceremony_id"],
            "credential": device.register(registration["publicKey"]),
        },
    )
    assert result.status_code == 200
    tab_a = client.post("/api/approvals/p/options", headers=headers).json()
    assertion = device.sign(tab_a["publicKey"])
    assert client.post(
        "/api/approvals/p/cancel",
        headers=headers,
        json={"reason": "Recipient verification withdrawn in another tab"},
    ).json() == {"state": "VOID"}
    stale = client.post(
        "/api/passkeys/finish",
        headers=headers,
        json={
            "ceremony_id": tab_a["ceremony_id"],
            "credential": assertion,
        },
    )
    assert stale.status_code == 409
    assert client.post("/api/approvals/p/execute", headers=headers).status_code == 409
    assert (
        domain[0].connection().execute("SELECT COUNT(*) FROM approval_signature").fetchone()[0] == 0
    )


def test_operational_views_require_login_and_expose_only_real_rows(operator_service):
    client = operator_service
    assert client.get("/api/operations").status_code == 401
    login(client, 3)
    result = client.get("/api/operations")
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["role"] == "ops"
    assert [r["id"] for r in body["approvals"]] == ["p"]
    assert body["payments"] == [] and body["jobs"] == [] and body["tie_outs"] == []
    assert client.get("/assets/operations.js").status_code == 200
    assert client.get("/assets/operations.css").status_code == 200


def test_secret_key_never_appears_in_structured_logs_even_in_nested_data_or_exception():
    secret = "test-only-key-never-written-to-log"
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(RedactedJSON([secret]))
    logger = logging.Logger("redaction-test")
    logger.addHandler(handler)
    logger.error(
        {
            "event": "request.failed",
            "nested": {"api_key": secret, "password": "hidden"},
            "message": "upstream echoed " + secret,
        }
    )
    try:
        raise RuntimeError("Authorization: Bearer " + secret)
    except RuntimeError:
        logger.exception("request exception")
    result = stream.getvalue()
    assert secret not in result and "hidden" not in result
    rows = [json.loads(line) for line in result.splitlines()]
    assert rows[0]["event"]["nested"]["api_key"] == "[REDACTED]"
    assert rows[1]["error_type"] == "RuntimeError"


def test_cancel_cannot_recall_a_claimed_payment(domain, operator_service):
    conn = domain[0].connection()
    conn.execute(
        "INSERT INTO approval_consumption(packet_id,consumed_at,intent_audit_seq) "
        "VALUES('p','2026-11-14',1)"
    )
    client = operator_service
    headers = login(client, 1)
    result = client.post("/api/approvals/p/cancel", headers=headers, json={"reason": "too late"})
    assert result.status_code == 409
    assert conn.execute("SELECT state FROM approval_packet WHERE id='p'").fetchone()[0] == "OPEN"


def test_cancelled_packet_is_unavailable_even_without_a_pending_ceremony(domain):
    conn = domain[0].connection()
    conn.execute("UPDATE approval_packet SET state='VOID' WHERE id='p'")
    with pytest.raises(signing.SigningError, match="unavailable"):
        signing.packet(conn, "p")
