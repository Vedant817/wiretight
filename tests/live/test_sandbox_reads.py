"""Read-only live sandbox acceptance for FX rates, balances, transfers, and financial transactions.

No money moves, no approvals, no cooling-off. Only read legs are exercised.
"""

import os
from datetime import UTC, datetime

import pytest

from app.config import WorkerSettings
from app.integrations.airwallex import AirwallexClient
from app.money import parse_money

# Capture settings before the root offline fixture clears inherited credentials.
# Secret values are never displayed or used as test parameter ids.
_SETTINGS = WorkerSettings()
_CONFIRMED = os.environ.get("CONFIRM_LIVE") == "1"


@pytest.mark.live
def test_sandbox_fx_rate_balances_transfers_and_financial_reads():
    """Prove the real AirwallexClient can read FX rates, balances, transfers, and financials."""
    if not _CONFIRMED:
        pytest.skip("Read-only sandbox test requires CONFIRM_LIVE=1")
    if not _SETTINGS.has_credentials():
        pytest.skip("AWX_CLIENT_ID and AWX_API_KEY are not configured")

    client = AirwallexClient(_SETTINGS.awx_client_id, _SETTINGS.awx_api_key)
    try:
        # Leg 1: FX rates (GBP/USD)
        rates = client.get_rates(buy_currency="GBP", sell_currency="USD")
        assert rates.get("buy_currency") == "GBP"
        assert rates.get("sell_currency") == "USD"
        assert "rate_details" in rates
        client_level = [r for r in rates["rate_details"] if r.get("level") == "CLIENT"]
        assert len(client_level) == 1
        rate = client_level[0]
        assert "buy_amount" in rate
        assert "sell_amount" in rate
        buy_amount = parse_money(str(rate["buy_amount"]))
        sell_amount = parse_money(str(rate["sell_amount"]))
        assert buy_amount > 0
        assert sell_amount > 0
        assert buy_amount / sell_amount > 0

        # Leg 2: Balances
        balances = client.get_balances()
        assert len(balances) >= 1
        for b in balances:
            assert b.currency
            assert b.available_amount is not None

        # Leg 3: Transfers (list)
        now = datetime.now(UTC).isoformat()
        transfers = client.list_transfers(start="1970-01-01T00:00:00+00:00")
        assert isinstance(transfers, list)

        # Leg 4: Financial transactions
        financial = client.financial_transactions(
            start="1970-01-01T00:00:00+00:00",
            end=now,
        )
        assert isinstance(financial, list)

    finally:
        client.close()
