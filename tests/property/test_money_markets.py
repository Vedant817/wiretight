"""Generated arithmetic/minor-unit laws; these are not new supported payout corridors."""

import ast
import re
from decimal import Decimal
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.core import ledger
from app.money import (
    Money,
    ceil_money,
    exponent_for,
    floor_money,
    parse_money,
    raise_on_float,
    to_money_string,
)

MARKETS = {"JPY": 0, "KRW": 0, "KWD": 3, "BHD": 3, "USD": 2, "EUR": 2, "GBP": 2}
CURRENCIES = st.sampled_from(tuple(MARKETS))
AMOUNTS = st.integers(-(10**12), 10**12).map(lambda n: Decimal(n).scaleb(-6))


@given(CURRENCIES, AMOUNTS)
def test_wire_round_trip_and_exact_minor_units(currency, amount):
    wire = to_money_string(amount, currency)
    exponent = MARKETS[currency]
    pattern = r"-?[0-9]+" + (rf"\.[0-9]{{{exponent}}}" if exponent else "")
    assert re.fullmatch(pattern, wire)
    assert isinstance(parse_money(wire), Decimal)
    assert to_money_string(parse_money(wire), currency) == wire
    assert Decimal(wire).scaleb(exponent) == Decimal(wire).scaleb(exponent).to_integral_value()
    assert not (Decimal(wire) == 0 and wire.startswith("-"))
    assert str(Money(wire, currency)) == wire


@given(CURRENCIES, AMOUNTS)
def test_directional_rounding_encloses_exact_amount(currency, amount):
    quantum = Decimal(1).scaleb(-MARKETS[currency])
    below, above = floor_money(amount, currency), ceil_money(amount, currency)
    assert below <= amount <= above
    assert amount - below < quantum and above - amount < quantum


@given(CURRENCIES, st.integers(0, 10**8), st.integers(1, 10**6))
def test_fx_funding_rounds_up_and_capped_sale_rounds_down(currency, units, rate_units):
    exact = Decimal(units).scaleb(-MARKETS[currency]) / Decimal(rate_units).scaleb(-4)
    assert ceil_money(exact, currency) >= exact
    assert floor_money(exact, currency) <= exact


@given(CURRENCIES, st.integers(-(10**8), 10**8))
def test_half_even_ties_do_not_systematically_round_up(currency, units):
    quantum = Decimal(1).scaleb(-MARKETS[currency])
    exact = (Decimal(units) + Decimal("0.5")) * quantum
    expected_units = units if units % 2 == 0 else units + 1
    assert parse_money(to_money_string(exact, currency)) == Decimal(expected_units) * quantum


@given(st.floats(allow_nan=True, allow_infinity=True))
def test_float_rejected_at_parse_and_nested_payload_boundary(value):
    with pytest.raises(TypeError):
        parse_money(value)
    with pytest.raises(TypeError):
        raise_on_float({"items": [{"amount": value}]})


@pytest.mark.parametrize("bad", ["1_000.00", "\u0661\u0662.00", ".5", "1.", "1e2", "+1.00"])
def test_non_wire_decimal_spellings_are_refused(bad):
    with pytest.raises(ValueError):
        parse_money(bad)


@given(CURRENCIES, st.integers(1, 10**6))
def test_ledger_refuses_sub_minor_unit_amounts(currency, units):
    amount = format(
        Decimal(units).scaleb(-MARKETS[currency]) + Decimal(1).scaleb(-MARKETS[currency] - 1), "f"
    )
    with pytest.raises(ValueError):
        ledger.Leg("Wallet:" + currency, currency, debit=amount)


def test_monetary_arithmetic_source_has_no_float_literals_or_conversions():
    root = Path(__file__).resolve().parents[2]
    paths = [
        "app/money.py",
        "app/core/ledger.py",
        "app/core/packets.py",
        "app/core/counters.py",
        "app/core/reconciliation.py",
        "app/workers/executor.py",
        "app/workers/fx.py",
    ]
    for relative in paths:
        tree = ast.parse((root / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            assert not (isinstance(node, ast.Constant) and isinstance(node.value, float)), relative
            assert not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "float"
            ), relative


@given(st.sampled_from(["ZZZ", "QQQ", "BTC"]))
def test_unknown_currency_cannot_be_serialized_as_money(currency):
    with pytest.raises(ValueError):
        to_money_string(Decimal("1"), currency)


@settings(max_examples=40)
@given(CURRENCIES, st.integers(0, 10**8))
def test_known_exponents_are_explicit(currency, units):
    assert exponent_for(currency) == MARKETS[currency]
    assert parse_money(to_money_string(Decimal(units), currency)) == Decimal(units)
