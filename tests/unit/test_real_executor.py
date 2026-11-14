"""Fault tests at the HTTP boundary; these are not recorded sandbox contracts."""

# ruff: noqa: F811
import hashlib
import json
from datetime import timedelta
from email.utils import format_datetime

import httpx
import pytest
import time_machine

from app.core import (
    audit,
    callbacks,
    installation,
    operators,
    packets,
    record_signing,
    runtime_policy,
    signing,
    trust,
)
from app.core.bank_details import BankDetails, DetailVault
from app.integrations.airwallex import AirwallexClient
from app.workers.executor import ExecutionBlockedError, Executor
from tests.unit.test_operators_signing import domain, registered, session_for  # noqa: F401


class ProviderBoundary:
    def __init__(self):
        self.balance = "20000.00"
        self.beneficiaries = {}
        self.transfers = {}
        self.posts = []
        self.fault = None

    def handle(self, request):
        path = request.url.path.removeprefix("/api/v1")
        headers = {"Date": format_datetime(operators.utcnow(), usegmt=True)}
        if path == "/authentication/login":
            return httpx.Response(
                201,
                headers=headers,
                json={
                    "token": "test-token",
                    "expires_at": (operators.utcnow() + timedelta(minutes=30)).isoformat(),
                },
            )
        if request.method == "GET":
            if path == "/balances/current":
                return httpx.Response(
                    200,
                    headers=headers,
                    json=[{"currency": "USD", "available_amount": self.balance}],
                )
            if path == "/beneficiaries":
                values = list(self.beneficiaries.values())
                if "nick_name" in request.url.params:
                    values = [
                        row for row in values if row["nickname"] == request.url.params["nick_name"]
                    ]
                return httpx.Response(
                    200, headers=headers, json={"has_more": False, "items": values}
                )
            if path.startswith("/beneficiaries/"):
                return httpx.Response(
                    200, headers=headers, json=self.beneficiaries[path.rsplit("/", 1)[1]]
                )
            if path == "/transfers":
                values = list(self.transfers.values())
                if "request_id" in request.url.params:
                    values = [
                        row
                        for row in values
                        if row["request_id"] == request.url.params["request_id"]
                    ]
                return httpx.Response(
                    200, headers=headers, json={"has_more": False, "items": values}
                )
            if path in {"/rfis", "/fx/conversions"}:
                return httpx.Response(200, headers=headers, json={"has_more": False, "items": []})
        body = json.loads(request.content)
        if path == "/beneficiary_api_schemas/generate":
            return httpx.Response(200, headers=headers, json={"type": "object"})
        if path == "/beneficiaries/validate":
            return httpx.Response(200, headers=headers, text="OK")
        if path == "/beneficiaries/create":
            self.posts.append((path, body))
            identifier = "beneficiary-" + str(len(self.beneficiaries) + 1)
            result = {**body, "id": identifier, "created_at": operators.utcnow().isoformat()}
            self.beneficiaries[identifier] = result
            if self.fault == "beneficiary_timeout_after_create":
                raise httpx.ReadTimeout("beneficiary response lost")
            return httpx.Response(201, headers=headers, json=result)
        if path == "/transfers/create":
            self.posts.append((path, body))
            if self.fault == "timeout_before_create":
                raise httpx.ReadTimeout("no response; provider outcome unknown")
            if self.fault == "insufficient_after_check":
                return httpx.Response(400, headers=headers, json={"code": "balance_insufficient"})
            result = {
                **body,
                "id": "transfer-" + str(len(self.transfers) + 1),
                "status": "SENT",
                "created_at": operators.utcnow().isoformat(),
            }
            self.transfers[result["id"]] = result
            if self.fault == "timeout_after_create":
                raise httpx.ReadTimeout("lost response")
            if self.fault == "server_error_after_create":
                return httpx.Response(503, headers=headers, json={"code": "unavailable"})
            if self.fault == "crash_after_create":
                raise SystemExit("process lost after provider accepted payout")
            return httpx.Response(201, headers=headers, json=result)
        raise AssertionError(f"Unexpected boundary call {request.method} {path}")


