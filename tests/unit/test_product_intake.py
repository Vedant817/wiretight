"""HTTP intake boundaries with real SQLite, encryption and passkey signatures.

Provider data and company/contact values here are test fixtures only. No socket
can reach Airwallex; these tests do not prove live provider acceptance.
"""

# ruff: noqa: F811
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest

from app.core import callbacks, evidence, installation, intake, operators, packets, signing
from app.core.bank_details import BankDetails, DetailVault
from tests.unit.test_operators_signing import domain, registered, session_for  # noqa: F401
from tests.unit.test_product_webhooks import service  # noqa: F401


@pytest.fixture
def product(domain, tmp_path, monkeypatch, request):
    database, ids = domain
    key_dir = tmp_path / "keys"
    policy_path = tmp_path / "policy.yaml"
    installation.initialize(
        database.connection(),
        legal_name="Fixture installation",
        reserve_usd="8000.00",
        policy_path=policy_path,
        key_dir=key_dir,
        seal_dir=tmp_path / "seals",
    )
    monkeypatch.setenv("APP_DB_PATH", str(database.path))
    monkeypatch.setenv("APP_KEY_DIR", str(key_dir))
    monkeypatch.setenv("APP_POLICY_PATH", str(policy_path))
    client = request.getfixturevalue("service")
    csrf = login(client, 0)
    return database, client, csrf, DetailVault(key_dir / "details.key"), ids


def login(client, index):
    result = client.post(
        "/api/login",
        json={
            "email": f"operator{index}@example.test",
            "password": f"test-password-{index}-long",
        },
    )
    assert result.status_code == 200, result.text
    return {"x-csrf-token": result.json()["csrf_token"]}


def upload(client, csrf, content=b"Fixture source evidence", filename="source.txt"):
    result = client.post(
        "/api/evidence",
        content=content,
        headers={
            **csrf,
            "content-type": "text/plain",
            "x-filename": filename,
        },
    )
    assert result.status_code == 201, result.text
    return result.json()["sha256"]


def supplier(client, csrf):
    result = client.post(
        "/api/suppliers",
        headers=csrf,
        json={
            "legal_name": "Fixture supplier Ltd",
            "display_name": "Fixture supplier",
            "category": "manufacturing",
        },
    )
    assert result.status_code == 201, result.text
    return result.json()["vendor_id"]


def bank_details():
    return {
        "company_name": "Fixture supplier Ltd",
        "country": "US",
        "currency": "USD",
        "account_name": "Fixture supplier Ltd",
        "account_number": "123456789",
        "routing_value": "021000021",
        "bank_account_category": "Checking",
    }


def bank(client, csrf, vendor_id, source=None):
    digest = source or upload(client, csrf, b"Fixture bank request: account 123456789")
    result = client.post(
        f"/api/suppliers/{vendor_id}/bank-changes",
        headers=csrf,
        json={
            "details": bank_details(),
            "evidence_sha256": digest,
        },
    )
    assert result.status_code == 201, result.text
    return result.json()


def test_intake_is_authenticated_csrf_protected_and_never_backdates(product):
    database, client, csrf, _, ids = product
    identifier = supplier(client, csrf)
    digest = upload(client, csrf)
    contact = {"phone": "+12025550100", "provenance": "contract", "evidence_sha256": digest}
    url = f"/api/suppliers/{identifier}/contacts"
    assert client.post(url, json=contact).status_code == 401
    assert (
        client.post(url, headers={**csrf, "origin": "https://evil.test"}, json=contact).status_code
        == 403
    )
    assert (
        client.post(url, headers=csrf, json={**contact, "created_at": "2020-01-01"}).status_code
        == 422
    )
    before = operators.utcnow()
    result = client.post(url, headers=csrf, json=contact)
    assert result.status_code == 201, result.text
    row = (
        database.connection()
        .execute("SELECT * FROM vendor_contact WHERE id=?", (result.json()["contact_id"],))
        .fetchone()
    )
    assert row["created_at"] >= before.isoformat()
    assert row["provenance_sha256"] == digest
    changed = bank(client, csrf, identifier)
    request = (
        database.connection()
        .execute("SELECT * FROM payee_change_request WHERE id=?", (changed["request_id"],))
        .fetchone()
    )
    assert request["intake_user_id"] == ids[0]
    assert json.loads(request["requester_set"]) == [ids[0]]
    assert changed["status"] == "PENDING_CALLBACK"
    client.cookies.clear()
    for route in (
        "/api/suppliers",
        "/api/invoices",
        f"/api/evidence/{digest}",
        "/api/provider/snapshots",
    ):
        assert client.get(route).status_code == 401


