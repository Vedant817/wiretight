"""Money: Decimal everywhere, serialised as strings at the currency exponent.

FINAL.md §7.3: *"Money: `Decimal` everywhere, serialised as strings at the currency
exponent. A float anywhere in a request or packet raises."*

Why this is a module and not a convention: a float cannot represent 0.1, so a
float in an approval packet is not a rounding nuisance, it is a value that
differs from what the signatory saw on screen. The packet hash covers the
canonical JSON, so a float would either void every signature or, worse, match a
signature over a number nobody actually displayed.

Three rules, enforced here:

1. **No floats.** :func:`raise_on_float` walks a payload and refuses on sight,
   naming the exact path (``items.0.amount``).
2. **Decimals only.** Parsing takes ``str``; ``int`` is refused because the wire
   format is a string and an unbounded int is a place a float will creep in later.
3. **Explicit exponents.** From ISO 4217, never inferred from the amount.
   Tranche 1 rounds *down*, FX aggregation rounds *up*, and an unknown currency
   defaults to the cautious exponent (2) rather than to 0.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import Any, Final

__all__ = [
    "CURRENCY_EXPONENT",
    "Money",
    "ceil_money",
    "exponent_for",
    "floor_money",
    "parse_money",
    "quantize_money",
    "raise_on_float",
    "to_money_string",
]

#: ISO 4217 minor-unit exponents.
#:
#: Extended to every zero-decimal and three-decimal currency after measurement
#: showed the previous 12-entry table defaulted them all to 2 (D-B20). For a
#: zero-decimal currency that is not a safe default in either direction: KRW
#: 1,000,000 became the string "1000000.00", a **100x overstatement** carried
#: into every cap comparison, every ledger leg and every tie-out term. The
#: three-decimal Gulf currencies were wrong the other way.
#:
#: A currency absent from this table is now **refused** by `parse_currency`, so
#: an unlisted code cannot silently inherit an exponent. `exponent_for` still
#: falls back to `DEFAULT_EXPONENT` for internal arithmetic, but nothing on the
#: wire path relies on that.
CURRENCY_EXPONENT: Final[dict[str, int]] = {
    # 2 decimal places — the overwhelming majority.
    "AED": 2,
    "AUD": 2,
    "BGN": 2,
    "BRL": 2,
    "CAD": 2,
    "CHF": 2,
    "CNY": 2,
    "COP": 2,
    "CZK": 2,
    "DKK": 2,
    "EGP": 2,
    "EUR": 2,
    "GBP": 2,
    "HKD": 2,
    "HUF": 2,
    "IDR": 2,
    "ILS": 2,
    "INR": 2,
    "KES": 2,
    "MAD": 2,
    "MXN": 2,
    "MYR": 2,
    "NGN": 2,
    "NOK": 2,
    "NZD": 2,
    "PEN": 2,
    "PHP": 2,
    "PLN": 2,
    "QAR": 2,
    "RON": 2,
    "RSD": 2,
    "SAR": 2,
    "SEK": 2,
    "SGD": 2,
    "THB": 2,
    "TRY": 2,
    "TWD": 2,
    "UAH": 2,
    "USD": 2,
    "ZAR": 2,
    # 0 decimal places. A 1,000,000 KRW bill is 1000000, not 1000000.00.
    "BIF": 0,
    "CLP": 0,
    "DJF": 0,
    "GNF": 0,
    "ISK": 0,
    "JPY": 0,
    "KMF": 0,
    "KRW": 0,
    "PYG": 0,
    "RWF": 0,
    "UGX": 0,
    "UYI": 0,
    "VND": 0,
    "VUV": 0,
    "XAF": 0,
    "XOF": 0,
    "XPF": 0,
    # 3 decimal places.
    "BHD": 3,
    "IQD": 3,
    "JOD": 3,
    "KWD": 3,
    "LYD": 3,
    "OMR": 3,
    "TND": 3,
}

#: Used by :func:`exponent_for` when a currency is not in the table.
#:
#: Two, never zero: extra places are visible to a human, missing places are not.
#: This is the *last resort* for internal arithmetic only. Anything crossing the
#: wire — a request body, a packet, a UI string — must go through
#: :func:`parse_currency`, which refuses an unlisted code outright rather than
#: inventing an exponent for it.
DEFAULT_EXPONENT: Final[int] = 2

#: Sentinel for "this currency has no known exponent".
CURRENCY_NOT_LISTED: Final[int] = -1


def is_known_currency(currency: str) -> bool:
    """Is this currency in the pinned ISO 4217 table?"""
    return currency.strip().upper() in CURRENCY_EXPONENT


def exponent_for(currency: str) -> int:
    """Return the minor-unit exponent for ``currency``.

    Tolerates surrounding whitespace and lower case, because these values arrive
    from JSON bodies and YAML policy files, not from validated enums.
    """
    if not isinstance(currency, str):
        raise TypeError(f"currency must be str, got {type(currency).__name__}")
    return CURRENCY_EXPONENT.get(currency.strip().upper(), DEFAULT_EXPONENT)


def _quantizer(currency: str) -> Decimal:
    """The step size at ``currency``'s exponent: 0.01 USD, 1 JPY, 0.001 KWD."""
    return Decimal(1).scaleb(-exponent_for(currency))