@pytest.fixture
def execution(domain, tmp_path):
    database, ids = domain
    conn = database.connection()
    with time_machine.travel("2026-11-10T10:00:00+00:00", tick=False) as clock:
        key_dir, seal_dir, policy_path = (
            tmp_path / "keys",
            tmp_path / "seals",
            tmp_path / "policy.yaml",
        )
        installation.initialize(
            conn,
            legal_name="Fixture company",
            reserve_usd="8000.00",
            policy_path=policy_path,
            key_dir=key_dir,
            seal_dir=seal_dir,
        )
        passkeys = signing.Passkeys(rp_id="localhost", origin="http://localhost:8000")
        devices = {i: registered(conn, i, passkeys)[1] for i in range(4)}
        bank = BankDetails(
            company_name="Fixture supplier",
            country="US",
            currency="USD",
            account_name="Fixture supplier",
            account_number="123456789",
            routing_value="021000021",
            bank_account_category="Checking",
        )
        vault = DetailVault(key_dir / "details.key")
        details_id = vault.store(conn, bank)
        now = operators.utcnow()
        conn.execute("UPDATE vendor SET category='manufacturing' WHERE id='v'")
        conn.execute(
            "INSERT INTO vendor_contact(id,vendor_id,kind,value,value_norm,provenance,created_at) "
            "VALUES('contact','v','phone','+12025550100','12025550100','contract',?)",
            ((now - timedelta(days=100)).isoformat(),),
        )
        conn.execute(
            "INSERT INTO "
            "payee_version(id,vendor_id,fingerprint,details_ref,masked,"
            "method,rail,country,currency,status,created_at,updated_at) "
            "VALUES('payee','v',?,?,'masked','LOCAL','ACH','US','USD','PROPOSED',?,?)",
            (bank.fingerprint(), details_id, now.isoformat(), now.isoformat()),
        )
        conn.execute(
            "INSERT INTO "
            "payee_change_request(id,vendor_id,source_kind,received_at,"
            "intake_user_id,requester_set,proposed_details_ref,"
            "proposed_masked,proposed_fingerprint,status) "
            "VALUES('change','v','manual',?,?,?,?,'masked',?,'PENDING_CALLBACK')",
            (
                (now - timedelta(minutes=5)).isoformat(),
                ids[0],
                json.dumps([ids[0]]),
                details_id,
                bank.fingerprint(),
            ),
        )
        body = callbacks.CallbackInput(
            contact_id="contact",
            vendor_person_name="Fixture contact",
            vendor_person_role="Owner",
            called_at=(now - timedelta(minutes=1)).isoformat(),
            outcome="CONFIRMED",
            readback_last4_ok=True,
            readback_name_ok=True,
        )
        ops, _, _ = session_for(conn, 3)
        options = callbacks.begin_callback(conn, ops, passkeys, request_id="change", body=body)
        callbacks.apply_callback(
            conn,
            ops,
            passkeys,
            request_id="change",
            body=body,
            ceremony_id=options["ceremony_id"],
            credential=devices[3].sign(options["publicKey"]),
        )
        clock.shift(timedelta(hours=73))
        for index in (1, 2):
            user, _, _ = session_for(conn, index)
            policy, record = runtime_policy.validated_policy(conn, policy_path)
            options = record_signing.begin_record(
                conn, user, passkeys, purpose="POLICY", subject_id=policy.sha256, record=record
            )
            record_signing.finish_record(
                conn,
                user,
                passkeys,
                purpose="POLICY",
                subject_id=policy.sha256,
                record=record,
                ceremony_id=options["ceremony_id"],
                credential=devices[index].sign(options["publicKey"]),
            )
        now = operators.utcnow().isoformat()
        conn.execute(
            "INSERT INTO "
            "bill(id,source_kind,source_ref,document_sha256,raw_json,ingested_by,ingested_at) "
            "VALUES('bill','json','fixture',?,'{}',?,?)",
            (hashlib.sha256(b"fixture invoice").hexdigest(), ids[0], now),
        )
        conn.execute("UPDATE obligation SET bill_id='bill',invoice_no_raw='invoice-1' WHERE id='o'")
        conn.execute(
            "INSERT INTO "
            "duplicate_lock(obligation_key,obligation_id,created_at) "
            "VALUES('v:INVOICE1','o',?)",
            (now,),
        )
        conn.execute("INSERT INTO run(id,started_at,state) VALUES('run',?,'OPEN')", (now,))
        conn.execute(
            "INSERT INTO "
            "compliance_review(id,payee_version_id,recorded_by,result,"
            "source,evidence_sha256,checked_at,created_at,payee_fingerprint,details_sha256) "
            "VALUES('review','payee',?,'CLEAR','fixture manual review',?,?,?,?,?)",
            (
                ids[3],
                hashlib.sha256(b"fixture screening").hexdigest(),
                now,
                now,
                bank.fingerprint(),
                conn.execute(
                    "SELECT sha256 FROM protected_details WHERE id=?", (details_id,)
                ).fetchone()[0],
            ),
        )
        review = conn.execute("SELECT * FROM compliance_review WHERE id='review'").fetchone()
        record = packets.compliance_terms(review)
        ops, _, _ = session_for(conn, 3)
        options = record_signing.begin_record(
            conn, ops, passkeys, purpose="CALLBACK", subject_id="review:review", record=record
        )
        record_signing.finish_record(
            conn,
            ops,
            passkeys,
            purpose="CALLBACK",
            subject_id="review:review",
            record=record,
            ceremony_id=options["ceremony_id"],
            credential=devices[3].sign(options["publicKey"]),
        )
        policy = runtime_policy.load_runtime_policy(conn, policy_path, passkeys)
        with database.transaction():
            terms = packets.build_payment(
                conn,
                obligation_id="o",
                payee_id="payee",
                tranche_no=1,
                run_id="run",
                policy=policy,
                passkeys=passkeys,
                vault=vault,
                rates={"USD": __import__("decimal").Decimal(1)},
            )
            packet_id = packets.save_payment(conn, terms)
        for index in (1, 2):
            user, _, _ = session_for(conn, index)
            options = passkeys.begin(conn, user, packet_id=packet_id)
            passkeys.finish(
                conn,
                user,
                ceremony_id=options["ceremony_id"],
                credential=devices[index].sign(options["publicKey"]),
            )
        trust.pin_roster(conn, key_dir=key_dir, seal_dir=seal_dir)
        provider = ProviderBoundary()
        client = AirwallexClient(
            "test-client",
            "test-api-key",
            transport=httpx.MockTransport(provider.handle),
            sleep=lambda _: None,
        )
        executor = Executor(
            database,
            client,
            policy_path=policy_path,
            key_dir=key_dir,
            seal_dir=seal_dir,
            halt_file=tmp_path / "HALT",
            lock_file=tmp_path / "worker.lock",
        )
        try:
            yield executor, provider, packet_id, terms
        finally:
            client.close()


