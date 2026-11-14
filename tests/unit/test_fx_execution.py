"""Locked-quote execution through real crypto/SQLite/client with test-only HTTP."""

# ruff: noqa: F811
import json
from datetime import timedelta
from decimal import Decimal
from email.utils import format_datetime

import httpx
import pytest
import time_machine

from app.core import operators, signing
from app.integrations.airwallex import AirwallexClient
from app.workers import fx
from tests.unit.test_operators_signing import domain, session_for  # noqa: F401
from tests.unit.test_real_executor import execution  # noqa: F401

pytestmark = pytest.mark.parametrize("execution", ["GBP"], indirect=True)


class FXBoundary:
    def __init__(self, payouts):
        self.payouts = payouts
        self.quotes = {}
        self.conversions = {}
        self.posts = []
        self.native = "0.00"
        self.usd = Decimal("20000.00")
        self.cost = Decimal("1.25")
        self.quote_seconds = 4 * 3600
        self.timeout_after_commit = False

    def handle(self, request):
        path = request.url.path.removeprefix("/api/v1")
        headers = {"Date": format_datetime(operators.utcnow(), usegmt=True)}
        if path == "/balances/current":
            return httpx.Response(
                200,
                headers=headers,
                json=[
                    {"currency": "USD", "available_amount": str(self.usd)},
                    {"currency": "GBP", "available_amount": self.native},
                ],
            )
        if path == "/fx/rates/current":
            buy_usd = request.url.params["buy_currency"] == "USD"
            return httpx.Response(
                200,
                headers=headers,
                json={
                    "buy_currency": request.url.params["buy_currency"],
                    "sell_currency": request.url.params["sell_currency"],
                    "rate_details": [
                        {
                            "level": "CLIENT",
                            "buy_amount": "125" if buy_usd else "100",
                            "sell_amount": "100" if buy_usd else str(100 * self.cost),
                        }
                    ],
                },
            )
        if path == "/fx/conversions":
            return httpx.Response(
                200,
                headers=headers,
                json={"has_more": False, "items": list(self.conversions.values())},
            )
        if path.startswith("/fx/quotes/") and request.method == "GET":
            return httpx.Response(200, headers=headers, json=self.quotes[path.rsplit("/", 1)[1]])
        if path == "/fx/quotes/create":
            body = json.loads(request.content)
            identifier = "fixture-quote-" + str(len(self.quotes) + 1)
            sell = str(Decimal(body["buy_amount"]) * self.cost)
            quote = {
                "quote_id": identifier,
                "client_rate": "0.8",
                "buy_currency": "GBP",
                "sell_currency": "USD",
                "buy_amount": body["buy_amount"],
                "sell_amount": sell,
                "conversion_date": operators.utcnow().date().isoformat(),
                "valid_to_at": (
                    operators.utcnow() + timedelta(seconds=self.quote_seconds)
                ).isoformat(),
                "rate_details": [
                    {"level": "CLIENT", "buy_amount": body["buy_amount"], "sell_amount": sell}
                ],
            }
            self.quotes[identifier] = quote
            return httpx.Response(201, headers=headers, json=quote)
        if path == "/fx/conversions/create":
            body = json.loads(request.content)
            self.posts.append(body)
            result = {
                **body,
                "conversion_id": "fixture-conversion-" + str(len(self.conversions) + 1),
                "sell_amount": str(Decimal(body["buy_amount"]) * self.cost),
                "status": "SETTLED",
                "created_at": operators.utcnow().isoformat(),
            }
            self.conversions[body["request_id"]] = result
            self.native = str(Decimal(self.native) + Decimal(body["buy_amount"]))
            self.usd -= Decimal(result["sell_amount"])
            if self.timeout_after_commit:
                raise httpx.ReadTimeout("Fixture lost response after conversion commit")
            return httpx.Response(201, headers=headers, json=result)
        return self.payouts.handle(request)


def setup(execution):
    executor, payouts, payment, _ = execution
    boundary = FXBoundary(payouts)
    executor.client.close()
    executor.client = AirwallexClient(
        "fixture-client",
        "fixture-key",
        transport=httpx.MockTransport(boundary.handle),
        sleep=lambda _: None,
    )
    packet = fx.prepare(executor, payment)
    return executor, boundary, packet, payouts.devices


