"""Run the product in a separate process and exercise real loopback HTTP intake.

Test fixture business/operator data stays inside a temporary installation. This
does not contact Airwallex or claim real device/browser passkey acceptance.
Run: uv run python -m tests.support.http_smoke
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

from app.core import db, installation, operators


def run() -> None:
    with tempfile.TemporaryDirectory(prefix="wiretight-http-") as temporary:
        root = Path(temporary)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        with db.Database(root / "app.sqlite") as database:
            for index in range(4):
                operators.provision(
                    database.connection(),
                    name=f"Fixture operator {index}",
                    email=f"fixture{index}@example.test",
                    role="ops" if index == 3 else "approver",
                    password=f"fixture-password-{index}-long",
                )
            installation.initialize(
                database.connection(),
                legal_name="HTTP fixture installation",
                reserve_usd="8000.00",
                policy_path=root / "policy.yaml",
                key_dir=root / "keys",
                seal_dir=root / "seals",
            )
        environment = {
            key: value
            for key, value in os.environ.items()
            if key
            not in {
                "AWX_CLIENT_ID",
                "AWX_API_KEY",
                "ANTHROPIC_API_KEY",
                "DEMO_MODE",
                "APP_DEMO_TIMING",
            }
        }
        environment.update(
            APP_DB_PATH=str(root / "app.sqlite"),
            APP_KEY_DIR=str(root / "keys"),
            APP_POLICY_PATH=str(root / "policy.yaml"),
            AWX_ENV="sandbox",
            AWX_MODE="live",
            AWX_BASE_URL="https://api.sandbox.airwallex.com",
            WEBAUTHN_RP_ID="localhost",
            WEBAUTHN_ORIGIN=f"http://localhost:{port}",
        )
        with (root / "server.log").open("wb") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.api.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--no-access-log",
                ],
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            try:
                with httpx.Client(
                    base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=10
                ) as client:
                    for _ in range(150):
                        if process.poll() is not None:
                            raise RuntimeError("Product HTTP process exited during startup")
                        try:
                            ready = client.get("/ready")
                            break
                        except httpx.ConnectError:
                            time.sleep(0.1)
                    else:
                        raise RuntimeError("Product HTTP startup timed out")
                    assert ready.status_code == 503 and ready.json()["ready"] is False
                    assert client.get("/api/suppliers").status_code == 401
                    result = client.post(
                        "/api/login",
                        json={
                            "email": "fixture0@example.test",
                            "password": "fixture-password-0-long",
                        },
                    )
                    assert result.status_code == 200
                    headers = {"x-csrf-token": result.json()["csrf_token"]}
                    assert client.get("/api/suppliers").json() == []
                    result = client.post(
                        "/api/evidence",
                        content=b"HTTP fixture invoice evidence",
                        headers={
                            **headers,
                            "content-type": "text/plain",
                            "x-filename": "invoice.txt",
                        },
                    )
                    assert result.status_code == 201
                    digest = result.json()["sha256"]
                    result = client.post(
                        "/api/suppliers",
                        headers=headers,
                        json={
                            "legal_name": "HTTP fixture supplier",
                            "display_name": "HTTP fixture supplier",
                            "category": "manufacturing",
                        },
                    )
                    assert result.status_code == 201
                    vendor = result.json()["vendor_id"]
                    body = {
                        "vendor_id": vendor,
                        "invoice_number": "HTTP-123",
                        "amount": "12.34",
                        "currency": "USD",
                        "due_date": "2026-12-30",
                        "evidence_sha256": digest,
                    }
                    result = client.post("/api/invoices", headers=headers, json=body)
                    assert result.status_code == 201
                    assert (
                        client.post("/api/invoices", headers=headers, json=body).status_code == 409
                    )
                    assert client.post("/api/invoices", json=body).status_code == 401
                    assert client.get("/api/invoices").json()[0]["amount"] == "12.34"
                    result = client.get(f"/api/evidence/{digest}")
                    assert result.content == b"HTTP fixture invoice evidence"
                    assert result.headers["content-disposition"].startswith("attachment;")
                    assert result.headers["x-content-type-options"] == "nosniff"
                    assert client.post("/api/logout", headers=headers).status_code == 200
                    assert client.get("/api/invoices").status_code == 401
                print(
                    "PASS: separate-process HTTP login, evidence, supplier, invoice, "
                    "duplicate/CSRF, logout"
                )
                print(
                    "PASS: health remains unready; "
                    "no provider, device or payment acceptance claimed"
                )
            finally:
                process.terminate()
                process.wait(timeout=15)


if __name__ == "__main__":
    run()
