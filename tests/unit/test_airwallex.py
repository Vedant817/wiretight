"""Synthetic HTTP fault vectors, not recorded provider-contract evidence."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.integrations.airwallex import AirwallexClient, ProviderError, TransferRequest


def login_response() -> dict[str, str]:
    return {
        "token": "test-token",
        "expires_at": (datetime.now(UTC) + timedelta(minutes=30)).isoformat(),
    }


def client_for(handler):
    return AirwallexClient(
        "test-id", "test-key", transport=httpx.MockTransport(handler), sleep=lambda _: None
    )


def test_refresh_only_expired_token():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path.endswith("login"):
            return httpx.Response(201, json=login_response())
        if len(calls) == 2:
            return httpx.Response(401, json={"code": "credentials_expired"})
        return httpx.Response(200, json=[])

    client = client_for(handler)
    assert client.get_balances() == []
    assert len(calls) == 4
    client.close()


@pytest.mark.parametrize("status", [429, 500, 502, 503])
def test_transient_read_backoff(status):
    calls = []
    waits = []

    def handler(request):
        if request.url.path.endswith("login"):
            return httpx.Response(201, json=login_response())
        calls.append(request)
        return httpx.Response(status if len(calls) < 4 else 200, json=[])

    client = AirwallexClient(
        "id", "key", transport=httpx.MockTransport(handler), sleep=waits.append
    )
    assert client.get_balances() == []
    assert len(calls) == 4 and len(waits) == 3
    assert waits[0] < waits[1] < waits[2]
    client.close()


@pytest.mark.parametrize(
    "status,code", [(400, "validation_error"), (401, "credentials_invalid"), (403, "forbidden")]
)
def test_definitive_errors_never_retry(status, code):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"code": code, "message": "secret-bank-details"})

    client = client_for(handler)
    with pytest.raises(ProviderError) as error:
        client.get_balances()
    assert len(calls) == 1
    assert "secret-bank-details" not in str(error.value)
    client.close()


def test_timeout_is_ambiguous_and_not_retried():
    posts = []

    def handler(request):
        if request.url.path.endswith("login"):
            return httpx.Response(201, json=login_response())
        posts.append(request)
        raise httpx.ReadTimeout("potentially contains sensitive url")

    client = client_for(handler)
    with pytest.raises(ProviderError, match="ambiguous"):
        client.request("POST", "/transfers/create", payload={"request_id": "durable"})
    assert len(posts) == 1
    client.close()


def test_mutation_server_error_requires_lookup_before_retry():
    bodies = []

    def handler(request):
        if request.url.path.endswith("login"):
            return httpx.Response(201, json=login_response())
        bodies.append(request.content)
        return httpx.Response(503, json={})

    client = client_for(handler)
    with pytest.raises(ProviderError, match="ambiguous"):
        client.request(
            "POST",
            "/transfers/create",
            payload={"request_id": "durable", "transfer_amount": "1.00"},
        )
    assert len(bodies) == 1
    client.close()


def test_unkeyed_beneficiary_not_retried():
    posts = []

    def handler(request):
        if request.url.path.endswith("login"):
            return httpx.Response(201, json=login_response())
        posts.append(request)
        return httpx.Response(503, json={})

    client = client_for(handler)
    with pytest.raises(ProviderError, match="ambiguous"):
        client.create_beneficiary({"nickname": "unique-persisted-name"})
    assert len(posts) == 1
    client.close()


def test_lookup_paginates_and_matches_exact_request():
    pages = []

    def handler(request):
        if request.url.path.endswith("login"):
            return httpx.Response(201, json=login_response())
        page = request.url.params["page_num"]
        pages.append(page)
        return httpx.Response(
            200,
            json={
                "has_more": page == "0",
                "items": [
                    {
                        "id": "provider-id",
                        "status": "SENT",
                        "request_id": "other" if page == "0" else "wanted",
                    }
                ],
            },
        )

    client = client_for(handler)
    result = client.find_transfer("wanted", from_created_at="2026-11-01T00:00:00Z")
    assert result and result.request_id == "wanted"
    assert pages == ["0", "1"]
    client.close()


def test_missing_credentials_fail_before_socket():
    with pytest.raises(ProviderError, match="setup_missing_credentials"):
        AirwallexClient("", "")


def test_invalid_amount_and_request_id():
    with pytest.raises(ValueError):
        TransferRequest(
            request_id="",
            beneficiary_id="b",
            transfer_amount="nan",
            transfer_currency="USD",
            source_currency="USD",
            transfer_method="LOCAL",
            reason="goods_purchased",
            reference="Invoice 1",
        )


def test_api_version_omitted_on_fx_and_secrets_masked():
    seen = []

    def handler(request):
        seen.append(request)
        return (
            httpx.Response(201, json=login_response())
            if request.url.path.endswith("login")
            else httpx.Response(200, json={})
        )

    client = AirwallexClient(
        "id", "key", api_version="2025-06-30", transport=httpx.MockTransport(handler)
    )
    client.request("GET", "/fx/rates/current")
    client.request("GET", "/balances/current")
    assert "x-api-version" not in seen[1].headers
    assert seen[2].headers["x-api-version"] == "2025-06-30"
    assert "test-token" not in repr(client._token)
    client.close()


def test_real_validation_ack_and_exact_decimal_rate_basis():
    from decimal import Decimal

    def handler(request):
        if request.url.path.endswith("login"):
            return httpx.Response(201, json=login_response())
        if request.url.path.endswith("validate"):
            return httpx.Response(200, text="OK")
        return httpx.Response(
            200,
            content=b'{"buy_currency":"USD","sell_currency":"EUR",'
            b'"rate":7632,"rate_details":[{"level":"CLIENT","buy_amount":10000.10,"sell_amount":9000.01}]}',
        )

    client = client_for(handler)
    assert client.validate_beneficiary({"beneficiary": {}}) is True
    assert client.usd_rates({"USD", "EUR"})["EUR"] == Decimal("10000.10") / Decimal("9000.01")
    client.close()
