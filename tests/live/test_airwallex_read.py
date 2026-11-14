"""Read-only live acceptance. No account provisioning or simulated funding."""

import os

import pytest

from app.config import WorkerSettings
from app.integrations.airwallex import AirwallexClient

# Capture settings before the root offline fixture clears inherited credentials.
# Secret values are never displayed or used as test parameter ids.
_SETTINGS = WorkerSettings()
_CONFIRMED = os.environ.get("CONFIRM_LIVE") == "1"


@pytest.mark.live
def test_sandbox_auth_and_balances():
    if not _CONFIRMED:
        pytest.skip("Read-only sandbox test requires CONFIRM_LIVE=1")
    if not _SETTINGS.has_credentials():
        pytest.skip("AWX_CLIENT_ID and AWX_API_KEY are not configured")
    client = AirwallexClient(_SETTINGS.awx_client_id, _SETTINGS.awx_api_key)
    try:
        client.get_balances()
    finally:
        client.close()
