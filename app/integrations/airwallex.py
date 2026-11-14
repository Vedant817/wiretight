"""Real sandbox HTTP boundary. No simulation or fixture loading in this module.

Mutation timeouts are ambiguous, never definitive rejection. The durable caller
must preserve its request_id and resolve it using provider list endpoints.
"""

from __future__ import annotations

import json
import random
import threading
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from email.utils import parsedate_to_datetime
from typing import Any, Literal
from urllib.parse import quote

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.config import SANDBOX_BASE_URL
from app.integrations.rate_budget import RateBudget
from app.money import raise_on_float


def _invalid_json_number(_value: str) -> None:
    raise ValueError("Non-finite provider number")


class ProviderError(RuntimeError):
    """Sanitized error: never includes response bodies, tokens or account data."""

    def __init__(self, category: str, *, status: int | None = None) -> None:
        self.category = category
        self.status = status
        super().__init__(f"Airwallex {category}" + (f" (HTTP {status})" if status else ""))


class ProviderModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class Token(ProviderModel):
    token: SecretStr
    expires_at: datetime


class Balance(ProviderModel):
    currency: str
    available_amount: Decimal


class Transfer(ProviderModel):
    id: str
    status: str
    request_id: str


class Conversion(ProviderModel):
    conversion_id: str
    status: str
    request_id: str


class Quote(ProviderModel):
    quote_id: str
    client_rate: Decimal
    valid_to_at: datetime


class TransferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    request_id: str = Field(min_length=1, max_length=50)
    beneficiary_id: str = Field(min_length=1, max_length=128)
    transfer_amount: str = Field(pattern=r"^[0-9]+(?:\.[0-9]+)?$")
    transfer_currency: str = Field(pattern=r"^[A-Z]{3}$")
    source_currency: str = Field(pattern=r"^[A-Z]{3}$")
    transfer_method: Literal["LOCAL", "SWIFT"]
    reason: str = Field(min_length=1, max_length=64)
    reference: str = Field(pattern=r"^[A-Za-z0-9 ./-]{1,35}$")
    swift_charge_option: Literal["PAYER"] | None = None
    fee_paid_by: Literal["PAYER"] | None = None


