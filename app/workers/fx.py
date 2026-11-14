"""Human-approved locked-quote funding, with lookup-only uncertain recovery.

Only USD funding of an approved GBP/EUR payment shortfall is supported. General
speculative FX and arbitrary amounts are not exposed by this executor.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import ROUND_UP, Decimal
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID, uuid4, uuid5
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from app.core import audit, db, signing
from app.core.operators import utcnow
from app.core.process_lock import exclusive_process
from app.core.runtime_policy import load_runtime_policy
from app.integrations.airwallex import Conversion, ProviderError, Quote

if TYPE_CHECKING:
    from app.workers.executor import Executor


class FXBlockedError(RuntimeError):
    pass


class ConversionPacket(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    kind: Literal["CONVERSION"] = "CONVERSION"
    packet_version: Literal[1] = 1
    tier: Literal["T2"] = "T2"
    required_approvers: Literal[2] = 2
    created_at: str
    expires_at: str
    run_id: str
    payment_packet_id: str
    payment_sha256: str
    funded_items: list[str] = Field(min_length=1, max_length=1)
    policy_sha256: str
    request_id: str
    quote_id: str
    quote_expires_at: str
    quote_sha256: str
    buy_currency: Literal["GBP", "EUR"]
    sell_currency: Literal["USD"] = "USD"
    buy_amount: str = Field(pattern=r"^[0-9]+\.[0-9]{2}$")
    fee_reservation_usd: str
    native_reserve_floor: str
    maximum_sell_amount: str = Field(pattern=r"^[0-9]+\.[0-9]{2}$")
    locked_cost_per_unit: str
    drift_bp: int = Field(ge=0, le=25)
    safety_margin_seconds: int = Field(ge=120)
    conversion_date: str


def _client_cost(data: dict[str, Any]) -> tuple[Decimal, Decimal]:
    levels = [row for row in data.get("rate_details", []) if row.get("level") == "CLIENT"]
    if len(levels) != 1:
        raise FXBlockedError("A unique actual CLIENT quote/rate amount pair is required")
    buy, sell = (Decimal(str(levels[0][key])) for key in ("buy_amount", "sell_amount"))
    if not buy.is_finite() or not sell.is_finite() or min(buy, sell) <= 0:
        raise FXBlockedError("Invalid CLIENT amounts")
    return buy, sell


def _shortfall(
    payment: Any, balances: dict[str, Decimal], rates: dict[str, Decimal], policy: Any
) -> Decimal:
    item = payment.items[0]
    fee = Decimal(policy.policy["rails"]["fee_reservation_usd"][item.rail])
    floor = Decimal(policy.policy["reserve_floor"].get(item.source_currency, "0.00"))
    target = Decimal(item.transfer_amount) + fee / rates[item.source_currency] + floor
    return (target - balances.get(item.source_currency, Decimal(0))).quantize(
        Decimal("0.01"), rounding=ROUND_UP
    )


def _quote_terms(quote: Quote) -> dict[str, Any]:
    value = quote.model_dump()
    if value.get("application_fees") or value.get("application_fee_options"):
        raise FXBlockedError("Quotes with application fees require a separate approval design")
    buy, sell = _client_cost(value)
    if buy != Decimal(str(value.get("buy_amount"))) or sell != Decimal(
        str(value.get("sell_amount"))
    ):
        raise FXBlockedError("Quote top-level and CLIENT amounts disagree")
    # Economic equality must not depend on JSON spelling (104 vs 104.00).
    # Provider reference-rate metadata is not part of the locked CLIENT price.
    return {
        **{
            key: value[key]
            for key in (
                "quote_id",
                "buy_currency",
                "sell_currency",
                "conversion_date",
                "valid_to_at",
            )
        },
        "buy_amount": format(buy.normalize(), "f"),
        "sell_amount": format(sell.normalize(), "f"),
        "client_rate": format(quote.client_rate.normalize(), "f"),
        "rate_details": [
            {
                "level": "CLIENT",
                "buy_amount": format(buy.normalize(), "f"),
                "sell_amount": format(sell.normalize(), "f"),
            }
        ],
    }


def _budget(
    executor: Executor,
    conn: db.Connection,
    terms: ConversionPacket,
    rates: dict[str, Decimal],
    transfers: list[dict[str, Any]],
    limits: dict[str, Any],
) -> None:
    day = (
        utcnow()
        .astimezone(ZoneInfo(limits["per_day"]["calendar_tz"]))
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .astimezone(UTC)
    )
    observed = executor.client.list_items(
        "/fx/conversions", from_created_at=day.isoformat(), to_created_at=utcnow().isoformat()
    )
    amounts: dict[str, Decimal] = {}
    for value in observed:
        rate = rates.get(value["sell_currency"])
        amount = Decimal(str(value["sell_amount"]))
        if rate is None or not amount.is_finite() or amount <= 0:
            raise FXBlockedError("Provider conversion risk basis is unavailable")
        amounts[value["request_id"]] = amount * rate
    for row in conn.execute(
        "SELECT id FROM execution_intent WHERE kind='CONVERSION' "
        "AND state<>'REJECTED' AND created_at>=?",
        (day.isoformat(),),
    ).fetchall():
        intent = executor._intent(conn, row["id"])
        packet = ConversionPacket.model_validate_json(
            conn.execute(
                "SELECT canonical_json FROM approval_packet WHERE id=?", (intent["packet_id"],)
            ).fetchone()[0]
        )
        amounts.setdefault(intent["request_id"], Decimal(packet.maximum_sell_amount))
    payouts = Decimal(0)
    for value in transfers:
        created = datetime.fromisoformat(value["created_at"].replace("Z", "+00:00"))
        if created >= day:
            payouts += Decimal(str(value["transfer_amount"])) * rates[value["transfer_currency"]]
    # Unknown ownership is charged conservatively to every potential signer.
    ceiling = min(Decimal(limits["per_day"]["all_usd"]), Decimal(limits["per_approver_day_usd"]))
    if sum(amounts.values(), Decimal(0)) + payouts + Decimal(terms.maximum_sell_amount) > ceiling:
        raise FXBlockedError("Combined conversion/payment daily cap would be exceeded")


def prepare(executor: Executor, payment_packet_id: str) -> str:
    with exclusive_process(executor.lock_file):
        conn = executor.database.connection()
        executor._trust(conn)
        signing.packet(conn, payment_packet_id)
        live = executor._live(conn)
        payment, _ = executor._guard(conn, payment_packet_id, live, funding=True)
        item = payment.items[0]
        if item.source_currency not in {"GBP", "EUR"}:
            raise FXBlockedError("Only USD-funded GBP/EUR payment shortfalls are supported")
        policy = load_runtime_policy(conn, executor.policy_path, executor.passkeys)
        need = _shortfall(payment, live.balances, live.rates, policy)
        if need <= 0:
            raise FXBlockedError("Native payment balance is already sufficient")
        quote = executor.client.create_quote(
            {
                "buy_currency": item.source_currency,
                "sell_currency": "USD",
                "buy_amount": format(need, ".2f"),
                "validity": "HR_4",
            }
        )
        value = _quote_terms(quote)
        if value["buy_currency"] != item.source_currency or value["sell_currency"] != "USD":
            raise FXBlockedError("Quote currency direction differs from requested funding")
        buy, sell = _client_cost(value)
        if buy != need:
            raise FXBlockedError("Provider quote amount differs from the required shortfall")
        policy = load_runtime_policy(conn, executor.policy_path, executor.passkeys)
        margin = policy.policy["fx"]["quote_safety_margin_seconds"]
        expires = min(
            quote.valid_to_at - timedelta(seconds=margin),
            datetime.fromisoformat(payment.expires_at),
        )
        if expires <= utcnow():
            raise FXBlockedError("Quote expired or lacks the required safety margin")
        namespace = conn.execute(
            "SELECT value FROM schema_meta WHERE key='request_namespace'"
        ).fetchone()[0]
        terms = ConversionPacket(
            created_at=utcnow().isoformat(),
            expires_at=expires.isoformat(),
            run_id=payment.run_id,
            payment_packet_id=payment_packet_id,
            payment_sha256=hashlib.sha256(
                audit.canonical_json(payment.model_dump()).encode()
            ).hexdigest(),
            funded_items=[item.obligation_id + ":" + str(item.tranche_no)],
            policy_sha256=policy.sha256,
            request_id=str(
                uuid5(UUID(namespace), "conversion:" + payment_packet_id + ":" + quote.quote_id)
            ),
            quote_id=quote.quote_id,
            quote_expires_at=quote.valid_to_at.isoformat(),
            quote_sha256=hashlib.sha256(audit.canonical_json(value).encode()).hexdigest(),
            buy_currency=item.source_currency,
            buy_amount=format(need, ".2f"),
            fee_reservation_usd=policy.policy["rails"]["fee_reservation_usd"][item.rail],
            native_reserve_floor=policy.policy["reserve_floor"].get(item.source_currency, "0.00"),
            maximum_sell_amount=format(sell.quantize(Decimal("0.01"), rounding=ROUND_UP), ".2f"),
            locked_cost_per_unit=str(sell / buy),
            drift_bp=policy.policy["fx"]["drift_bp"],
            safety_margin_seconds=margin,
            conversion_date=str(value["conversion_date"]),
        )
        identifier = str(uuid4())
        raw = audit.canonical_json(terms.model_dump())
        digest = hashlib.sha256(raw.encode()).hexdigest()
        with db.transaction(conn):
            if conn.execute(
                "SELECT 1 FROM execution_intent e JOIN approval_packet p ON p.id=e.packet_id "
                "WHERE e.kind='CONVERSION' AND e.state<>'REJECTED' "
                "AND json_extract(p.canonical_json,'$.payment_packet_id')=?",
                (payment_packet_id,),
            ).fetchone():
                raise FXBlockedError("An existing conversion must be resolved before new funding")
            conn.execute(
                "UPDATE approval_packet SET state='VOID' WHERE kind='CONVERSION' "
                "AND state IN ('OPEN','APPROVED') "
                "AND json_extract(canonical_json,'$.payment_packet_id')=?",
                (payment_packet_id,),
            )
            conn.execute(
                "INSERT INTO approval_packet(id,kind,canonical_json,sha256,tier,required_approvers,"
                "created_at,expires_at,state) VALUES(?,'CONVERSION',?,?,'T2',2,?,?,'OPEN')",
                (identifier, raw, digest, terms.created_at, terms.expires_at),
            )
            audit.append(conn, "approval.created", {"packet_id": identifier, "sha256": digest})
        return identifier


def _accept(
    executor: Executor, conn: db.Connection, intent: db.sqlite3.Row, result: Conversion
) -> str:
    payload = json.loads(intent["canonical_payload"])
    terms = ConversionPacket.model_validate_json(
        conn.execute(
            "SELECT canonical_json FROM approval_packet WHERE id=?", (intent["packet_id"],)
        ).fetchone()[0]
    )
    value = result.model_dump()
    if any(
        value.get(key) != payload[key]
        for key in ("request_id", "quote_id", "buy_currency", "sell_currency")
    ):
        raise FXBlockedError("Provider conversion terms differ from the audited intent")
    if (
        Decimal(str(value.get("buy_amount"))) != Decimal(terms.buy_amount)
        or Decimal(str(value.get("sell_amount"))) > Decimal(terms.maximum_sell_amount)
        or result.status not in {"SCHEDULED", "OVERDUE", "CANCELLED", "SETTLED"}
    ):
        raise FXBlockedError("Provider conversion amount or status is invalid")
    with db.transaction(conn):
        executor._result(conn, intent["id"], "SUBMITTED", provider_id=result.conversion_id)
        conn.execute(
            "INSERT INTO conversion(id,request_id,conversion_id,quote_id,buy_currency,"
            "sell_currency,"
            "buy_amount,status,raw_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(request_id) DO UPDATE SET status=excluded.status,"
            "raw_json=excluded.raw_json,"
            "updated_at=excluded.updated_at",
            (
                str(uuid4()),
                result.request_id,
                result.conversion_id,
                terms.quote_id,
                terms.buy_currency,
                terms.sell_currency,
                terms.buy_amount,
                result.status,
                executor.vault.encrypt_json(value),
                intent["created_at"],
                utcnow().isoformat(),
            ),
        )
    audit.write_checkpoint(
        conn, executor.seal_dir, executor.key, reason="conversion-result-" + intent["id"]
    )
    return result.status


def recover(executor: Executor, conn: db.Connection, intent: db.sqlite3.Row) -> str:
    found = executor.client.find_conversion(
        intent["request_id"], from_created_at=intent["created_at"]
    )
    if found:
        return _accept(executor, conn, intent, found)
    executor._result(conn, intent["id"], "AMBIGUOUS", error="conversion_not_found")
    return "AMBIGUOUS"


def execute(executor: Executor, packet_id: str) -> str:
    with exclusive_process(executor.lock_file):
        conn = executor.database.connection()
        existing = conn.execute(
            "SELECT id FROM execution_intent WHERE packet_id=? AND kind='CONVERSION'", (packet_id,)
        ).fetchone()
        executor._trust(conn, roster=not bool(existing))
        if existing:
            intent = executor._intent(conn, existing["id"])
            if intent["state"] == "REJECTED":
                return "REJECTED"
            return recover(executor, conn, intent)
        row = signing.packet(conn, packet_id)
        executor.passkeys.verify_stored(conn, packet_id)
        terms = ConversionPacket.model_validate_json(row["canonical_json"])
        if datetime.fromisoformat(terms.expires_at) <= utcnow():
            raise FXBlockedError("Conversion approval expired; obtain a fresh quote and re-approve")
        live = executor._live(conn)
        signing.packet(conn, terms.payment_packet_id)
        payment, _ = executor._guard(conn, terms.payment_packet_id, live, funding=True)
        item = payment.items[0]
        if (
            terms.run_id != payment.run_id
            or terms.funded_items != [item.obligation_id + ":" + str(item.tranche_no)]
            or terms.buy_currency != item.source_currency
        ):
            raise FXBlockedError("Funded obligation or currency differs from the approved payment")
        if (
            hashlib.sha256(audit.canonical_json(payment.model_dump()).encode()).hexdigest()
            != terms.payment_sha256
        ):
            raise FXBlockedError("Funded payment changed; fresh quote and re-approval required")
        policy = load_runtime_policy(conn, executor.policy_path, executor.passkeys)
        if terms.policy_sha256 != policy.sha256:
            raise FXBlockedError("Signed conversion policy changed")
        if (
            terms.drift_bp > policy.policy["fx"]["drift_bp"]
            or terms.safety_margin_seconds < policy.policy["fx"]["quote_safety_margin_seconds"]
        ):
            raise FXBlockedError("Signed conversion tolerances exceed current policy")
        quote = executor.client.get_quote(terms.quote_id)
        if quote.valid_to_at <= utcnow() + timedelta(seconds=terms.safety_margin_seconds):
            raise FXBlockedError("Quote expired; obtain a fresh quote and re-approve")
        if (
            hashlib.sha256(audit.canonical_json(_quote_terms(quote)).encode()).hexdigest()
            != terms.quote_sha256
        ):
            raise FXBlockedError("Locked quote rate or amount changed; re-approval required")
        current_buy, current_sell = _client_cost(
            executor.client.get_rates(
                buy_currency=terms.buy_currency, sell_currency=terms.sell_currency
            )
        )
        drift = abs((current_sell / current_buy) / Decimal(terms.locked_cost_per_unit) - 1) * 10000
        if drift > terms.drift_bp:
            raise FXBlockedError("Market rate drift exceeds the signed tolerance")
        need = _shortfall(payment, live.balances, live.rates, policy)
        if need != Decimal(terms.buy_amount):
            raise FXBlockedError("Funding amount changed; obtain a fresh quote and re-approve")
        maximum = Decimal(terms.maximum_sell_amount)
        quoted = _quote_terms(quote)
        quoted_buy, quoted_sell = _client_cost(quoted)
        if (
            quoted_buy != Decimal(terms.buy_amount)
            or quoted_sell > maximum
            or quoted["buy_currency"] != terms.buy_currency
            or quoted["sell_currency"] != terms.sell_currency
            or str(quoted["conversion_date"]) != terms.conversion_date
        ):
            raise FXBlockedError("Quote amounts or direction differ from approved conversion")
        if live.balances.get("USD", Decimal(0)) - maximum < Decimal(
            policy.policy["reserve_floor"]["USD"]
        ):
            raise FXBlockedError("USD funding would breach the reserve floor")
        _budget(executor, conn, terms, live.rates, live.transfers, policy.policy["limits"])
        payload = {
            key: getattr(terms, key)
            for key in (
                "request_id",
                "quote_id",
                "buy_currency",
                "sell_currency",
                "buy_amount",
                "conversion_date",
            )
        }
        # Quote check is deliberately repeated immediately before consumption;
        # intervening network reads cannot extend a quote's execution window.
        if datetime.fromisoformat(terms.quote_expires_at) <= utcnow() + timedelta(
            seconds=terms.safety_margin_seconds
        ):
            raise FXBlockedError("Quote expired before execution; fresh approval required")
        with db.transaction(conn):
            signing.packet(conn, terms.payment_packet_id)
            executor._guard(conn, terms.payment_packet_id, live, funding=True)
            executor.passkeys.verify_stored(conn, packet_id)
            executor.passkeys.verify_stored(conn, terms.payment_packet_id)
            if conn.execute(
                "SELECT 1 FROM execution_intent e JOIN approval_packet p ON p.id=e.packet_id "
                "WHERE e.kind='CONVERSION' AND e.state<>'REJECTED' "
                "AND json_extract(p.canonical_json,'$.payment_packet_id')=?",
                (terms.payment_packet_id,),
            ).fetchone():
                raise FXBlockedError("Payment funding was already claimed")
            identifier = str(uuid4())
            raw = audit.canonical_json(payload)
            digest = hashlib.sha256(raw.encode()).hexdigest()
            seq = audit.log_intent(
                conn,
                "execution.intent",
                {
                    "intent_id": identifier,
                    "packet_id": packet_id,
                    "kind": "CONVERSION",
                    "request_id": terms.request_id,
                    "payload_sha256": digest,
                    "packet_sha256": row["sha256"],
                },
            )
            conn.execute(
                "INSERT INTO approval_consumption VALUES(?,?,?)",
                (packet_id, utcnow().isoformat(), seq),
            )
            conn.execute("UPDATE approval_packet SET state='CONSUMED' WHERE id=?", (packet_id,))
            conn.execute(
                "INSERT INTO execution_intent(id,packet_id,kind,request_id,canonical_payload,"
                "payload_sha256,state,created_at,updated_at) "
                "VALUES(?,?,'CONVERSION',?,?,?,'PREPARED',?,?)",
                (
                    identifier,
                    packet_id,
                    terms.request_id,
                    raw,
                    digest,
                    utcnow().isoformat(),
                    utcnow().isoformat(),
                ),
            )
        audit.write_checkpoint(
            conn, executor.seal_dir, executor.key, reason="conversion-intent-" + identifier
        )
        intent = executor._intent(conn, identifier)
        if datetime.fromisoformat(terms.quote_expires_at) <= utcnow() + timedelta(
            seconds=terms.safety_margin_seconds
        ):
            executor._result(conn, identifier, "REJECTED", error="quote_expired_before_post")
            return "REJECTED"
        try:
            return _accept(executor, conn, intent, executor.client.create_conversion(payload))
        except ProviderError as exc:
            if exc.category in {"ambiguous", "duplicate_request_id", "unavailable"}:
                found = executor.client.find_conversion(
                    terms.request_id, from_created_at=intent["created_at"]
                )
                if found:
                    return _accept(executor, conn, intent, found)
                executor._result(conn, identifier, "AMBIGUOUS", error=exc.category)
                return "AMBIGUOUS"
            executor._result(conn, identifier, "REJECTED", error=exc.category)
            return "REJECTED"