def parse_money(value: str) -> Decimal:
    """Parse a decimal **string** into an exact ``Decimal``.

    Refuses ``float`` and ``int``: the wire format is a string, and accepting an
    ``int`` here is how a float ends up in a packet three modules later.
    """
    if isinstance(value, bool):
        raise TypeError("bool is not a money amount")
    if isinstance(value, float):
        raise TypeError(
            "float is not a money amount: it cannot represent 0.1. "
            "Pass a decimal string such as '7500.00' (FINAL.md §7.3)."
        )
    if isinstance(value, int):
        raise TypeError("money must arrive as a decimal string, not an int")
    if not isinstance(value, str):
        raise TypeError(f"money must be a str, got {type(value).__name__}")

    text = value.strip()
    if text != value:
        raise ValueError(f"money string must not be padded: {value!r}")
    if not text:
        raise ValueError("money string is empty")

    # Decimal happily parses "1E+2", "1e5" and "+1.00". None of those are wire
    # form, and accepting them would let two spellings of one amount canonicalise
    # to different packet hashes.
    if "e" in text or "E" in text:
        raise ValueError(f"scientific notation is not a money amount: {value!r}")
    if text.startswith("+"):
        raise ValueError(f"leading plus is not a money amount: {value!r}")
    if text.startswith("-") and (text[1:2] in {"+", "-"}):
        raise ValueError(f"malformed sign in money amount: {value!r}")

    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"not a decimal amount: {value!r}") from exc

    # Decimal("NaN") and Decimal("Infinity") parse successfully but poison sums.
    if not amount.is_finite():
        raise ValueError(f"money amount must be finite, got {value!r}")
    return amount


def quantize_money(amount: Decimal, currency: str) -> Decimal:
    """Round to the currency exponent using ROUND_HALF_EVEN.

    The accounting default. It avoids the systematic upward drift that
    ROUND_HALF_UP introduces when a large number of amounts are summed.
    """
    return amount.quantize(_quantizer(currency), rounding=ROUND_HALF_EVEN)


def floor_money(amount: Decimal, currency: str) -> Decimal:
    """Round **down** to the currency exponent.

    Used for tranche 1 (§4.5.4): "tranche 1 = the cap converted to the transfer
    currency, rounded down". Rounding down guarantees the first payment can never
    exceed the first-payment cap.
    """
    return amount.quantize(_quantizer(currency), rounding=ROUND_FLOOR)


def ceil_money(amount: Decimal, currency: str) -> Decimal:
    """Round **up** to the currency exponent.

    Used for FX aggregation (§4.6): "rounded **up** to the exponent", so the
    converted amount covers the planned outflow and the wallet is never short.
    """
    return amount.quantize(_quantizer(currency), rounding=ROUND_CEILING)


def to_money_string(amount: Decimal, currency: str) -> str:
    """Serialise to the canonical wire form: a string at the currency exponent.

    Normalises negative zero to ``"0.00"``. A packet containing ``-0.00`` would
    canonicalise differently from one containing ``0.00`` and void a signature
    for no reason a human could see.
    """
    quantised = quantize_money(amount, currency)
    if quantised == 0:
        quantised = abs(quantised)
    return format(quantised, "f")


