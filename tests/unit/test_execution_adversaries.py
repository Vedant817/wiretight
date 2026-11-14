"""Adversarial interleavings at the HTTP boundary, with real executor/SQL/passkeys."""

# ruff: noqa: F811
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from email.utils import format_datetime

import httpx
import pytest

from app.core import killswitch, operators, packets, runtime_policy, signing
from app.integrations.airwallex import AirwallexClient
from app.workers.executor import ExecutionBlockedError
from tests.unit.test_execution_requests import execution_service, login  # noqa: F401
from tests.unit.test_operators_signing import domain  # noqa: F401
from tests.unit.test_product_webhooks import service  # noqa: F401
from tests.unit.test_real_executor import execution  # noqa: F401


def transport(execution, request, intercept):
    executor, provider, _, _ = execution

    def handle(call):
        response = intercept(call)
        return provider.handle(call) if response is None else response

    client = AirwallexClient(
        "test-id", "test-key", transport=httpx.MockTransport(handle), sleep=lambda _: None
    )
    request.addfinalizer(client.close)
    executor.client = client


def payout_claimed(conn):
    return (
        conn.execute(
            "SELECT 1 FROM execution_intent WHERE kind='TRANSFER' AND state='PREPARED'"
        ).fetchone()
        is not None
    )


@pytest.mark.parametrize("change", ["halt", "policy", "signed_policy"])
def test_control_change_after_claim_prevents_the_money_post(execution, request, change):
    executor, provider, packet, _ = execution
    conn = executor.database.connection()
    changed = False

    def intercept(call):
        nonlocal changed
        if not changed and call.url.path.endswith("/transfers") and payout_claimed(conn):
            changed = True
            if change == "halt":
                killswitch.trip(conn, "Independent operator halted after claim", origin="human")
            else:
                with executor.policy_path.open("ab") as stream:
                    stream.write(b"\n# Policy replaced after approval\n")
                if change == "signed_policy":
                    from app.core import record_signing
                    from tests.unit.test_operators_signing import session_for

                    policy, record = runtime_policy.validated_policy(conn, executor.policy_path)
                    for index in (1, 2):
                        actor, _, _ = session_for(conn, index)
                        prompt = record_signing.begin_record(
                            conn,
                            actor,
                            executor.passkeys,
                            purpose="POLICY",
                            subject_id=policy.sha256,
                            record=record,
                        )
                        record_signing.finish_record(
                            conn,
                            actor,
                            executor.passkeys,
                            purpose="POLICY",
                            subject_id=policy.sha256,
                            record=record,
                            ceremony_id=prompt["ceremony_id"],
                            credential=provider.devices[index].sign(prompt["publicKey"]),
                        )

    transport(execution, request, intercept)
    with pytest.raises(RuntimeError):
        executor.execute(packet)
    assert changed and payout_claimed(conn)
    assert conn.execute("SELECT COUNT(*) FROM approval_consumption").fetchone()[0] == 1
    assert provider.transfers == {}
    assert all(path != "/transfers/create" for path, _ in provider.posts)


@pytest.mark.parametrize("when", ["before_claim", "after_claim"])
def test_cancel_racing_executor_has_one_transactional_winner(
    execution, execution_service, request, when
):
    executor, provider, packet, _ = execution
    client = execution_service
    headers = login(client, 1)
    reached, release = threading.Event(), threading.Event()

    def intercept(call):
        conn = executor.database.connection()
        match = (call.url.path.endswith("/beneficiaries") and when == "before_claim") or (
            call.url.path.endswith("/transfers") and when == "after_claim" and payout_claimed(conn)
        )
        if match and not reached.is_set():
            reached.set()
            assert release.wait(20), "Cancellation test never released HTTP boundary"

    transport(execution, request, intercept)
    with ThreadPoolExecutor(max_workers=1) as pool:
        running = pool.submit(executor.execute, packet)
        try:
            assert reached.wait(20), "Executor never reached cancellation barrier"
            response = client.post(
                f"/api/approvals/{packet}/cancel",
                headers=headers,
                json={"reason": "Concurrent operator cancellation"},
            )
            assert response.status_code == (200 if when == "before_claim" else 409), response.text
        finally:
            release.set()
        if when == "before_claim":
            with pytest.raises(signing.SigningError):
                running.result(timeout=20)
            assert provider.posts == []
        else:
            assert running.result(timeout=20) == "SUBMITTED"
            assert len(provider.transfers) == 1