def approve(executor, packet, devices):
    conn = executor.database.connection()
    for index in (1, 2):
        actor = session_for(conn, index)[0]
        prompt = executor.passkeys.begin(conn, actor, packet_id=packet)
        executor.passkeys.finish(
            conn,
            actor,
            ceremony_id=prompt["ceremony_id"],
            credential=devices[index].sign(prompt["publicKey"]),
        )


def test_conversion_requires_humans_then_executes_once(execution):
    executor, boundary, packet, devices = setup(execution)
    with pytest.raises(signing.SigningError, match="Insufficient"):
        fx.execute(executor, packet)
    assert boundary.posts == []
    approve(executor, packet, devices)
    assert fx.execute(executor, packet) == "SETTLED"
    assert fx.execute(executor, packet) == "SETTLED"
    assert len(boundary.posts) == 1
    assert (
        executor.database.connection()
        .execute("SELECT COUNT(*) FROM approval_consumption")
        .fetchone()[0]
        == 1
    )


def test_settled_fx_funds_the_real_payout_including_fee_reservation(execution):
    executor, boundary, packet, devices = setup(execution)
    approve(executor, packet, devices)
    assert fx.execute(executor, packet) == "SETTLED"
    assert Decimal(boundary.posts[0]["buy_amount"]) > Decimal(execution[3].items[0].transfer_amount)
    assert executor.execute(execution[2]) == "SUBMITTED"
    assert len(boundary.posts) == 1 and len(execution[1].transfers) == 1


def test_quote_expiry_requires_new_quote_and_new_human_approval(execution):
    executor, boundary, packet, devices = setup(execution)
    approve(executor, packet, devices)
    # The provider can shorten/withdraw a quote before the local approval expiry.
    quote = next(iter(boundary.quotes.values()))
    quote["valid_to_at"] = (operators.utcnow() - timedelta(seconds=1)).isoformat()
    with pytest.raises(fx.FXBlockedError, match="Quote expired"):
        fx.execute(executor, packet)
    assert boundary.posts == []
    fresh = fx.prepare(executor, execution[2])
    assert fresh != packet
    with pytest.raises(signing.SigningError):
        fx.execute(executor, fresh)
    approve(executor, fresh, devices)
    assert fx.execute(executor, fresh) == "SETTLED"


@pytest.mark.parametrize("fault", ["market_rate", "locked_amount", "wallet_amount", "cooling_bank"])
def test_rate_amount_or_bank_drift_blocks_conversion(execution, fault):
    executor, boundary, packet, devices = setup(execution)
    approve(executor, packet, devices)
    if fault == "market_rate":
        boundary.cost = Decimal("1.30")
    elif fault == "locked_amount":
        next(iter(boundary.quotes.values()))["buy_amount"] = "101.00"
    elif fault == "wallet_amount":
        boundary.native = "1.00"
    else:
        executor.database.connection().execute(
            "UPDATE payee_version SET fingerprint=? WHERE id='payee'", ("b" * 64,)
        )
    with pytest.raises((fx.FXBlockedError, RuntimeError)):
        fx.execute(executor, packet)
    assert boundary.posts == []


def test_conversion_lost_response_is_resolved_without_second_post(execution):
    executor, boundary, packet, devices = setup(execution)
    approve(executor, packet, devices)
    boundary.timeout_after_commit = True
    assert fx.execute(executor, packet) == "SETTLED"
    assert fx.execute(executor, packet) == "SETTLED"
    assert len(boundary.posts) == 1


def test_elapsed_quote_window_cannot_be_reused_even_if_database_expiry_is_extended(execution):
    executor, boundary, packet, devices = setup(execution)
    approve(executor, packet, devices)
    conn = executor.database.connection()
    conn.execute(
        "UPDATE approval_packet SET expires_at=? WHERE id=?",
        ((operators.utcnow() + timedelta(days=1)).isoformat(), packet),
    )
    with (
        time_machine.travel(operators.utcnow() + timedelta(hours=3, minutes=59), tick=False),
        pytest.raises(fx.FXBlockedError, match="approval expired"),
    ):
        fx.execute(executor, packet)
    assert boundary.posts == []
