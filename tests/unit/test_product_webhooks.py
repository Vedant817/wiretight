import hashlib
import hmac
import socket
import time

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app, verify_webhook

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