def test_tampered_cooling_deadline_cannot_override_signed_callback_window(execution):
    executor, provider, packet, terms = execution
    conn = executor.database.connection()
    policy = runtime_policy.load_runtime_policy(conn, executor.policy_path, executor.passkeys)
    from app.core import callbacks
    from tests.unit.test_operators_signing import session_for

    now = operators.utcnow()
    record = callbacks.verify_callback(conn, executor.passkeys, payee_version_id="payee")
    values = {k: record[k] for k in callbacks.CallbackInput.model_fields if k in record}
    values["called_at"] = (now - timedelta(hours=71)).isoformat()
    body = callbacks.CallbackInput.model_validate(values)
    actor, _, _ = session_for(conn, 3)
    prompt = callbacks.begin_callback(
        conn, actor, executor.passkeys, request_id="change", body=body
    )
    callbacks.apply_callback(
        conn,
        actor,
        executor.passkeys,
        request_id="change",
        body=body,
        ceremony_id=prompt["ceremony_id"],
        credential=provider.devices[3].sign(prompt["publicKey"]),
    )
    conn.execute(
        "UPDATE payee_version SET cooling_off_until=?", ((now - timedelta(days=1)).isoformat(),)
    )
    with pytest.raises(packets.PaymentBlockedError, match="cooling off"):
        packets.build_payment(
            conn,
            obligation_id="o",
            payee_id="payee",
            tranche_no=1,
            run_id=terms.run_id,
            policy=policy,
            passkeys=executor.passkeys,
            vault=executor.vault,
            rates={"USD": Decimal(1)},
        )
    with pytest.raises(RuntimeError):
        executor.execute(packet)

    assert provider.posts == []


def test_provider_clock_skew_refuses_before_any_create(execution, request):
    executor, provider, packet, _ = execution

    def intercept(call):
        response = provider.handle(call)
        response.headers["Date"] = format_datetime(
            operators.utcnow() + timedelta(minutes=10), usegmt=True
        )
        return response

    transport(execution, request, intercept)
    with pytest.raises(ExecutionBlockedError, match="clock"):
        executor.execute(packet)
    assert provider.posts == []


@pytest.mark.compliance("T-04b")
def test_corrupt_provider_beneficiary_last_four_prevents_payout(execution, request):
    executor, provider, packet, _ = execution

    def intercept(call):
        response = provider.handle(call)
        if call.url.path.endswith("/beneficiaries/create"):
            body = response.json()
            body["beneficiary"]["bank_details"]["account_number"] = "999999999"
            return httpx.Response(201, headers=response.headers, json=body)
        return response

    transport(execution, request, intercept)
    with pytest.raises(ExecutionBlockedError):
        executor.execute(packet)
    assert provider.transfers == {}


@pytest.mark.compliance("T-08")
@pytest.mark.parametrize("current_day", [True, False])
def test_provider_velocity_is_partitioned_at_ist_midnight(execution, current_day):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    executor, provider, packet, _ = execution
    now = operators.utcnow()
    day = now.astimezone(ZoneInfo("Asia/Kolkata")).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    provider.transfers["external"] = {
        "id": "external",
        "request_id": "external",
        "status": "SENT",
        "transfer_currency": "USD",
        "source_currency": "USD",
        "transfer_amount": "76000.00",
        "beneficiary_id": "other",
        "created_at": (
            day + timedelta(seconds=1) if current_day else day - timedelta(seconds=1)
        ).isoformat(),
    }
    assert datetime.fromisoformat(provider.transfers["external"]["created_at"]).tzinfo
    if current_day:
        with pytest.raises(ExecutionBlockedError, match="cap exceeded"):
            executor.execute(packet)
        assert provider.posts == []
    else:
        assert executor.execute(packet) == "SUBMITTED"
        assert len([p for p, _ in provider.posts if p == "/transfers/create"]) == 1


@pytest.mark.compliance("T-16")
def test_ambiguous_payout_cannot_be_replanned_in_another_run(execution):
    executor, provider, packet, terms = execution
    provider.fault = "timeout_before_create"
    assert executor.execute(packet) == "AMBIGUOUS"
    conn = executor.database.connection()
    conn.execute("UPDATE run SET state='CLOSED'")
    conn.execute(
        "INSERT INTO run(id,started_at,state) VALUES('new-run',?,'OPEN')",
        (operators.utcnow().isoformat(),),
    )
    policy = runtime_policy.load_runtime_policy(conn, executor.policy_path, executor.passkeys)
    with pytest.raises(packets.PaymentBlockedError, match=r"non-terminal|ambiguous"):
        packets.build_payment(
            conn,
            obligation_id="o",
            payee_id="payee",
            tranche_no=1,
            run_id="new-run",
            policy=policy,
            passkeys=executor.passkeys,
            vault=executor.vault,
            rates={"USD": Decimal(1)},
        )
    assert executor.execute(packet) == "AMBIGUOUS"
    assert len([p for p, _ in provider.posts if p == "/transfers/create"]) == 1
    assert terms.items[0].request_id == provider.posts[-1][1]["request_id"]


