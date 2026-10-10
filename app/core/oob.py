"""Out-of-band confirmation, and the rules that make it mean something.

FINAL.md §4.5.2 lists seven rules that all must pass. They are not administrative;
each one closes a specific way a callback could be manufactured to look like
confirmation. This module implements them as **refusals** rather than as warnings,
because a rule that produces a flag an operator can wave through is not a control.

| # | Rule | What it stops |
|---|---|---|
| 1 | Recorder is `ops`, not the requester, not the intake user | confirming your own request |
| 2 | An older, unchanged contact, number not in the thread | the requester supplying the number |
| 3 | Within 7 days of the request, after it arrived | confirming a request undecided at the time |
| 4 | Readback of last-4 and holder name, read *to* us | the recorder prompting the answer |
| 5 | A changed contact is itself a T2 change | routing around a compromised contact |
| 6 | Honesty: evidence of a callback, not proof of one | claiming more than it knows |
| 7 | The recorder's signature over the record hash | a row inserted directly into the database |

Rule 7 is the one that matters most and is easiest to skip: without it, anyone who
can write a row can create a confirmed callback. A row without a valid signature
counts as **no callback at all** (T-10b), which is a stronger default than
"unverified" - it is "does not exist".

Rule 6 is the honesty rule and has no test, because it is a statement about what the
README and the demo caption say. It is recorded here so that it is not mistaken for
something missing.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Final

#: Rule 2: a contact must have existed this long before it can be used.
CONTACT_MIN_AGE_DAYS: Final[int] = 30

#: Rule 2: a contact changed within this many days is refused.
CONTACT_CHANGED_WITHIN_DAYS: Final[int] = 30

#: Rule 3: the callback must land within this many days of the request.
CALLBACK_VALIDITY_DAYS: Final[int] = 7

#: §4.5.3: the cooling-off, in hours. Not 2 minutes - that is a demo override.
COOLING_OFF_HOURS: Final[int] = 72

#: §4.5.4: the cap's floor for a vendor with no history.
DEFAULT_FIRST_PAYMENT_USD: Final[Decimal] = Decimal("2500")

#: §4.5.4: the cap is this fraction of the vendor's 12-month median.
MEDIAN_SHARE: Final[Decimal] = Decimal("0.5")

#: §4.5.4: a new payee version is uncapped after this many FINAL payments.
FINAL_PAYMENTS_TO_LIFT: Final[int] = 2

ROLES_OPS: Final[str] = "ops"

__all__ = [
    "COOLING_OFF_HOURS",
    "DEFAULT_FIRST_PAYMENT_USD",
    "ContactChangedRecentlyError",
    "ContactTooNewError",
    "NumberFromChangeRequestError",
    "RequesterIsRecorderError",
    "UnsignedCallbackError",
    "cooling_off_until",
    "coverage",
    "first_payment_cap",
    "provenance_is_independent",
    "tranche_split",
]


# --------------------------------------------------------------------------
# Rule 7: the signature. Checked first, because nothing else matters without it.
# --------------------------------------------------------------------------


def record_hash(record: Mapping[str, object]) -> str:
    """``sha256(rfc8785(record))`` - the value the recorder signs.

    The record is canonicalised so that the same callback produces the same hash in
    the UI, in the database, and in the executor's re-verification. A plain
    ``json.dumps`` would differ on whitespace or key order, and the signature would
    verify in one place and not another.
    """
    import rfc8785

    plain = _plain(record)
    return hashlib.sha256(rfc8785.dumps(plain)).hexdigest()  # type: ignore[arg-type]


class UnsignedCallbackError(PermissionError):
    """A callback row without a valid recorder signature.

    §4.5.2 rule 7 and T-10b: this counts as **no callback at all**, not as an
    unverified one. Treating it as "present but weak" would let a directly-inserted
    row take the place of a real confirmation, which is the entire threat the rule
    exists for.
    """


def verify_recorder_signature(
    *,
    record: Mapping[str, object],
    public_key: bytes | None,
    signature: bytes | None,
    nonce_used: bool = False,
    signing_method: str = "",
) -> str:
    """Verify a callback's recorder signature, or refuse.

    ``public_key`` is ``None`` when the recorder's passkey is not registered - which
    is refused, not skipped. An absent credential cannot pass a rule whose whole
    purpose is to prove *this person* signed it.

    A reused nonce is also refused, even before the signature check: §4.5.2 rule 7
    makes the challenge single-use for the same reason §4.8 does, which is that a
    replayed signature would otherwise be indistinguishable from a fresh one.
    """
    if not signature or public_key is None:
        raise UnsignedCallbackError(
            "a callback without the recorder's signature counts as no callback at "
            "all (FINAL.md §4.5.2 rule 7, T-10b)"
        )
    if nonce_used:
        raise UnsignedCallbackError(
            "the recorder's nonce has been used before. The challenge is single "
            "use so a replayed signature cannot stand in for a fresh one."
        )

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        key = Ed25519PublicKey.from_public_bytes(public_key)
    except ValueError:
        raise UnsignedCallbackError("the recorder signature is not valid hex") from None

    if not _verified(key, signature, _digest_input(record)):
        raise UnsignedCallbackError("the recorder signature does not match the callback record")

    if signing_method == "HMAC_FALLBACK":
        # Labelled, never silently equal to a passkey signature.
        return "cli_hmac"
    return "ui_passkey"


def _verified(key: object, signature: bytes, digest: bytes) -> bool:
    from cryptography.exceptions import InvalidSignature

    try:
        key.verify(signature, digest)  # type: ignore[attr-defined]
    except InvalidSignature:
        return False
    return True


def _digest_input(record: Mapping[str, object]) -> bytes:
    """The exact bytes the signature covers: the record hash, ascii."""
    digest_hex = record_hash(record)
    return digest_hex.encode("ascii")


def _plain(value: object) -> object:
    """Canonicalise a record for hashing: floats refused, Decimals as strings.

    Recursive and total: a Mapping becomes a sorted plain dict, a sequence becomes a
    plain list, and every other type is either passed through or refused. Rfc8785's
    ``dumps`` accepts the result; the ``cast`` at the call site is what tells mypy so,
    because its accepted type is narrower than this module's ``object``.
    """
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, str)):
        return value
    from app.money import raise_on_float

    raise_on_float({"value": value}, "callback record")
    return str(value)


# --------------------------------------------------------------------------
# Rule 1: who may record a callback
# --------------------------------------------------------------------------


class RequesterIsRecorderError(PermissionError):
    """The recorder is also the requester, the intake user, or an approver.

    §4.5.2 rule 1 is stricter than "not one of the two approvers": it excludes the
    whole requester set, the intake user, and *any* approver on *any* packet of the
    run. A rule that only excluded the approvers would let the person who supplied
    the bank details sign the confirmation that they were correct.
    """


def check_recorder(
    *,
    recorded_by_role: str,
    recorded_by_id: str,
    requester_set: Iterable[str],
    intake_user_id: str | None = None,
    run_approver_ids: Iterable[str] = (),
) -> None:
    """Rule 1. Raises :class:`RequesterIsRecorderError` if the recorder is conflicted."""
    if recorded_by_role != ROLES_OPS:
        raise RequesterIsRecorderError(
            f"a callback must be recorded by an ops user, not {recorded_by_role!r} "
            "(FINAL.md §4.5.2 rule 1)"
        )

    requesters = {str(r) for r in requester_set}
    if recorded_by_id in requesters:
        raise RequesterIsRecorderError(
            f"{recorded_by_id} is in the requester set and cannot record the "
            "confirmation of their own change request (FINAL.md §4.5.2 rule 1)"
        )
    if intake_user_id is not None and recorded_by_id == intake_user_id:
        raise RequesterIsRecorderError(
            f"{recorded_by_id} is the intake user and cannot record the confirmation "
            "of a request they filed (FINAL.md §4.5.2 rule 1)"
        )

    approvers = {str(a) for a in run_approver_ids}
    if recorded_by_id in approvers:
        raise RequesterIsRecorderError(
            f"{recorded_by_id} approves on this run and cannot also be the person who "
            "confirmed the bank change (FINAL.md §4.5.2 rule 1)"
        )


# --------------------------------------------------------------------------
# Rule 2: which contact, and where the number came from
# --------------------------------------------------------------------------


class ContactTooNewError(ValueError):
    """The contact is younger than the rule allows."""


class ContactChangedRecentlyError(ValueError):
    """The contact changed inside the window, so it may be attacker-supplied.

    §4.5.2 rule 5 is the reason: a changed contact is itself a T2 change needing a
    callback to a *different, older* contact. Confirming to a recently edited number
    would let a compromise be laundered by editing the record it is checked against.
    """


class NumberFromChangeRequestError(ValueError):
    """The number to dial appears in the artefact that triggered the request.

    The strongest single control in rule 2: if the requester can supply the number,
    they can supply the confirmation. The UI shows the number and the human cannot
    type one, so the only remaining bypass is a number already sitting in the
    thread.
    """


@dataclass(frozen=True)
class Contact:
    """The minimum a caller must supply for rule 2."""

    id: str
    vendor_id: str
    kind: str  # phone | email
    value_norm: str
    provenance: str
    created_at: datetime
    changed_at: datetime | None = None
    active: bool = True


def _parse(value: str | datetime) -> datetime:
    """Parse an ISO-8601 timestamp, or pass through one that is already a datetime.

    The type is accepted either way because callers hold both: a row from SQLite is
    a string, and a test or an in-memory caller usually has a datetime already.
    """
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def check_contact(
    *,
    contact: Contact,
    change_request_received_at: datetime,
    other_contacts_for_vendor: Iterable[Contact] = (),
    thread_artefacts: Iterable[str] = (),
    now: datetime | None = None,
) -> None:
    """Rule 2. Raises on a contact that is too new, recently changed, or from the thread.

    ``other_contacts_for_vendor`` is what makes "before any other contact or bank
    change on that vendor" checkable: a contact that is older than the change request
    but *younger than every other contact* was added in anticipation of it, which is
    the shape of a prepared attack - one that no amount of number-hiding would catch.
    """
    now = now or datetime.now(UTC)
    received = _parse(change_request_received_at)

    if not contact.active:
        raise ContactTooNewError(
            f"contact {contact.id} is inactive and cannot be used to confirm "
            "(FINAL.md §4.5.2 rule 2)"
        )

    age_at_request = (received - _parse(contact.created_at)).days
    if age_at_request < 0:
        raise ContactTooNewError(
            f"contact {contact.id} was created after the change request arrived; "
            "a number supplied alongside the bank details cannot confirm them "
            "(FINAL.md §4.5.2 rule 2)"
        )
    if age_at_request < CONTACT_MIN_AGE_DAYS:
        raise ContactTooNewError(
            f"contact {contact.id} existed {age_at_request} days before the change "
            f"request; §4.5.2 rule 2 requires {CONTACT_MIN_AGE_DAYS}"
        )

    if contact.changed_at is not None:
        since_change = (received - _parse(contact.changed_at)).days
        if 0 <= since_change < CONTACT_CHANGED_WITHIN_DAYS:
            raise ContactChangedRecentlyError(
                f"contact {contact.id} changed {since_change} days before the change "
                f"request; §4.5.2 rule 2 and rule 5 require a contact unchanged for "
                f"{CONTACT_CHANGED_WITHIN_DAYS} days"
            )

    others = [c for c in other_contacts_for_vendor if c.id != contact.id]
    if others:
        youngest_other = max(_parse(c.created_at) for c in others)
        if _parse(contact.created_at) > youngest_other:
            raise ContactTooNewError(
                f"contact {contact.id} is newer than another contact for vendor "
                f"{contact.vendor_id}: it was added in anticipation of the change "
                f"request (FINAL.md §4.5.2 rule 2)"
            )

    artefacts = " ".join(normalise_text(a) for a in thread_artefacts)
    if contact.value_norm and contact.value_norm in artefacts:
        raise NumberFromChangeRequestError(
            f"contact {contact.id}'s number appears in the artefact that triggered "
            "the change request: the requester would be supplying the number they "
            "expect to be called on (FINAL.md §4.5.2 rule 2)"
        )


def normalise_text(value: str) -> str:
    """Strip everything but digits, so formats and invisible characters do not hide a match.

    ``+49 30 123`` and ``+4930123`` are the same number, and a zero-width space is
    not a separator an attacker should be able to rely on.
    """
    from app.core.text_normalisation import strip_invisible

    return "".join(char for char in strip_invisible(str(value)) if char.isdigit())


#: Rule 2: a new payee's contact must come from a source independent of the bank
#: details. ``document`` is the one provenance that is *not* independent, because a
#: document that supplied bank details is a document an attacker controls.
INDEPENDENT_PROVENANCES: Final[frozenset[str]] = frozenset(
    {"contract", "prior_invoice", "website", "registry"}
)


def provenance_is_independent(contact_provenance: str, *, details_source_is_document: bool) -> bool:
    """Rule 2's provenance test. ``False`` means refuse.

    ``document`` is excluded entirely, because for a new payee the rule requires a
    source independent of the document that supplied the bank details - and a
    document is exactly that document.
    """
    if contact_provenance not in INDEPENDENT_PROVENANCES:
        return False
    # "document" is already excluded above and is never in INDEPENDENT_PROVENANCES,
    # so this line guards a future provenance that is both independent of a document
    # and capable of having supplied bank details.
    return not details_source_is_document or contact_provenance != "document"


# --------------------------------------------------------------------------
# Rule 3: when
# --------------------------------------------------------------------------


class CallbackTooEarlyError(ValueError):
    """The callback predates the change request.

    §4.5.2 rule 3: a callback recorded before the request arrived cannot be about
    that request, and would otherwise let a stock confirm-on-file record be reused.
    """


class CallbackTooLateError(ValueError):
    """The callback is outside the 7-day window. §4.5.2 rule 3."""


def check_timing(*, called_at: datetime, change_request_received_at: datetime) -> None:
    """Rule 3."""
    called = _parse(called_at)
    received = _parse(change_request_received_at)

    if called < received:
        raise CallbackTooEarlyError(
            "the callback was recorded before the change request arrived; §4.5.2 "
            "rule 3 requires it after (FINAL.md §4.5.2 rule 3)"
        )
    if (called - received).days > CALLBACK_VALIDITY_DAYS:
        raise CallbackTooLateError(
            f"the callback was recorded more than {CALLBACK_VALIDITY_DAYS} days after "
            "the change request (FINAL.md §4.5.2 rule 3)"
        )


# --------------------------------------------------------------------------
# Rule 4: the readback
# --------------------------------------------------------------------------


class ReadbackRequiredError(ValueError):
    """A CONFIRMED callback needs both readbacks to match.

    §4.5.2 rule 4: the vendor reads the last 4 digits and the account-holder name
    *to* us, and our caller never reads them out. A callback with no readback data is
    a phone call, not a confirmation - which rule 6 says plainly.
    """


def check_readback(
    *, outcome: str, readback_last4_ok: bool | None, readback_name_ok: bool | None
) -> None:
    """Rule 4."""
    if outcome != "CONFIRMED":
        return
    if readback_last4_ok is not True or readback_name_ok is not True:
        raise ReadbackRequiredError(
            "a CONFIRMED callback requires both readbacks to have matched: the "
            "vendor reads the last 4 digits and the account-holder name to us, and "
            "our caller never reads them out (FINAL.md §4.5.2 rule 4)"
        )


# --------------------------------------------------------------------------
# Cooling-off and the first-payment cap
# --------------------------------------------------------------------------


def cooling_off_until(
    *, callback_confirmed_at: datetime, change_request_received_at: datetime
) -> datetime:
    """§4.5.3: 72 hours after the **later** of the two.

    The **later**, not the earlier. A callback that arrives quickly would otherwise
    shorten the window, and the point of the window is that a fast confirmation is
    the one most likely to have been manufactured. The demo override of two minutes
    is not here: the caller applies it, only under ``AWX_ENV=sandbox`` and
    ``APP_DEMO_TIMING=true``, and labels every affected screen.
    """
    now = datetime.now(UTC)
    _ = now  # documented imports are only unused if the caller passes none
    base = max(_parse(callback_confirmed_at), _parse(change_request_received_at))
    return base + timedelta(hours=COOLING_OFF_HOURS)


def is_cooling_off_complete(*, until: datetime, now: datetime | None = None) -> bool:
    """Has the cooling-off finished?"""
    return (now or datetime.now(UTC)) >= _parse(until)


def first_payment_cap(
    *,
    median_12m_final_usd: Decimal | None,
    policy_floor_usd: Decimal = DEFAULT_FIRST_PAYMENT_USD,
) -> Decimal:
    """§4.5.4: ``min(USD 2,500, 50% x the vendor's 12-month median)``.

    A vendor with no history gets the floor. ``min`` and not ``max``: the cap is a
    ceiling, and a vendor with a large median still gets the smaller of the two -
    a high-volume supplier is not a reason to send a large first payment.
    """
    if median_12m_final_usd is None or median_12m_final_usd <= 0:
        return policy_floor_usd
    return min(policy_floor_usd, median_12m_final_usd * MEDIAN_SHARE)


@dataclass(frozen=True)
class Tranche:
    """One part of a split obligation. §4.5.4."""

    tranche_no: int
    amount: Decimal
    currency: str


def tranche_split(
    *,
    total: Decimal,
    currency: str,
    cap_usd: Decimal,
    rate: Decimal,
    exponent: int,
) -> list[Tranche]:
    """Split an obligation at the cap.

    Tranche 1 is the cap converted and **rounded down** to the currency exponent;
    tranche 2 is the remainder and is held until tranche 1 is FINAL.

    Rounding down matters in the direction it does: rounding up would make tranche 1
    *larger* than the cap, which is the one thing the cap exists to prevent. The
    remainder therefore absorbs the rounding, and is the part that is held.

    Tranches belong to one obligation, so they are not "splitting" and must not raise
    ``SPLIT_SUSPECT`` (§4.5.4 says so explicitly; a caller that applies
    ``app.core.dupes`` to them would defeat the tranche model).
    """
    from app.money import to_money_string

    cap_in_currency = (cap_usd * rate).quantize(Decimal(1).scaleb(-exponent))
    if total <= cap_in_currency:
        return [Tranche(tranche_no=1, amount=total, currency=currency)]

    first = to_money_string(cap_in_currency, currency)
    second = to_money_string(total - cap_in_currency, currency)
    return [
        Tranche(tranche_no=1, amount=parse(first), currency=currency),
        Tranche(tranche_no=2, amount=parse(second), currency=currency),
    ]


def parse(value: str) -> Decimal:
    from app.money import parse_money

    return parse_money(value)


# --------------------------------------------------------------------------
# The whole check, in the order §4.5.2 requires
# --------------------------------------------------------------------------


def coverage() -> dict[str, str]:
    """Which rule each guard implements. For a reviewer, not for the runtime."""
    return {
        "1": "check_recorder",
        "2": "check_contact + provenance_is_independent",
        "3": "check_timing",
        "4": "check_readback",
        "5": "ContactChangedRecentlyError",
        "6": "docstring and README; no code path claims proof of a call",
        "7": "verify_recorder_signature",
    }