class AirwallexClient:
    """Serialized token cache and bounded requests, exact sandbox host only.

    Transport and sleeper injection are HTTP-boundary test seams. Redirects and
    environment proxies are disabled. Network timeouts are not blindly retried.
    """

    def __init__(
        self,
        client_id: str,
        api_key: str,
        *,
        timeout: float = 20,
        api_version: str = "",
        login_as: str = "",
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if not client_id or not api_key:
            raise ProviderError("setup_missing_credentials")
        if timeout <= 0 or timeout > 120:
            raise ValueError("HTTP timeout must be between 0 and 120 seconds")
        self._client_id = SecretStr(client_id)
        self._api_key = SecretStr(api_key)
        self._api_version = api_version
        self._login_as = login_as
        self._sleep = sleep
        self._budget = RateBudget(sleep=sleep)
        self._now = now
        self._token: Token | None = None
        self.clock_skew_s: float | None = None
        self._lock = threading.RLock()
        self._http = httpx.Client(
            base_url=SANDBOX_BASE_URL + "/api/v1/",
            timeout=timeout,
            trust_env=False,
            follow_redirects=False,
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def _send(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str],
        payload: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        retry_safe: bool = True,
    ) -> httpx.Response:
        if not path.startswith("/") or ".." in path or "?" in path:
            raise ValueError("invalid endpoint path")
        if payload is not None:
            raise_on_float(payload)
        for attempt in range(4):
            self._budget.acquire(path)
            try:
                response = self._http.request(
                    method,
                    path.lstrip("/"),
                    headers=headers,
                    json=payload,
                    params=params,
                )
            except httpx.TransportError:
                raise ProviderError("ambiguous" if method == "POST" else "unavailable") from None
            if response.headers.get("Date"):
                try:
                    self.clock_skew_s = (
                        parsedate_to_datetime(response.headers["Date"]) - self._now()
                    ).total_seconds()
                except (ValueError, TypeError):
                    self.clock_skew_s = None
            if response.status_code != 429 and response.status_code < 500:
                return response
            # A 5xx can follow a committed mutation. Resolve through a GET
            # before any future POST; request-id rejection is not a replay.
            if method == "POST" and path != "/authentication/login" and response.status_code >= 500:
                return response
            if attempt == 3 or not retry_safe:
                return response
            # Never let a malicious Retry-After suspend the worker indefinitely.
            delay = min(8.0, 0.25 * 2**attempt + random.uniform(0, 0.25))
            retry_after = response.headers.get("Retry-After", "")
            if retry_after.isdigit():
                delay = min(30.0, max(delay, float(retry_after)))
            self._sleep(delay)
        raise AssertionError("unreachable")

    @staticmethod
    def _decode(response: httpx.Response) -> Any:
        if not 200 <= response.status_code < 300:
            try:
                code = response.json().get("code", "")
            except (ValueError, AttributeError):
                code = ""
            if not isinstance(code, str):
                code = ""
            # Only known error names are allowed to escape this boundary.
            category = {
                "credentials_expired": "credentials_expired",
                "credentials_invalid": "credentials_invalid",
                "duplicate_request_id": "duplicate_request_id",
                "balance_insufficient": "insufficient_balance",
                "insufficient_funds": "insufficient_balance",
            }.get(code, "rejected")
            if response.status_code == 429:
                category = "rate_limited"
            elif response.status_code >= 500:
                category = "unavailable"
            raise ProviderError(category, status=response.status_code)
        try:
            if response.text == "OK":
                return "OK"
            return json.loads(
                response.content, parse_float=Decimal, parse_constant=_invalid_json_number
            )
        except ValueError:
            raise ProviderError("invalid_response") from None

    def _login(self) -> None:
        headers = {
            "x-client-id": self._client_id.get_secret_value(),
            "x-api-key": self._api_key.get_secret_value(),
        }
        if self._login_as:
            headers["x-login-as"] = self._login_as
        try:
            self._token = Token.model_validate(
                self._decode(
                    self._send(
                        "POST",
                        "/authentication/login",
                        headers=headers,
                    )
                )
            )
            if self._token.expires_at.tzinfo is None:
                raise ValueError("missing timezone")
        except ValueError:
            self._token = None
            raise ProviderError("invalid_auth_response") from None

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> Any:
        # Single shared token; never log request/response headers or bodies.
        with self._lock:
            if self._token is None or self._token.expires_at <= self._now() + timedelta(minutes=5):
                self._login()
            for refreshed in (False, True):
                assert self._token is not None
                headers = {"Authorization": "Bearer " + self._token.token.get_secret_value()}
                if self._api_version and not path.startswith("/fx/"):
                    headers["x-api-version"] = self._api_version
                response = self._send(
                    method,
                    path,
                    headers=headers,
                    payload=payload,
                    params=params,
                    retry_safe=method == "GET" or bool(payload and payload.get("request_id")),
                )
                try:
                    return self._decode(response)
                except ProviderError as exc:
                    if exc.category == "credentials_expired" and not refreshed:
                        self._login()
                        continue
                    if method == "POST" and response.status_code >= 500:
                        raise ProviderError("ambiguous", status=response.status_code) from None
                    raise
        raise AssertionError("unreachable")

    def list_items(self, path: str, **filters: str) -> Iterator[dict[str, Any]]:
        for page in range(10000):
            data = self.request(
                "GET", path, params={**filters, "page_num": str(page), "page_size": "100"}
            )
            if not isinstance(data, dict) or not isinstance(data.get("items"), list):
                raise ProviderError("invalid_page")
            yield from data["items"]
            has_more = data.get("has_more")
            if has_more is False:
                return
            if has_more is None:
                # Key absent: stop if fewer than a full page, else continue.
                if len(data["items"]) < 100:
                    return
                continue
            if has_more is True:
                if not data["items"]:
                    raise ProviderError("invalid_pagination")
                continue
            # Any other type (string, int, etc.) is invalid.
            raise ProviderError("invalid_pagination")
        raise ProviderError("pagination_limit")

    def get_balances(self) -> list[Balance]:
        return [Balance.model_validate(row) for row in self.request("GET", "/balances/current")]

    def global_accounts(self) -> list[dict[str, Any]]:
        return list(self.list_items("/global_accounts"))

    def balance_history(self, *, currency: str, start: str, end: str) -> list[dict[str, Any]]:
        return list(
            self.list_items(
                "/balances/history",
                currency=currency,
                from_post_at=start,
                to_post_at=end,
            )
        )

    def get_rates(self, *, buy_currency: str, sell_currency: str) -> dict[str, Any]:
        return dict(
            self.request(
                "GET",
                "/fx/rates/current",
                params={
                    "buy_currency": buy_currency,
                    "sell_currency": sell_currency,
                },
            )
        )

    def find_beneficiary(self, nickname: str) -> dict[str, Any] | None:
        rows = [
            row
            for row in self.list_items("/beneficiaries", nick_name=nickname)
            if row.get("nickname") == nickname
        ]
        if len(rows) > 1:
            raise ProviderError("multiple_nickname_matches")
        return rows[0] if rows else None

    def find_conversion(
        self, request_id: str, *, from_created_at: str | None = None
    ) -> Conversion | None:
        filters = {"request_id": request_id}
        if from_created_at:
            filters.update(from_created_at=from_created_at, to_created_at=self._now().isoformat())
        rows = [
            row
            for row in self.list_items("/fx/conversions", **filters)
            if row.get("request_id") == request_id
        ]
        if len(rows) > 1:
            raise ProviderError("multiple_request_matches")
        return Conversion.model_validate(rows[0]) if rows else None

    def get_transfer(self, transfer_id: str) -> Transfer:
        return Transfer.model_validate(
            self.request("GET", "/transfers/" + quote(transfer_id, safe=""))
        )

    def beneficiary(self, beneficiary_id: str) -> dict[str, Any]:
        return dict(self.request("GET", "/beneficiaries/" + quote(beneficiary_id, safe="")))

    def beneficiary_schema(self, payload: dict[str, Any]) -> dict[str, Any]:
        return dict(self.request("POST", "/beneficiary_api_schemas/generate", payload=payload))

    def validate_beneficiary(self, payload: dict[str, Any]) -> bool:
        result = self.request("POST", "/beneficiaries/validate", payload=payload)
        if result != "OK":
            raise ProviderError("invalid_validation_response")
        return True

    def create_beneficiary(self, payload: dict[str, Any]) -> dict[str, Any]:
        # This endpoint has no documented idempotency contract. Never retry it.
        if not payload.get("nickname"):
            raise ValueError("a durable unique nickname is required")
        return dict(self.request("POST", "/beneficiaries/create", payload=payload))

    def create_quote(self, payload: dict[str, Any]) -> Quote:
        return Quote.model_validate(self.request("POST", "/fx/quotes/create", payload=payload))

    def get_quote(self, quote_id: str) -> Quote:
        return Quote.model_validate(self.request("GET", "/fx/quotes/" + quote(quote_id, safe="")))

    def create_conversion(self, payload: dict[str, Any]) -> Conversion:
        if not payload.get("request_id") or len(payload["request_id"]) > 64:
            raise ValueError("conversion requires a durable request_id of at most 64 characters")
        return Conversion.model_validate(
            self.request("POST", "/fx/conversions/create", payload=payload)
        )

    def create_transfer(self, payload: TransferRequest) -> Transfer:
        if Decimal(payload.transfer_amount) <= 0:
            raise ValueError("transfer amount must be positive")
        return Transfer.model_validate(
            self.request(
                "POST",
                "/transfers/create",
                payload=payload.model_dump(exclude_none=True),
            )
        )

    def find_transfer(self, request_id: str, *, from_created_at: str) -> Transfer | None:
        rows = [
            row
            for row in self.list_items(
                "/transfers",
                request_id=request_id,
                from_created_at=from_created_at,
            )
            if row.get("request_id") == request_id
        ]
        if len(rows) > 1:
            raise ProviderError("multiple_request_matches")
        return Transfer.model_validate(rows[0]) if rows else None

    def financial_transactions(self, *, start: str, end: str) -> list[dict[str, Any]]:
        return list(
            self.list_items("/financial_transactions", from_created_at=start, to_created_at=end)
        )

    def list_transfers(self, *, start: str) -> list[dict[str, Any]]:
        return list(self.list_items("/transfers", from_created_at=start))

    def list_rfis(self) -> list[dict[str, Any]]:
        return list(self.list_items("/rfis", types="TRANSACTION", statuses="ACTION_REQUIRED"))

    def usd_rates(self, currencies: set[str]) -> dict[str, Decimal]:
        rates = {"USD": Decimal(1)}
        for currency in currencies - {"USD"}:
            data = self.get_rates(buy_currency="USD", sell_currency=currency)
            if data.get("buy_currency") != "USD" or data.get("sell_currency") != currency:
                raise ProviderError("invalid_rate_currencies")
            levels = [row for row in data.get("rate_details", []) if row.get("level") == "CLIENT"]
            if len(levels) != 1:
                raise ProviderError("missing_client_rate_basis")
            bought, sold = (
                Decimal(str(levels[0]["buy_amount"])),
                Decimal(str(levels[0]["sell_amount"])),
            )
            if not bought.is_finite() or not sold.is_finite() or min(bought, sold) <= 0:
                raise ProviderError("invalid_rate_amounts")
            rates[currency] = bought / sold
        return rates

    def usd_risk_rates(self, currencies: set[str]) -> dict[str, Decimal]:
        """Risk basis: worse of current CLIENT amounts and last booked USD pair."""
        rates = self.usd_rates(currencies)
        latest: dict[str, tuple[datetime, Decimal]] = {}
        for row in self.list_items(
            "/fx/conversions",
            from_created_at="1970-01-01T00:00:00+00:00",
            to_created_at=self._now().isoformat(),
        ):
            if row.get("status") != "SETTLED":
                continue
            buy, sell = row.get("buy_currency"), row.get("sell_currency")
            if "USD" not in {buy, sell} or buy == sell:
                continue
            currency = sell if buy == "USD" else buy
            if currency not in currencies:
                continue
            try:
                bought, sold = Decimal(str(row["buy_amount"])), Decimal(str(row["sell_amount"]))
                created = datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00"))
                if (
                    not bought.is_finite()
                    or not sold.is_finite()
                    or min(bought, sold) <= 0
                    or created.tzinfo is None
                ):
                    raise ValueError("invalid booked amounts")
                basis = bought / sold if buy == "USD" else sold / bought
            except (KeyError, ValueError, ArithmeticError):
                raise ProviderError("invalid_booked_rate_basis") from None
            if currency not in latest or created > latest[currency][0]:
                latest[currency] = created, basis
        for currency, (_, basis) in latest.items():
            rates[currency] = max(rates[currency], basis)
        return rates