def test_approved_payment_executes_once_and_uses_real_boundaries(execution):
    executor, provider, packet_id, terms = execution
    assert executor.execute(packet_id) == "SUBMITTED"
    assert executor.execute(packet_id) == "SUBMITTED"
    assert [path for path, _ in provider.posts] == ["/beneficiaries/create", "/transfers/create"]
    assert provider.posts[-1][1]["request_id"] == terms.items[0].request_id
    conn = executor.database.connection()
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM approval_consumption WHERE packet_id=?", (packet_id,)
        ).fetchone()[0]
        == 1
    )
    assert audit.verify(conn).ok


def test_timeout_after_provider_commit_resolves_without_second_payout(execution):
    executor, provider, packet_id, _ = execution
    provider.fault = "timeout_after_create"
    assert executor.execute(packet_id) == "SUBMITTED"
    assert len(provider.transfers) == 1
    assert len([row for row in provider.posts if row[0] == "/transfers/create"]) == 1


def test_restart_after_lost_process_looks_up_instead_of_posting(execution):
    executor, provider, packet_id, _ = execution
    provider.fault = "crash_after_create"
    with pytest.raises(SystemExit):
        executor.execute(packet_id)
    assert (
        executor.database.connection()
        .execute("SELECT state FROM execution_intent WHERE kind='TRANSFER'")
        .fetchone()[0]
        == "PREPARED"
    )
    assert list(executor.recover().values()) == ["SUBMITTED"]
    assert executor.execute(packet_id) == "SUBMITTED"
    assert len([row for row in provider.posts if row[0] == "/transfers/create"]) == 1


def test_insufficient_balance_refuses_before_any_mutation(execution):
    executor, provider, packet_id, _ = execution
    provider.balance = "10.00"
    with pytest.raises(ExecutionBlockedError, match="Insufficient"):
        executor.execute(packet_id)
    assert provider.posts == []