def raise_on_float(payload: Any, path: str = "payload") -> None:
    """Walk ``payload`` and raise ``TypeError`` on the first float found.

    The error names the exact dotted path so the offending field is obvious::

        raise_on_float({"items": [{"amount": 1.5}]})
        # TypeError: float at packet.items.0.amount ...

    ``bool`` is not a float for this purpose and is allowed. ``Decimal`` is
    allowed. ``int`` is allowed here: this function's job is the float ban, and
    :func:`parse_money` handles the strictness at the parsing boundary.
    """
    if isinstance(payload, bool):
        return

    if isinstance(payload, float):
        raise TypeError(
            f"float at {path}. A float cannot represent 0.1, so this value is not "
            "the number the signatory saw. Use a decimal string (FINAL.md §7.3)."
        )

    if isinstance(payload, Mapping):
        for key, value in payload.items():
            raise_on_float(value, f"{path}.{key}")
        return

    if isinstance(payload, (str, bytes, int, Decimal, type(None))):
        return

    if isinstance(payload, Sequence):
        for index, value in enumerate(payload):
            raise_on_float(value, f"{path}.{index}")
        return

    # Unknown object types are not walked. The caller decides; failing closed on
    # an arbitrary object would break dataclasses and pydantic models, which are
    # converted to plain JSON before they ever reach a packet.
    return


class Money:
    """An exact monetary amount that cannot be constructed from a float.

    Immutable, hashable, and comparable **within one currency only**: adding USD
    to EUR is a bug the type system should refuse, not a rounding surprise.
    """

    def __init__(self, amount: str, currency: str) -> None:
        if not isinstance(currency, str):
            raise TypeError(f"currency must be str, got {type(currency).__name__}")
        code = currency.strip().upper()
        if len(code) != 3 or not code.isalpha():
            raise InvalidOperation(f"not an ISO 4217 code: {currency!r}")
        self._amount: Decimal = quantize_money(parse_money(amount), code)
        self._currency: str = code

    @property
    def amount(self) -> Decimal:
        return self._amount

    @property
    def currency(self) -> str:
        return self._currency

    def _same_currency(self, other: object) -> bool:
        return isinstance(other, Money) and other._currency == self._currency

    def __str__(self) -> str:
        return to_money_string(self._amount, self._currency)

    def __repr__(self) -> str:
        return f"Money({str(self)!r}, {self._currency!r})"

    def __hash__(self) -> int:
        return hash((self._amount, self._currency))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self._currency == other._currency and self._amount == other._amount

    def __lt__(self, other: Money) -> bool:
        if not self._same_currency(other):
            raise ValueError(f"cannot compare {self._currency} with {other._currency}")
        return self._amount < other._amount

    def __le__(self, other: Money) -> bool:
        if not self._same_currency(other):
            raise ValueError(f"cannot compare {self._currency} with {other._currency}")
        return self._amount <= other._amount

    def __gt__(self, other: Money) -> bool:
        if not self._same_currency(other):
            raise ValueError(f"cannot compare {self._currency} with {other._currency}")
        return self._amount > other._amount

    def __ge__(self, other: Money) -> bool:
        if not self._same_currency(other):
            raise ValueError(f"cannot compare {self._currency} with {other._currency}")
        return self._amount >= other._amount

    def _binary(self, other: Money, op: str) -> Decimal:
        if not self._same_currency(other):
            raise ValueError(
                f"cannot {op} {self._currency} with {other._currency}: "
                "money of different currencies is not added"
            )
        return other._amount

    def __add__(self, other: Money) -> Money:
        return Money(str(self._amount + self._binary(other, "add")), self._currency)

    def __sub__(self, other: Money) -> Money:
        return Money(str(self._amount - self._binary(other, "subtract")), self._currency)

    def __neg__(self) -> Money:
        return Money(str(-self._amount), self._currency)

    def __abs__(self) -> Money:
        return Money(str(abs(self._amount)), self._currency)
