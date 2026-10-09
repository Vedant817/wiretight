"""Money: Decimal everywhere, serialised as strings at the currency exponent.

FINAL.md §7.3: "Money: Decimal everywhere, serialised as strings at the currency
exponent. A float anywhere in a request or packet raises."

That last sentence is the whole point of this module. A float cannot represent
0.1, so a float in a payment packet is not a rounding nuisance, it is a value
that differs from what the signatory saw. These tests exist to make that
impossible rather than merely discouraged.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import pytest

from app.money import (
    CURRENCY_EXPONENT,
    Money,
    exponent_for,
    parse_money,
    quantize_money,
    raise_on_float,
    to_money_string,
)


class TestExponents:
    """ISO 4217 exponents come from the spec, never guessed from the amount."""

    @pytest.mark.parametrize(
        ("currency", "expected"),
        [
            ("USD", 2),
            ("EUR", 2),
            ("GBP", 2),
            ("JPY", 0),
            ("KWD", 3),
            ("BHD", 3),
        ],
    )
    def test_known_exponents(self, currency: str, expected: int) -> None:
        assert exponent_for(currency) == expected

    def test_unknown_currency_defaults_to_two_not_zero(self) -> None:
        """Fail toward the cautious exponent.

        An unknown currency defaulting to 0 would silently drop cents from an
        amount someone signed off on. Two extra places are visible; zero places
        is not.
        """
        assert exponent_for("ZZZ") == 2

    def test_currency_is_upper_cased_and_trimmed(self) -> None:
        assert exponent_for("  usd ") == 2

    def test_exponent_table_has_no_zero_default_gap(self) -> None:
        """Every configured currency must be a 3-letter uppercase code."""
        for code, exponent in CURRENCY_EXPONENT.items():
            assert len(code) == 3
            assert code.isupper()
            assert exponent in (0, 2, 3)


class TestParseMoney:
    def test_parses_a_decimal_string(self) -> None:
        assert parse_money("7500.00") == Decimal("7500.00")

    def test_parses_an_int_string_without_float_contamination(self) -> None:
        """`Decimal("7500")` is exact; `Decimal(7500.0)` would already be a float."""
        result = parse_money("7500")
        assert result == Decimal("7500")
        assert isinstance(result, Decimal)

    def test_rejects_a_python_float(self) -> None:
        with pytest.raises(TypeError, match="float"):
            parse_money(7500.00)  # type: ignore[arg-type]

    def test_rejects_a_python_int(self) -> None:
        """Ints are safe but unbounded; the wire format is always a string."""
        with pytest.raises(TypeError, match="str"):
            parse_money(7500)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "bad", ["", "abc", "1,000.00", "1 000.00", "$100", "1.2.3", "NaN", "Infinity"]
    )
    def test_rejects_malformed_strings(self, bad: str) -> None:
        with pytest.raises(ValueError):
            parse_money(bad)

    def test_rejects_nan_and_infinity_decimal_forms(self) -> None:
        """A NaN amount would poison every sum it touches, silently."""
        for bad in ("NaN", "sNaN", "Infinity", "-Infinity"):
            with pytest.raises(ValueError):
                parse_money(bad)

    def test_allows_negative_amounts(self) -> None:
        """Refunds and reversals are negative. Rejecting them would be wrong."""
        assert parse_money("-12.50") == Decimal("-12.50")

    def test_rejects_embedded_whitespace(self) -> None:
        with pytest.raises(ValueError):
            parse_money(" 100.00")


class TestQuantize:
    def test_quantizes_to_two_places_bankers_round_half_even(self) -> None:
        """ROUND_HALF_EVEN is the accounting default and avoids systematic drift."""
        assert quantize_money(Decimal("1.005"), "USD") == Decimal("1.00")
        assert quantize_money(Decimal("1.015"), "USD") == Decimal("1.02")

    def test_quantizes_to_zero_places_for_jpy(self) -> None:
        assert quantize_money(Decimal("100.4"), "JPY") == Decimal("100")
        assert quantize_money(Decimal("100.5"), "JPY") == Decimal("100")

    def test_quantizes_to_three_places_for_kwd(self) -> None:
        assert quantize_money(Decimal("1.2345"), "KWD") == Decimal("1.234")

    def test_floor_rounds_down_for_tranche_one(self) -> None:
        """Tranche 1 is the cap rounded DOWN, so the cap is never exceeded."""
        from app.money import floor_money

        assert floor_money(Decimal("2499.999"), "USD") == Decimal("2499.99")

    def test_ceiling_rounds_up_for_fx_aggregation(self) -> None:
        """Conversion per currency rounds UP, so the wallet is never short."""
        from app.money import ceil_money

        assert ceil_money(Decimal("7499.001"), "USD") == Decimal("7499.01")


class TestToMoneyString:
    @pytest.mark.parametrize(
        ("amount", "currency", "expected"),
        [
            ("7500", "USD", "7500.00"),
            ("7500.5", "USD", "7500.50"),
            ("7500", "JPY", "7500"),
            ("1.2345", "KWD", "1.234"),
            ("-12.5", "EUR", "-12.50"),
            ("0", "GBP", "0.00"),
        ],
    )
    def test_serialises_at_the_currency_exponent(
        self, amount: str, currency: str, expected: str
    ) -> None:
        assert to_money_string(Decimal(amount), currency) == expected

    def test_output_is_always_a_str_never_a_float(self) -> None:
        value = to_money_string(Decimal("0.10"), "USD")
        assert isinstance(value, str)
        assert value == "0.10"

    def test_negative_zero_is_normalised(self) -> None:
        """`-0.00` in a packet hash would differ from `0.00` and void a sign-off."""
        assert to_money_string(Decimal("-0.001"), "USD") == "0.00"


class TestRaiseOnFloat:
    """The guard that makes 'a float anywhere raises' true rather than aspirational."""

    def test_rejects_a_float_value(self) -> None:
        with pytest.raises(TypeError, match="float"):
            raise_on_float(0.1, "packet.amount")

    def test_rejects_a_float_hidden_in_a_dict(self) -> None:
        with pytest.raises(TypeError, match="totals_by_currency"):
            raise_on_float({"totals_by_currency": {"EUR": 7500.0}}, "packet")

    def test_rejects_a_float_hidden_in_a_list_of_dicts(self) -> None:
        payload = {"items": [{"transfer_amount": "7500.00"}, {"fee": 0.0}]}
        with pytest.raises(TypeError, match="fee"):
            raise_on_float(payload, "packet")

    def test_accepts_decimal_strings_and_ints(self) -> None:
        raise_on_float({"a": "1.00", "b": 3, "c": Decimal("2.5"), "d": None, "e": True}, "packet")

    def test_reports_the_full_path_to_the_float(self) -> None:
        with pytest.raises(TypeError, match=r"items\.0\.amount"):
            raise_on_float({"items": [{"amount": 1.5}]}, "packet")

    def test_recurses_into_nested_lists(self) -> None:
        with pytest.raises(TypeError):
            raise_on_float([[[1.0]]], "packet")


class TestMoney:
    def test_arithmetic_stays_exact(self) -> None:
        a = Money("0.10", "USD")
        b = Money("0.20", "USD")
        assert (a + b).amount == Decimal("0.30")

    def test_the_classic_float_error_does_not_occur(self) -> None:
        """0.1 + 0.2 == 0.3 in Decimal. In float it does not."""
        total = sum((Money("0.10", "USD") for _ in range(3)), Money("0", "USD"))
        assert total.amount == Decimal("0.30")

    def test_refuses_to_add_different_currencies(self) -> None:
        with pytest.raises(ValueError, match="cannot add"):
            _ = Money("1.00", "USD") + Money("1.00", "EUR")

    def test_refuses_to_subtract_different_currencies(self) -> None:
        with pytest.raises(ValueError, match="cannot subtract"):
            _ = Money("1.00", "USD") - Money("1.00", "EUR")

    def test_refuses_to_construct_from_a_float(self) -> None:
        with pytest.raises(TypeError, match="float"):
            Money(1.5, "USD")  # type: ignore[arg-type]

    def test_refuses_a_non_iso_currency_code(self) -> None:
        with pytest.raises(InvalidOperation):
            Money("1.00", "DOLLARS")

    def test_a_currency_of_the_wrong_length_is_refused(self) -> None:
        with pytest.raises(InvalidOperation):
            Money("1.00", "US")  # type: ignore[arg-type]

    def test_str_is_the_canonical_wire_form(self) -> None:
        assert str(Money("7500", "USD")) == "7500.00"

    def test_equality_compares_value_and_currency(self) -> None:
        assert Money("1.00", "USD") == Money("1.00", "USD")
        assert Money("1.00", "USD") != Money("1.00", "EUR")
        # "1.000" normalises to 1.00 on construction, so the two compare equal. That is
        # the point: the canonical form is the exponent, not what was typed.
        assert Money("1.00", "USD") == Money("1.000", "USD")

    def test_ordering_is_allowed_within_one_currency(self) -> None:
        assert Money("1.00", "USD") < Money("2.00", "USD")

    def test_hashable_for_use_as_a_dict_key(self) -> None:
        ledger = {Money("1.00", "USD"): "payout"}
        assert ledger[Money("1.00", "USD")] == "payout"

    def test_zero_and_negative_round_trip(self) -> None:
        assert Money("0", "USD").amount == Decimal("0.00")
        assert Money("-5", "USD").amount == Decimal("-5.00")

    def test_scientific_notation_is_refused(self) -> None:
        """`Decimal` accepts "1E+2"; the wire format never does."""
        with pytest.raises(ValueError):
            Money("1E+2", "USD")