def test_bank_terms_changed_after_signing_refuses_all_mutations(execution):
    executor, provider, packet_id, _ = execution
    executor.database.connection().execute(
        "UPDATE payee_version SET fingerprint=? WHERE id='payee'", ("b" * 64,)
    )
    with pytest.raises(packets.PaymentBlockedError, match="Bank details changed"):
        executor.execute(packet_id)
    assert provider.posts == []


def test_unknown_payout_is_held_and_never_automatically_reposted(execution):
    executor, provider, packet_id, _ = execution
    provider.fault = "timeout_before_create"
    assert executor.execute(packet_id) == "AMBIGUOUS"
    assert executor.execute(packet_id) == "AMBIGUOUS"
    assert len([row for row in provider.posts if row[0] == "/transfers/create"]) == 1
    assert provider.transfers == {}


def test_provider_5xx_after_commit_is_resolved_by_lookup(execution):
    executor, provider, packet_id, _ = execution
    provider.fault = "server_error_after_create"
    assert executor.execute(packet_id) == "SUBMITTED"
    assert len(provider.transfers) == 1
    assert len([row for row in provider.posts if row[0] == "/transfers/create"]) == 1


def test_beneficiary_recovery_never_claims_the_payout_was_submitted(execution):
    executor, provider, packet_id, _ = execution
    provider.fault = "beneficiary_timeout_after_create"
    assert executor.execute(packet_id) == "BENEFICIARY_READY"
    assert provider.transfers == {}
    assert executor.execute(packet_id) == "SUBMITTED"
    assert len(provider.beneficiaries) == 1 and len(provider.transfers) == 1


def test_provider_insufficient_funds_is_definitive_and_consumed(execution):
    executor, provider, packet_id, _ = execution
    provider.fault = "insufficient_after_check"
    assert executor.execute(packet_id) == "REJECTED"
    assert executor.execute(packet_id) == "REJECTED"
    assert provider.transfers == {}
    assert len([row for row in provider.posts if row[0] == "/transfers/create"]) == 1


def test_concurrent_executors_never_create_two_payouts(execution):
    from concurrent.futures import ThreadPoolExecutor

    from app.core.process_lock import ProcessLockHeldError

    executor, provider, packet_id, _ = execution

    def submit(_):
        try:
            return executor.execute(packet_id)
        except ProcessLockHeldError:
            return "LOCKED"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, range(2)))
    assert "SUBMITTED" in results
    assert len(provider.transfers) == 1
    assert len([row for row in provider.posts if row[0] == "/transfers/create"]) == 1


def test_approved_status_without_valid_signature_cannot_move_money(execution):
    executor, provider, packet_id, _ = execution
    conn = executor.database.connection()
    signature = conn.execute(
        "SELECT id,assertion FROM approval_signature WHERE packet_id=? LIMIT 1", (packet_id,)
    ).fetchone()
    material = json.loads(signature["assertion"])
    material["credential"]["response"]["signature"] = "AAAA"
    conn.execute("DROP TRIGGER approval_signature_no_update")
    conn.execute(
        "UPDATE approval_signature SET assertion=? WHERE id=?",
        (json.dumps(material).encode(), signature["id"]),
    )
    with pytest.raises(signing.SigningError, match="signature failed"):
        executor.execute(packet_id)
    assert provider.posts == []


def test_untrusted_roster_change_refuses_all_mutations(execution):
    executor, provider, packet_id, _ = execution
    executor.database.connection().execute(
        "UPDATE user SET name='Changed after trust pin' WHERE role='ops'"
    )
    with pytest.raises(ExecutionBlockedError, match="operator trust"):
        executor.execute(packet_id)
    assert provider.posts == []


def test_provider_history_counts_toward_caps_even_when_not_in_local_ledger(execution):
    executor, provider, packet_id, _ = execution
    provider.transfers["external"] = {
        "id": "external",
        "request_id": "external-request",
        "status": "SENT",
        "transfer_currency": "USD",
        "source_currency": "USD",
        "transfer_amount": "60000.00",
        "created_at": operators.utcnow().isoformat(),
        "beneficiary_id": "external-beneficiary",
    }
    with pytest.raises(ExecutionBlockedError, match="cap exceeded"):
        executor.execute(packet_id)
    assert provider.posts == []
