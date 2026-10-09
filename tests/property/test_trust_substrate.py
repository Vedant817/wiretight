"""Property tests for the trust substrate (FINAL.md §14 b).

§14 (b) names three properties as acceptance for this milestone:

* the state machine never regresses past a terminal state;
* ``failure_type`` is never nulled once captured;
* the ledger sums to zero.

They are written as properties rather than examples because that is what they
are. A handful of hand-picked cases can only show that the chosen cases pass; the
claim being made is that *no* input violates the rule, and only generating inputs
says anything about that.

The first run of this file found two things, both recorded (D-B23):

* an assertion of mine was **backwards**. I had asserted that a terminal
  ``awx_status`` makes ``is_regression`` false. Observing ``FAILED`` after
  ``CANCELLED`` *is* a backwards move, and the code correctly flags it while
  still holding the state. The two are separate claims and are now tested
  separately.
* a real defect: ``failure_type: ""`` was stored as a non-NULL value, creating a
  third state between "no failure recorded" and "this failure was recorded".

A third lesson from the same run is in ``money_at`` below: the amounts must be
drawn at the currency's own exponent. Drawing every currency at two decimal
places produced a ``UnbalancedError`` - in the test, not the code.

Hypothesis runs with ``derandomize=True`` so a failure is reproducible from its
database rather than from luck.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from app.core import db as db_module
from app.core import ledger
from app.core import statemachine as sm
from app.money import CURRENCY_EXPONENT, parse_money, to_money_string

#: Every status the poller can observe, plus ones we do not know about. The
#: unknown ones are the interesting half: §4.16 requires them to become incidents
#: rather than silently holding the state forever.
sorted_statuses = sorted(sm.AWX_STATUSES)
AWX_STATUS = st.sampled_from([*sorted_statuses, "UNKNOWN_STATUS", "", "settled", "Sent"])

WT_STATE = st.sampled_from(sorted(sm.WT_STATES))

FAILURE_TYPE = st.one_of(
    st.sampled_from(
        ["ACCOUNT_CLOSED", "ACCOUNT_UNDER_RESTRICTION", "WATCHLIST_HIT", "OTHER", None, ""]
    ),
    st.text(max_size=20),
)

FAILURE_REASON = st.one_of(
    st.sampled_from(["simulation", "90701", "boom", "", None]), st.text(max_size=20)
)

ACCOUNT = st.from_regex(r"[A-Za-z][A-Za-z0-9 :-]{0,31}", fullmatch=True)
RUN_ID = st.from_regex(r"[a-z0-9]{1,8}", fullmatch=True)
CURRENCY = st.sampled_from(sorted(CURRENCY_EXPONENT))


def money_at(currency: str) -> st.SearchStrategy[str]:
    """A decimal string that ``currency`` can express exactly.

    Drawn at ``places=2`` for every currency, which is what a first draft did,
    produces the ``UnbalancedError`` this file exists to avoid - but in the test,
    not the code. UGX has no minor unit, so four legs of ``0.01`` each quantize
    to ``0`` while their sum quantizes to ``1``, and the posting fails to balance
    through no fault of the ledger.

    So the exponent comes from the currency. That is also the only regime the
    system can actually see, because ``parse_amount`` refuses an input with more
    precision than the currency allows.
    """
    exponent = CURRENCY_EXPONENT[currency]
    step = Decimal(1).scaleb(-exponent)
    return st.decimals(
        min_value=step,
        max_value=Decimal("1000000"),
        places=exponent,
        allow_nan=False,
        allow_infinity=False,
    ).map(lambda d: to_money_string(d, currency))


@st.composite
def a_balanced_posting(draw: st.DrawFn) -> list[ledger.Leg]:
    """Draw a posting whose debits and credits cancel, in any currency.

    One account pays, the rest receive. Each amount is already at the currency's
    exponent, so no rounding happens inside the ledger.
    """
    currency = draw(CURRENCY)
    count = draw(st.integers(min_value=1, max_value=4))

    amounts = [draw(money_at(currency)) for _ in range(count)]
    total = Decimal("0")
    for amount in amounts:
        total += parse_money(amount)

    payer = draw(ACCOUNT)
    legs = [ledger.Leg(account=payer, currency=currency, debit=to_money_string(total, currency))]
    for amount in amounts:
        legs.append(ledger.Leg(account=draw(ACCOUNT), currency=currency, credit=amount))
    return legs


# --------------------------------------------------------------------------
# Property 1: no regression past a terminal state
# --------------------------------------------------------------------------


@given(current=st.sampled_from(sorted(sm.TERMINAL_AWX)), observed=AWX_STATUS)
@settings(max_examples=200, derandomize=True)
def test_a_terminal_awx_status_never_moves(current: str, observed: str) -> None:
    """§4.11's regression rule, stated as a property.

    A status Airwallex reports as terminal is one we treat as final regardless of
    what a later poll says. The poller retries; the state must not rewind.

    Corrected on its first run (D-B23): the original version also asserted
    ``not is_regression(...)``, which is the **opposite** of the truth. A terminal
    state going backwards is a regression and *should* be flagged. Splitting that
    into its own test below is what makes both claims checkable.
    """
    assert sm.transfer_next_awx(current, observed) == current


@given(current=st.sampled_from(sorted(sm.TERMINAL_AWX)), observed=AWX_STATUS)
@settings(max_examples=300, derandomize=True)
def test_every_backwards_move_from_a_terminal_state_is_flagged(current: str, observed: str) -> None:
    """The flag and the state are two claims, so test both separately.

    ``is_regression`` is what the audit entry and the incident record read. A
    genuine backwards move that went unflagged would leave no trace at all except
    a status that quietly stayed put.
    """
    assume(observed != current)
    assume(observed in sm.AWX_STATUSES)
    assert sm.is_regression(current, observed)


@given(current=WT_STATE, observed=AWX_STATUS)
@settings(max_examples=300, derandomize=True)
def test_a_terminal_wt_state_never_regresses(current: str, observed: str) -> None:
    """The Wiretight overlay: once terminal, always the same state.

    ``FINAL`` is the documented exception - a late ``FAILED`` after settlement is a
    real event (§4.11 group C) and reopens it. Every other terminal state has no
    path back, which is what makes the money state calculable at all.
    """
    assume(sm.is_terminal_wt(current))

    result = sm.wt_next(current, awx_status=observed)
    if current == "FINAL" and observed == "FAILED":
        assert result == "REOPENED"
    else:
        assert result == current, f"{current} regressed to {result} on {observed}"


@given(current=WT_STATE, observed=AWX_STATUS)
@settings(max_examples=300, derandomize=True)
def test_an_unknown_status_is_an_incident(current: str, observed: str) -> None:
    """An unlisted status is an incident, not a silent no-op.

    §4.16 requires an unknown ``failure_type`` to take the DEFAULT handler; the
    same reasoning extends to an unknown status. Continuing silently would let an
    Airwallex API change strand a transfer with nothing reported.
    """
    assume(observed not in sm.AWX_STATUSES)

    result = sm.apply_transfer_observation(
        awx_status=observed,
        failure_type=None,
        failure_reason=None,
        current_awx_status="PENDING",
        wt_state=current,
    )
    assert result.unknown_status_incident


# --------------------------------------------------------------------------
# Property 2: failure_type is never nulled
# --------------------------------------------------------------------------


@given(
    first_type=FAILURE_TYPE,
    second_type=FAILURE_TYPE,
    first_reason=FAILURE_REASON,
    second_reason=FAILURE_REASON,
)
@settings(max_examples=400, derandomize=True)
def test_failure_type_and_reason_are_never_nulled(
    first_type: str | None,
    second_type: str | None,
    first_reason: str | None,
    second_reason: str | None,
) -> None:
    """§4.11's "first sight wins", stated as a property.

    The poller observes a transfer many times. Whichever informative value arrives
    first must survive: overwriting it with a later, vaguer one erases the only
    evidence of *why* a payment stopped.

    This is the dangerous direction specifically. Accepting a second vaguer value
    is how ``ACCOUNT_CLOSED`` becomes ``OTHER: simulation`` over a weekend.
    """
    after_first = sm.apply_transfer_observation(
        awx_status="FAILED", failure_type=first_type, failure_reason=first_reason
    )
    after_second = sm.apply_transfer_observation(
        awx_status="FAILED",
        failure_type=second_type,
        failure_reason=second_reason,
        current_awx_status=after_first.awx_status,
        current_failure_type=after_first.failure_type,
        current_failure_reason=after_first.failure_reason,
    )

    if after_first.failure_type is not None:
        assert after_second.failure_type == after_first.failure_type
    if after_first.failure_reason is not None:
        assert after_second.failure_reason == after_first.failure_reason


@given(observations=st.lists(st.tuples(FAILURE_TYPE, FAILURE_REASON), max_size=12))
@settings(max_examples=250, derandomize=True)
def test_an_arbitrary_sequence_preserves_the_first(
    observations: list[tuple[str | None, str | None]],
) -> None:
    """The same property over a sequence rather than two events.

    The expected value is the first *present* one, where present means not None
    and not blank. That last part is the D-B23 fix: before it, ``""`` survived as
    a stored value and the test correctly said that should not happen.
    """
    type_seen: str | None = None
    reason_seen: str | None = None

    for failure_type, failure_reason in observations:
        result = sm.apply_transfer_observation(
            awx_status="FAILED",
            failure_type=failure_type,
            failure_reason=failure_reason,
            current_failure_type=type_seen,
            current_failure_reason=reason_seen,
        )
        type_seen = result.failure_type
        reason_seen = result.failure_reason

    # "First present" means first non-blank, because a blank is absent (D-B23).
    # The stored value is the *stripped* form, so ``"0 "`` is kept as ``"0"``.
    expected_type = next((t for t, _ in observations if (t or "").strip()), None)
    expected_reason = next((r for _, r in observations if (r or "").strip()), None)
    assert type_seen == (expected_type.strip() if expected_type else None)
    assert reason_seen == (expected_reason.strip() if expected_reason else None)


@given(blank=st.sampled_from(["", " ", "\t", "\n", "   ", "\r"]))
@settings(max_examples=50, derandomize=True)
def test_a_blank_failure_type_is_absent_not_present(blank: str) -> None:
    """A blank is absent evidence, which is the same as no evidence.

    Found by property test, not by reading (D-B23). ``failure_type: ""`` used to be
    stored verbatim, so the column held a third value between NULL and a real
    type: truthy to ``is not None``, yet ``playbook_for("")`` reports an unknown
    type. A code path reading the column concluded a failure *was* recorded.
    """
    result = sm.apply_transfer_observation(
        awx_status="FAILED", failure_type=blank, failure_reason=blank
    )
    assert result.failure_type is None
    assert result.failure_reason is None


# --------------------------------------------------------------------------
# Property 3: the ledger sums to zero
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def db_root(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    """A module-scoped directory, so Hypothesis's health check is satisfied.

    Each example still gets its own database file; only the directory is shared,
    which is the part the health check objects to. Sharing a *file* would leak
    balances between examples and make the property untestable.
    """
    yield tmp_path_factory.mktemp("ledger-properties")


_counter: Iterator[int] = itertools.count(1)


def _fresh_database(db_root: Path, run_id: str) -> tuple[db_module.Database, str]:
    """A database containing one run row, so journal rows can reference it."""
    database = db_module.Database(db_root / f"prop-{next(_counter)}.sqlite")
    conn = database.connection()
    conn.execute(
        "INSERT INTO run (id, started_at, shadow, state) VALUES (?, 't', 0, 'OPEN')",
        (run_id,),
    )
    return database, conn


@given(posting=a_balanced_posting(), run_id=RUN_ID)
@settings(max_examples=200, derandomize=True)
def test_a_balanced_posting_leaves_the_ledger_at_zero(
    posting: list[ledger.Leg], run_id: str, db_root: Path
) -> None:
    """The ledger's invariant, over arbitrary postings.

    Generating the postings is the point: a hand-written example is balanced by
    construction, so testing it only proves the writer can subtract. A generated
    posting is balanced by the same arithmetic the test asserts, which is a real
    check that nothing in the rounding path drifts.

    ``ROUND_HALF_EVEN`` is the rounding mode, so an amount that cannot be
    expressed at the currency's exponent either rounds or is refused - and drift
    in either direction stops the ledger summing to zero.
    """
    database, conn = _fresh_database(db_root, run_id)
    try:
        first = ledger.post(conn, run_id=run_id, legs=posting)
        assert first >= 1
        # No exception means balanced, per currency.
        ledger.assert_ledger_balances(conn)

        net = ledger.balances(conn)
        for currency, totals in net.items():
            assert totals["debit"] == totals["credit"], f"{currency} does not balance: {totals}"
    finally:
        database.close()


@given(postings=st.lists(a_balanced_posting(), min_size=1, max_size=3))
@settings(max_examples=120, derandomize=True)
def test_many_postings_still_sum_to_zero(postings: list[list[ledger.Leg]], db_root: Path) -> None:
    """Sequence of postings: the invariant holds cumulatively, not just once.

    This is the one that matters in production, where every payment adds legs and
    a rounding error would accumulate rather than cancel.
    """
    database, conn = _fresh_database(db_root, "r")
    try:
        for posting in postings:
            ledger.post(conn, run_id="r", legs=posting)
        ledger.assert_ledger_balances(conn)
    finally:
        database.close()


@given(posting=a_balanced_posting())
@settings(max_examples=100, derandomize=True)
def test_an_unbalanced_posting_is_refused(posting: list[ledger.Leg], db_root: Path) -> None:
    """The other half: the guard actually refuses, it does not just not-trigger.

    A test that only proves balanced postings pass is worthless if the check is
    never reached. The tamper shifts a credit down by one minor unit, which is
    unbalanced in every currency by construction - not merely "some change", which
    a first draft got wrong when a drawn amount happened to land on the new value.
    """
    database, conn = _fresh_database(db_root, "r")
    try:
        credit = next(leg for leg in posting if leg.credit is not None)
        one_unit = Decimal(1).scaleb(-CURRENCY_EXPONENT[credit.currency])
        reduced = parse_money(credit.credit) - one_unit
        assume(reduced >= 0)

        tampered = list(posting)
        tampered[tampered.index(credit)] = ledger.Leg(
            account=credit.account,
            currency=credit.currency,
            credit=to_money_string(reduced, credit.currency),
        )

        with pytest.raises(ledger.UnbalancedError):
            ledger.post(conn, run_id="r", legs=tampered)

        assert conn.execute("SELECT count(*) FROM journal_line").fetchone()[0] == 0
    finally:
        database.close()
