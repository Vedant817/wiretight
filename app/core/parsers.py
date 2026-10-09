"""Deterministic parsers. Authoritative for identifiers and amounts.

FINAL.md §4.3. This module decides what a payment *is*: which country an IBAN
belongs to, whether a routing number's digits actually check out, what the
transfer reference will look like on the wire, and whether the bank details a
supplier sent match the ones we already pay.

Three rules shape everything here:

1. **No guessing.** A malformed identifier is refused, never repaired. A parser
   that "fixes" an IBAN by dropping a character is a parser that will one day
   route money to a different bank.
2. **Normalise before comparing.** ``INV 0042`` and ``INV-42`` are one invoice;
   ``DE89 3704...`` and ``DE893704...`` are one account. Otherwise formatting
   differences look like bank changes, and the lock would fire on noise.
3. **No network, no model.** ``app/core`` never imports ``app.integrations`` and
   never imports a language model. A test asserts both.

The failure-type table is here rather than in the incident playbook because the
*classifier* and the *response* are different concerns: this says which group a
type belongs to, and ``incidents.py`` says what the group does.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final

import rfc8785

from app.core.text_normalisation import (
    bidi_present,
    describe_invisible,
    strip_invisible,
)
from app.money import (
    CURRENCY_EXPONENT,
    exponent_for,
    parse_money,
    to_money_string,
)

__all__ = [
    "CATEGORY_REASONS",
    "FAILURE_TYPES",
    "TRANSFER_REASONS",
    "PayeeDetails",
    "detect_hidden_text",
    "fingerprint",
    "last4",
    "mask_account",
    "normalise_invoice_no",
    "parse_aba",
    "parse_amount",
    "parse_bic",
    "parse_currency",
    "parse_iban",
    "parse_reason",
    "parse_reference",
    "parse_sort_code",
    "playbook_for",
]


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ParseResult:
    """Outcome of one parse. ``valid`` is the only thing callers must branch on.

    ``reason`` is for logs and the UI. It never says "verified": a format check
    proves the string is well formed, nothing more (§4.5.1).
    """

    valid: bool
    value: str | None = None
    normalised: str | None = None
    country: str | None = None
    currency: str | None = None
    exponent: int | None = None
    reason: str | None = None

    def __bool__(self) -> bool:
        return self.valid


# ---------------------------------------------------------------------------
# IBAN
# ---------------------------------------------------------------------------
#: IBAN length per country, from the ISO 13616 registry. Checked explicitly
#: because mod-97 alone does not prove an IBAN belongs to the country it claims.
IBAN_LENGTHS: Final[dict[str, int]] = {
    "AD": 24,
    "AE": 23,
    "AL": 28,
    "AT": 20,
    "AZ": 28,
    "BA": 20,
    "BE": 16,
    "BG": 22,
    "BH": 22,
    "BR": 29,
    "BY": 28,
    "CH": 21,
    "CR": 22,
    "CY": 28,
    "CZ": 24,
    "DE": 22,
    "DK": 18,
    "DO": 28,
    "EE": 20,
    "EG": 29,
    "ES": 24,
    "FI": 18,
    "FO": 18,
    "FR": 27,
    "GB": 22,
    "GE": 22,
    "GI": 23,
    "GL": 18,
    "GR": 27,
    "GT": 28,
    "HR": 21,
    "HU": 28,
    "IE": 22,
    "IL": 23,
    "IS": 26,
    "IT": 27,
    "JO": 30,
    "KW": 30,
    "KZ": 20,
    "LB": 28,
    "LC": 32,
    "LI": 21,
    "LT": 20,
    "LU": 20,
    "LV": 21,
    "MC": 27,
    "MD": 24,
    "ME": 22,
    "MK": 19,
    "MR": 27,
    "MT": 31,
    "MU": 30,
    "NL": 18,
    "NO": 15,
    "PK": 24,
    "PL": 28,
    "PS": 29,
    "PT": 25,
    "QA": 29,
    "RO": 24,
    "RS": 22,
    "SA": 24,
    "SE": 24,
    "SI": 19,
    "SK": 24,
    "SM": 27,
    "ST": 25,
    "SV": 28,
    "TL": 23,
    "TN": 24,
    "TR": 26,
    "UA": 29,
    "VA": 22,
    "VG": 24,
    "XK": 20,
}

#: Currency implied by each IBAN country.
#:
#: SEPA countries are EUR. The UK is included because a GBP IBAN is a real
#: destination this product pays, and leaving it out meant `parse_iban` returned
#: `currency=None` for GB, so a UK beneficiary would have had to guess its
#: currency from somewhere less reliable.
IBAN_CURRENCY: Final[dict[str, str]] = {
    "AT": "EUR",
    "BE": "EUR",
    "CY": "EUR",
    "DE": "EUR",
    "EE": "EUR",
    "ES": "EUR",
    "FI": "EUR",
    "FR": "EUR",
    "GR": "EUR",
    "HR": "EUR",
    "IE": "EUR",
    "IT": "EUR",
    "LT": "EUR",
    "LU": "EUR",
    "LV": "EUR",
    "MT": "EUR",
    "NL": "EUR",
    "PT": "EUR",
    "SI": "EUR",
    "SK": "EUR",
    "GB": "GBP",
    "CH": "CHF",
    "PL": "PLN",
    "CZ": "CZK",
    "HU": "HUF",
    "RO": "RON",
    "SE": "SEK",
    "NO": "NOK",
    "DK": "DKK",
}

_IBAN_ALLOWED = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]+$")


def iban_length(country: str) -> int:
    """Expected IBAN length for ``country``. 0 when the country is unknown."""
    return IBAN_LENGTHS.get(country.strip().upper(), 0)


def _strip_iban(value: str) -> str:
    return re.sub(r"[\s-]", "", value).strip().upper()


def _iban_for_mod97(iban: str) -> str:
    """Rearrange for the checksum: move the first four characters to the end.

    Letters become their two-digit numeric position (``D`` -> 13), which is what
    makes mod-97 arithmetic possible on an alphanumeric string.
    """
    rearranged = iban[4:] + iban[:4]
    return "".join(str(ord(char) - 55) if char.isalpha() else char for char in rearranged)


def parse_iban(value: str) -> ParseResult:
    """Validate an IBAN's structure, country length and mod-97 checksum."""
    compact = _strip_iban(value)
    if not _IBAN_ALLOWED.match(compact):
        return ParseResult(
            valid=False,
            reason="an IBAN is two country letters, two check digits, then alphanumerics",
        )

    country = compact[:2]
    expected = iban_length(country)
    if expected == 0:
        return ParseResult(valid=False, reason=f"{country} is not an IBAN country in the registry")
    if len(compact) != expected:
        return ParseResult(
            valid=False,
            reason=f"a {country} IBAN is {expected} characters, got {len(compact)}",
        )

    # mod-97 per ISO 7064: the rearranged number must leave remainder 1.
    if int(_iban_for_mod97(compact)) % 97 != 1:
        return ParseResult(valid=False, reason="mod-97 checksum failed")

    return ParseResult(
        valid=True,
        value=compact,
        normalised=compact,
        country=country,
        currency=IBAN_CURRENCY.get(country),
    )


