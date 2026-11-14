"""Runtime decisions use real passkey verification, never the historical HMAC seed."""

# ruff: noqa: F811
import copy
import json
from datetime import timedelta

import pytest
import yaml

from app.core import (
    callbacks,
    killswitch,
    operators,
    record_signing,
    runtime_halt,
    runtime_policy,
    signing,
)
from app.core.policy import PolicyError
from tests.acceptance.test_b_policy_floor import BASE_POLICY
from tests.unit.test_operators_signing import domain, registered  # noqa: F401
from tests.unit.test_product_webhooks import service  # noqa: F401


def test_runtime_policy_requires_two_distinct_real_signers(domain, tmp_path):
    database, _ = domain
    conn = database.connection()
    conn.execute(
        "INSERT INTO entity(id,legal_name,base_currency,created_at) "
        "VALUES('entity','Test business','USD',?)",
        (operators.utcnow().isoformat(),),
    )
    policy = copy.deepcopy(BASE_POLICY)
    policy.pop("demo_timing")
    policy["entity_id"] = "entity"
    policy["roster"] = [
        dict(row) for row in conn.execute("SELECT id,name,role,email FROM user ORDER BY id")
    ]
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.safe_dump(policy), encoding="utf-8")
    keys = signing.Passkeys(rp_id="localhost", origin="http://localhost:8000")
    loaded, record = runtime_policy.validated_policy(conn, path)
    with pytest.raises(signing.SigningError, match="Insufficient"):
        runtime_policy.load_runtime_policy(conn, path, keys)
    for index in (1, 2):
        user, device = registered(conn, index, keys)
        options = record_signing.begin_record(
            conn, user, keys, purpose="POLICY", subject_id=loaded.sha256, record=record
        )
        record_signing.finish_record(
            conn,
            user,
            keys,
            purpose="POLICY",
            subject_id=loaded.sha256,
            record=record,
            ceremony_id=options["ceremony_id"],
            credential=device.sign(options["publicKey"]),
        )
    assert runtime_policy.load_runtime_policy(conn, path, keys).sha256 == loaded.sha256
    policy["demo_timing"] = True
    path.write_text(yaml.safe_dump(policy), encoding="utf-8")
    with pytest.raises(PolicyError):
        runtime_policy.validated_policy(conn, path)


def prepare_callback(domain):
    database, ids = domain
    conn = database.connection()
    now = operators.utcnow()
    conn.execute(
        "INSERT INTO vendor_contact(id,vendor_id,kind,value,value_norm,provenance,created_at) "
        "VALUES('phone','v','phone','+1 202 555 0100','12025550100','contract',?)",
        ((now - timedelta(days=100)).isoformat(),),
    )
    conn.execute(
        "INSERT INTO payee_version(id,vendor_id,fingerprint,details_ref,masked,method,rail,"
        "country,currency,status,created_at,updated_at) "
        "VALUES('payee','v','fingerprint','details','masked','LOCAL','ACH','US','USD','PROPOSED',?,?)",
        (now.isoformat(), now.isoformat()),
    )
    conn.execute(
        "INSERT INTO payee_change_request(id,vendor_id,source_kind,received_at,intake_user_id,"
        "requester_set,proposed_details_ref,proposed_masked,proposed_fingerprint,status) "
        "VALUES('change','v','manual',?,?,?,'details','masked','fingerprint','PENDING_CALLBACK')",
        ((now - timedelta(minutes=5)).isoformat(), ids[0], json.dumps([ids[0]])),
    )
    return callbacks.CallbackInput(
        contact_id="phone",
        vendor_person_name="Test contact",
        vendor_person_role="Owner",
        called_at=(now - timedelta(minutes=1)).isoformat(),
        outcome="CONFIRMED",
        readback_last4_ok=True,
        readback_name_ok=True,
    )


