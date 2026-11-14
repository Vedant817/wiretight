import hashlib
import hmac
import os
import socket
import time

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app, verify_webhook
from app.core import db

# TestClient's event loop needs an internal socketpair. Preserve that operation
# while still refusing all outbound connects, including accidental provider I/O.
_SOCKET = socket.socket


@pytest.fixture
def service(monkeypatch):
    class LocalSocket(_SOCKET):
        def connect(self, address):
            if isinstance(address, tuple) and address[0] == "127.0.0.1":
                return super().connect(address)
            raise AssertionError("Outbound sockets forbidden in product tests")

        def connect_ex(self, address):
            if isinstance(address, tuple) and address[0] == "127.0.0.1":
                return super().connect_ex(address)
            raise AssertionError("Outbound sockets forbidden in product tests")

    monkeypatch.setattr(socket, "socket", LocalSocket)
    monkeypatch.setenv("AWX_MODE", "live")
    monkeypatch.setenv("AWX_WEBHOOK_SECRET", "test-signing-secret")
    with TestClient(create_app()) as client:
        yield client


def signed(body):
    timestamp = str(int(time.time() * 1000))
    signature = hmac.new(
        b"test-signing-secret", timestamp.encode() + body, hashlib.sha256
    ).hexdigest()
    return {"x-timestamp": timestamp, "x-signature": signature}


def test_missing_setup_is_unready(service):
    result = service.get("/ready")
    assert result.status_code == 503
    assert result.json()["ready"] is False
    assert "credentials" in str(result.json())
    assert service.get("/").status_code == 200
    assert service.post("/transfers").status_code == 404


def test_duplicate_and_out_of_order_events_only_enqueue(service):
    for name, event_id in [("paid", "new"), ("sent", "old")]:
        body = (
            '{"id":"' + event_id + '","name":"payout.transfer.' + name + '","data":{}}'
        ).encode()
        assert service.post("/webhooks/airwallex", content=body, headers=signed(body)).json() == {
            "accepted": True,
            "duplicate": False,
        }
        assert service.post("/webhooks/airwallex", content=body, headers=signed(body)).json() == {
            "accepted": True,
            "duplicate": True,
        }


def test_bad_signature_and_malformed_input(service):
    assert service.post("/webhooks/airwallex", content=b"{}").status_code == 400
    body = b"invalid json"
    assert (
        service.post("/webhooks/airwallex", content=body, headers=signed(body)).status_code == 400
    )
    body = b'{"id":"e","name":"payout.transfer.sent","data":{}}'
    assert (
        service.post("/webhooks/airwallex", content=body, headers=signed(body)).status_code == 200
    )
    changed = body.replace(b"sent", b"paid")
    assert (
        service.post("/webhooks/airwallex", content=changed, headers=signed(changed)).status_code
        == 409
    )


def test_oversized_body_and_missing_secret(service, monkeypatch):
    assert service.post("/webhooks/airwallex", content=b"x" * 262145).status_code == 413
    monkeypatch.delenv("AWX_WEBHOOK_SECRET")
    # Configuration is fixed at startup; rotation/removal requires a new service.
    with TestClient(create_app()) as missing_secret:
        assert missing_secret.post("/webhooks/airwallex", content=b"{}").status_code == 503


def test_expired_signed_event():
    timestamp = str(int((time.time() - 301) * 1000))
    body = b"{}"
    signature = hmac.new(b"secret", timestamp.encode() + body, hashlib.sha256).hexdigest()
    with pytest.raises(ValueError, match="tolerance"):
        verify_webhook(body, timestamp, signature, "secret")


def test_unknown_event_name_is_only_a_poll_hint_and_malformed_events_are_refused(service):
    # The provider may add event names we have never seen. A correctly signed
    # one is still only a hint to GET authoritative data: it must be stored and
    # must not create or advance any transfer state.
    body = b'{"id":"unknown-1","name":"ledger.reconciliation.mystery","data":{"unexpected":[1,2]}}'
    assert service.post("/webhooks/airwallex", content=body, headers=signed(body)).json() == {
        "accepted": True,
        "duplicate": False,
    }
    conn = db.connect(os.environ["APP_DB_PATH"])
    try:
        row = conn.execute("SELECT * FROM webhook_event WHERE event_id='unknown-1'").fetchone()
        assert row["enqueued_poll"] == 1
        assert conn.execute("SELECT COUNT(*) FROM transfer_attempt").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM provider_job").fetchone()[0] == 0
        audit_rows = conn.execute(
            "SELECT payload_json FROM audit_log WHERE kind='webhook.received'"
        ).fetchall()
        assert [row[0] for row in audit_rows if "ledger.reconciliation.mystery" in row[0]]
    finally:
        conn.close()

    # Replaying the same signed bytes is a duplicate; changing the body under
    # the same id is a conflict, never a second poll.
    assert service.post("/webhooks/airwallex", content=body, headers=signed(body)).json() == {
        "accepted": True,
        "duplicate": True,
    }
    changed = body.replace(b"mystery", b"mystery2")
    assert (
        service.post("/webhooks/airwallex", content=changed, headers=signed(changed)).status_code
        == 409
    )

    for malformed in (
        b'{"id":"m1","name":"payout.transfer.sent"}',
        b'{"id":"m2","name":"","data":{}}',
        b'{"id":"m3","name":"payout.transfer.sent","data":"not-an-object"}',
        b'{"id":"","name":"payout.transfer.sent","data":{}}',
    ):
        resp = service.post("/webhooks/airwallex", content=malformed, headers=signed(malformed))
        assert resp.status_code == 400, malformed