# ---------------------------------------------------------------------------
# US ABA routing number
# ---------------------------------------------------------------------------
_ABA_DIGITS = re.compile(r"^[0-9]{9}$")


def _aba_checksum_ok(routing: str) -> bool:
    """3(d1+d4+d7) + 7(d2+d5+d8) + (d3+d6+d9) is a multiple of 10."""
    digits = [int(char) for char in routing]
    total = (
        3 * (digits[0] + digits[3] + digits[6])
        + 7 * (digits[1] + digits[4] + digits[7])
        + (digits[2] + digits[5] + digits[8])
    )
    return total % 10 == 0


def parse_aba(value: str) -> ParseResult:
    """Validate a 9-digit US ABA routing number and its checksum."""
    compact = value.strip()
    if not _ABA_DIGITS.match(compact):
        return ParseResult(valid=False, reason="a US ABA routing number is 9 digits")
    if not _aba_checksum_ok(compact):
        return ParseResult(valid=False, reason="ABA checksum failed")
    return ParseResult(valid=True, value=compact, normalised=compact, country="US", currency="USD")


# ---------------------------------------------------------------------------
# UK sort code
# ---------------------------------------------------------------------------
_SORT_CODE = re.compile(r"^(\d{2})-?(\d{2})-?(\d{2})$")