def test_source_bytes_encrypted_and_exact_hash_retrieved_as_attachment(product):
    database, client, csrf, vault, _ = product
    content = b"Private fixture bank account: 123456789"
    digest = upload(client, csrf, content)
    row = (
        database.connection()
        .execute("SELECT * FROM evidence_file WHERE sha256=?", (digest,))
        .fetchone()
    )
    assert digest == hashlib.sha256(content).hexdigest()
    assert content not in row["encrypted_content"]
    result = client.get(f"/api/evidence/{digest}")
    assert result.content == content
    assert result.headers["content-disposition"].startswith("attachment;")
    assert result.headers["content-type"] == "application/octet-stream"
    assert evidence.read(database.connection(), vault, digest)[1] == content
    assert upload(client, csrf, content, "second.txt") == digest
    assert database.connection().execute("SELECT COUNT(*) FROM evidence_file").fetchone()[0] == 1
    assert (
        client.post(
            "/api/evidence",
            content=b"x",
            headers={**csrf, "content-type": "text/html", "x-filename": "file.html"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/evidence",
            content=b"x",
            headers={**csrf, "content-type": "text/plain", "x-filename": "../file.txt"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/evidence", content=b"x" * (evidence.MAX_BYTES + 1), headers=csrf
        ).status_code
        == 413
    )


def test_duplicate_invoice_concurrent_operators_create_one_bill_and_lock(product):
    database, client, csrf, _, ids = product
    vendor = supplier(client, csrf)
    digest = upload(client, csrf)
    body = intake.InvoiceInput(
        vendor_id=vendor,
        invoice_number="INV-123",
        amount="12.34",
        currency="USD",
        due_date="2026-12-30",
        evidence_sha256=digest,
    )
    actors = [session_for(database.connection(), index)[0] for index in (0, 1)]

    def create(actor):
        try:
            return intake.add_invoice(database.connection(), actor, body)
        except intake.IntakeError:
            return None

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(create, actors))
    assert sum(result is not None for result in results) == 1
    conn = database.connection()
    row = conn.execute("SELECT * FROM obligation WHERE vendor_id=?", (vendor,)).fetchone()
    assert row["amount"] == "12.34"
    assert json.loads(row["requester_set"])[0] in ids[:2]
    assert conn.execute("SELECT COUNT(*) FROM bill").fetchone()[0] == 1
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM duplicate_lock WHERE obligation_id=?", (row["id"],)
        ).fetchone()[0]
        == 1
    )
    assert client.post("/api/invoices", headers=csrf, json=body.model_dump()).status_code == 409
    for changes in (
        {"amount": 12.34},
        {"amount": "0.00"},
        {"currency": "JPY"},
        {"due_date": "2026-02-30"},
        {"requester_set": [ids[1]]},
    ):
        assert (
            client.post(
                "/api/invoices", headers=csrf, json={**body.model_dump(), **changes}
            ).status_code
            == 422
        )


