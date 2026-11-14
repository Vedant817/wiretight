"""Startup and dependency state cannot quietly fall back to recording behavior."""

# ruff: noqa: F811
from datetime import timedelta

import pytest

from app.config import SandboxGuardError, WebSettings, validate_product
from app.core import audit, db, operators
from app.local import environments
from tests.unit.test_product_webhooks import service  # noqa: F401


@pytest.mark.parametrize(
    "values",
    [
        {"AWX_MODE": "replay"},
        {"SIGNING_MODE": "hmac_fallback"},
        {"SHADOW_MODE": True},
        {"WEBAUTHN_ORIGIN": "http://untrusted.invalid"},
        {"APP_PORT": 0},
    ],
)
def test_invalid_product_configuration_is_refused(values, monkeypatch):
    monkeypatch.setenv("AWX_MODE", "live")
    settings = WebSettings(_env_file=None, **values)
    with pytest.raises(SandboxGuardError):
        validate_product(settings)


def test_launcher_separates_secret_environments():
    web, worker = environments(
        {
            "AWX_API_KEY": "test-worker-key",
            "AWX_CLIENT_ID": "test-id",
            "ANTHROPIC_API_KEY": "test-web-key",
            "AWX_WEBHOOK_SECRET": "test-hook",
        }
    )
    assert "AWX_API_KEY" not in web and "AWX_CLIENT_ID" not in web
    assert "ANTHROPIC_API_KEY" not in worker and "AWX_WEBHOOK_SECRET" not in worker


def test_readiness_requires_both_fresh_worker_and_provider_observations(service, monkeypatch):
    import os

    with db.Database(os.environ["APP_DB_PATH"]) as database:
        conn = database.connection()
        now = operators.utcnow()
        conn.execute(
            "INSERT INTO worker_health VALUES(1,1,'provider_connected; ready',?)",
            (now.isoformat(),),
        )
        assert service.get("/ready").status_code == 503
        conn.execute(
            "INSERT INTO provider_snapshot VALUES('BALANCES','wallet',?,?)",
            (audit.canonical_json([]), now.isoformat()),
        )
        result = service.get("/ready")
        assert result.status_code == 200 and result.json()["ready"] is True
        stale = (now - timedelta(minutes=3)).isoformat()
        conn.execute("UPDATE provider_snapshot SET observed_at=?", (stale,))
        assert service.get("/ready").status_code == 503
        conn.execute("UPDATE provider_snapshot SET observed_at=?", (now.isoformat(),))
        conn.execute("UPDATE worker_health SET checked_at=?", (stale,))
        assert service.get("/health").status_code == 503


def test_real_http_error_logs_omit_private_exception_body(service, caplog):
    secret = "test-only-key-in-a-private-exception"

    @service.app.get("/test-private-error")
    def fail():
        raise RuntimeError(secret)

    response = service.get("/test-private-error")
    assert response.status_code == 503
    assert secret not in response.text and secret not in caplog.text
    assert "request.failed" in caplog.text
