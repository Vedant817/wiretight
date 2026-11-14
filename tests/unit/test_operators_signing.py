import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest

from app.core import audit, db, operators, signing
from tests.support.authenticator import Authenticator


@pytest.fixture
def domain(tmp_path):
    database = db.Database(tmp_path / "operator.sqlite")
    conn = database.connection()
    ids = [
        operators.provision(
            conn,
            name=f"Operator {i}",
            email=f"operator{i}@example.test",
            role="ops" if i == 3 else "approver",
            password=f"test-password-{i}-long",
        )
        for i in range(4)
    ]
    conn.execute(
        "INSERT INTO vendor(id,legal_name_norm,display_name,category,created_at) "
        "VALUES('v','supplier','Supplier','goods',?)",
        (operators.utcnow().isoformat(),),
    )
    conn.execute(
        "INSERT INTO obligation(id,vendor_id,invoice_no_norm,amount,currency,due_date,state,"
        "requester_set,created_at,updated_at) "
        "VALUES('o','v','invoice-1','100.00','USD','2026-12-01','READY',?,?,?)",
        (json.dumps([ids[0]]), operators.utcnow().isoformat(), operators.utcnow().isoformat()),
    )
    payload = {
        "kind": "PAYMENT",
        "items": [{"obligation_id": "o"}],
        "tier": "T2",
        "required_approvers": 2,
    }
    canonical = audit.canonical_json(payload)
    conn.execute(
        "INSERT INTO approval_packet(id,kind,canonical_json,sha256,tier,required_approvers,"
        "created_at,expires_at,state) "
        "VALUES('p','PAYMENT',?,?,'T2',2,?,?,'OPEN')",
        (
            canonical,
            hashlib.sha256(canonical.encode()).hexdigest(),
            operators.utcnow().isoformat(),
            (operators.utcnow() + timedelta(hours=4)).isoformat(),
        ),
    )
    try:
        yield database, ids
    finally:
        database.close()


def session_for(conn, index):
    token, csrf = operators.login(
        conn,
        email=f"operator{index}@example.test",
        password=f"test-password-{index}-long",
        source="test-local",
    )
    return operators.authenticate(conn, token, csrf=csrf), token, csrf


def registered(conn, index, passkeys):
    session, _, _ = session_for(conn, index)
    device = Authenticator()
    options = passkeys.begin(conn, session)
    passkeys.finish(
        conn,
        session,
        ceremony_id=options["ceremony_id"],
        credential=device.register(options["publicKey"]),
    )
    return session, device


def test_passwords_sessions_revocation_and_csrf(domain):
    database, _ = domain
    conn = database.connection()
    session, token, _ = session_for(conn, 0)
    assert operators.authenticate(conn, token).user_id == session.user_id
    with pytest.raises(operators.AuthenticationError, match="token"):
        operators.authenticate(conn, token, csrf="wrong")
    operators.logout(conn, session)
    with pytest.raises(operators.AuthenticationError, match="expired or revoked"):
        operators.authenticate(conn, token)
    assert (
        "test-password"
        not in conn.execute("SELECT password_hash FROM operator_auth LIMIT 1").fetchone()[0]
    )


def test_failed_login_rate_limit_survives_connections(domain):
    database, _ = domain
    for _ in range(10):
        with pytest.raises(operators.AuthenticationError, match="Invalid"):
            operators.login(
                database.connection(),
                email="operator0@example.test",
                password="wrong",
                source="attacker",
            )
    with pytest.raises(operators.AuthenticationError, match="temporarily"):
        operators.login(
            database.connection(),
            email="operator0@example.test",
            password="test-password-0-long",
            source="attacker",
        )


@pytest.mark.compliance("T-06")
def test_real_passkey_two_person_approval_and_reverification(domain):
    database, _ = domain
    conn = database.connection()
    passkeys = signing.Passkeys(rp_id="localhost", origin="http://localhost:8000")
    for index in (1, 2):
        session, device = registered(conn, index, passkeys)
        options = passkeys.begin(conn, session, packet_id="p")
        credential = device.sign(options["publicKey"])
        passkeys.finish(conn, session, ceremony_id=options["ceremony_id"], credential=credential)
        with pytest.raises(signing.SigningError, match="already used"):
            passkeys.finish(
                conn, session, ceremony_id=options["ceremony_id"], credential=credential
            )
    assert (
        conn.execute("SELECT state FROM approval_packet WHERE id='p'").fetchone()[0] == "APPROVED"
    )
    passkeys.verify_stored(conn, "p")
    assert audit.verify(conn).ok