def test_bank_request_cannot_supply_its_own_callback_phone(product):
    database, client, csrf, _, _ = product
    vendor = supplier(client, csrf)
    digest = upload(client, csrf, b"Fixture contract phone +12025550100")
    actor = session_for(database.connection(), 0)[0]
    contact_id = intake.add_contact(
        database.connection(),
        actor,
        vendor,
        intake.ContactInput(phone="+12025550100", provenance="contract", evidence_sha256=digest),
        historical_created_at=operators.utcnow() - timedelta(days=100),
    )
    source = upload(client, csrf, b"Fixture bank change. Call +1 (202) 555-0100 to confirm.")
    changed = bank(client, csrf, vendor, source)
    keys = signing.Passkeys(rp_id="localhost", origin="http://localhost:8000")
    ops, _ = registered(database.connection(), 3, keys)
    body = callbacks.CallbackInput(
        contact_id=contact_id,
        vendor_person_name="Fixture contact",
        vendor_person_role="Owner",
        called_at=operators.utcnow().isoformat(),
        outcome="CONFIRMED",
        readback_last4_ok=True,
        readback_name_ok=True,
    )
    with pytest.raises(signing.SigningError, match="phone supplied"):
        callbacks.begin_callback(
            database.connection(), ops, keys, request_id=changed["request_id"], body=body
        )


@pytest.mark.parametrize("result", ["CLEAR", "HIT", "ERROR"])
def test_signed_compliance_review_binds_actual_version_and_hold(product, result):
    database, client, csrf, _, _ = product
    vendor = supplier(client, csrf)
    changed = bank(client, csrf, vendor)
    payee = changed["payee_version_id"]
    digest = upload(client, csrf, b"Fixture operator review evidence")
    keys = signing.Passkeys(rp_id="localhost", origin="http://localhost:8000")
    _, device = registered(database.connection(), 3, keys)
    # Register on the same database with real software WebAuthn proofs, then
    # finish the decision through the actual HTTP/session/CSRF route.
    csrf = login(client, 3)
    url = f"/api/banks/{payee}/reviews"
    review = {
        "result": result,
        "source": "Fixture independent manual review",
        "evidence_sha256": digest,
        "checked_at": operators.utcnow().isoformat(),
    }
    options = client.post(url + "/options", headers=csrf, json=review)
    assert options.status_code == 200, options.text
    prompted = options.json()
    finish = {
        "ceremony_id": prompted["ceremony_id"],
        "credential": device.sign(prompted["publicKey"]),
    }
    completed = client.post(url + "/finish", headers=csrf, json=finish)
    assert completed.status_code == 201, completed.text
    assert client.post(url + "/finish", headers=csrf, json=finish).status_code == 409
    assert client.get(url).json()[0]["payee_fingerprint"] == prompted["record"]["payee_fingerprint"]
    conn = database.connection()
    if result == "CLEAR":
        packets.review_clear(conn, payee, keys)
        conn.execute("UPDATE payee_version SET fingerprint=? WHERE id=?", ("a" * 64, payee))
        with pytest.raises(packets.PaymentBlockedError, match="does not cover"):
            packets.review_clear(conn, payee, keys)
    else:
        assert (
            conn.execute("SELECT status FROM payee_version WHERE id=?", (payee,)).fetchone()[0]
            == "COMPLIANCE_HOLD"
        )
        with pytest.raises(packets.PaymentBlockedError, match="review is required"):
            packets.review_clear(conn, payee, keys)


def test_provider_refresh_is_durable_deduplicated_and_not_claimed_done(product):
    database, client, csrf, _, _ = product
    first = client.post("/api/provider/refresh", headers=csrf)
    assert first.status_code == 202, first.text
    second = client.post("/api/provider/refresh", headers=csrf)
    assert first.json() == second.json()
    result = client.get("/api/provider/jobs/" + first.json()["job_id"])
    assert result.status_code == 200, result.text
    assert result.json()["state"] == "PENDING" and result.json()["result_json"] is None
    assert database.connection().execute("SELECT COUNT(*) FROM provider_job").fetchone()[0] == 1
    assert client.get("/api/provider/snapshots").json()["snapshots"] == []


def test_us_account_type_is_required_instead_of_guessed():
    body = bank_details()
    del body["bank_account_category"]
    with pytest.raises(ValueError, match="actual US bank account category"):
        BankDetails.model_validate(body)