def test_signed_callback_persists_real_cooling_and_reverifies(domain):
    database, _ = domain
    conn = database.connection()
    body = prepare_callback(domain)
    keys = signing.Passkeys(rp_id="localhost", origin="http://localhost:8000")
    user, device = registered(conn, 3, keys)
    options = callbacks.begin_callback(conn, user, keys, request_id="change", body=body)
    callbacks.apply_callback(
        conn,
        user,
        keys,
        request_id="change",
        body=body,
        ceremony_id=options["ceremony_id"],
        credential=device.sign(options["publicKey"]),
    )
    record = callbacks.verify_callback(conn, keys, payee_version_id="payee")
    assert record["outcome"] == "CONFIRMED"
    until = conn.execute("SELECT cooling_off_until FROM payee_version WHERE id='payee'").fetchone()[
        0
    ]
    assert until > (operators.utcnow() + timedelta(hours=71)).isoformat()
    conn.execute(
        "UPDATE vendor_contact SET changed_at=? WHERE id='phone'", (operators.utcnow().isoformat(),)
    )
    with pytest.raises(signing.SigningError, match="Contact changed"):
        callbacks.verify_callback(conn, keys, payee_version_id="payee")


def test_callback_terms_changed_after_prompt_is_refused(domain):
    database, _ = domain
    conn = database.connection()
    body = prepare_callback(domain)
    keys = signing.Passkeys(rp_id="localhost", origin="http://localhost:8000")
    user, device = registered(conn, 3, keys)
    options = callbacks.begin_callback(conn, user, keys, request_id="change", body=body)
    changed = body.model_copy(update={"outcome": "DENIED"})
    with pytest.raises(signing.SigningError, match="changed"):
        callbacks.apply_callback(
            conn,
            user,
            keys,
            request_id="change",
            body=changed,
            ceremony_id=options["ceremony_id"],
            credential=device.sign(options["publicKey"]),
        )
    assert conn.execute("SELECT COUNT(*) FROM callback_verification").fetchone()[0] == 0


def test_no_answer_can_be_followed_by_a_confirmed_callback(domain):
    database, _ = domain
    conn = database.connection()
    body = prepare_callback(domain)
    keys = signing.Passkeys(rp_id="localhost", origin="http://localhost:8000")
    user, device = registered(conn, 3, keys)
    for current in (body.model_copy(update={"outcome": "NO_ANSWER"}), body):
        options = callbacks.begin_callback(conn, user, keys, request_id="change", body=current)
        callbacks.apply_callback(
            conn,
            user,
            keys,
            request_id="change",
            body=current,
            ceremony_id=options["ceremony_id"],
            credential=device.sign(options["publicKey"]),
        )
    assert callbacks.verify_callback(conn, keys, payee_version_id="payee")["outcome"] == "CONFIRMED"


def test_callback_cannot_use_recent_or_requester_contact(domain):
    database, _ = domain
    conn = database.connection()
    body = prepare_callback(domain)
    keys = signing.Passkeys(rp_id="localhost", origin="http://localhost:8000")
    user, _ = registered(conn, 0, keys)
    with pytest.raises(PermissionError):
        callbacks.begin_callback(conn, user, keys, request_id="change", body=body)
    user, _ = registered(conn, 3, keys)
    conn.execute(
        "UPDATE vendor_contact SET created_at=? WHERE id='phone'",
        ((operators.utcnow() - timedelta(days=1)).isoformat(),),
    )
    with pytest.raises(ValueError, match="requires 30"):
        callbacks.begin_callback(conn, user, keys, request_id="change", body=body)


def test_halt_requires_two_fresh_passkey_decisions_and_never_deletes_local_marker(domain, tmp_path):
    database, _ = domain
    conn = database.connection()
    marker = tmp_path / "HALT"
    trip = killswitch.trip(conn, "Operator requested halt", halt_file=marker)
    keys = signing.Passkeys(rp_id="localhost", origin="http://localhost:8000")
    users = [registered(conn, index, keys) for index in (1, 2)]
    outcomes = []
    for user, device in users:
        subject, record = runtime_halt.clear_record(conn, "Verified issue resolved")
        options = record_signing.begin_record(
            conn, user, keys, purpose="CLEAR", subject_id=subject, record=record
        )
        outcomes.append(
            runtime_halt.finish_clear(
                conn,
                user,
                keys,
                reason="Verified issue resolved",
                ceremony_id=options["ceremony_id"],
                credential=device.sign(options["publicKey"]),
            )
        )
    assert outcomes == [False, True]
    assert marker.exists()
    assert not conn.execute("SELECT halted FROM killswitch_state WHERE id=1").fetchone()[0]
    assert conn.execute("SELECT cleared_at FROM trip WHERE id=?", (trip.id,)).fetchone()[0]
    assert killswitch.load(conn, marker).is_halted()


