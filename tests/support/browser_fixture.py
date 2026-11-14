"""Disposable browser-only records and a genuine Uvicorn service, without provider keys."""

from __future__ import annotations

# ruff: noqa: E501
import hashlib
import os
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

import httpx

from app.core import audit, db, operators
from app.local import stop_child


@contextmanager
def server(port=8766):
    with tempfile.TemporaryDirectory(prefix="wiretight-browser-test-") as directory:
        root = Path(directory)
        with db.Database(root / "app.sqlite") as database:
            conn = database.connection()
            users = [
                operators.provision(
                    conn,
                    name=f"Browser operator {i}",
                    email=f"browser{i}@example.test",
                    role="ops" if i == 3 else "approver",
                    password=f"browser-test-password-{i}-long",
                )
                for i in range(4)
            ]
            now = operators.utcnow()
            conn.execute(
                "INSERT INTO vendor(id,legal_name_norm,display_name,category,created_at) "
                "VALUES('browser-vendor','browser test supplier','Browser test supplier','goods',?)",
                (now.isoformat(),),
            )
            conn.execute(
                "INSERT INTO obligation(id,vendor_id,invoice_no_norm,amount,currency,"
                "due_date,state,requester_set,created_at,updated_at) "
                "VALUES('browser-invoice','browser-vendor','BROWSER-1','100.00','USD',"
                "?,'READY',?,?,?)",
                (
                    (now + timedelta(days=10)).date().isoformat(),
                    audit.canonical_json([users[0]]),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            terms = {
                "kind": "PAYMENT",
                "tier": "T2",
                "required_approvers": 2,
                "items": [
                    {
                        "obligation_id": "browser-invoice",
                        "vendor_name": "Browser test supplier",
                        "transfer_amount": "100.00",
                        "transfer_currency": "USD",
                        "masked_destination": "Test destination ending 1234",
                    }
                ],
            }
            canonical = audit.canonical_json(terms)
            conn.execute(
                "INSERT INTO approval_packet(id,kind,canonical_json,sha256,tier,"
                "required_approvers,created_at,expires_at,state) "
                "VALUES('browser-approval','PAYMENT',?,?,'T2',2,?,?,'OPEN')",
                (
                    canonical,
                    hashlib.sha256(canonical.encode()).hexdigest(),
                    now.isoformat(),
                    (now + timedelta(hours=4)).isoformat(),
                ),
            )
        environment = {
            k: v
            for k, v in os.environ.items()
            if k
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
            AWX_ENV="sandbox",
            AWX_MODE="live",
            AWX_BASE_URL="https://api.sandbox.airwallex.com",
            WEBAUTHN_RP_ID="localhost",
            WEBAUTHN_ORIGIN=f"http://localhost:{port}",
        )
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
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
                stdout=log,
                stderr=log,
                creationflags=flags,
            )
            try:
                with httpx.Client(trust_env=False, timeout=1) as client:
                    for _ in range(150):
                        if process.poll() is not None:
                            raise RuntimeError("Browser test service exited")
                        try:
                            if client.get(f"http://127.0.0.1:{port}/").status_code == 200:
                                break
                        except httpx.RequestError:
                            time.sleep(0.1)
                    else:
                        raise RuntimeError("Browser test service did not start")
                yield root
            finally:
                stop_child(process)


if __name__ == "__main__":
    with server():
        print("Disposable UI test service running on http://localhost:8766", flush=True)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