@pytest.mark.compliance("T-11")
def test_requester_and_ops_cannot_approve(domain):
    database, _ = domain
    conn = database.connection()
    passkeys = signing.Passkeys(rp_id="localhost", origin="http://localhost:8000")
    for index, reason in [(0, "Requester"), (3, "Only approvers")]:
        session, _ = registered(conn, index, passkeys)
        with pytest.raises(signing.SigningError, match=reason):
            passkeys.begin(conn, session, packet_id="p")
    assert conn.execute("SELECT COUNT(*) FROM approval_signature").fetchone()[0] == 0


@pytest.mark.parametrize("bad", ["origin", "verification", "signature"])
def test_passkey_failures_never_approve(domain, bad):
    database, _ = domain
    conn = database.connection()
    passkeys = signing.Passkeys(rp_id="localhost", origin="http://localhost:8000")
    session, device = registered(conn, 1, passkeys)
    options = passkeys.begin(conn, session, packet_id="p")
    credential = device.sign(
        options["publicKey"],
        origin="https://attacker.test" if bad == "origin" else passkeys.origin,
        verified=bad != "verification",
    )
    if bad == "signature":
        credential["response"]["signature"] = "AAAA"
    with pytest.raises(signing.SigningError, match="verification failed"):
        passkeys.finish(conn, session, ceremony_id=options["ceremony_id"], credential=credential)
    assert conn.execute("SELECT COUNT(*) FROM approval_signature").fetchone()[0] == 0


@pytest.mark.compliance("T-06")
@pytest.mark.compliance("T-11")
def test_concurrent_double_click_records_one_signature(domain):
    database, _ = domain
    passkeys = signing.Passkeys(rp_id="localhost", origin="http://localhost:8000")
    session, device = registered(database.connection(), 1, passkeys)
    options = passkeys.begin(database.connection(), session, packet_id="p")
    credential = device.sign(options["publicKey"])

    def click(_):
        try:
            passkeys.finish(
                database.connection(),
                session,
                ceremony_id=options["ceremony_id"],
                credential=credential,
            )
            return "accepted"
        except signing.SigningError:
            return "refused"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(click, range(2))) == ["accepted", "refused"]
    assert (
        database.connection().execute("SELECT COUNT(*) FROM approval_signature").fetchone()[0] == 1
    )