def test_halt_signature_is_bound_to_exact_reason(domain):
    database, _ = domain
    conn = database.connection()
    killswitch.trip(conn, "Test halt")
    keys = signing.Passkeys(rp_id="localhost", origin="http://localhost:8000")
    user, device = registered(conn, 1, keys)
    subject, record = runtime_halt.clear_record(conn, "Reviewed original reason")
    options = record_signing.begin_record(
        conn, user, keys, purpose="CLEAR", subject_id=subject, record=record
    )
    with pytest.raises(signing.SigningError, match="changed"):
        runtime_halt.finish_clear(
            conn,
            user,
            keys,
            reason="Different reason",
            ceremony_id=options["ceremony_id"],
            credential=device.sign(options["publicKey"]),
        )
    assert conn.execute("SELECT halted FROM killswitch_state WHERE id=1").fetchone()[0]


def test_expired_halt_clear_round_requires_new_signatures_even_with_same_reason(domain):
    import time_machine

    database, _ = domain
    conn = database.connection()
    with time_machine.travel("2026-11-10T12:00:00Z", tick=False) as clock:
        killswitch.trip(conn, "Test halt")
        keys = signing.Passkeys(rp_id="localhost", origin="http://localhost:8000")
        users = [registered(conn, index, keys) for index in (1, 2)]
        old_subject, old_record = runtime_halt.clear_record(conn, "Issue resolved")
        user, device = users[0]
        options = record_signing.begin_record(
            conn, user, keys, purpose="CLEAR", subject_id=old_subject, record=old_record
        )
        assert not runtime_halt.finish_clear(
            conn,
            user,
            keys,
            reason="Issue resolved",
            ceremony_id=options["ceremony_id"],
            credential=device.sign(options["publicKey"]),
        )
        clock.shift(timedelta(hours=4, minutes=1))
        with pytest.raises(signing.SigningError, match="expired"):
            record_signing.verify_records(
                conn, keys, purpose="CLEAR", subject_id=old_subject, record=old_record, required=1
            )
        subject, record = runtime_halt.clear_record(conn, "Issue resolved")
        assert subject != old_subject and record["round_id"] != old_record["round_id"]
        outcomes = []
        for user, device in users:
            current_subject, current = runtime_halt.clear_record(conn, "Issue resolved")
            # begin_record persists the proposed round for the second signer.
            options = record_signing.begin_record(
                conn, user, keys, purpose="CLEAR", subject_id=current_subject, record=current
            )
            outcomes.append(
                runtime_halt.finish_clear(
                    conn,
                    user,
                    keys,
                    reason="Issue resolved",
                    ceremony_id=options["ceremony_id"],
                    credential=device.sign(options["publicKey"]),
                )
            )
        assert outcomes == [False, True]


@pytest.fixture
def decision_service(domain, monkeypatch, request):
    monkeypatch.setenv("APP_DB_PATH", str(domain[0].path))
    return request.getfixturevalue("service")


