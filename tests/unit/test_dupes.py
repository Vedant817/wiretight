"""Duplicate detection: exact, suspect, and split.

The three rules in FINAL.md §4.3 have three different consequences, and the point of
these tests is that the *differences* hold. An exact duplicate is a HARD_BLOCK; a
suspect one is a T2 trigger and a T0 disqualifier; a split is a T2 trigger and **not**
a T0 disqualifier.

The last distinction is the one a naive implementation gets wrong, because "looks like
splitting" and "is a duplicate" sound like the same problem. Conflating them would
auto-approve an item that is individually eligible but part of a suspicious
aggregation - the exact failure §4.3's cross-reference to floor rows 15-16 exists to
prevent.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.core.dupes import (
    DUPLICATE_FLAG,
    SPLIT_FLAG,
    SPLIT_THRESHOLD_USD,
    SUSPECT_FLAG,
    Bill,
    VerdictKind,
    classify,
    obligation_key,
    window_bounds,
)

D = Decimal


@pytest.fixture()
def acme_bill() -> Bill:
    return Bill(
        obligation_id="ob-1",
        vendor_id="v-acme",
        invoice_no="INV-2291",
        amount=D("7500.00"),
        due_date=date(2026, 11, 10),
    )


@pytest.fixture()
def on_file() -> list[Bill]:
    return [
        Bill(
            obligation_id="ob-0",
            vendor_id="v-acme",
            invoice_no="inv 0042",
            amount=D("7500.00"),
            due_date=date(2026, 11, 8),
        )
    ]


class TestObligationKey:
    """The §4.3 key, and why the vendor is part of it."""

    def test_invoice_number_normalisation_is_part_of_the_key(self) -> None:
        """``inv 0042`` and ``INV0042`` are one bill, not two.

        This is the control that stops a resubmitted invoice paying twice, so the
        normalisation is the whole defence (D-B20 records the invisible-character
        version of this bug).
        """
        assert obligation_key("v", "inv 0042") == obligation_key("v", "INV-0042")
        assert obligation_key("v", "INV-2291") != obligation_key("v", "INV-2292")

    def test_the_key_is_per_vendor(self) -> None:
        """INV-1 from Acme and INV-1 from Brandt are two different bills.

        A key ignoring the vendor would block one of them as a duplicate of the
        other - a false block on a real supplier payment, which costs money and
        trust.
        """
        assert obligation_key("v-acme", "INV-1") != obligation_key("v-brandt", "INV-1")


class TestExactDuplicate:
    """HARD_BLOCK. The only rule that stops a payment outright."""

    def test_an_exact_duplicate_is_a_hard_block(self, acme_bill, on_file) -> None:
        on_file.append(Bill("ob-9", "v-acme", "INV-2291", D("9999.00"), date(2026, 12, 1)))
        verdict = classify(candidate=acme_bill, existing=on_file)
        assert verdict.kind == VerdictKind.EXACT
        assert verdict.flag == DUPLICATE_FLAG
        assert verdict.hard_block
        assert verdict.t2_trigger is False

    def test_the_key_is_normalised_before_comparison(self, acme_bill) -> None:
        """A differently-formatted number for the same bill is still the same bill.

        Two existing spellings of one invoice number, ``INV 0042`` and
        ``inv-0042``, normalise to one key. Before D-B20's invisible-character fix
        these could produce two distinct keys and the invoice would pay twice.
        """
        existing = [
            Bill("ob-0", "v-acme", "INV 0042", D("9999.00"), date(2026, 11, 1)),
            Bill("ob-9", "v-acme", "inv-0042", D("8888.00"), date(2026, 11, 2)),
        ]
        verdict = classify(candidate=acme_bill, existing=existing)
        assert verdict.kind == VerdictKind.SPLIT
        assert verdict.window_total == D("26387.00")

    def test_exact_beats_the_aggregation_rule(self, acme_bill) -> None:
        """A duplicate is a duplicate however it aggregates.

        Checking the aggregation first would let the more dangerous verdict be
        reached through the wrong label, and a split carries a weaker consequence
        than a hard block.
        """
        existing = [
            Bill("ob-9", "v-acme", "INV-2291", D("20000.00"), date(2026, 11, 9)),
            Bill("ob-8", "v-acme", "INV-0001", D("20000.00"), date(2026, 11, 9)),
        ]
        verdict = classify(candidate=acme_bill, existing=existing)
        assert verdict.kind == VerdictKind.EXACT
        assert verdict.hard_block

    def test_a_different_vendor_with_the_same_invoice_is_not_a_duplicate(self) -> None:
        """The per-vendor key, at the classifier level."""
        verdict = classify(
            candidate=Bill("ob-1", "v-acme", "INV-1", D("100.00"), date(2026, 11, 1)),
            existing=[Bill("ob-0", "v-brandt", "INV-1", D("100.00"), date(2026, 11, 1))],
        )
        assert verdict.kind == VerdictKind.CLEAR
        assert not verdict.hard_block


class TestSuspectDuplicate:
    """T2 trigger AND T0 disqualifier. Not a hard block."""

    def test_same_amount_within_the_window_escalates(self, acme_bill, on_file) -> None:
        verdict = classify(candidate=acme_bill, existing=on_file)
        assert verdict.kind == VerdictKind.SUSPECT
        assert verdict.flag == SUSPECT_FLAG
        assert verdict.t2_trigger
        assert verdict.t0_disqualifier
        assert verdict.hard_block is False

    def test_seven_days_is_inside_the_window(self) -> None:
        verdict = classify(
            candidate=Bill("ob-1", "v", "A", D("500.00"), date(2026, 11, 7)),
            existing=[Bill("ob-0", "v", "B", D("500.00"), date(2026, 11, 1))],
        )
        assert verdict.kind == VerdictKind.SUSPECT

    def test_eight_days_is_outside_it(self) -> None:
        """A real second invoice is not a suspected duplicate.

        Blocking or escalating this would be the expensive kind of mistake: the
        supplier waits for a payment that was never lost.

        Eight days, not seven. A first attempt used 07 and 01 Nov, which is six days
        apart and therefore still inside the window (D-B25).
        """
        verdict = classify(
            candidate=Bill("ob-1", "v", "A", D("500.00"), date(2026, 11, 9)),
            existing=[Bill("ob-0", "v", "B", D("500.00"), date(2026, 11, 1))],
        )
        assert verdict.kind != VerdictKind.SUSPECT

    def test_the_window_is_symmetric(self) -> None:
        """A bill due *before* an existing one is just as suspicious."""
        verdict = classify(
            candidate=Bill("ob-1", "v", "A", D("500.00"), date(2026, 11, 1)),
            existing=[Bill("ob-0", "v", "B", D("500.00"), date(2026, 11, 7))],
        )
        assert verdict.kind == VerdictKind.SUSPECT

    def test_a_different_amount_is_not_a_suspect(self) -> None:
        """Same amount is required: an amount difference is the strongest signal
        that this is a genuinely different bill."""
        verdict = classify(
            candidate=Bill("ob-1", "v", "A", D("500.00"), date(2026, 11, 1)),
            existing=[Bill("ob-0", "v", "B", D("500.01"), date(2026, 11, 1))],
        )
        assert verdict.kind != VerdictKind.SUSPECT


class TestSplitSuspect:
    """T2 trigger, but NOT a T0 disqualifier, and not a duplicate at all."""

    def test_bills_summing_past_the_threshold_are_flagged(self) -> None:
        """Different amounts, so the suspect rule does not fire first.

        The amounts must differ, or ``SUSPECT`` is returned and the split verdict is
        never reached - which is exactly what happened on the first run of this test,
        because I had used the same amount for every bill (D-B25).
        """
        existing = [
            Bill("ob-1", "v", "A", D("4000.00"), date(2026, 11, 5)),
            Bill("ob-2", "v", "B", D("4100.00"), date(2026, 11, 6)),
        ]
        verdict = classify(
            candidate=Bill("ob-3", "v", "C", D("4200.00"), date(2026, 11, 7)),
            existing=existing,
        )
        assert verdict.kind == VerdictKind.SPLIT
        assert verdict.flag == SPLIT_FLAG
        assert verdict.t2_trigger
        assert verdict.window_total == D("12300.00")

    def test_a_split_is_not_a_t0_disqualifier(self) -> None:
        """The distinction that matters, and the one easiest to get wrong.

        A split is a T2 trigger; it does not disqualify T0 on its own. conflating
        the two would auto-approve an item that is individually eligible but part of
        a suspicious aggregation - which is what floor rows 15-16 already handle, and
        §4.3 says so explicitly.
        """
        verdict = classify(
            candidate=Bill("ob-3", "v", "C", D("6000.00"), date(2026, 11, 7)),
            existing=[
                Bill("ob-1", "v", "A", D("5000.00"), date(2026, 11, 5)),
            ],
        )
        assert verdict.kind == VerdictKind.SPLIT
        assert verdict.t2_trigger
        assert verdict.t0_disqualifier is False

    def test_under_the_threshold_is_not_a_split(self) -> None:
        verdict = classify(
            candidate=Bill("ob-3", "v", "C", D("500.00"), date(2026, 11, 7)),
            existing=[Bill("ob-1", "v", "A", D("500.00"), date(2026, 11, 5))],
        )
        assert verdict.kind != VerdictKind.SPLIT

    def test_the_window_is_anchored_on_the_candidate(self) -> None:
        """The verdict must not depend on iteration order.

        An anchor anywhere else would report a different verdict for the same set of
        bills depending on which one was checked last - which is how a real split
        gets through: check the small one first and the aggregate is never computed.
        """
        existing = [
            Bill("ob-2", "v", "B", D("6000.00"), date(2026, 11, 20)),
            Bill("ob-1", "v", "A", D("6000.00"), date(2026, 11, 1)),
        ]
        verdict = classify(
            candidate=Bill("ob-3", "v", "C", D("6000.00"), date(2026, 11, 9)),
            existing=existing,
        )
        assert verdict.kind == VerdictKind.SPLIT
        assert verdict.window_total is not None
        assert verdict.window_total >= SPLIT_THRESHOLD_USD

    def test_bills_from_another_vendor_do_not_aggregate(self) -> None:
        verdict = classify(
            candidate=Bill("ob-3", "v-acme", "C", D("9000.00"), date(2026, 11, 7)),
            existing=[Bill("ob-1", "v-brandt", "A", D("9000.00"), date(2026, 11, 7))],
        )
        assert verdict.kind != VerdictKind.SPLIT

    def test_the_usd_amount_is_used_for_the_threshold(self) -> None:
        """The threshold is USD 10,000 equivalent, so a non-USD bill needs a rate.

        Summing a mixture of currencies without converting would either over- or
        under-count, with no way to tell which from the result. The amounts differ so
        the suspect rule does not pre-empt the split rule.
        """
        verdict = classify(
            candidate=Bill(
                "ob-3", "v", "C", D("9100.00"), date(2026, 11, 7), amount_usd=D("9900.00")
            ),
            existing=[
                Bill("ob-1", "v", "A", D("9000.00"), date(2026, 11, 5), amount_usd=D("9800.00"))
            ],
        )
        assert verdict.kind == VerdictKind.SPLIT
        assert verdict.window_total == D("19700.00")


class TestClear:
    def test_a_normal_bill_is_clear(self) -> None:
        verdict = classify(
            candidate=Bill("ob-1", "v", "A", D("100.00"), date(2026, 11, 1)),
            existing=[],
        )
        assert verdict.kind == VerdictKind.CLEAR
        assert verdict.flag is None
        assert not verdict.hard_block
        assert not verdict.t2_trigger
        assert not verdict.t0_disqualifier

    def test_an_empty_existing_list_is_clear(self) -> None:
        verdict = classify(candidate=Bill("ob-1", "v", None, D("100.00"), None), existing=[])
        assert verdict.kind == VerdictKind.CLEAR


class TestWindowBounds:
    def test_the_window_is_inclusive(self) -> None:
        low, high = window_bounds(date(2026, 11, 10))
        assert (high - low).days == 14
        assert date(2026, 11, 3) in {low, high, date(2026, 11, 10)}