def parse_sort_code(value: str) -> ParseResult:
    """Validate a 6-digit UK sort code. Accepts the 2-2-3 grouped form."""
    compact = value.strip()
    match = _SORT_CODE.match(compact)
    if match is None:
        return ParseResult(valid=False, reason="a UK sort code is 6 digits")
    digits = "".join(match.groups())
    return ParseResult(valid=True, value=compact, normalised=digits, country="GB", currency="GBP")


# ---------------------------------------------------------------------------
# BIC
# ---------------------------------------------------------------------------
_BIC = re.compile(r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$")


def parse_bic(value: str) -> ParseResult:
    """Validate an 8 or 11 character BIC and extract its country."""
    compact = value.strip().upper().replace(" ", "")
    if len(compact) not in (8, 11) or not _BIC.match(compact):
        return ParseResult(valid=False, reason="a BIC is 8 or 11 characters")
    return ParseResult(valid=True, value=compact, normalised=compact, country=compact[4:6])


# ---------------------------------------------------------------------------
# Currency
# ---------------------------------------------------------------------------
_CURRENCY = re.compile(r"^[A-Z]{3}$")


def parse_currency(value: str) -> ParseResult:
    """Validate an ISO 4217 code and return its exponent.

    The code must be **known**, not merely three letters. Any three letters used
    to pass, so a currency with no exponent entry silently inherited the default
    of 2 — which for a zero-decimal currency like KRW overstates every amount by
    100x, straight into the cap comparisons, the ledger and the tie-out (D-B20).
    """
    if not isinstance(value, str):
        return ParseResult(
            valid=False, reason=f"a currency is a string, got {type(value).__name__}"
        )
    code = strip_invisible(value).strip().upper()
    if not _CURRENCY.match(code):
        return ParseResult(valid=False, reason="a currency is a 3-letter ISO 4217 code")
    if code not in CURRENCY_EXPONENT:
        return ParseResult(
            valid=False,
            reason=(
                f"{code} is not in the pinned ISO 4217 exponent table. Guessing an "
                "exponent would misstate every amount in this currency."
            ),
        )
    return ParseResult(
        valid=True,
        value=code,
        normalised=code,
        currency=code,
        exponent=exponent_for(code),
    )


# ---------------------------------------------------------------------------
# Invoice number
# ---------------------------------------------------------------------------
def normalise_invoice_no(value: str) -> str:
    """Upper-case, strip invisibles and punctuation, and drop leading zeros.

    This produces ``duplicate_lock.obligation_key``, so it is the single control
    standing between a resubmitted invoice and a second payment. Two properties
    were measured wrong before (D-B20) and both are fixed here:

    * ``\\s`` does not match Unicode format characters, so ``INV-2291`` and
      ``INV-2291\\u200b`` produced different keys and the invoice paid twice.
      Invisible characters are now stripped explicitly.
    * ``lstrip("0")`` on the whole string collides a vendor's ``0V042`` with a
      different vendor's ``V42``. Leading zeros are now only dropped from a
      purely numeric invoice number, which is the §8.5 bill #4 case the spec
      actually describes.
    """
    text = strip_invisible(value).strip().upper()
    text = re.sub(r"[\s.\-/\\:]+", "", text)
    # Only a wholly numeric number has its leading zeros stripped. "0V042" and
    # "V42" are two invoices at most vendors; "0042" and "42" are one.
    if text.isdigit():
        return text.lstrip("0") or "0"
    return text


def parse_invoice_no(value: str) -> ParseResult:
    normalised = normalise_invoice_no(value)
    if not normalised:
        return ParseResult(valid=False, reason="an invoice number must not be empty")

    # Report rather than silently repair. A bill carrying a zero-width space is
    # worth flagging: nothing legitimate adds one, and §4.14.5 measures precision
    # on exactly this class of input.
    invisible = describe_invisible(value)
    if invisible:
        return ParseResult(
            valid=False,
            normalised=normalised,
            reason=(
                "the invoice number contains characters that render as nothing: "
                + ", ".join(invisible)
            ),
        )
    if bidi_present(value):
        return ParseResult(
            valid=False,
            normalised=normalised,
            reason="the invoice number contains a bidirectional override (text reordering attack)",
        )
    return ParseResult(valid=True, value=value.strip(), normalised=normalised)


# ---------------------------------------------------------------------------
# Transfer reference (§7.4)
# ---------------------------------------------------------------------------
#: Our own limit, not Airwallex's. A reference outside it goes to REVIEW.
REFERENCE_PATTERN: Final[str] = r"^[A-Za-z0-9 ./-]{1,35}$"
_REFERENCE = re.compile(REFERENCE_PATTERN)


def parse_reference(value: str) -> ParseResult:
    """Check the reference against ``^[A-Za-z0-9 ./-]{1,35}$``.

    The value is returned unchanged. We never rewrite a reference to make it
    fit: a signatory saw the string they are approving, and silently editing it
    would be editing the thing they approved.
    """
    if not _REFERENCE.match(value):
        return ParseResult(
            valid=False,
            reason=f"a transfer reference must match {REFERENCE_PATTERN} to go on a payment",
        )
    return ParseResult(valid=True, value=value, normalised=value)


# ---------------------------------------------------------------------------
# Transfer reason enum (§7.4)
# ---------------------------------------------------------------------------
TRANSFER_REASONS: Final[frozenset[str]] = frozenset(
    {
        "audio_visual_services",
        "bill_payment",
        "business_expenses",
        "construction",
        "donation_charitable_contribution",
        "education_training",
        "freight",
        "goods_purchased",
        "investment_capital",
        "investment_proceeds",
        "living_expenses",
        "loan_credit_repayment",
        "medical_services",
        "pension",
        "professional_business_services",
        "real_estate",
        "taxes",
        "technical_services",
        "transfer_to_own_account",
        "travel",
        "wages_salary",
        "other_services",
    }
)


def parse_reason(value: str) -> ParseResult:
    if value not in TRANSFER_REASONS:
        return ParseResult(valid=False, reason=f"{value!r} is not an Airwallex transfer reason")
    return ParseResult(valid=True, value=value, normalised=value)


#: §4.17 ``vendor_category_reason``, the same mapping the policy file carries.
CATEGORY_REASONS: Final[dict[str, str]] = {
    "freight": "freight",
    "manufacturing": "goods_purchased",
    "design_services": "professional_business_services",
    "software": "technical_services",
    "contractor": "professional_business_services",
}


# ---------------------------------------------------------------------------
# Failure types (§4.11)
# ---------------------------------------------------------------------------
#: Every simulator ``failure_type`` and the playbook group it belongs to.
#: ``INBOUND_BENEFICIARY_VALIDATION_ERROR`` is misspelled upstream and is
#: matched byte for byte; correcting it would silently miss the failure.
FAILURE_TYPES: Final[dict[str, str]] = {
    # A. bank details wrong or closed
    "ACCOUNT_CLOSED": "A",
    "ACCOUNT_INACTIVE_OR_DORMANT": "A",
    "ACCOUNT_CURRENCY_MISMATCH": "A",
    "BENEFICIARY_NAME_MISMATCH": "A",
    "INVALID_ACCOUNT_NAME_OR_NUMBER": "A",
    "INVALID_BANK_OR_BRANCH_CODE": "A",
    "INVALID_SWIFT_BIC_CODE": "A",
    "INVALID_BENEFICIARY_DETAILS": "A",
    "INVALID_BANK_INFORMATION": "A",
    "INVALID_CORRESPONDENT_BANK_INFORMATION": "A",
    # B. bank return
    "BENEFICIARY_BANK_RETURNED": "B",
    # C. data fixes
    "INVALID_SPECIAL_CHARACTER": "C",
    "INVALID_PAYMENT_PURPOSE": "C",
    # D. funding and limits
    "INSUFFICIENT_FUNDS": "D",
    "TRANSACTION_AMOUNT_NOT_COVERING_FEE": "D",
    "EXCEEDED_TRANSACTION_AMOUNT_OR_LIMIT": "D",
    # E. channel and system
    "CHANNEL_TIMEOUT": "E",
    "SYSTEM_ERROR": "E",
    # F. compliance
    "ACCOUNT_UNDER_RESTRICTION": "F",
    "TM_SUSPENDED": "F",
    "CHANNEL_POLICY": "F",
    # G. investigate
    "RECALL_REQUESTED": "G",
    "CLIENT_REQUESTED": "G",
    "DUPLICATION_RETURN": "G",
    "BENEFICIARY_REQUESTED": "G",
    # H. DEFAULT: everything else, including null and unknown strings
    "UNABLE_TO_APPLY": "H",
    "OTHER": "H",
    "CARD_ISSUER_ERROR": "H",
    "INBOUND_2B_CARD_NOT_SUPPORTED": "H",
    "INBOUND_BENEFICIARY_VALIDATION_ERROR": "H",
    "INBOUND_COMPANY_REGISTRATION_NUMBER_ERROR": "H",
    "INBOUND_ORDER_ERROR": "H",
    "DEFAULT": "H",
}

#: Documented numeric reason codes, shown verbatim on the demo caption (§4.12).
FAILURE_REASON_CODES: Final[dict[str, str]] = {
    "ACCOUNT_CLOSED": "90701",
    "ACCOUNT_INACTIVE_OR_DORMANT": "90702",
    "ACCOUNT_UNDER_RESTRICTION": "90703",
    "BENEFICIARY_NAME_MISMATCH": "90301",
    "INVALID_ACCOUNT_NAME_OR_NUMBER": "90101",
    "INVALID_BANK_OR_BRANCH_CODE": "90201",
    "INVALID_SWIFT_BIC_CODE": "90202",
    "INVALID_BENEFICIARY_DETAILS": "90401",
    "CHANNEL_POLICY": "90501",
    "TM_SUSPENDED": "90502",
    "BENEFICIARY_BANK_RETURNED": "90802",
    "RECALL_REQUESTED": "91001",
    "CLIENT_REQUESTED": "91002",
    "INVALID_PAYMENT_PURPOSE": "91101",
    "CHANNEL_TIMEOUT": "91401",
    "SYSTEM_ERROR": "91402",
}


def normalise_failure_type(value: str | None) -> str | None:
    """Upper-case and strip a ``failure_type`` before any lookup.

    Airwallex returns these as enum values, so they should already be canonical.
    But a trailing space or a differently-cased string would otherwise fall to
    the DEFAULT handler — and for the *compliance* group that is the difference
    between "halt everything and escalate to the founder" (§4.15 r29) and "carry
    on". Normalising means a near-miss still reaches its real playbook, and a
    genuinely unknown type still reaches H (D-B20).
    """
    if value is None:
        return None
    return strip_invisible(value).strip().upper()


def playbook_for(failure_type: str | None) -> str:
    """Which playbook group handles ``failure_type``. Anything unknown is ``H``.

    There is no "wait and re-check". An unknown type gets the DEFAULT handler,
    which escalates and never retries.
    """
    if not failure_type:
        return "H"
    return FAILURE_TYPES.get(normalise_failure_type(failure_type) or "", "H")


# ---------------------------------------------------------------------------
# Amounts
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AmountResult:
    valid: bool
    value: str | None = None
    reason: str | None = None


def parse_amount(value: object, currency: str | None) -> AmountResult:
    """Parse an amount at ``currency``'s exponent. A float is refused.

    Refunds and reversals are negative, so a negative amount is valid here; it is
    the caller that decides whether a negative *obligation* makes sense.

    Three defects fixed here (D-B20), all of which turned a guard that exists into
    a guard that did not:

    * the quantise step sat **outside** the ``try``, so a 27-digit amount escaped
      as an uncaught ``decimal.InvalidOperation``;
    * at JPY's exponent of 0 the same amount *succeeded*, rounding 1e27 to a
      completely different number, because the fractional part simply disappeared;
    * ``currency=None`` — which a valid IBAN with no currency mapping returns —
      raised ``TypeError`` instead of routing the item to REVIEW.
    """
    if isinstance(value, float):
        return AmountResult(
            valid=False,
            reason="a float is not an amount; pass a decimal string (FINAL.md §7.3)",
        )
    if not currency or not isinstance(currency, str):
        return AmountResult(
            valid=False,
            reason=f"no currency for this amount (got {currency!r}); cannot pick an exponent",
        )
    try:
        amount = parse_money(value)  # type: ignore[arg-type]
        return AmountResult(valid=True, value=to_money_string(amount, currency))
    except (TypeError, ValueError, ArithmeticError) as exc:
        # ArithmeticError covers decimal.InvalidOperation, which is not a
        # ValueError and so was never caught by the original except clause.
        return AmountResult(
            valid=False,
            reason=f"{exc} (an amount this large cannot be represented exactly)",
        )


# ---------------------------------------------------------------------------
# Bank fingerprint (§4.3)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PayeeDetails:
    """The inputs to a bank fingerprint.

    Note what is *absent*: the payee's name. The fingerprint is about the
    destination account, so renaming a supplier does not read as a bank change,
    and changing an account always does.

    ``extra`` is wrapped in a read-only mapping. ``frozen=True`` on a dataclass
    only stops attribute rebinding, so a plain ``dict`` field let the fingerprint
    of a "frozen" object change underneath its holder (measured, D-B20).
    """

    country: str
    currency: str
    method: str
    account: str
    bic: str | None = None
    #: Other corridor-specific identifiers. Read-only; keys may not shadow
    #: ``account`` or ``bic``.
    extra: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))