def test_real_policy_callback_and_halt_http_flows(domain, decision_service, tmp_path, monkeypatch):
    database, _ = domain
    conn = database.connection()
    callback = prepare_callback(domain)
    conn.execute(
        "INSERT INTO entity(id,legal_name,base_currency,created_at) "
        "VALUES('entity','Test business','USD',?)",
        (operators.utcnow().isoformat(),),
    )
    policy = copy.deepcopy(BASE_POLICY)
    policy.pop("demo_timing")
    policy["entity_id"] = "entity"
    policy["roster"] = [
        dict(row) for row in conn.execute("SELECT id,name,role,email FROM user ORDER BY id")
    ]
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.safe_dump(policy), encoding="utf-8")
    monkeypatch.setenv("APP_POLICY_PATH", str(path))
    keys = signing.Passkeys(rp_id="localhost", origin="http://localhost:8000")
    devices = {index: registered(conn, index, keys)[1] for index in (1, 2, 3)}
    client = decision_service

    def sign_in(index):
        result = client.post(
            "/api/login",
            json={
                "email": f"operator{index}@example.test",
                "password": f"test-password-{index}-long",
            },
        )
        assert result.status_code == 200
        return {"x-csrf-token": result.json()["csrf_token"]}

    for index in (1, 2):
        headers = sign_in(index)
        options = client.post("/api/policy/options", headers=headers)
        assert options.status_code == 200
        result = client.post(
            "/api/policy/finish",
            headers=headers,
            json={
                "ceremony_id": options.json()["ceremony_id"],
                "credential": devices[index].sign(options.json()["publicKey"]),
            },
        )
        assert result.status_code == 200
    assert client.get("/api/policy").json()["signatures"] == 2
    runtime_policy.load_runtime_policy(conn, path, keys)
    headers = sign_in(3)
    options = client.post(
        "/api/bank-changes/change/callback/options", headers=headers, json=callback.model_dump()
    )
    assert options.status_code == 200
    result = client.post(
        "/api/bank-changes/change/callback/finish",
        headers=headers,
        json={
            "callback": callback.model_dump(),
            "ceremony_id": options.json()["ceremony_id"],
            "credential": devices[3].sign(options.json()["publicKey"]),
        },
    )
    assert result.status_code == 200
    callbacks.verify_callback(conn, keys, payee_version_id="payee")
    assert (
        client.post("/api/halt", headers=headers, json={"reason": "Operator halt"}).status_code
        == 200
    )
    for index in (1, 2):
        headers = sign_in(index)
        options = client.post(
            "/api/halt/clear/options", headers=headers, json={"reason": "Issue resolved"}
        )
        assert options.status_code == 200
        result = client.post(
            "/api/halt/clear/finish",
            headers=headers,
            json={
                "reason": "Issue resolved",
                "ceremony_id": options.json()["ceremony_id"],
                "credential": devices[index].sign(options.json()["publicKey"]),
            },
        )
        assert result.status_code == 200
        assert result.json()["database_halt_cleared"] is (index == 2)


def test_public_hmac_test_seed_cannot_authorize_runtime_decision(domain):
    from webauthn.helpers.bytes_to_base64url import bytes_to_base64url

    from app.core.policy import sign_policy_bytes

    database, _ = domain
    conn = database.connection()
    keys = signing.Passkeys(rp_id="localhost", origin="http://localhost:8000")
    user, device = registered(conn, 1, keys)
    record = {"kind": "POLICY", "file_sha256": "a" * 64}
    options = record_signing.begin_record(
        conn, user, keys, purpose="POLICY", subject_id="policy", record=record
    )
    credential = device.sign(options["publicKey"])
    legacy = sign_policy_bytes(b"untrusted policy", [user.user_id])
    credential["response"]["signature"] = bytes_to_base64url(
        bytes.fromhex(legacy["signatures"][0]["signature"])
    )
    with pytest.raises(signing.SigningError, match="verification failed"):
        record_signing.finish_record(
            conn,
            user,
            keys,
            purpose="POLICY",
            subject_id="policy",
            record=record,
            ceremony_id=options["ceremony_id"],
            credential=credential,
        )
    assert conn.execute("SELECT COUNT(*) FROM signed_record").fetchone()[0] == 0


def test_version_two_upgrade_preserves_existing_operator(domain, tmp_path):
    from app.core import db

    path = tmp_path / "v2.sqlite"
    conn = db.sqlite3.connect(path, isolation_level=None)
    conn.row_factory = db.sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(db._SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.executescript(db._SCHEMA_PATH.with_name("migration_002.sql").read_text(encoding="utf-8"))
    conn.execute("PRAGMA user_version=2")
    user = operators.provision(
        conn,
        name="Migration operator",
        email="migrate@example.test",
        role="approver",
        password="migration-test-password",
    )
    db.migrate(conn)
    assert conn.execute("SELECT id FROM user").fetchone()[0] == user
    assert db.user_version(conn) == db.SCHEMA_VERSION
    assert conn.execute("SELECT COUNT(*) FROM signed_record").fetchone()[0] == 0
    conn.close()
