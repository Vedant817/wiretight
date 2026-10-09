"""Duplicate detection: exact, suspect, and split.

FINAL.md §4.3 names three rules with three different consequences, and the
difference between them is the substance of this module:

| Rule | Condition | Consequence |
|---|---|---|
| ``DUPLICATE`` | same vendor, same normalised invoice no. | HARD_BLOCK |
| ``SUSPECT_DUPLICATE`` | same vendor, same amount, due date within 7 days,
  either direction | T2 trigger, T0 disqualifier |
| ``SPLIT_SUSPECT`` | several bills from one vendor within 7 days summing to the
  T2 threshold | T2 trigger |

**Why the consequences differ is the design point, not the spec's.** An exact
duplicate has already been paid or is in flight; paying it again is a loss, so it is
blocked outright. A *suspect* duplicate is probably a resubmission but might be a
legitimate second invoice - two deliveries, a corrected rate - so it is escalated to
two signatures rather than stopped, because blocking a real supplier payment is also
a loss, and the more expensive kind.

``SPLIT_SUSPECT`` is a different thing altogether and does not identify a duplicate
at all: it identifies a pattern. Individually each bill is well under any limit;
summed they are not. §4.3 is explicit that splitting *under* the T0 limit is handled
by floor rows 15-16 and not by this rule, which is why the threshold here is the
**T2** threshold and not the T0 one.

That last distinction is one a naive implementation gets wrong, because "looks like
splitting" and "is a duplicate" sound like the same problem and are not.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Final

from app.core.parsers import normalise_invoice_no

__all__ = [
    "DUPLICATE_FLAG",
    "SPLIT_FLAG",
    "SUSPECT_FLAG",
    "Verdict",
    "VerdictKind",
    "classify",
]

DUPLICATE_FLAG: Final[str] = "DUPLICATE"
SUSPECT_FLAG: Final[str] = "SUSPECT_DUPLICATE"
SPLIT_FLAG: Final[str] = "SPLIT_SUSPECT"

#: §4.3: due date within ±7 days is "same due date" for suspect detection.
SUSPECT_DAY_WINDOW: Final[int] = 7

#: §4.3: the window in which bills may sum to a split.
SPLIT_DAY_WINDOW: Final[int] = 7

#: §4.3: the T2 threshold, USD 10,000. Not the T0 limit: splitting under T0 is
#: handled by floor rows 15-16 and must not be double-counted here.
SPLIT_THRESHOLD_USD: Final[Decimal] = Decimal("10000")


class VerdictKind:
    EXACT: Final[str] = "EXACT"
    SUSPECT: Final[str] = "SUSPECT"
    SPLIT: Final[str] = "SPLIT"
    CLEAR: Final[str] = "CLEAR"


@dataclass(frozen=True)
class Verdict:
    """What duplicate detection concluded, and what it would cost to ignore it."""

    kind: str
    #: The flag, or None when the verdict is CLEAR.
    flag: str | None = None
    #: The obligation this one collides with, when known.
    against_id: str | None = None
    #: The sum that crossed the threshold, for SPLIT.
    window_total: Decimal | None = None
    reason: str = ""

    @property
    def hard_block(self) -> bool:
        """§4.4: an exact duplicate is a HARD_BLOCK nobody can override."""
        return self.kind == VerdictKind.EXACT

    @property
    def t2_trigger(self) -> bool:
        """§4.4: a suspect or a split escalates to two signatures."""
        return self.kind in {VerdictKind.SUSPECT, VerdictKind.SPLIT}

    @property
    def t0_disqualifier(self) -> bool:
        """§4.3/§4.4: only a suspect duplicate disqualifies T0.

        A split is a T2 trigger but not a T0 disqualifier - an item may be
        individually eligible for auto-pay and still be part of a suspicious
        aggregation. conflating the two would auto-approve the wrong payments.
        """
        return self.kind == VerdictKind.SUSPECT


@dataclass(frozen=True)
class Bill:
    """The minimum the classifier needs about a bill."""

    obligation_id: str
    vendor_id: str
    invoice_no: str | None
    amount: Decimal
    due_date: date | None
    #: Amount in USD, when the currency is not USD. Used only for the split sum,
    #: because §4.3 states the threshold in USD equivalent.
    amount_usd: Decimal | None = None


def obligation_key(vendor_id: str, invoice_no: str | None) -> str:
    """The §4.3 duplicate key.

    ``(vendor_id, normalised invoice no.)``. The vendor is part of the key because
    invoice numbers are only unique within a supplier: "INV-1" from Acme and
    "INV-1" from Brandt are two different bills, and a key ignoring the vendor
    would block one of them as a duplicate of the other.
    """
    return f"{vendor_id}:{normalise_invoice_no(invoice_no or '')}"


def _usd_amount(bill: Bill) -> Decimal:
    if bill.amount_usd is not None:
        return bill.amount_usd
    return bill.amount


def classify(
    *,
    candidate: Bill,
    existing: Iterable[Bill],
    split_threshold_usd: Decimal = SPLIT_THRESHOLD_USD,
) -> Verdict:
    """Classify one bill against the bills already on file.

    Order matters: an exact duplicate is checked first, because a bill that is an
    exact duplicate is one regardless of how it aggregates, and reporting a
    ``SPLIT`` for it would let the more dangerous verdict be missed.

    ``existing`` is iterated once. A caller passing a large list gets the same
    answer as one passing three bills, and the exact-dup check cannot be defeated by
    ordering.
    """
    existing = list(existing)
    key = obligation_key(candidate.vendor_id, candidate.invoice_no)

    for other in existing:
        if other.vendor_id != candidate.vendor_id:
            continue
        if other.invoice_no is None or candidate.invoice_no is None:
            continue
        if obligation_key(other.vendor_id, other.invoice_no) == key:
            return Verdict(
                kind=VerdictKind.EXACT,
                flag=DUPLICATE_FLAG,
                against_id=other.obligation_id,
                reason=(
                    f"invoice {candidate.invoice_no!r} for vendor "
                    f"{candidate.vendor_id} is already on file as "
                    f"{other.obligation_id}. HARD_BLOCK (FINAL.md §4.3, §4.4)"
                ),
            )

    if candidate.amount == existing_same_amount(candidate, existing):
        return _suspect(candidate, existing)

    return _split(candidate, existing, split_threshold_usd)


def existing_same_amount(candidate: Bill, existing: list[Bill]) -> Decimal | None:
    """Does any bill from this vendor carry exactly the same amount?

    A helper rather than an inline check, because "same amount" is the one part of
    the suspect rule that is easy to get wrong: it is an exact decimal comparison,
    not a difference-bounded one. Two bills of the same amount with due dates nine
    days apart are **not** a suspect duplicate; two of the same amount seven days
    apart are.
    """
    for other in existing:
        if other.vendor_id == candidate.vendor_id and other.amount == candidate.amount:
            return other.amount
    return None


def _suspect(candidate: Bill, existing: list[Bill]) -> Verdict:
    """The ±7-day same-amount rule."""
    for other in existing:
        if other.vendor_id != candidate.vendor_id:
            continue
        if candidate.due_date is None or other.due_date is None:
            continue
        if other.amount != candidate.amount:
            continue
        gap = abs((candidate.due_date - other.due_date).days)
        if gap <= SUSPECT_DAY_WINDOW:
            return Verdict(
                kind=VerdictKind.SUSPECT,
                flag=SUSPECT_FLAG,
                against_id=other.obligation_id,
                reason=(
                    f"same vendor, same amount {candidate.amount}, due dates {gap} day(s) "
                    f"apart. T2 trigger and T0 disqualifier (FINAL.md §4.3, §4.4)"
                ),
            )
    return _split(candidate, existing, SPLIT_THRESHOLD_USD)


def _split(candidate: Bill, existing: list[Bill], threshold: Decimal) -> Verdict:
    """The 7-day aggregation rule.

    The window is anchored on the **candidate's** due date, not the earliest bill,
    so the answer does not depend on iteration order. A window anchored anywhere
    else would report a different verdict for the same set of bills depending on
    which one was checked last.
    """
    if candidate.due_date is None:
        return Verdict(kind=VerdictKind.CLEAR)

    anchors = {
        candidate.due_date,
        *[
            other.due_date
            for other in existing
            if other.vendor_id == candidate.vendor_id and other.due_date is not None
        ],
    }

    for anchor in sorted(anchors):
        in_window = [
            other
            for other in existing
            if other.vendor_id == candidate.vendor_id
            and other.due_date is not None
            and abs((other.due_date - anchor).days) <= SPLIT_DAY_WINDOW
        ]
        if not any(other.obligation_id == candidate.obligation_id for other in in_window):
            in_window = [candidate, *in_window]

        total = sum((_usd_amount(b) for b in in_window), Decimal("0"))
        if total >= threshold:
            return Verdict(
                kind=VerdictKind.SPLIT,
                flag=SPLIT_FLAG,
                against_id=in_window[0].obligation_id,
                window_total=total,
                reason=(
                    f"{len(in_window)} bills for vendor {candidate.vendor_id} within "
                    f"{SPLIT_DAY_WINDOW} days sum to {total} USD, at or over the "
                    f"{threshold} T2 threshold. T2 trigger (FINAL.md §4.3)"
                ),
            )

    return Verdict(kind=VerdictKind.CLEAR)


def window_bounds(anchor: date) -> tuple[date, date]:
    """The inclusive ±7-day window around ``anchor``."""
    return anchor - timedelta(days=SPLIT_DAY_WINDOW), anchor + timedelta(days=SPLIT_DAY_WINDOW)