def _normalise_identifier(value: str) -> str:
    """Strip formatting so spacing and case never read as a bank change.

    Invisible characters are stripped too. A soft hyphen in an IBAN is a
    formatting artefact of some upstream systems, so treating it as a change
    produces a ``HOLD: BANK_CHANGE`` and a 72-hour cooling-off on a supplier whose
    bank details did not move — which is exactly the false positive §4.14.5's
    ``bank_change_flag_precision`` is measured against.
    """
    return re.sub(r"[\s\-]", "", strip_invisible(value)).strip().upper()


#: Keys ``PayeeDetails.extra`` may not use. ``extra`` exists for
#: *other* corridor identifiers, and the fingerprint dict is built with ``account``
#: first, so an injected ``account`` key would shadow the real one (D-B20).
RESERVED_FINGERPRINT_KEYS: frozenset[str] = frozenset({"account", "bic"})


class FingerprintKeyError(ValueError):
    """An identifier was placed under a key the fingerprint already owns."""


def fingerprint(details: PayeeDetails) -> str:
    """``sha256(rfc8785({country, currency, method, identifiers, bic}))``.

    RFC 8785 is what makes this safe: the same details hashed from two different
    code paths produce the same digest, so a fingerprint comparison compares data
    rather than serialisation choices.

    ``extra`` is copied into the identifiers mapping and a key that shadows
    ``account`` is refused. Before that check, an attacker-supplied corridor
    field made two *different* bank accounts fingerprint identically, so a real
    bank change never fired the lock.
    """
    identifiers: dict[str, str] = {"account": _normalise_identifier(details.account)}
    for key, value in sorted(details.extra.items()):
        if key in RESERVED_FINGERPRINT_KEYS:
            raise FingerprintKeyError(
                f"extra[{key!r}] would shadow the {key} being fingerprinted; "
                f"reserved keys are {sorted(RESERVED_FINGERPRINT_KEYS)}"
            )
        identifiers[key] = _normalise_identifier(value)

    payload = {
        "country": strip_invisible(details.country).strip().upper(),
        "currency": strip_invisible(details.currency).strip().upper(),
        "method": strip_invisible(details.method).strip().upper(),
        "identifiers": identifiers,
        "bic": _normalise_identifier(details.bic) if details.bic else None,
    }
    return hashlib.sha256(rfc8785.dumps(payload)).hexdigest()