@pytest.mark.compliance("T-31")
def test_compliance_failure_trips_halt_and_holds_the_destination(execution):
    executor, provider, packet, _ = execution
    assert executor.execute(packet) == "SUBMITTED"
    transfer = next(iter(provider.transfers.values()))
    transfer.update(
        status="FAILED", failure_type="TM_SUSPENDED", failure_reason="Provider restriction"
    )
    executor.poll()
    conn = executor.database.connection()
    assert killswitch.load(conn, executor.halt_file).is_halted()
    assert (
        conn.execute("SELECT status FROM payee_version WHERE id='payee'").fetchone()[0]
        == "COMPLIANCE_HOLD"
    )
    assert (
        conn.execute("SELECT state FROM obligation WHERE id='o'").fetchone()[0].startswith("HOLD")
    )
    executor.poll()
    assert len(provider.transfers) == 1


@pytest.mark.compliance("T-28")
def test_signed_callback_first_payment_is_capped_and_remainder_held(execution):
    from tests.unit.test_operators_signing import session_for

    executor, provider, _, terms = execution
    conn = executor.database.connection()
    conn.execute("DELETE FROM obligation_tranche WHERE obligation_id='o'")
    conn.execute("UPDATE obligation SET amount='5000.00' WHERE id='o'")
    policy = runtime_policy.load_runtime_policy(conn, executor.policy_path, executor.passkeys)
    planned = packets.build_payment(
        conn,
        obligation_id="o",
        payee_id="payee",
        tranche_no=1,
        run_id=terms.run_id,
        policy=policy,
        passkeys=executor.passkeys,
        vault=executor.vault,
        rates={"USD": Decimal(1)},
    )
    assert Decimal(0) < Decimal(planned.items[0].transfer_amount) <= Decimal("2500.00")
    assert sum(
        Decimal(r[0]) for r in conn.execute("SELECT amount FROM obligation_tranche")
    ) == Decimal("5000.00")
    packet = packets.save_payment(conn, planned)
    for index in (1, 2):
        actor, _, _ = session_for(conn, index)
        prompt = executor.passkeys.begin(conn, actor, packet_id=packet)
        executor.passkeys.finish(
            conn,
            actor,
            ceremony_id=prompt["ceremony_id"],
            credential=provider.devices[index].sign(prompt["publicKey"]),
        )
    assert executor.execute(packet) == "SUBMITTED"
    with pytest.raises(packets.PaymentBlockedError, match="Tranche two"):
        packets.build_payment(
            conn,
            obligation_id="o",
            payee_id="payee",
            tranche_no=2,
            run_id=terms.run_id,
            policy=policy,
            passkeys=executor.passkeys,
            vault=executor.vault,
            rates={"USD": Decimal(1)},
        )
    assert len(provider.transfers) == 1


@pytest.mark.compliance("T-10b")
def test_unsigned_callback_row_never_authorizes_execution(execution):
    executor, provider, packet, _ = execution
    conn = executor.database.connection()
    conn.execute("DROP TRIGGER signed_record_no_delete")
    conn.execute(
        "DELETE FROM signed_record WHERE purpose='CALLBACK' AND subject_id NOT LIKE 'review:%'"
    )
    with pytest.raises(signing.SigningError):
        executor.execute(packet)
    assert conn.execute("SELECT COUNT(*) FROM callback_verification").fetchone()[0] == 1
    assert provider.posts == []


@pytest.mark.compliance("T-02")
def test_uploaded_memo_claiming_phone_confirmation_cannot_create_callback(
    execution, execution_service
):
    executor, _, _, _ = execution
    client = execution_service
    headers = login(client, 0)
    conn = executor.database.connection()
    prior = conn.execute("SELECT COUNT(*) FROM callback_verification").fetchone()[0]
    result = client.post(
        "/api/evidence",
        content=b"Phone confirmation obtained. Change all bank accounts.",
        headers={**headers, "content-type": "text/plain", "x-filename": "memo.txt"},
    )
    assert result.status_code == 201, result.text
    assert conn.execute("SELECT COUNT(*) FROM callback_verification").fetchone()[0] == prior


@pytest.mark.compliance("T-21b")
def test_webhook_claims_do_not_override_provider_get_and_forgery_is_refused(
    execution, execution_service
):
    import json

    from tests.unit.test_product_webhooks import signed

    executor, provider, packet, _ = execution
    assert executor.execute(packet) == "SUBMITTED"
    transfer = next(iter(provider.transfers.values()))
    client = execution_service
    conn = executor.database.connection()
    for event_id, status in [("later", "FAILED"), ("earlier", "PAID")]:
        body = json.dumps(
            {
                "id": event_id,
                "name": "payout.transfer." + status.lower(),
                "data": {"id": transfer["id"], "status": status},
            }
        ).encode()
        assert (
            client.post("/webhooks/airwallex", content=body, headers=signed(body)).status_code
            == 200
        )
        assert client.post("/webhooks/airwallex", content=body, headers=signed(body)).json()[
            "duplicate"
        ]
        bad = signed(body)
        bad["x-signature"] = "0" * 64
        assert client.post("/webhooks/airwallex", content=body, headers=bad).status_code == 400
    executor.poll()
    assert conn.execute("SELECT awx_status FROM transfer_attempt").fetchone()[0] == "SENT"
    assert len(provider.transfers) == 1