def test_compliance_cannot_be_recorded_by_approver_or_for_changed_terms(product):
    database, client, csrf, _, _ = product
    vendor = supplier(client, csrf)
    payee = bank(client, csrf, vendor)["payee_version_id"]
    digest = upload(client, csrf)
    url = f"/api/banks/{payee}/reviews"
    body = {
        "result": "CLEAR",
        "source": "Fixture review",
        "evidence_sha256": digest,
        "checked_at": operators.utcnow().isoformat(),
    }
    assert client.post(url + "/options", headers=csrf, json=body).status_code == 409
    keys = signing.Passkeys(rp_id="localhost", origin="http://localhost:8000")
    _, device = registered(database.connection(), 3, keys)
    csrf = login(client, 3)
    assert (
        client.post(
            url + "/options",
            headers=csrf,
            json={**body, "checked_at": (operators.utcnow() + timedelta(hours=1)).isoformat()},
        ).status_code
        == 409
    )
    options = client.post(url + "/options", headers=csrf, json=body).json()
    database.connection().execute(
        "UPDATE payee_version SET fingerprint=? WHERE id=?", ("a" * 64, payee)
    )
    result = client.post(
        url + "/finish",
        headers=csrf,
        json={
            "ceremony_id": options["ceremony_id"],
            "credential": device.sign(options["publicKey"]),
        },
    )
    assert result.status_code == 409, result.text
    assert (
        database.connection().execute("SELECT COUNT(*) FROM compliance_review").fetchone()[0] == 0
    )


def test_concurrent_bank_changes_rollback_losing_vault_write(product):
    database, client, csrf, vault, _ = product
    vendor = supplier(client, csrf)
    digest = upload(client, csrf, b"Fixture bank request")
    actors = [session_for(database.connection(), index)[0] for index in (0, 1)]

    def propose(index):
        from app.core.lock import ChangeRequestConflictError

        try:
            return intake.propose_bank(
                database.connection(),
                vault,
                actors[index],
                vendor,
                intake.BankInput(
                    details=BankDetails.model_validate(
                        {
                            **bank_details(),
                            "account_number": "123456789" if index == 0 else "987654321",
                        }
                    ),
                    evidence_sha256=digest,
                ),
            )
        except ChangeRequestConflictError:
            return None

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(propose, (0, 1)))
    assert sum(result is not None for result in results) == 1
    conn = database.connection()
    assert conn.execute("SELECT COUNT(*) FROM protected_details").fetchone()[0] == 1
    assert (
        conn.execute("SELECT COUNT(*) FROM payee_version WHERE vendor_id=?", (vendor,)).fetchone()[
            0
        ]
        == 1
    )
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM payee_change_request WHERE vendor_id=?", (vendor,)
        ).fetchone()[0]
        == 1
    )


def test_cli_import_preserves_historical_master_source_and_actual_import_time(
    product, tmp_path, monkeypatch, capsys
):
    import getpass

    from app import cli

    database, client, csrf, _, _ = product
    vendor = supplier(client, csrf)
    source = tmp_path / "contract.txt"
    source.write_text("Fixture historical contract +12025550100", encoding="utf-8")
    monkeypatch.setattr(getpass, "getpass", lambda _: "test-password-0-long")
    result = cli.main(
        [
            "import-contact",
            "--db",
            str(database.path),
            "--key-dir",
            str(tmp_path / "keys"),
            "--operator-email",
            "operator0@example.test",
            "--vendor-id",
            vendor,
            "--phone",
            "+12025550100",
            "--master-created-at",
            "2025-11-01T12:00:00+00:00",
            "--source",
            str(source),
            "--media-type",
            "text/plain",
            "--provenance",
            "contract",
        ]
    )
    assert result == 0
    row = (
        database.connection()
        .execute("SELECT * FROM vendor_contact WHERE vendor_id=?", (vendor,))
        .fetchone()
    )
    assert row["created_at"] == "2025-11-01T12:00:00+00:00"
    assert row["imported_at"] > row["created_at"]
    assert row["provenance_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert (
        database.connection().execute("SELECT COUNT(*) FROM callback_verification").fetchone()[0]
        == 0
    )
    assert "test-password" not in capsys.readouterr().out
