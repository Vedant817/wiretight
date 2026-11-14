"""Generated provider-event sequences must always tie the ledger out to cash.

Each example opens one real run against a fresh SQLite database and a mock
transport, then replays a random sequence of settled financial transactions:
deposits, mapped and unmapped payouts, fees, cross-currency pairs, cash drift
that no financial row explains, and no-op retries/approval decisions. After
every step the run is reconciled, and the test asserts that

* ``ledger.assert_ledger_balances`` holds per currency,
* ``Wallet:<ccy>`` equals the sum of observed nets and ``Provider:`` equals its
  negation, in every currency, even when the provider cash total disagrees,
* ``opening + delta == actual + residual`` exactly, with the residual computed
  for the observed rows rather than assumed to be zero,
* the run is clean exactly when every residual is zero and every observed
  payout maps to a transfer attempt, and
* a retry or a decision that changes no provider row posts no new journal legs.

Amounts use the real ISO 4217 exponents (JPY/KRW 0, KWD/BHD 3), so a
zero-decimal or three-decimal currency that drifted by a minor unit would fail.
"""

from __future__ import annotations

import shutil
import tempfile
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.core import db, ledger, operators, reconciliation
from app.integrations.airwallex import AirwallexClient
from app.money import to_money_string

EXPONENTS = {"USD": 2, "EUR": 2, "JPY": 0, "KWD": 3}
CURRENCIES = tuple(EXPONENTS)
KINDS = (
    "DEPOSIT",
    "PAYOUT_MAPPED",
    "PAYOUT_UNMAPPED",
    "FEE",
    "FX",
    "DRIFT",
    "RETRY",
    "APPROVAL",
    "REJECTION",
)


def minor_units(draw, currency: str) -> Decimal:
    return Decimal(draw(st.integers(min_value=0, max_value=10**8))).scaleb(-EXPONENTS[currency])


def signed(draw, currency: str, sign: int) -> Decimal:
    return (minor_units(draw, currency) * sign).quantize(Decimal(1).scaleb(-EXPONENTS[currency]))


def nonzero(draw, currency: str) -> Decimal:
    amount = signed(draw, currency, 1)
    return amount if amount else Decimal(1).scaleb(-EXPONENTS[currency])


@st.composite
def scenarios(draw):
    opening = {
        currency: minor_units(draw, currency) + Decimal(1000).scaleb(-EXPONENTS[currency])
        for currency in CURRENCIES
    }
    events = []
    for _ in range(draw(st.integers(min_value=0, max_value=8))):
        kind = draw(st.sampled_from(KINDS))
        currency = draw(st.sampled_from(CURRENCIES))
        if kind == "FX":
            other = draw(st.sampled_from(CURRENCIES).filter(lambda c, cur=currency: c != cur))
            events.append(
                {
                    "kind": kind,
                    "sell": currency,
                    "sell_amount": signed(draw, currency, -1),
                    "buy": other,
                    "buy_amount": signed(draw, other, 1),
                }
            )
        elif kind == "DEPOSIT":
            events.append({"kind": kind, "currency": currency, "amount": signed(draw, currency, 1)})
        elif kind in {"PAYOUT_MAPPED", "PAYOUT_UNMAPPED", "FEE"}:
            events.append(
                {"kind": kind, "currency": currency, "amount": signed(draw, currency, -1)}
            )
        elif kind == "DRIFT":
            events.append({"kind": kind, "currency": currency, "amount": nonzero(draw, currency)})
        else:
            events.append({"kind": kind, "currency": currency, "amount": Decimal(0)})
    return opening, events


def client_for(state) -> AirwallexClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/authentication/login"):
            return httpx.Response(
                200, json={"token": "fixture-token", "expires_at": "2099-01-01T00:00:00Z"}
            )
        if request.url.path.endswith("/balances/current"):
            return httpx.Response(
                200,
                json=[
                    {
                        "currency": currency,
                        "available_amount": to_money_string(amount, currency),
                        "account_type": "cash",
                        "total_amount": to_money_string(amount, currency),
                        "pending_amount": to_money_string(Decimal(0), currency),
                        "reserved_amount": to_money_string(Decimal(0), currency),
                        "prepayment_amount": to_money_string(Decimal(0), currency),
                    }
                    for currency, amount in sorted(state["balances"].items())
                ],
            )
        assert request.url.path.endswith("/financial_transactions"), request.url.path
        return httpx.Response(200, json={"has_more": False, "items": state["rows"]})

    return AirwallexClient("fixture-id", "fixture-key", transport=httpx.MockTransport(handler))


def financial_row(identifier, currency, net, source_type, source_id):
    return {
        "id": identifier,
        "currency": currency,
        "net": to_money_string(net, currency),
        "source_id": source_id,
        "source_type": source_type,
        "transaction_type": source_type,
        "status": "SETTLED",
    }