def last4(details: PayeeDetails) -> str:
    """The last four characters of the account.

    The U16 fallback: if ``GET /beneficiaries/{id}`` returns masked identifiers
    only, this is all the executor can compare, and T-04b covers that path.
    """
    normalised = re.sub(r"[^A-Za-z0-9]", "", details.account)
    return normalised[-4:] if len(normalised) >= 4 else normalised


def mask_account(value: str) -> str:
    """``DE•• •••• 3000``. The form shown in every UI and every log line.

    The mask must never disclose the whole account. A 5-character account used to
    render as ``AB•• •••• B123``, where the 2-character prefix and the 4-character
    tail overlap and every character is visible — in every UI row and every log
    line (D-B20).
    """
    compact = re.sub(r"[\s\-]", "", strip_invisible(value)).strip()
    if len(compact) <= 4:
        return "•" * len(compact)
    prefix = compact[:2] if compact[:2].isalpha() else ""
    tail = compact[-4:]

    # Overlap check: if the prefix would appear inside the tail, mask more.
    if prefix and prefix in tail:
        prefix = ""

    body = len(compact) - len(prefix) - 4
    if body <= 0:
        # Too short to show a prefix and a tail without revealing everything.
        return f"{prefix}{'•' * 4} {tail}" if prefix else f"{'•' * 4} {tail}"
    return f"{prefix}{'•' * 2} {'•' * 4} {tail}"