def test_upgrade_preserves_version_one_audit(tmp_path):
    conn = db.sqlite3.connect(tmp_path / "old.sqlite", isolation_level=None)
    conn.row_factory = db.sqlite3.Row
    conn.executescript(db._SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute("PRAGMA user_version=1")
    audit.append(conn, "before.upgrade", {"value": "preserve"})
    db.migrate(conn)
    assert db.user_version(conn) == db.SCHEMA_VERSION
    assert audit.verify(conn).ok
    assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 1
    db.migrate(conn)
    conn.close()


def test_expired_ceremony_and_revoked_session_refused(domain):
    database, _ = domain
    conn = database.connection()
    passkeys = signing.Passkeys(rp_id="localhost", origin="http://localhost:8000")
    session, device = registered(conn, 1, passkeys)
    options = passkeys.begin(conn, session, packet_id="p")
    conn.execute(
        "UPDATE signing_challenge SET expires_at=? WHERE id=?",
        ((operators.utcnow() - timedelta(seconds=1)).isoformat(), options["ceremony_id"]),
    )
    with pytest.raises(signing.SigningError, match="expired"):
        passkeys.finish(
            conn,
            session,
            ceremony_id=options["ceremony_id"],
            credential=device.sign(options["publicKey"]),
        )
    operators.disable(conn, "operator1@example.test")
    with pytest.raises(operators.AuthenticationError, match="revoked"):
        passkeys.begin(conn, session, packet_id="p")
    assert conn.execute("SELECT COUNT(*) FROM approval_signature").fetchone()[0] == 0


def test_executor_reverification_refuses_revoked_or_changed_requester(domain):
    database, ids = domain
    conn = database.connection()
    passkeys = signing.Passkeys(rp_id="localhost", origin="http://localhost:8000")
    for index in (1, 2):
        session, device = registered(conn, index, passkeys)
        options = passkeys.begin(conn, session, packet_id="p")
        passkeys.finish(
            conn,
            session,
            ceremony_id=options["ceremony_id"],
            credential=device.sign(options["publicKey"]),
        )
    passkeys.verify_stored(conn, "p")
    conn.execute("UPDATE obligation SET requester_set=? WHERE id='o'", (json.dumps([ids[1]]),))
    with pytest.raises(signing.SigningError, match="Requester"):
        passkeys.verify_stored(conn, "p")
    conn.execute("UPDATE obligation SET requester_set=? WHERE id='o'", (json.dumps([ids[0]]),))
    operators.disable(conn, "operator1@example.test")
    with pytest.raises(signing.SigningError):
        passkeys.verify_stored(conn, "p")


def test_shared_reader_concurrent_count_is_never_corrupted(domain):
    database, _ = domain
    reader = database.reader()

    def count(_):
        return reader.execute("SELECT COUNT(*) FROM user").fetchone()[0]

    with ThreadPoolExecutor(max_workers=8) as pool:
        result = list(pool.map(count, range(1000)))
    assert result == [4] * 1000


def test_auth_http_boundaries(service):  # noqa: F811 - imported pytest fixture
    import os

    with db.Database(os.environ["APP_DB_PATH"]) as database:
        operators.provision(
            database.connection(),
            name="HTTP Operator",
            email="http@example.test",
            role="approver",
            password="http-test-password-long",
        )
    assert service.get("/api/session").status_code == 401
    assert service.get("/api/approvals").status_code == 401
    assert (
        service.post(
            "/api/login",
            json={"email": "http@example.test", "password": "http-test-password-long"},
            headers={"origin": "https://attacker.test"},
        ).status_code
        == 403
    )
    response = service.post(
        "/api/login", json={"email": "http@example.test", "password": "http-test-password-long"}
    )
    assert response.status_code == 200
    csrf = response.json()["csrf_token"]
    assert service.get("/api/session").json()["name"] == "HTTP Operator"
    assert service.post("/api/passkeys/register/options").status_code == 401
    options = service.post("/api/passkeys/register/options", headers={"x-csrf-token": csrf})
    assert options.status_code == 200
    device = Authenticator()
    credential = device.register(options.json()["publicKey"])
    assert (
        service.post(
            "/api/passkeys/finish",
            json={"ceremony_id": options.json()["ceremony_id"], "credential": credential},
            headers={"x-csrf-token": csrf},
        ).status_code
        == 200
    )
    assert service.get("/api/session").json()["passkey_registered"] is True
    assert service.post("/api/logout", headers={"x-csrf-token": csrf}).status_code == 200
    assert service.get("/api/session").status_code == 401


def test_invalid_login_body_does_not_echo_secret(service):  # noqa: F811 - imported pytest fixture
    secret = "sensitive-password" * 30
    response = service.post("/api/login", json={"email": "http@example.test", "password": secret})
    assert response.status_code == 422
    assert secret not in response.text


def test_executor_reverification_detects_stored_assertion_tampering(domain):
    database, _ = domain
    conn = database.connection()
    passkeys = signing.Passkeys(rp_id="localhost", origin="http://localhost:8000")
    for index in (1, 2):
        session, device = registered(conn, index, passkeys)
        options = passkeys.begin(conn, session, packet_id="p")
        passkeys.finish(
            conn,
            session,
            ceremony_id=options["ceremony_id"],
            credential=device.sign(options["publicKey"]),
        )
    passkeys.verify_stored(conn, "p")
    row = conn.execute("SELECT id,assertion FROM approval_signature LIMIT 1").fetchone()
    material = json.loads(row["assertion"])
    material["credential"]["response"]["signature"] = "AAAA"
    # Emulate an offline DB edit that bypasses the append-only trigger.
    conn.execute("DROP TRIGGER approval_signature_no_update")
    conn.execute(
        "UPDATE approval_signature SET assertion=? WHERE id=?",
        (audit.canonical_json(material).encode(), row["id"]),
    )
    assert (
        conn.execute("SELECT state FROM approval_packet WHERE id='p'").fetchone()[0] == "APPROVED"
    )
    with pytest.raises(signing.SigningError, match="signature failed"):
        passkeys.verify_stored(conn, "p")


# Reuse the localhost-only TestClient fixture; application code is never patched.
from tests.unit.test_product_webhooks import service  # noqa: E402,F401


@pytest.mark.compliance("T-34")
def test_two_enabled_approvers_cannot_begin_t2_signoff(domain):
    database, _ = domain
    conn = database.connection()
    passkeys = signing.Passkeys(rp_id="localhost", origin="http://localhost:8000")
    actor, _ = registered(conn, 1, passkeys)
    operators.disable(conn, "operator2@example.test")
    with pytest.raises(signing.SigningError, match="at least three"):
        passkeys.begin(conn, actor, packet_id="p")
    assert conn.execute("SELECT COUNT(*) FROM approval_signature").fetchone()[0] == 0


@pytest.mark.compliance("T-11")
def test_duplicate_roster_email_is_not_a_second_human(domain):
    database, _ = domain
    with pytest.raises(db.sqlite3.IntegrityError):
        operators.provision(
            database.connection(),
            name="Duplicate",
            email=" OPERATOR1@EXAMPLE.TEST ",
            role="approver",
            password="another-test-password-long",
        )
    assert database.connection().execute("SELECT COUNT(*) FROM user").fetchone()[0] == 4