def map_attempt(conn, source_id: str, attempt_no: int) -> None:
    now = operators.utcnow().isoformat()
    conn.execute(
        "INSERT INTO transfer_attempt(id,obligation_id,attempt_no,request_id,transfer_id,"
        "created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
        (f"attempt-{source_id}", "o", attempt_no, f"request-{source_id}", source_id, now, now),
    )


def latest_tie_outs(conn, count: int):
    return conn.execute("SELECT * FROM tie_out ORDER BY rowid DESC LIMIT ?", (count,)).fetchall()


def expected_state(residual: Decimal, unmapped: bool) -> str:
    return "RESIDUAL_0.00" if not unmapped and residual == 0 else "RESIDUAL_UNEXPLAINED"


@given(scenarios())
@settings(
    max_examples=60,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_generated_sequence_always_ties_out_to_observed_cash(scenario):
    opening, events = scenario
    directory = Path(tempfile.mkdtemp(prefix="wiretight-tie-out-"))
    database = db.Database(directory / f"tie-out-{uuid4()}.sqlite")
    try:
        conn = database.connection()
        now = operators.utcnow().isoformat()
        conn.execute(
            "INSERT INTO vendor(id,legal_name_norm,display_name,category,created_at) "
            "VALUES('v','supplier','Supplier','goods',?)",
            (now,),
        )
        conn.execute(
            "INSERT INTO obligation(id,vendor_id,invoice_no_norm,amount,currency,due_date,"
            "state,requester_set,created_at,updated_at) "
            "VALUES('o','v','inv','1.00','USD','2030-01-01','OPEN','[]',?,?)",
            (now, now),
        )
        state = {"balances": dict(opening), "rows": []}
        client = client_for(state)
        try:
            run = reconciliation.open_run(conn, client)
            observed = {currency: Decimal(0) for currency in CURRENCIES}
            unmapped = False
            attempts = 0
            for index, event in enumerate(events):
                kind = event["kind"]
                before = conn.execute("SELECT COUNT(*) FROM journal_line").fetchone()[0]
                if kind == "FX":
                    for currency, amount, source_type in (
                        (event["sell"], event["sell_amount"], "CONVERSION"),
                        (event["buy"], event["buy_amount"], "CONVERSION"),
                    ):
                        source = f"fx-{index}-{currency}"
                        state["rows"].append(
                            financial_row(source, currency, amount, source_type, source)
                        )
                        state["balances"][currency] += amount
                        observed[currency] += amount
                elif kind == "DEPOSIT":
                    source = f"deposit-{index}"
                    state["rows"].append(
                        financial_row(source, event["currency"], event["amount"], "DEPOSIT", source)
                    )
                    state["balances"][event["currency"]] += event["amount"]
                    observed[event["currency"]] += event["amount"]
                elif kind in {"PAYOUT_MAPPED", "PAYOUT_UNMAPPED", "FEE"}:
                    source = f"payout-{index}"
                    source_type = "FEE" if kind == "FEE" else "PAYOUT"
                    state["rows"].append(
                        financial_row(
                            source, event["currency"], event["amount"], source_type, source
                        )
                    )
                    state["balances"][event["currency"]] += event["amount"]
                    observed[event["currency"]] += event["amount"]
                    if kind == "PAYOUT_MAPPED":
                        attempts += 1
                        map_attempt(conn, source, attempts)
                    elif kind == "PAYOUT_UNMAPPED":
                        unmapped = True
                elif kind == "DRIFT":
                    # Cash moved without a financial row: the residual must show it.
                    state["balances"][event["currency"]] += event["amount"]
                # RETRY / APPROVAL / REJECTION change no provider observation.

                residual = {
                    currency: state["balances"][currency] - (opening[currency] + observed[currency])
                    for currency in CURRENCIES
                }
                clean = reconciliation.reconcile(conn, client, run)
                if kind in {"RETRY", "APPROVAL", "REJECTION"}:
                    after = conn.execute("SELECT COUNT(*) FROM journal_line").fetchone()[0]
                    assert after == before, "no-op event posted journal legs"
                assert clean is (not unmapped and all(value == 0 for value in residual.values()))

                ledger.assert_ledger_balances(conn)
                wallet = ledger.account_prefix_totals(conn, "Wallet:")
                provider = ledger.account_prefix_totals(conn, "Provider:")
                for currency in CURRENCIES:
                    assert wallet.get(currency, Decimal(0)) == observed[currency]
                    assert provider.get(currency, Decimal(0)) == -observed[currency]

                tie_outs = latest_tie_outs(conn, len(CURRENCIES))
                assert len(tie_outs) == len(CURRENCIES)
                for row in tie_outs:
                    currency = row["currency"]
                    assert Decimal(row["b_open"]) == opening[currency]
                    expected_close = opening[currency] + observed[currency]
                    assert Decimal(row["b_close_computed"]) == expected_close
                    assert Decimal(row["b_actual"]) == state["balances"][currency]
                    assert Decimal(row["residual"]) == residual[currency]
                    assert row["state"] == expected_state(residual[currency], unmapped)
        finally:
            client.close()
    finally:
        database.close()
        shutil.rmtree(directory, ignore_errors=True)
