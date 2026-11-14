"""Actual provider-client/SQLite boundary; all transport responses are test-only."""

# ruff: noqa: F811
import httpx
import pytest

from app.core import reconciliation
from app.integrations.airwallex import AirwallexClient
from tests.unit.test_operators_signing import domain  # noqa: F401


@pytest.fixture
def finance(domain):
    database, _ = domain
    state = {"balance": "100.00", "rows": []}

    def handler(request):
        assert not database.connection().in_transaction
        if request.url.path.endswith("/authentication/login"):
            return httpx.Response(
                200, json={"token": "fixture-token", "expires_at": "2099-01-01T00:00:00Z"}
            )
        if request.url.path.endswith("/balances/current"):
            return httpx.Response(
                200,
                json=[
                    {
                        "currency": "USD",
                        "account_type": "cash",
                        "available_amount": state["balance"],
                        "total_amount": state["balance"],
                        "pending_amount": "0.00",
                        "reserved_amount": "0.00",
                        "prepayment_amount": "0.00",
                    }
                ],
            )
        assert request.url.path.endswith("/financial_transactions")
        return httpx.Response(200, json={"has_more": False, "items": state["rows"]})

    client = AirwallexClient("fixture-id", "fixture-key", transport=httpx.MockTransport(handler))
    try:
        yield database.connection(), client, state
    finally:
        client.close()


def movement(identifier="transaction", net="10.00", kind="DEPOSIT", source="external"):
    return {
        "id": identifier,
        "currency": "USD",
        "net": net,
        "source_id": source,
        "source_type": kind,
        "transaction_type": kind,
        "status": "SETTLED",
    }


def test_reconciliation_posts_missing_actual_movements_once_and_detects_deleted_ledger(finance):
    conn, client, state = finance
    run = reconciliation.open_run(conn, client)
    state["rows"] = [movement()]
    state["balance"] = "110.00"
    assert reconciliation.reconcile(conn, client, run)
    assert reconciliation.reconcile(conn, client, run)
    assert conn.execute("SELECT COUNT(*) FROM journal_line").fetchone()[0] == 2
    conn.execute("DELETE FROM journal_line")
    with pytest.raises(reconciliation.ReconciliationError, match="journal legs"):
        reconciliation.reconcile(conn, client, run)


def test_actual_cash_mismatch_is_unexplained_even_when_journal_balances(finance):
    conn, client, state = finance
    run = reconciliation.open_run(conn, client)
    state["rows"] = [movement()]
    state["balance"] = "111.00"
    assert not reconciliation.reconcile(conn, client, run)
    row = conn.execute("SELECT * FROM tie_out").fetchone()
    assert row["residual"] == "1.00" and row["state"] == "RESIDUAL_UNEXPLAINED"


def test_unmapped_provider_payout_is_not_falsely_cleared_by_zero_residual(finance):
    conn, client, state = finance
    run = reconciliation.open_run(conn, client)
    state["rows"] = [movement(net="-10.00", kind="PAYOUT")]
    state["balance"] = "90.00"
    assert not reconciliation.reconcile(conn, client, run)
    assert conn.execute("SELECT residual FROM tie_out").fetchone()[0] == "0.00"
    assert conn.execute("SELECT state FROM tie_out").fetchone()[0] == "RESIDUAL_UNEXPLAINED"


def test_missing_financial_history_and_changed_settled_row_fail_closed(finance):
    conn, client, state = finance
    state["rows"] = [movement("baseline")]
    run = reconciliation.open_run(conn, client)
    state["rows"] = []
    with pytest.raises(reconciliation.ReconciliationError, match="history is missing"):
        reconciliation.reconcile(conn, client, run)
    state["rows"] = [movement("baseline"), movement("new")]
    state["balance"] = "110.00"
    assert reconciliation.reconcile(conn, client, run)
    state["rows"][1]["net"] = "11.00"
    with pytest.raises(reconciliation.ReconciliationError, match="changed"):
        reconciliation.reconcile(conn, client, run)
