"""Real worker persistence against a test-only HTTP transport boundary."""

# ruff: noqa: F811
import json
import sys
from datetime import timedelta
from email.utils import format_datetime

import httpx

from app.core import db, operators
from app.integrations.airwallex import AirwallexClient
from app.workers import service
from tests.unit.test_operators_signing import domain  # noqa: F401


def queue(conn, user_id, identifier="refresh"):
    now = operators.utcnow().isoformat()
    conn.execute(
        "INSERT INTO provider_job(id,kind,requested_by,request_json,state,created_at,updated_at) "
        "VALUES(?,'REFRESH',?,'{}','PENDING',?,?)",
        (identifier, user_id, now, now),
    )


def test_successful_refresh_commits_actual_observation_but_never_marks_payment_ready(domain):
    database, ids = domain
    conn = database.connection()
    queue(conn, ids[0])

    def handler(request):
        assert not database.connection().in_transaction
        headers = {"Date": format_datetime(operators.utcnow(), usegmt=True)}
        if request.url.path.endswith("/authentication/login"):
            return httpx.Response(
                200,
                json={
                    "token": "fixture-token",
                    "expires_at": (operators.utcnow() + timedelta(hours=1)).isoformat(),
                },
                headers=headers,
            )
        assert request.url.path.endswith("/balances/current")
        return httpx.Response(
            200, content=b'[{"currency":"USD","available_amount":12345.67}]', headers=headers
        )

    client = AirwallexClient("fixture-id", "fixture-key", transport=httpx.MockTransport(handler))
    try:
        assert service.refresh(database, client)
    finally:
        client.close()
    row = conn.execute("SELECT * FROM provider_snapshot").fetchone()
    assert json.loads(row["canonical_json"])["balances"][0]["available_amount"] == "12345.67"
    assert conn.execute("SELECT state FROM provider_job").fetchone()[0] == "DONE"
    assert conn.execute("SELECT ready FROM worker_health").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM execution_intent").fetchone()[0] == 0


def test_failed_refresh_preserves_old_observation_and_marks_job_failed(domain):
    database, ids = domain
    conn = database.connection()
    queue(conn, ids[0])
    conn.execute(
        "INSERT INTO provider_snapshot(kind,subject,canonical_json,observed_at) "
        "VALUES('BALANCES','wallet','{\"balances\":[]}','2026-01-01T00:00:00+00:00')"
    )

    def handler(request):
        if request.url.path.endswith("/authentication/login"):
            return httpx.Response(
                200,
                json={
                    "token": "fixture-token",
                    "expires_at": (operators.utcnow() + timedelta(hours=1)).isoformat(),
                },
            )
        return httpx.Response(503, json={"message": "private provider body must not be logged"})

    client = AirwallexClient(
        "fixture-id", "fixture-key", transport=httpx.MockTransport(handler), sleep=lambda _: None
    )
    try:
        assert not service.refresh(database, client)
    finally:
        client.close()
    row = conn.execute("SELECT * FROM provider_snapshot").fetchone()
    assert row["observed_at"] == "2026-01-01T00:00:00+00:00"
    job = conn.execute("SELECT * FROM provider_job").fetchone()
    assert job["state"] == "FAILED" and job["error"] == "unavailable"
    assert job["result_json"] is None


def test_missing_credentials_fails_closed_without_provider_socket(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    for key in ("AWX_CLIENT_ID", "AWX_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    path = tmp_path / "worker.sqlite"
    monkeypatch.setenv("APP_DB_PATH", str(path))
    monkeypatch.setenv("AWX_MODE", "live")
    monkeypatch.setenv("AWX_ENV", "sandbox")
    monkeypatch.setenv("AWX_BASE_URL", "https://api.sandbox.airwallex.com")
    monkeypatch.setattr(sys, "argv", ["worker", "--once"])
    assert service.main() == 2
    assert "check_sandbox_credentials_and_config" in capsys.readouterr().out
    with db.Database(path) as database:
        row = database.connection().execute("SELECT * FROM worker_health").fetchone()
        assert row["ready"] == 0 and "missing_credentials" in row["detail"]
        assert (
            database.connection().execute("SELECT COUNT(*) FROM provider_snapshot").fetchone()[0]
            == 0
        )