# ---------------------------------------------------------------------------
# Hidden text (T-01)
# ---------------------------------------------------------------------------
#: Body text below this size is treated as hidden regardless of colour.
MIN_VISIBLE_PT: Final[float] = 8.0

#: Light colours, matched numerically rather than by exact spelling.
#:
#: The previous pattern listed literal strings, so ``rgb(255,255,255)`` — the
#: notation every HTML-to-PDF renderer and every browser emits, and therefore the
#: one an attacker would use — was missed entirely while ``#fff`` was caught
#: (measured, D-B20).
_RGB = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", re.IGNORECASE)
_HEX = re.compile(r"^#?([0-9a-f]{3}|[0-9a-f]{6})$", re.IGNORECASE)
_NAMED_LIGHT = frozenset({"white", "ghostwhite", "snow", "ivory", "azure"})

#: Above this luminance, text is treated as invisible on a white page.
LIGHT_LUMINANCE_THRESHOLD: float = 0.85


def _is_light(colour: str) -> bool:
    """Is this colour light enough to be invisible on white paper?"""
    text = colour.strip().lower()
    if not text:
        return False
    if text in _NAMED_LIGHT:
        return True

    match = _RGB.match(text)
    if match:
        r, g, b = (int(group) / 255 for group in match.groups())
        # Relative luminance, the standard formula.
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        return luminance >= LIGHT_LUMINANCE_THRESHOLD

    hex_match = _HEX.match(text)
    if hex_match:
        digits = hex_match.group(1)
        if len(digits) == 3:
            digits = "".join(char * 2 for char in digits)
        r, g, b = (int(digits[i : i + 2], 16) / 255 for i in (0, 2, 4))
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        return luminance >= LIGHT_LUMINANCE_THRESHOLD

    return False


def detect_hidden_text(chars: list[tuple[str, float] | tuple[str, float, str]]) -> bool:
    """True when any run of text is too small or too light to be meant as read.

    Accepts 2-tuples ``(text, size_pt)`` and 3-tuples
    ``(text, size_pt, colour)`` so a caller with no colour information still
    gets the size check.

    A one-point white line under an 11-point invoice is the T-01 attack: the
    human reads the IBAN on the page, the model reads the whole text layer.
    Three further evasions closed here (D-B20): ``rgb()`` notation, a ``NaN``
    font size, and an empty-text run at 0.5 pt, all of which previously returned
    ``False``.
    """
    for entry in chars:
        try:
            size = float(entry[1])
        except (IndexError, TypeError, ValueError):
            continue

        # A NaN size fails every comparison, so an unparseable or NaN measurement
        # must not read as "visible".
        if size != size:
            return True
        if size < MIN_VISIBLE_PT:
            return True

        if len(entry) > 2 and _is_light(str(entry[2])):
            return True
    return False
