"""A mocked AirwallexClient that returns documented-shape responses.

This module never opens a socket and never needs a key. Every response carries
``mock_label`` = "mocked API response" so any surface that renders it can show
the label. Status names and field names follow the public payout documentation
(transfer statuses include REJECTED, PROCESSING, PAID, WITHDRAWN, CANCELLED;
a payout can still fail after PAID), but the data is scripted.
"""

from __future__ import annotations

from typing import Any, Final

from app.core import statemachine

#: The label every mocked response carries.
MOCK_LABEL: Final[str] = "mocked API response"

#: Scripted outcome for the recovery story: the replacement payout succeeds.
#: A later poll reports PAID, still provisional per the transfer-status docs.
_REPLACEMENT_STATUS: Final[str] = "PAID"


def _now_iso(seq: int) -> str:
    """Deterministic fake timestamps so the recording is reproducible."""
    return f"2026-11-12T09:{seq:02d}:00+05:30"


class MockAirwallexClient:
    """Returns documented-shape sandbox responses from a script, not a socket."""

    def __init__(self) -> None:
        self.transfers: dict[str, dict[str, Any]] = {}
        self._seq = 0

    def _next_id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}_demo_{self._seq:04d}"

    def create_transfer(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Documented shape: POST /v1/pa/transfers.

        Creation always reports ``PROCESSING``, as the documented status flow
        starts. A transfer scripted to fail delivers ``FAILED`` through the
        poll, not at creation, the same way a real one would.
        """
        transfer_id = self._next_id("trf")
        response: dict[str, Any] = {
            "id": transfer_id,
            "transfer_status": "PROCESSING",
            "source_currency": payload.get("source_currency", "USD"),
            "source_amount": payload.get("source_amount"),
            "target_currency": payload.get("target_currency"),
            "target_amount": payload.get("target_amount"),
            "payment_method": "LOCAL",
            "created_at": _now_iso(self._seq),
            "updated_at": _now_iso(self._seq),
            "mock_label": MOCK_LABEL,
        }
        if payload.get("_scripted_failure") == "ACCOUNT_CLOSED":
            self.transfers[transfer_id] = {
                "_scripted_failure": "ACCOUNT_CLOSED",
                "failure_reason": "The beneficiary account is closed.",
            }
            self.transfers[transfer_id].update(response)
        else:
            self.transfers[transfer_id] = dict(response)
        return response

    def poll_transfer(self, transfer_id: str, observed_status: str) -> dict[str, Any]:
        """Documented shape: GET /v1/pa/transfers/{id}, driven by the script.

        Runs the observed status through the real state machine so the demo
        shows the same transition rules the production code enforces. A
        scripted failure arrives on the ``FAILED`` poll.
        """
        current = self.transfers.get(transfer_id, {})
        scripted = current.get("_scripted_failure")
        observed_failure = scripted if observed_status == "FAILED" and scripted else None
        current_status = current.get("transfer_status")
        if statemachine.is_regression(current_status, observed_status):
            raise ValueError(f"mocked poll regression: {current_status} -> {observed_status}")
        next_status = statemachine.transfer_next_awx(current_status, observed_status)
        updated: dict[str, Any] = dict(current)
        updated["transfer_status"] = next_status if next_status else observed_status
        updated["failure_type"] = observed_failure
        if observed_failure:
            updated["failure_reason"] = "The beneficiary account is closed."
        updated["updated_at"] = _now_iso(self._seq + 1)
        updated["mock_label"] = MOCK_LABEL
        self.transfers[transfer_id] = updated
        return updated

    def create_conversion(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Documented shape: POST /v1/fx/conversions (a booked quote)."""
        conversion_id = self._next_id("conv")
        return {
            "id": conversion_id,
            "conversion_status": "BOOKED",
            "buy_currency": payload.get("buy_currency"),
            "sell_currency": payload.get("sell_currency"),
            "buy_amount": payload.get("buy_amount"),
            "sell_amount": payload.get("sell_amount"),
            "created_at": _now_iso(self._seq),
            "mock_label": MOCK_LABEL,
        }

    def withdraw_conversion(self, conversion_id: str) -> dict[str, Any]:
        """Documented shape: POST /v1/fx/conversions/{id}/withdraw."""
        return {
            "id": conversion_id,
            "conversion_status": "WITHDRAWN",
            "mock_label": MOCK_LABEL,
        }

    def list_balances(self) -> list[dict[str, Any]]:
        """Documented shape: GET /v1/balances (synthetic amounts)."""
        return [
            {"currency": "USD", "available_amount": 21340.0, "mock_label": MOCK_LABEL},
            {"currency": "EUR", "available_amount": 11480.0, "mock_label": MOCK_LABEL},
            {"currency": "GBP", "available_amount": 6210.0, "mock_label": MOCK_LABEL},
        ]
